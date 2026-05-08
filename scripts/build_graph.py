#!/usr/bin/env python3
"""Build a lightweight knowledge graph for UFO records, events, agencies, and files."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/manifest/records.jsonl"
DOCUMENTS = ROOT / "data/extracted/documents.jsonl"
FINAL_DOCUMENTS = ROOT / "data/extracted/final_text/documents.jsonl"
CURATED_DOCUMENTS = ROOT / "data/curated/readable/documents.jsonl"
GRAPH_DIR = ROOT / "data/graph"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def node_id(prefix: str, value: str) -> str:
    normalized = re.sub(r"\s+", " ", value or "").strip()
    normalized = normalized if normalized and normalized.upper() != "N/A" else "unknown"
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-") or "unknown"
    return f"{prefix}:{slug[:140]}"


def event_key(record: dict) -> str:
    date = record.get("incident_date") or "N/A"
    location = record.get("incident_location") or "N/A"
    if date.upper() == "N/A" and location.upper() == "N/A":
        return f"record:{record['id']}"
    return f"{date}|{location}"


def add_node(nodes: dict, node: dict) -> None:
    current = nodes.get(node["id"])
    if not current:
        nodes[node["id"]] = node
        return
    for key, value in node.items():
        if key not in current or current[key] in ("", None, [], {}):
            current[key] = value


def add_edge(edges: list[dict], source: str, target: str, relation: str, **attrs: str) -> None:
    edges.append({"source": source, "target": target, "relation": relation, **attrs})


def main() -> None:
    records = read_jsonl(MANIFEST)
    extracted = {row["id"]: row for row in read_jsonl(DOCUMENTS)}
    final_text = {row["record_id"]: row for row in read_jsonl(FINAL_DOCUMENTS)}
    curated_text = {row["record_id"]: row for row in read_jsonl(CURATED_DOCUMENTS)}
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    event_members: dict[str, list[str]] = defaultdict(list)

    release_id = "release:release_1"
    add_node(nodes, {"id": release_id, "type": "release", "label": "PURSUE Release 01", "date": "5/8/26"})

    for record in records:
        doc_id = f"record:{record['id']}"
        extraction = extracted.get(record["id"], {})
        final = final_text.get(record["id"], {})
        curated = curated_text.get(record["id"], {})
        add_node(nodes, {
            "id": doc_id,
            "type": "record",
            "label": record["title"],
            "kind": record["kind"],
            "agency": record["agency"],
            "incident_date": record["incident_date"],
            "incident_location": record["incident_location"],
            "source_url": record["source_url"],
            "thumbnail_url": record["thumbnail_url"],
            "local_path": record["local_path"],
            "extraction_status": extraction.get("status", "not_extracted"),
            "page_count": extraction.get("page_count", 0),
            "text_chars": extraction.get("text_chars", 0),
            "ocr_text_chars": final.get("ocr_text_chars", 0),
            "final_text_chars": final.get("final_text_chars", extraction.get("text_chars", 0)),
            "final_text_path": final.get("final_text_path", extraction.get("text_path", "")),
            "clean_text_chars": curated.get("clean_text_chars", final.get("final_text_chars", extraction.get("text_chars", 0))),
            "readable_doc_path": curated.get("readable_doc_path", ""),
            "quality_counts": curated.get("quality_counts", {}),
            "image_count": extraction.get("image_count", 0),
            "description": record["description"],
        })
        add_edge(edges, release_id, doc_id, "contains_record")

        agency_id = node_id("agency", record["agency"])
        add_node(nodes, {"id": agency_id, "type": "agency", "label": record["agency"] or "Unknown agency"})
        add_edge(edges, doc_id, agency_id, "from_agency")

        if record["incident_location"] and record["incident_location"].upper() != "N/A":
            location_id = node_id("location", record["incident_location"])
            add_node(nodes, {"id": location_id, "type": "location", "label": record["incident_location"]})
            add_edge(edges, doc_id, location_id, "incident_location")

        if record["incident_date"] and record["incident_date"].upper() != "N/A":
            date_id = node_id("date", record["incident_date"])
            add_node(nodes, {"id": date_id, "type": "date", "label": record["incident_date"]})
            add_edge(edges, doc_id, date_id, "incident_date")

        key = event_key(record)
        event_id = node_id("event", key)
        event_members[event_id].append(record["id"])
        add_node(nodes, {
            "id": event_id,
            "type": "event",
            "label": key if not key.startswith("record:") else record["title"],
            "incident_date": record["incident_date"],
            "incident_location": record["incident_location"],
        })
        add_edge(edges, event_id, doc_id, "supported_by")

        for pairing_field in ("pdf_pairing", "video_pairing"):
            pairing = record.get(pairing_field)
            if pairing:
                pairing_id = node_id("pairing", pairing)
                add_node(nodes, {"id": pairing_id, "type": "pairing", "label": pairing})
                add_edge(edges, doc_id, pairing_id, pairing_field)

    for event_id, members in event_members.items():
        nodes[event_id]["record_count"] = len(members)

    graph = {
        "metadata": {
            "source": "https://www.war.gov/UFO/",
            "release": "release_1",
            "record_count": len(records),
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
        "nodes": sorted(nodes.values(), key=lambda item: item["id"]),
        "edges": edges,
    }
    (GRAPH_DIR / "knowledge_graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    with (GRAPH_DIR / "events.md").open("w", encoding="utf-8") as handle:
        handle.write("# UFO Event Index\n\n")
        for node in sorted((n for n in nodes.values() if n["type"] == "event"), key=lambda n: n["label"]):
            handle.write(f"## {node['label']}\n\n")
            handle.write(f"- Incident date: {node.get('incident_date') or 'N/A'}\n")
            handle.write(f"- Incident location: {node.get('incident_location') or 'N/A'}\n")
            handle.write(f"- Record count: {node.get('record_count', 0)}\n\n")
    print(json.dumps(graph["metadata"], ensure_ascii=False))


if __name__ == "__main__":
    main()
