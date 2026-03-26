#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_LIBRARY_PATH = ROOT / "data" / "normalized" / "library-canonical.json"
OUTPUT_PATH = ROOT / "data" / "normalized" / "eugene_schwartz_swipe.json"

KEYWORDS = [
    "eugene schwartz",
    "gene schwartz",
    "breakthrough advertising",
    "brilliance breakthrough",
    "instant improvement",
]


def load_canonical_entries() -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(CANONICAL_LIBRARY_PATH.read_text())
    return payload.get("generated_at", ""), payload.get("entries", [])


def is_keyword_match(entry: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(entry.get("title") or ""),
            str(entry.get("source_path") or ""),
            " ".join(entry.get("tags") or []),
            str(entry.get("excerpt") or ""),
            str(entry.get("content") or "")[:4000],
        ]
    ).lower()
    return any(keyword in text for keyword in KEYWORDS)


def build_export(entries: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    export_entries: list[dict[str, Any]] = []
    for entry in entries:
        direct_author = entry.get("author_key") == "eugene_schwartz"
        keyword_match = is_keyword_match(entry)
        if not (direct_author or keyword_match):
            continue

        match_type: list[str] = []
        if direct_author:
            match_type.append("direct_author")
        if keyword_match:
            match_type.append("keyword_match")

        export_entries.append(
            {
                "match_type": match_type,
                "entry_id": entry.get("entry_id"),
                "author_key": entry.get("author_key"),
                "title": entry.get("title"),
                "source_type": entry.get("source_type"),
                "source_collection": entry.get("source_collection"),
                "source_path": entry.get("source_path"),
                "tags": entry.get("tags"),
                "excerpt": entry.get("excerpt"),
                "quality": entry.get("quality"),
            }
        )

    export_entries.sort(
        key=lambda item: (
            0 if "direct_author" in item["match_type"] else 1,
            item.get("author_key") or "",
            item.get("title") or "",
        )
    )

    author_counts: dict[str, int] = {}
    for item in export_entries:
        key = item.get("author_key") or "unknown"
        author_counts[key] = author_counts.get(key, 0) + 1

    summary = {
        "generated_at": generated_at,
        "total_entries": len(export_entries),
        "direct_author_entries": sum(1 for item in export_entries if "direct_author" in item["match_type"]),
        "keyword_match_entries": sum(1 for item in export_entries if "keyword_match" in item["match_type"]),
        "authors": dict(sorted(author_counts.items())),
    }
    return {"summary": summary, "entries": export_entries}


def main() -> None:
    generated_at, entries = load_canonical_entries()
    payload = build_export(entries, generated_at)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
    print(f"Wrote Eugene export: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Total entries: {payload['summary']['total_entries']}")
    print(f"Direct Eugene entries: {payload['summary']['direct_author_entries']}")


if __name__ == "__main__":
    main()
