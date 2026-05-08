#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const root = path.resolve(new URL("..", import.meta.url).pathname);
const recordsPath = path.join(root, "data/manifest/records.jsonl");
const targetKinds = new Set((process.env.KINDS || "PDF,IMG").split(",").map((item) => item.trim().toUpperCase()));
const limit = Number.parseInt(process.env.LIMIT || "0", 10);

function parseJsonl(text) {
  return text
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function installChunkWriter(page) {
  await page.exposeFunction("__ufoStartWrite", async (relativePath) => {
    const outputPath = path.join(root, relativePath);
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await fs.writeFile(outputPath, Buffer.alloc(0));
  });
  await page.exposeFunction("__ufoAppendChunk", async (relativePath, base64) => {
    const outputPath = path.join(root, relativePath);
    await fs.appendFile(outputPath, Buffer.from(base64, "base64"));
  });
}

async function downloadWithPageFetch(page, record) {
  return await page.evaluate(async ({ url, localPath }) => {
    function bytesToBase64(bytes) {
      let binary = "";
      const chunkSize = 0x8000;
      for (let offset = 0; offset < bytes.length; offset += chunkSize) {
        const chunk = bytes.subarray(offset, offset + chunkSize);
        binary += String.fromCharCode(...chunk);
      }
      return btoa(binary);
    }

    const response = await fetch(url, { credentials: "include" });
    const contentType = response.headers.get("content-type") || "";
    if (!response.ok || !response.body) {
      return { ok: response.ok, status: response.status, contentType, bytes: 0 };
    }

    await window.__ufoStartWrite(localPath);
    const reader = response.body.getReader();
    let total = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      await window.__ufoAppendChunk(localPath, bytesToBase64(value));
    }
    return { ok: true, status: response.status, contentType, bytes: total };
  }, { url: record.source_url, localPath: record.local_path });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const allRecords = parseJsonl(await fs.readFile(recordsPath, "utf8"));
  let records = allRecords.filter((record) => targetKinds.has(record.kind) && record.source_url && record.local_path);
  if (limit > 0) records = records.slice(0, limit);

  const browser = await chromium.launch({
    headless: process.env.HEADLESS !== "false",
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
  });
  const page = await browser.newPage({
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
  });
  await installChunkWriter(page);
  await page.goto("https://www.war.gov/UFO/", { waitUntil: "networkidle" });

  const results = [];
  for (const record of records) {
    const outputPath = path.join(root, record.local_path);
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    if (await exists(outputPath)) {
      const stat = await fs.stat(outputPath);
      results.push({ id: record.id, status: "exists", bytes: stat.size, path: record.local_path });
      console.log(`exists ${record.id} ${stat.size} ${record.filename}`);
      continue;
    }

    let result;
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      try {
        result = await downloadWithPageFetch(page, record);
        break;
      } catch (error) {
        if (attempt === 3) {
          result = { ok: false, status: "fetch_exception", contentType: "", bytes: 0, error: String(error) };
          break;
        }
        console.log(`retry ${record.id} attempt=${attempt} ${record.filename}`);
        await sleep(1500 * attempt);
        await page.goto("https://www.war.gov/UFO/", { waitUntil: "domcontentloaded", timeout: 60000 });
      }
    }

    if (!result.ok) {
      results.push({
        id: record.id,
        status: "error",
        http_status: result.status,
        content_type: result.contentType,
        url: record.source_url,
        error: result.error || "",
      });
      console.log(`error ${record.id} ${result.status} ${record.filename}`);
      continue;
    }

    results.push({ id: record.id, status: "downloaded", bytes: result.bytes, path: record.local_path, content_type: result.contentType });
    console.log(`downloaded ${record.id} ${result.bytes} ${record.filename}`);
  }

  await browser.close();
  await fs.writeFile(
    path.join(root, "data/manifest/download_results.json"),
    JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2),
  );
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
