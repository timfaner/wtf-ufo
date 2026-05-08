#!/usr/bin/env python3
"""Build a self-contained interactive HTML view for the knowledge graph."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "data/graph/knowledge_graph.json"
OUT_PATH = ROOT / "data/graph/knowledge_graph_view.html"


def clamp_text(value: str, limit: int = 180) -> str:
    value = " ".join(str(value or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "..."


def build_summary(graph: dict) -> dict:
    nodes = graph["nodes"]
    edges = graph["edges"]
    node_by_id = {node["id"]: node for node in nodes}

    degree = Counter()
    relation_counts = Counter(edge["relation"] for edge in edges)
    type_counts = Counter(node["type"] for node in nodes)
    agency_counts = Counter(
        node.get("agency") for node in nodes if node["type"] == "record" and node.get("agency")
    )

    event_records = defaultdict(set)
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
        source = node_by_id.get(edge["source"])
        target = node_by_id.get(edge["target"])
        if edge["relation"] == "supported_by" and source and target:
            if source["type"] == "event" and target["type"] == "record":
                event_records[source["id"]].add(target["id"])

    top_nodes = []
    for node_id, count in degree.most_common(18):
        node = node_by_id[node_id]
        top_nodes.append(
            {
                "id": node_id,
                "type": node["type"],
                "label": node["label"],
                "degree": count,
            }
        )

    top_events = []
    for event_id, record_ids in sorted(
        event_records.items(), key=lambda item: len(item[1]), reverse=True
    )[:10]:
        node = node_by_id[event_id]
        top_events.append(
            {
                "id": event_id,
                "label": node["label"].replace("|", " / "),
                "record_count": len(record_ids),
            }
        )

    records = [node for node in nodes if node["type"] == "record"]
    total_final_text = sum(int(node.get("final_text_chars") or 0) for node in records)
    total_images = sum(int(node.get("image_count") or 0) for node in records)

    return {
        "metadata": graph.get("metadata", {}),
        "type_counts": dict(type_counts),
        "relation_counts": dict(relation_counts),
        "agency_counts": dict(agency_counts),
        "top_nodes": top_nodes,
        "top_events": top_events,
        "total_final_text": total_final_text,
        "total_images": total_images,
    }


def render_html(graph: dict, summary: dict) -> str:
    graph_json = json.dumps(graph, ensure_ascii=False, separators=(",", ":"))
    summary_json = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    title = "UFO/UAP Knowledge Graph"
    generated_note = escape(
        f"{summary['metadata'].get('node_count', len(graph['nodes']))} nodes, "
        f"{summary['metadata'].get('edge_count', len(graph['edges']))} edges"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101113;
      --panel: #17191d;
      --panel-2: #1e2227;
      --ink: #f4efe3;
      --muted: #b6b0a2;
      --line: rgba(244, 239, 227, 0.13);
      --line-strong: rgba(244, 239, 227, 0.25);
      --release: #f0d46b;
      --record: #7bc8ff;
      --event: #ff8e63;
      --agency: #9fe27d;
      --date: #b79cff;
      --location: #59dec7;
      --pairing: #ff78ac;
      --shadow: rgba(0, 0, 0, 0.32);
    }}

    * {{ box-sizing: border-box; }}

    html,
    body {{
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      background:
        radial-gradient(circle at 28% 18%, rgba(89, 222, 199, 0.14), transparent 34%),
        linear-gradient(145deg, #101113 0%, #141213 48%, #0e1110 100%);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}

    button,
    input,
    select {{
      font: inherit;
    }}

    button {{
      border: 1px solid var(--line);
      background: rgba(244, 239, 227, 0.07);
      color: var(--ink);
      border-radius: 7px;
      padding: 8px 10px;
      cursor: pointer;
      transition: background 140ms ease, border-color 140ms ease, transform 140ms ease;
    }}

    button:hover {{
      background: rgba(244, 239, 227, 0.12);
      border-color: var(--line-strong);
      transform: translateY(-1px);
    }}

    .app {{
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr) 360px;
      width: 100vw;
      height: 100vh;
      min-height: 640px;
    }}

    .sidebar,
    .inspector {{
      position: relative;
      z-index: 3;
      min-width: 0;
      overflow: auto;
      border-color: var(--line);
      background: rgba(23, 25, 29, 0.91);
      backdrop-filter: blur(18px);
      box-shadow: 0 18px 48px var(--shadow);
    }}

    .sidebar {{
      border-right: 1px solid var(--line);
      padding: 22px 18px 18px;
    }}

    .inspector {{
      border-left: 1px solid var(--line);
      padding: 20px 18px 18px;
    }}

    .brand {{
      display: grid;
      gap: 8px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--line);
    }}

    .brand h1 {{
      margin: 0;
      font-size: 27px;
      line-height: 1.05;
      font-weight: 720;
      letter-spacing: 0;
    }}

    .brand p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 16px 0;
    }}

    .stat {{
      border: 1px solid var(--line);
      background: rgba(244, 239, 227, 0.055);
      border-radius: 8px;
      padding: 10px;
      min-width: 0;
    }}

    .stat strong {{
      display: block;
      font-size: 22px;
      line-height: 1;
      font-weight: 760;
    }}

    .stat span {{
      display: block;
      margin-top: 6px;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
    }}

    .section {{
      border-top: 1px solid var(--line);
      padding-top: 15px;
      margin-top: 15px;
    }}

    .section h2 {{
      margin: 0 0 10px;
      color: var(--ink);
      font-size: 12px;
      line-height: 1;
      font-weight: 720;
      text-transform: uppercase;
    }}

    .search {{
      width: 100%;
      height: 40px;
      border: 1px solid var(--line);
      border-radius: 7px;
      outline: none;
      padding: 0 12px;
      background: rgba(0, 0, 0, 0.2);
      color: var(--ink);
    }}

    .search:focus {{
      border-color: rgba(123, 200, 255, 0.58);
      box-shadow: 0 0 0 3px rgba(123, 200, 255, 0.13);
    }}

    .toggle-list {{
      display: grid;
      gap: 7px;
    }}

    .toggle {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 32px;
      gap: 10px;
      color: var(--muted);
      font-size: 13px;
      cursor: pointer;
      user-select: none;
    }}

    .toggle-left {{
      display: flex;
      align-items: center;
      min-width: 0;
      gap: 8px;
    }}

    .toggle input {{
      accent-color: var(--record);
      margin: 0;
    }}

    .dot {{
      width: 11px;
      height: 11px;
      flex: 0 0 auto;
      border-radius: 50%;
      box-shadow: 0 0 0 3px rgba(244, 239, 227, 0.06);
    }}

    .count {{
      color: rgba(244, 239, 227, 0.62);
      font-variant-numeric: tabular-nums;
    }}

    .actions {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }}

    .range-row {{
      display: grid;
      gap: 7px;
      color: var(--muted);
      font-size: 13px;
    }}

    input[type="range"] {{
      width: 100%;
      accent-color: var(--event);
    }}

    .canvas-wrap {{
      position: relative;
      min-width: 0;
      min-height: 0;
    }}

    #graphCanvas {{
      display: block;
      width: 100%;
      height: 100%;
      cursor: grab;
    }}

    #graphCanvas.dragging {{
      cursor: grabbing;
    }}

    .hud {{
      position: absolute;
      top: 18px;
      left: 18px;
      right: 18px;
      z-index: 2;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      pointer-events: none;
    }}

    .hud-card {{
      max-width: 580px;
      border: 1px solid var(--line);
      background: rgba(16, 17, 19, 0.68);
      border-radius: 8px;
      padding: 12px 14px;
      backdrop-filter: blur(14px);
      pointer-events: auto;
    }}

    .hud-title {{
      margin: 0 0 6px;
      font-size: 13px;
      font-weight: 720;
    }}

    .hud-copy {{
      margin: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}

    .zoom-pill {{
      display: flex;
      gap: 6px;
      pointer-events: auto;
    }}

    .zoom-pill button {{
      width: 34px;
      height: 34px;
      padding: 0;
    }}

    .tooltip {{
      position: fixed;
      z-index: 5;
      max-width: 300px;
      pointer-events: none;
      border: 1px solid var(--line-strong);
      background: rgba(16, 17, 19, 0.94);
      border-radius: 8px;
      padding: 10px 11px;
      box-shadow: 0 16px 44px var(--shadow);
      opacity: 0;
      transform: translate(10px, 10px);
      transition: opacity 100ms ease;
    }}

    .tooltip.visible {{
      opacity: 1;
    }}

    .tooltip strong {{
      display: block;
      font-size: 13px;
      line-height: 1.25;
    }}

    .tooltip span {{
      display: block;
      margin-top: 5px;
      color: var(--muted);
      font-size: 12px;
    }}

    .panel-title {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }}

    .panel-title h2 {{
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
    }}

    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 5px 9px;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .detail-name {{
      margin: 0;
      font-size: 19px;
      line-height: 1.22;
      font-weight: 720;
      overflow-wrap: anywhere;
    }}

    .detail-meta {{
      margin: 9px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }}

    .kv {{
      display: grid;
      gap: 8px;
      margin-top: 14px;
    }}

    .kv-row {{
      display: grid;
      grid-template-columns: 104px minmax(0, 1fr);
      gap: 10px;
      border-top: 1px solid var(--line);
      padding-top: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }}

    .kv-row strong {{
      color: rgba(244, 239, 227, 0.76);
      font-weight: 650;
    }}

    .kv-row a {{
      color: var(--record);
      text-decoration: none;
      overflow-wrap: anywhere;
    }}

    .summary-text {{
      margin: 14px 0 0;
      color: rgba(244, 239, 227, 0.82);
      font-size: 13px;
      line-height: 1.55;
    }}

    .list {{
      display: grid;
      gap: 8px;
    }}

    .list-item {{
      display: grid;
      gap: 4px;
      border: 1px solid var(--line);
      background: rgba(244, 239, 227, 0.045);
      border-radius: 8px;
      padding: 9px 10px;
      cursor: pointer;
      min-width: 0;
    }}

    .list-item:hover {{
      background: rgba(244, 239, 227, 0.08);
    }}

    .list-item strong {{
      font-size: 12px;
      line-height: 1.28;
      overflow-wrap: anywhere;
    }}

    .list-item span {{
      color: var(--muted);
      font-size: 11px;
      line-height: 1.3;
    }}

    .bars {{
      display: grid;
      gap: 9px;
    }}

    .bar-row {{
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 12px;
    }}

    .bar-label {{
      display: flex;
      justify-content: space-between;
      gap: 8px;
    }}

    .bar {{
      height: 7px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(244, 239, 227, 0.08);
    }}

    .bar span {{
      display: block;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, var(--event), var(--record));
    }}

    .empty {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }}

    @media (max-width: 1120px) {{
      .app {{
        grid-template-columns: 280px minmax(0, 1fr);
      }}

      .inspector {{
        position: absolute;
        top: 0;
        right: 0;
        width: min(380px, 88vw);
        height: 100%;
      }}
    }}

    @media (max-width: 760px) {{
      html,
      body {{
        height: auto;
        min-height: 100%;
        overflow-x: hidden;
        overflow-y: auto;
      }}

      .app {{
        display: flex;
        flex-direction: column;
        height: auto;
        min-height: 100vh;
      }}

      .sidebar,
      .inspector {{
        border: 0;
        border-bottom: 1px solid var(--line);
        box-shadow: none;
      }}

      .sidebar {{
        max-height: 46vh;
        overflow: auto;
      }}

      .canvas-wrap {{
        height: 64vh;
        min-height: 440px;
      }}

      .inspector {{
        position: static;
        width: auto;
        height: auto;
      }}

      .hud {{
        align-items: flex-start;
      }}

      .hud-card {{
        max-width: 72vw;
      }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <header class="brand">
        <h1>UFO/UAP Knowledge Graph</h1>
        <p>Interactive network view for Department of War PURSUE Release 01 records. {generated_note}.</p>
      </header>

      <div class="stats" id="stats"></div>

      <section class="section">
        <h2>Search</h2>
        <input id="searchInput" class="search" type="search" placeholder="Find records, agencies, dates, places..." />
      </section>

      <section class="section">
        <h2>Node Types</h2>
        <div class="toggle-list" id="typeToggles"></div>
      </section>

      <section class="section">
        <h2>Relations</h2>
        <div class="toggle-list" id="relationToggles"></div>
      </section>

      <section class="section">
        <h2>Graph Density</h2>
        <label class="range-row">
          Minimum node degree <span id="degreeValue">0</span>
          <input id="degreeRange" type="range" min="0" max="12" value="0" />
        </label>
      </section>

      <section class="section">
        <h2>View</h2>
        <div class="actions">
          <button id="resetView">Reset</button>
          <button id="fitView">Fit graph</button>
          <button id="showRecords">Records</button>
          <button id="showEvents">Events</button>
        </div>
      </section>

      <section class="section">
        <h2>Agency Mix</h2>
        <div class="bars" id="agencyBars"></div>
      </section>
    </aside>

    <main class="canvas-wrap">
      <canvas id="graphCanvas"></canvas>
      <div class="hud">
        <div class="hud-card">
          <p class="hud-title" id="hudTitle">Network overview</p>
          <p class="hud-copy" id="hudCopy">Drag the canvas to pan, scroll to zoom, hover for labels, and click any node to inspect its evidence trail.</p>
        </div>
        <div class="zoom-pill" aria-label="Zoom controls">
          <button id="zoomOut" title="Zoom out">-</button>
          <button id="zoomIn" title="Zoom in">+</button>
        </div>
      </div>
    </main>

    <aside class="inspector">
      <div class="panel-title">
        <h2>Selection</h2>
        <span class="pill" id="visibleCount">0 visible</span>
      </div>
      <div id="detailPanel" class="empty">Select a node to see linked records, source metadata, local extraction paths, and adjacent entities.</div>

      <section class="section">
        <h2>High-Signal Nodes</h2>
        <div class="list" id="topNodes"></div>
      </section>

      <section class="section">
        <h2>Largest Events</h2>
        <div class="list" id="topEvents"></div>
      </section>
    </aside>
  </div>

  <div id="tooltip" class="tooltip"></div>

  <script id="graph-data" type="application/json">{graph_json}</script>
  <script id="summary-data" type="application/json">{summary_json}</script>
  <script>
    const graph = JSON.parse(document.getElementById("graph-data").textContent);
    const summary = JSON.parse(document.getElementById("summary-data").textContent);

    const TYPE_ORDER = ["release", "agency", "record", "event", "date", "location", "pairing"];
    const TYPE_COLORS = {{
      release: "#f0d46b",
      record: "#7bc8ff",
      event: "#ff8e63",
      agency: "#9fe27d",
      date: "#b79cff",
      location: "#59dec7",
      pairing: "#ff78ac",
    }};

    const TYPE_RADIUS = {{
      release: 16,
      agency: 12,
      record: 7,
      event: 9,
      date: 7,
      location: 8,
      pairing: 7,
    }};

    const RELATION_LABELS = {{
      contains_record: "contains record",
      from_agency: "from agency",
      supported_by: "supported by",
      incident_date: "incident date",
      incident_location: "incident location",
      video_pairing: "video pairing",
      pdf_pairing: "PDF pairing",
    }};

    const nodes = graph.nodes.map((node, index) => ({{
      ...node,
      index,
      x: Math.cos(index * 2.399963) * (90 + (index % 31) * 8),
      y: Math.sin(index * 2.399963) * (90 + (index % 29) * 8),
      vx: 0,
      vy: 0,
      fixed: false,
      visible: true,
      degree: 0,
    }}));
    const nodeById = new Map(nodes.map((node) => [node.id, node]));
    const edges = graph.edges
      .map((edge) => ({{ ...edge, sourceNode: nodeById.get(edge.source), targetNode: nodeById.get(edge.target) }}))
      .filter((edge) => edge.sourceNode && edge.targetNode);

    edges.forEach((edge) => {{
      edge.sourceNode.degree += 1;
      edge.targetNode.degree += 1;
    }});

    const typeBuckets = new Map(TYPE_ORDER.map((type) => [type, []]));
    nodes.forEach((node) => {{
      if (!typeBuckets.has(node.type)) typeBuckets.set(node.type, []);
      typeBuckets.get(node.type).push(node);
    }});
    typeBuckets.forEach((bucket) => {{
      bucket
        .sort((a, b) => b.degree - a.degree || a.label.localeCompare(b.label))
        .forEach((node, index) => {{
          node.layoutIndex = index;
          node.layoutCount = bucket.length;
          const anchor = anchorFor(node);
          node.x = anchor.x;
          node.y = anchor.y;
        }});
    }});

    const state = {{
      typeFilters: new Set(TYPE_ORDER),
      relationFilters: new Set(Object.keys(summary.relation_counts)),
      query: "",
      minDegree: 0,
      selected: null,
      hovered: null,
      transform: {{ x: 0, y: 0, k: 1 }},
      running: true,
      alpha: 1,
      pointer: {{ x: 0, y: 0 }},
    }};

    const canvas = document.getElementById("graphCanvas");
    const ctx = canvas.getContext("2d");
    const tooltip = document.getElementById("tooltip");
    const statsEl = document.getElementById("stats");
    const typeTogglesEl = document.getElementById("typeToggles");
    const relationTogglesEl = document.getElementById("relationToggles");
    const detailPanel = document.getElementById("detailPanel");
    const visibleCount = document.getElementById("visibleCount");
    const degreeRange = document.getElementById("degreeRange");
    const degreeValue = document.getElementById("degreeValue");
    const hudTitle = document.getElementById("hudTitle");
    const hudCopy = document.getElementById("hudCopy");

    function formatNumber(value) {{
      return new Intl.NumberFormat("en-US").format(value || 0);
    }}

    function humanType(type) {{
      return type.charAt(0).toUpperCase() + type.slice(1);
    }}

    function truncate(value, length = 96) {{
      const text = String(value || "").replace(/\\s+/g, " ").trim();
      return text.length > length ? text.slice(0, length - 1).trim() + "..." : text;
    }}

    function relationLabel(relation) {{
      return RELATION_LABELS[relation] || relation.replaceAll("_", " ");
    }}

    function nodeRadius(node) {{
      const base = TYPE_RADIUS[node.type] || 7;
      return base + Math.min(8, Math.sqrt(node.degree) * 0.75);
    }}

    function screenNodeRadius(node) {{
      return Math.max(2.8, nodeRadius(node) * Math.pow(state.transform.k, 0.82));
    }}

    function worldToScreen(x, y) {{
      return {{
        x: canvas.width / devicePixelRatio / 2 + (x + state.transform.x) * state.transform.k,
        y: canvas.height / devicePixelRatio / 2 + (y + state.transform.y) * state.transform.k,
      }};
    }}

    function screenToWorld(x, y) {{
      return {{
        x: (x - canvas.width / devicePixelRatio / 2) / state.transform.k - state.transform.x,
        y: (y - canvas.height / devicePixelRatio / 2) / state.transform.k - state.transform.y,
      }};
    }}

    function resizeCanvas() {{
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(320, Math.floor(rect.width * devicePixelRatio));
      canvas.height = Math.max(320, Math.floor(rect.height * devicePixelRatio));
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      draw();
    }}

    function matchesSearch(node) {{
      if (!state.query) return true;
      const q = state.query.toLowerCase();
      const fields = [
        node.label,
        node.id,
        node.type,
        node.agency,
        node.kind,
        node.incident_date,
        node.incident_location,
        node.description,
      ];
      return fields.some((field) => String(field || "").toLowerCase().includes(q));
    }}

    function recomputeVisibility() {{
      const visibleNodes = new Set();
      nodes.forEach((node) => {{
        node.visible =
          state.typeFilters.has(node.type) &&
          node.degree >= state.minDegree &&
          matchesSearch(node);
        if (node.visible) visibleNodes.add(node.id);
      }});

      edges.forEach((edge) => {{
        edge.visible =
          state.relationFilters.has(edge.relation) &&
          edge.sourceNode.visible &&
          edge.targetNode.visible;
      }});

      if (state.selected && !state.selected.visible) {{
        state.selected = null;
        renderDetails(null);
      }}

      const count = nodes.filter((node) => node.visible).length;
      visibleCount.textContent = `${{count}} visible`;
      hudTitle.textContent = state.query ? "Filtered view" : "Network overview";
      hudCopy.textContent = state.query
        ? `Showing matches for "${{state.query}}" plus relation filters. Click a result node to inspect its source metadata.`
        : "Drag the canvas to pan, scroll to zoom, hover for labels, and click any node to inspect its evidence trail.";
      state.alpha = Math.max(state.alpha, 0.35);
      draw();
    }}

    function renderStats() {{
      const stats = [
        ["Records", summary.metadata.record_count],
        ["Events", summary.type_counts.event],
        ["Text chars", summary.total_final_text],
        ["Images", summary.total_images],
      ];
      statsEl.innerHTML = stats
        .map(([label, value]) => `<div class="stat"><strong>${{formatNumber(value)}}</strong><span>${{label}}</span></div>`)
        .join("");
    }}

    function renderToggles() {{
      typeTogglesEl.innerHTML = TYPE_ORDER.map((type) => {{
        const count = summary.type_counts[type] || 0;
        return `<label class="toggle">
          <span class="toggle-left"><input type="checkbox" data-type="${{type}}" checked /><span class="dot" style="background:${{TYPE_COLORS[type]}}"></span>${{humanType(type)}}</span>
          <span class="count">${{count}}</span>
        </label>`;
      }}).join("");

      relationTogglesEl.innerHTML = Object.entries(summary.relation_counts)
        .sort((a, b) => b[1] - a[1])
        .map(([relation, count]) => `<label class="toggle">
          <span class="toggle-left"><input type="checkbox" data-relation="${{relation}}" checked />${{relationLabel(relation)}}</span>
          <span class="count">${{count}}</span>
        </label>`)
        .join("");

      typeTogglesEl.addEventListener("change", (event) => {{
        const type = event.target.dataset.type;
        if (!type) return;
        event.target.checked ? state.typeFilters.add(type) : state.typeFilters.delete(type);
        recomputeVisibility();
      }});

      relationTogglesEl.addEventListener("change", (event) => {{
        const relation = event.target.dataset.relation;
        if (!relation) return;
        event.target.checked ? state.relationFilters.add(relation) : state.relationFilters.delete(relation);
        recomputeVisibility();
      }});
    }}

    function renderAgencyBars() {{
      const entries = Object.entries(summary.agency_counts).sort((a, b) => b[1] - a[1]);
      const max = Math.max(...entries.map((entry) => entry[1]), 1);
      document.getElementById("agencyBars").innerHTML = entries
        .map(([label, value]) => `<div class="bar-row">
          <div class="bar-label"><span>${{label}}</span><span>${{value}}</span></div>
          <div class="bar"><span style="width:${{Math.max(4, (value / max) * 100)}}%"></span></div>
        </div>`)
        .join("");
    }}

    function renderTopLists() {{
      document.getElementById("topNodes").innerHTML = summary.top_nodes
        .map((item) => `<div class="list-item" data-node-id="${{item.id}}">
          <strong>${{truncate(item.label, 62)}}</strong>
          <span>${{humanType(item.type)}} / degree ${{item.degree}}</span>
        </div>`)
        .join("");

      document.getElementById("topEvents").innerHTML = summary.top_events
        .map((item) => `<div class="list-item" data-node-id="${{item.id}}">
          <strong>${{truncate(item.label, 62)}}</strong>
          <span>${{item.record_count}} supporting records</span>
        </div>`)
        .join("");

      document.querySelectorAll("[data-node-id]").forEach((item) => {{
        item.addEventListener("click", () => selectNode(nodeById.get(item.dataset.nodeId), true));
      }});
    }}

    function linkedEdges(node) {{
      return edges.filter((edge) => edge.source === node.id || edge.target === node.id);
    }}

    function neighborNodes(node) {{
      return linkedEdges(node)
        .map((edge) => (edge.source === node.id ? edge.targetNode : edge.sourceNode))
        .filter(Boolean)
        .sort((a, b) => b.degree - a.degree || a.label.localeCompare(b.label));
    }}

    function renderDetails(node) {{
      if (!node) {{
        detailPanel.className = "empty";
        detailPanel.textContent = "Select a node to see linked records, source metadata, local extraction paths, and adjacent entities.";
        return;
      }}

      detailPanel.className = "";
      const rows = [];
      rows.push(["Type", humanType(node.type)]);
      rows.push(["Degree", node.degree]);
      if (node.kind) rows.push(["Kind", node.kind]);
      if (node.agency) rows.push(["Agency", node.agency]);
      if (node.incident_date) rows.push(["Date", node.incident_date]);
      if (node.incident_location) rows.push(["Location", node.incident_location]);
      if (node.page_count) rows.push(["Pages", formatNumber(node.page_count)]);
      if (node.final_text_chars) rows.push(["Text chars", formatNumber(node.final_text_chars)]);
      if (node.image_count) rows.push(["Images", formatNumber(node.image_count)]);
      if (node.local_path) rows.push(["Local file", node.local_path]);
      if (node.final_text_path) rows.push(["Text file", node.final_text_path]);
      if (node.source_url) rows.push(["Source", `<a href="${{node.source_url}}" target="_blank" rel="noreferrer">Open official source</a>`]);

      const neighbors = neighborNodes(node).slice(0, 10);
      const neighborHtml = neighbors.length
        ? `<section class="section"><h2>Adjacent Entities</h2><div class="list">${{neighbors.map((neighbor) => `<div class="list-item" data-adjacent-id="${{neighbor.id}}"><strong>${{truncate(neighbor.label, 72)}}</strong><span>${{humanType(neighbor.type)}} / degree ${{neighbor.degree}}</span></div>`).join("")}}</div></section>`
        : "";

      detailPanel.innerHTML = `
        <p class="detail-name">${{node.label}}</p>
        <p class="detail-meta">${{node.id}}</p>
        <div class="kv">${{rows.map(([key, value]) => `<div class="kv-row"><strong>${{key}}</strong><span>${{value}}</span></div>`).join("")}}</div>
        ${{node.description ? `<p class="summary-text">${{truncate(node.description, 560)}}</p>` : ""}}
        ${{neighborHtml}}
      `;

      detailPanel.querySelectorAll("[data-adjacent-id]").forEach((item) => {{
        item.addEventListener("click", () => selectNode(nodeById.get(item.dataset.adjacentId), true));
      }});
    }}

    function selectNode(node, center = false) {{
      state.selected = node || null;
      renderDetails(state.selected);
      if (node && center) {{
        state.transform.x = -node.x;
        state.transform.y = -node.y;
        state.transform.k = Math.max(state.transform.k, 1.15);
      }}
      draw();
    }}

    function anchorFor(node) {{
      const index = node.layoutIndex || 0;
      const count = Math.max(1, node.layoutCount || 1);
      const turn = (index + 0.5) / count;
      const golden = index * 2.399963229728653;
      let angle = golden;
      let radius = 520;

      if (node.type === "release") {{
        return {{ x: 0, y: 0 }};
      }} else if (node.type === "agency") {{
        angle = turn * Math.PI * 2 - Math.PI / 2;
        radius = 150 + (index % 2) * 45;
      }} else if (node.type === "record") {{
        angle = golden - Math.PI / 2;
        radius = 390 + (index % 7) * 42;
      }} else if (node.type === "event") {{
        angle = golden + Math.PI / 8;
        radius = 650 + (index % 6) * 42;
      }} else if (node.type === "date") {{
        angle = -2.82 + turn * 1.36;
        radius = 720 + (index % 5) * 44;
      }} else if (node.type === "location") {{
        angle = 1.42 + turn * 1.38;
        radius = 720 + (index % 5) * 44;
      }} else if (node.type === "pairing") {{
        angle = -0.66 + turn * 1.26;
        radius = 690 + (index % 4) * 40;
      }}

      return {{
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      }};
    }}

    function simulate() {{
      const visibleNodes = nodes.filter((node) => node.visible);
      const visibleEdges = edges.filter((edge) => edge.visible);
      const alpha = state.alpha;
      if (alpha < 0.015) {{
        state.running = false;
        draw();
        return;
      }}

      for (let i = 0; i < visibleNodes.length; i += 1) {{
        const a = visibleNodes[i];
        for (let j = i + 1; j < visibleNodes.length; j += 1) {{
          const b = visibleNodes[j];
          let dx = a.x - b.x;
          let dy = a.y - b.y;
          let dist2 = dx * dx + dy * dy + 36;
          if (dist2 > 150000) continue;
          const dist = Math.max(6, Math.sqrt(dist2));
          const strength = Math.min(0.72, (2100 / dist2) * alpha);
          dx /= dist;
          dy /= dist;
          a.vx += dx * strength;
          a.vy += dy * strength;
          b.vx -= dx * strength;
          b.vy -= dy * strength;

          const collisionRadius = nodeRadius(a) + nodeRadius(b) + 16;
          if (dist < collisionRadius) {{
            const push = (collisionRadius - dist) * 0.052 * alpha;
            a.vx += dx * push;
            a.vy += dy * push;
            b.vx -= dx * push;
            b.vy -= dy * push;
          }}
        }}
      }}

      visibleEdges.forEach((edge) => {{
        const source = edge.sourceNode;
        const target = edge.targetNode;
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const desired = edge.relation === "contains_record"
          ? 280
          : edge.relation === "supported_by" ? 170 : 132;
        const strength = edge.relation === "contains_record" ? 0.0012 : 0.0038;
        const force = (dist - desired) * strength * alpha;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        source.vx += fx;
        source.vy += fy;
        target.vx -= fx;
        target.vy -= fy;
      }});

      visibleNodes.forEach((node) => {{
        if (!node.fixed) {{
          const anchor = anchorFor(node);
          const anchorStrength = node.type === "record" || node.type === "event" ? 0.009 : 0.007;
          node.vx += (anchor.x - node.x) * anchorStrength * alpha;
          node.vy += (anchor.y - node.y) * anchorStrength * alpha;
          node.vx *= 0.78;
          node.vy *= 0.78;
          const speed = Math.sqrt(node.vx * node.vx + node.vy * node.vy);
          if (speed > 18) {{
            node.vx = (node.vx / speed) * 18;
            node.vy = (node.vy / speed) * 18;
          }}
          node.x += node.vx;
          node.y += node.vy;
        }}
      }});

      state.alpha *= 0.987;
      draw();
      requestAnimationFrame(simulate);
    }}

    function restartSimulation() {{
      if (!state.running) {{
        state.running = true;
        requestAnimationFrame(simulate);
      }}
    }}

    function isHighlighted(node) {{
      if (!state.selected && !state.hovered) return true;
      const active = state.selected || state.hovered;
      if (active === node) return true;
      return edges.some((edge) => edge.visible && ((edge.sourceNode === active && edge.targetNode === node) || (edge.targetNode === active && edge.sourceNode === node)));
    }}

    function draw() {{
      const width = canvas.width / devicePixelRatio;
      const height = canvas.height / devicePixelRatio;
      ctx.clearRect(0, 0, width, height);
      ctx.save();

      const active = state.selected || state.hovered;
      const activeLinks = active ? new Set(linkedEdges(active)) : null;

      edges.forEach((edge) => {{
        if (!edge.visible) return;
        const source = worldToScreen(edge.sourceNode.x, edge.sourceNode.y);
        const target = worldToScreen(edge.targetNode.x, edge.targetNode.y);
        const activeEdge = activeLinks ? activeLinks.has(edge) : false;
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.strokeStyle = activeEdge ? "rgba(244, 239, 227, 0.52)" : "rgba(244, 239, 227, 0.105)";
        ctx.lineWidth = activeEdge ? 1.55 : 0.7;
        ctx.stroke();
      }});

      nodes.forEach((node) => {{
        if (!node.visible) return;
        const point = worldToScreen(node.x, node.y);
        const radius = screenNodeRadius(node);
        const highlighted = isHighlighted(node);

        ctx.beginPath();
        ctx.arc(point.x, point.y, radius + (node === state.selected ? 5 : 0), 0, Math.PI * 2);
        ctx.fillStyle = node === state.selected
          ? "rgba(244, 239, 227, 0.18)"
          : highlighted ? "rgba(244, 239, 227, 0.06)" : "rgba(244, 239, 227, 0.018)";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = highlighted ? TYPE_COLORS[node.type] : "rgba(182, 176, 162, 0.34)";
        ctx.fill();
        ctx.lineWidth = node === state.selected ? 2.2 : 1;
        ctx.strokeStyle = node === state.selected ? "#f4efe3" : "rgba(16, 17, 19, 0.85)";
        ctx.stroke();

        if (node.degree >= 12 || node === state.selected || node === state.hovered) {{
          drawLabel(node, point, radius);
        }}
      }});

      ctx.restore();
    }}

    function drawLabel(node, point, radius) {{
      const label = truncate(node.label.replace("|", " / "), node === state.selected ? 44 : 28);
      ctx.font = node === state.selected ? "700 12px Inter, system-ui" : "650 11px Inter, system-ui";
      const metrics = ctx.measureText(label);
      const x = point.x + radius + 7;
      const y = point.y - 8;
      ctx.fillStyle = "rgba(16, 17, 19, 0.76)";
      ctx.fillRect(x - 5, y - 12, metrics.width + 10, 19);
      ctx.fillStyle = node === state.selected ? "#f4efe3" : "rgba(244, 239, 227, 0.84)";
      ctx.fillText(label, x, y + 2);
    }}

    function nodeAt(clientX, clientY) {{
      const rect = canvas.getBoundingClientRect();
      const sx = clientX - rect.left;
      const sy = clientY - rect.top;
      let best = null;
      let bestDist = Infinity;
      nodes.forEach((node) => {{
        if (!node.visible) return;
        const point = worldToScreen(node.x, node.y);
        const radius = screenNodeRadius(node) + 6;
        const dx = point.x - sx;
        const dy = point.y - sy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < radius && dist < bestDist) {{
          best = node;
          bestDist = dist;
        }}
      }});
      return best;
    }}

    function showTooltip(node, clientX, clientY) {{
      if (!node) {{
        tooltip.classList.remove("visible");
        return;
      }}
      tooltip.innerHTML = `<strong>${{truncate(node.label.replace("|", " / "), 86)}}</strong><span>${{humanType(node.type)}} / degree ${{node.degree}}</span>`;
      tooltip.style.left = `${{clientX}}px`;
      tooltip.style.top = `${{clientY}}px`;
      tooltip.classList.add("visible");
    }}

    let dragMode = null;
    let dragNode = null;
    let lastPointer = null;

    canvas.addEventListener("pointerdown", (event) => {{
      canvas.setPointerCapture(event.pointerId);
      const node = nodeAt(event.clientX, event.clientY);
      lastPointer = {{ x: event.clientX, y: event.clientY }};
      if (node) {{
        dragMode = "node";
        dragNode = node;
        node.fixed = true;
        selectNode(node);
      }} else {{
        dragMode = "pan";
        canvas.classList.add("dragging");
      }}
    }});

    canvas.addEventListener("pointermove", (event) => {{
      const rect = canvas.getBoundingClientRect();
      state.pointer = {{ x: event.clientX - rect.left, y: event.clientY - rect.top }};
      if (dragMode && lastPointer) {{
        const dx = event.clientX - lastPointer.x;
        const dy = event.clientY - lastPointer.y;
        if (dragMode === "pan") {{
          state.transform.x += dx / state.transform.k;
          state.transform.y += dy / state.transform.k;
        }} else if (dragMode === "node" && dragNode) {{
          const world = screenToWorld(event.clientX - rect.left, event.clientY - rect.top);
          dragNode.x = world.x;
          dragNode.y = world.y;
          dragNode.vx = 0;
          dragNode.vy = 0;
        }}
        lastPointer = {{ x: event.clientX, y: event.clientY }};
        state.alpha = Math.max(state.alpha, 0.18);
        restartSimulation();
        draw();
        return;
      }}

      const node = nodeAt(event.clientX, event.clientY);
      state.hovered = node;
      showTooltip(node, event.clientX, event.clientY);
      draw();
    }});

    canvas.addEventListener("pointerup", () => {{
      if (dragNode) dragNode.fixed = false;
      dragMode = null;
      dragNode = null;
      lastPointer = null;
      canvas.classList.remove("dragging");
    }});

    canvas.addEventListener("pointerleave", () => {{
      state.hovered = null;
      showTooltip(null);
      if (!dragMode) draw();
    }});

    canvas.addEventListener("wheel", (event) => {{
      event.preventDefault();
      const factor = event.deltaY > 0 ? 0.9 : 1.1;
      const rect = canvas.getBoundingClientRect();
      const before = screenToWorld(event.clientX - rect.left, event.clientY - rect.top);
      state.transform.k = Math.max(0.18, Math.min(3.4, state.transform.k * factor));
      const after = screenToWorld(event.clientX - rect.left, event.clientY - rect.top);
      state.transform.x += after.x - before.x;
      state.transform.y += after.y - before.y;
      draw();
    }}, {{ passive: false }});

    document.getElementById("searchInput").addEventListener("input", (event) => {{
      state.query = event.target.value.trim();
      recomputeVisibility();
      restartSimulation();
    }});

    degreeRange.addEventListener("input", (event) => {{
      state.minDegree = Number(event.target.value);
      degreeValue.textContent = state.minDegree;
      recomputeVisibility();
      restartSimulation();
    }});

    document.getElementById("resetView").addEventListener("click", () => {{
      document.getElementById("searchInput").value = "";
      state.query = "";
      state.minDegree = 0;
      degreeRange.value = "0";
      degreeValue.textContent = "0";
      state.typeFilters = new Set(TYPE_ORDER);
      state.relationFilters = new Set(Object.keys(summary.relation_counts));
      document.querySelectorAll("input[type=checkbox]").forEach((input) => {{ input.checked = true; }});
      selectNode(null);
      fitGraph();
      recomputeVisibility();
      restartSimulation();
    }});

    document.getElementById("fitView").addEventListener("click", fitGraph);
    document.getElementById("zoomIn").addEventListener("click", () => {{ state.transform.k = Math.min(3.4, state.transform.k * 1.18); draw(); }});
    document.getElementById("zoomOut").addEventListener("click", () => {{ state.transform.k = Math.max(0.18, state.transform.k / 1.18); draw(); }});
    document.getElementById("showRecords").addEventListener("click", () => onlyTypes(["release", "agency", "record", "pairing"]));
    document.getElementById("showEvents").addEventListener("click", () => onlyTypes(["release", "event", "date", "location", "record"]));

    function onlyTypes(types) {{
      state.typeFilters = new Set(types);
      document.querySelectorAll("[data-type]").forEach((input) => {{
        input.checked = state.typeFilters.has(input.dataset.type);
      }});
      recomputeVisibility();
      restartSimulation();
    }}

    function fitGraph() {{
      const visibleNodes = nodes.filter((node) => node.visible);
      if (!visibleNodes.length) return;
      const minX = Math.min(...visibleNodes.map((node) => node.x));
      const maxX = Math.max(...visibleNodes.map((node) => node.x));
      const minY = Math.min(...visibleNodes.map((node) => node.y));
      const maxY = Math.max(...visibleNodes.map((node) => node.y));
      const width = canvas.width / devicePixelRatio;
      const height = canvas.height / devicePixelRatio;
      const spanX = Math.max(1, maxX - minX);
      const spanY = Math.max(1, maxY - minY);
      state.transform.k = Math.max(0.18, Math.min(2.2, Math.min((width - 90) / spanX, (height - 90) / spanY)));
      state.transform.x = -((minX + maxX) / 2);
      state.transform.y = -((minY + maxY) / 2);
      draw();
    }}

    renderStats();
    renderToggles();
    renderAgencyBars();
    renderTopLists();
    renderDetails(null);
    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    recomputeVisibility();
    requestAnimationFrame(simulate);
    setTimeout(fitGraph, 900);
  </script>
</body>
</html>
"""


def main() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    summary = build_summary(graph)
    OUT_PATH.write_text(render_html(graph, summary), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
