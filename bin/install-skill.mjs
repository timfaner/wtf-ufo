#!/usr/bin/env node

import { cp, mkdir, readFile, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..");
const skillName = "wtf-ufo";
const source = path.join(repoRoot, "skills", skillName);

function parseArgs(argv) {
  const args = { target: path.join(homedir(), ".codex", "skills", skillName), force: true };
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (item === "--target") {
      args.target = path.resolve(argv[index + 1] || "");
      index += 1;
    } else if (item === "--no-force") {
      args.force = false;
    } else if (item === "--help" || item === "-h") {
      args.help = true;
    } else {
      throw new Error(`Unknown argument: ${item}`);
    }
  }
  return args;
}

function usage() {
  return [
    "Install the wtf-ufo Codex skill.",
    "",
    "Usage:",
    "  npx --yes github:timfaner/wtf-ufo",
    "  npx --yes github:timfaner/wtf-ufo -- --target ~/.codex/skills/wtf-ufo",
    "",
    "Options:",
    "  --target <path>  Install target directory. Defaults to ~/.codex/skills/wtf-ufo",
    "  --no-force       Refuse to overwrite an existing target directory",
    "  -h, --help       Show this help",
  ].join("\n");
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usage());
    return;
  }

  if (!existsSync(path.join(source, "SKILL.md"))) {
    throw new Error(`Missing skill source: ${source}`);
  }

  if (existsSync(args.target)) {
    if (!args.force) {
      throw new Error(`Target already exists: ${args.target}`);
    }
    await rm(args.target, { recursive: true, force: true });
  }

  await mkdir(path.dirname(args.target), { recursive: true });
  await cp(source, args.target, { recursive: true });

  const skill = await readFile(path.join(args.target, "SKILL.md"), "utf8");
  const nameLine = skill.split("\n").find((line) => line.startsWith("name:")) || `name: ${skillName}`;

  console.log(`Installed ${nameLine.replace("name:", "").trim()} skill`);
  console.log(`Target: ${args.target}`);
  console.log("");
  console.log("Restart Codex if the skill list is already loaded in your session.");
}

main().catch((error) => {
  console.error(`wtf-ufo install failed: ${error.message}`);
  process.exit(1);
});
