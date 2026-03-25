#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
NORMALIZED_DIR = ROOT / "data" / "normalized"
CONFIG_DIR = ROOT / "config"

ASSET_ONLY_NAMES = {
    "style_analysis.json",
    "swipe_database.json",
    "swipe_compact.json",
    "swipe_file_agent_context.json",
    "source_inventory.json",
    "SWIPE_FILE_CONTEXT.md",
    "GMAIL_INGEST.md",
    "NEXT_STEPS.md",
    "MASTER_INDEX.md",
    "RESEARCH_COMPLETE.md",
    "README.md",
    "credits.json",
}
SKIP_NAMES = {".DS_Store"}
SKIP_PARTS = {".git-archive", "__pycache__"}
PRIMARY_SOURCE_TYPES = {
    "email_full",
    "csv_email_full",
    "research_markdown",
    "web_markdown",
    "codex_text",
    "codex_html",
    "json_content_doc",
}
SOURCE_TYPE_PRIORITY = {
    "email_full": 100,
    "csv_email_full": 95,
    "codex_text": 92,
    "research_markdown": 86,
    "web_markdown": 84,
    "codex_html": 76,
    "json_content_doc": 72,
    "email_metadata": 44,
}
TAG_KEYWORDS = {
    "story": ["story", "narrative", "scene", "anecdote"],
    "curiosity": ["curiosity", "tease", "mystery", "open loop"],
    "offer": ["offer", "pricing", "upsell", "guarantee", "value stack"],
    "landing-page": ["landing page", "landing_page", "above the fold"],
    "sales-page": ["sales page", "sales_page", "headline", "conversion"],
    "cold-email": ["cold email", "cold-email", "outreach"],
    "outbound": ["outbound", "prospecting", "b2b"],
    "lead-generation": ["lead generation", "lead-gen", "lead gen"],
    "mindset": ["mindset", "belief", "identity", "motivation"],
    "ai": [" ai ", "gpt", "agent", "automation", "claude", "chatgpt"],
    "automation": ["automation", "workflow", "system", "agent"],
    "mechanism": ["mechanism", "unique mechanism", "why it works"],
    "framework": ["framework", "formula", "method", "checklist"],
    "nurture": ["nurture", "relationship", "authority"],
    "newsletter": ["newsletter"],
    "training": ["training", "course", "workshop", "masterclass"],
    "podcast": ["podcast", "interview"],
    "book": ["book", "books", "audiobook"],
}


def load_json(path: Path) -> Any:
    with path.open() as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def read_text(path: Path) -> str:
    return path.read_text(errors="replace")


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def contains_keyword(haystack: str, keyword: str) -> bool:
    lowered_haystack = haystack.lower()
    lowered_keyword = keyword.lower().strip()
    if not lowered_keyword:
        return False
    if re.fullmatch(r"[a-z0-9]+", lowered_keyword):
        return re.search(rf"\b{re.escape(lowered_keyword)}\b", lowered_haystack) is not None
    return lowered_keyword in lowered_haystack


def html_to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>", "\n\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html.unescape(text)
    return normalize_whitespace(text)


def flatten_json_text(payload: Any) -> str:
    pieces: list[str] = []

    def visit(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, str):
            cleaned = normalize_whitespace(node)
            if cleaned:
                pieces.append(cleaned)
            return
        if isinstance(node, (int, float, bool)):
            pieces.append(str(node))
            return
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if isinstance(node, dict):
            for key, value in node.items():
                if isinstance(value, (str, int, float, bool)):
                    entry = normalize_whitespace(f"{key}: {value}")
                    if entry:
                        pieces.append(entry)
                else:
                    visit(value)

    visit(payload)
    joined = "\n".join(pieces)
    return normalize_whitespace(joined)


def sha1_text(*parts: str) -> str:
    digest = hashlib.sha1()
    for part in parts:
        digest.update(part.encode("utf-8", errors="ignore"))
        digest.update(b"\0")
    return digest.hexdigest()


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "entry"


def excerpt(text: str | None, limit: int = 280) -> str | None:
    if not text:
        return None
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def word_count(text: str | None) -> int:
    if not text:
        return 0
    return len(re.findall(r"\b\w+\b", text))


def load_authors() -> dict[str, dict[str, Any]]:
    payload = load_json(CONFIG_DIR / "authors.json")
    style_analysis = load_json(RAW_DIR / "root_snapshot" / "exports" / "style_analysis.json")
    authors: dict[str, dict[str, Any]] = {}
    for author in payload["authors"]:
        merged = dict(author)
        merged["subject_profile"] = style_analysis.get(author["key"], {})
        authors[author["key"]] = merged
    return authors


def load_profiles() -> dict[str, dict[str, Any]]:
    payload = load_json(CONFIG_DIR / "retrieval_profiles.json")
    return {item["key"]: item for item in payload["profiles"]}


def load_source_sets() -> list[dict[str, Any]]:
    payload = load_json(CONFIG_DIR / "source_sets.json")["source_sets"]
    payload.sort(key=lambda item: len(item["path"]), reverse=True)
    return payload


def resolve_source_collection(path: Path, source_sets: list[dict[str, Any]]) -> dict[str, Any]:
    rel = path.relative_to(ROOT).as_posix()
    for source_set in source_sets:
        prefix = source_set["path"].rstrip("/")
        if rel == prefix or rel.startswith(prefix + "/"):
            return source_set
    return {"key": "unknown", "label": "Unknown", "path": "data/raw", "priority": 10}


def author_from_text_hint(text: str, authors: dict[str, dict[str, Any]]) -> str | None:
    lowered = text.lower()
    for key, meta in authors.items():
        if key in lowered:
            return key
        for address in meta.get("emails", []):
            if address.lower() in lowered:
                return key
    return None


def detect_author(path: Path, authors: dict[str, dict[str, Any]], payload: Any = None) -> str | None:
    for part in reversed(path.parts):
        if part in authors:
            return part
        if part.endswith(".json") and part[:-5] in authors:
            return part[:-5]
        stem = Path(part).stem
        for author_key in authors:
            if stem.startswith(author_key):
                return author_key
    if isinstance(payload, dict):
        for field in ("from", "sender", "email", "author", "display_name"):
            value = payload.get(field)
            if isinstance(value, str):
                author_key = author_from_text_hint(value, authors)
                if author_key:
                    return author_key
    if isinstance(payload, list):
        for item in payload[:3]:
            if isinstance(item, dict):
                for field in ("from", "sender"):
                    value = item.get(field)
                    if isinstance(value, str):
                        author_key = author_from_text_hint(value, authors)
                        if author_key:
                            return author_key
    return None


def should_skip(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return True
    if any(part in SKIP_PARTS for part in path.parts):
        return True
    return path.suffix.lower() == ".pyc"


def is_email_content_json(path: Path, payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and isinstance(payload.get("id"), str)
        and isinstance(payload.get("subject"), str)
        and ("body" in payload or "snippet" in payload)
    )


def classify_path(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    suffix = path.suffix.lower()
    name = path.name
    if name in ASSET_ONLY_NAMES:
        return "asset"
    if suffix == ".py":
        return "asset"
    if suffix == ".csv" and "Bill Mueller Story Sales Machine Swipe File - All Emails.csv" in name:
        return "bill_csv"
    if suffix == ".json" and ("/ids/" in rel or "/email_ids/" in rel):
        return "email_index"
    if suffix == ".md" and "/web_swipe_file/" in rel:
        return "web_markdown"
    if suffix == ".md" and "/.firecrawl/content/" in rel:
        return "research_markdown"
    if suffix == ".md" and "/swipe-file-research/" in rel and "/content/" in rel:
        return "research_markdown"
    if suffix == ".md" and "/swipe-file-content/" in rel:
        return "research_markdown"
    if suffix == ".txt" and "/codex/" in rel and "/text/" in rel:
        return "codex_text"
    if suffix == ".html" and "/codex/" in rel and "/raw_html/" in rel:
        return "codex_html"
    if suffix == ".html":
        return "asset"
    if suffix == ".json":
        return "json_maybe_content"
    return "asset"


def infer_tags(path: Path, title: str, content: str | None, author_key: str | None) -> list[str]:
    haystack = " ".join(
        [
            path.as_posix().lower(),
            title.lower(),
            (content or "")[:5000].lower(),
        ]
    )
    tags: set[str] = set()
    for tag, needles in TAG_KEYWORDS.items():
        if any(contains_keyword(haystack, needle) for needle in needles):
            tags.add(tag)
    if "email" in haystack:
        tags.add("email")
    if "subject" in haystack:
        tags.add("subject-line")
    if author_key:
        tags.add(author_key)
    return sorted(tags)


def infer_profiles(tags: list[str], text_blob: str, author_key: str | None, profiles: dict[str, dict[str, Any]]) -> list[str]:
    lowered = text_blob.lower()
    matched: list[str] = []
    for key, profile in profiles.items():
        if author_key and author_key in profile.get("preferred_authors", []):
            author_match = True
        else:
            author_match = False
        keyword_match = any(contains_keyword(lowered, keyword) for keyword in profile.get("keywords", []))
        tag_match = any(tag in tags for tag in profile.get("preferred_tags", []))
        if keyword_match or (author_match and tag_match):
            matched.append(key)
    return sorted(set(matched))


def build_entry(
    *,
    path: Path,
    source_set: dict[str, Any],
    source_type: str,
    source_format: str,
    title: str,
    content: str | None,
    author_key: str | None,
    authors: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
    date: str | None = None,
    extra_fingerprint: str | None = None,
    completeness: str | None = None,
) -> dict[str, Any]:
    author_meta = authors.get(author_key or "")
    tags = infer_tags(path, title, content, author_key)
    profile_matches = infer_profiles(tags, " ".join([title, content or "", path.as_posix()]), author_key, profiles)
    completeness = completeness or ("full" if content else "metadata_only")
    priority = SOURCE_TYPE_PRIORITY.get(source_type, 40) + int(source_set.get("priority", 0) / 10)
    entry_id = sha1_text(source_set["key"], path.relative_to(ROOT).as_posix(), title, extra_fingerprint or "")
    fingerprint = sha1_text(author_key or "", title, content or "", extra_fingerprint or "")
    return {
        "entry_id": entry_id,
        "fingerprint": fingerprint,
        "author_key": author_key,
        "author_name": author_meta["display_name"] if author_meta else None,
        "source_collection": source_set["key"],
        "source_path": path.relative_to(ROOT).as_posix(),
        "source_type": source_type,
        "source_format": source_format,
        "title": title,
        "date": date,
        "content": content,
        "excerpt": excerpt(content),
        "tags": tags,
        "intent_profiles": profile_matches,
        "style_traits": author_meta.get("style_traits", []) if author_meta else [],
        "priority": priority,
        "quality": {
            "completeness": completeness,
            "char_count": len(content or ""),
            "word_count": word_count(content),
            "duplicate_count": 1,
        },
        "relationships": {
            "canonical_entry_id": None,
            "duplicate_group": fingerprint,
        },
        "is_canonical": False,
    }


def build_asset(path: Path, source_set: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "source_collection": source_set["key"],
        "source_format": path.suffix.lower().lstrip(".") or "unknown",
        "size_bytes": path.stat().st_size,
    }


def load_email_index_entries(path: Path, source_set: dict[str, Any], authors: dict[str, dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    payload = load_json(path)
    author_key = detect_author(path, authors, payload)
    entries: list[dict[str, Any]] = []
    if not isinstance(payload, list):
        return entries
    for item in payload:
        if not isinstance(item, dict):
            continue
        title = item.get("subject") or f"{author_key or 'unknown'} email metadata"
        content = normalize_whitespace("\n".join(filter(None, [item.get("subject", ""), item.get("from", ""), item.get("date", "")])))
        entries.append(
            build_entry(
                path=path,
                source_set=source_set,
                source_type="email_metadata",
                source_format="json",
                title=title,
                content=content,
                author_key=author_key,
                authors=authors,
                profiles=profiles,
                date=item.get("date"),
                extra_fingerprint=item.get("id"),
                completeness="metadata_only",
            )
        )
    return entries


def load_email_json_entry(path: Path, payload: dict[str, Any], source_set: dict[str, Any], authors: dict[str, dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    author_key = detect_author(path, authors, payload)
    content = normalize_whitespace(payload.get("body") or payload.get("snippet") or "")
    return build_entry(
        path=path,
        source_set=source_set,
        source_type="email_full",
        source_format="json",
        title=payload.get("subject") or path.stem,
        content=content or None,
        author_key=author_key,
        authors=authors,
        profiles=profiles,
        date=payload.get("date"),
        extra_fingerprint=payload.get("id"),
    )


def load_json_content_doc(path: Path, payload: Any, source_set: dict[str, Any], authors: dict[str, dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    author_key = detect_author(path, authors, payload)
    content = flatten_json_text(payload)
    if not content:
        return None
    title = path.stem.replace("_", " ").replace("-", " ").strip() or path.stem
    return build_entry(
        path=path,
        source_set=source_set,
        source_type="json_content_doc",
        source_format="json",
        title=title,
        content=content,
        author_key=author_key,
        authors=authors,
        profiles=profiles,
    )


def load_text_entry(path: Path, source_set: dict[str, Any], source_type: str, authors: dict[str, dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    author_key = detect_author(path, authors)
    content = normalize_whitespace(read_text(path))
    title = path.stem.replace("_", " ").replace("-", " ").strip() or path.stem
    return build_entry(
        path=path,
        source_set=source_set,
        source_type=source_type,
        source_format=path.suffix.lower().lstrip("."),
        title=title,
        content=content,
        author_key=author_key,
        authors=authors,
        profiles=profiles,
    )


def load_bill_csv_entries(path: Path, source_set: dict[str, Any], authors: dict[str, dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    with path.open(newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            body = normalize_whitespace(row.get("Full Body Content", ""))
            title = (row.get("Subject") or f"bill_mueller_csv_{index + 1}").strip()
            entries.append(
                build_entry(
                    path=path,
                    source_set=source_set,
                    source_type="csv_email_full",
                    source_format="csv",
                    title=title,
                    content=body or None,
                    author_key="bill_mueller",
                    authors=authors,
                    profiles=profiles,
                    date=row.get("Date") or None,
                    extra_fingerprint=row.get("Gmail Link") or title,
                )
            )
    return entries


def apply_duplicate_metadata(entries: list[dict[str, Any]]) -> None:
    by_fingerprint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_fingerprint[entry["fingerprint"]].append(entry)
    for group_key, group in by_fingerprint.items():
        canonical = sorted(
            group,
            key=lambda item: (
                -item["priority"],
                item["quality"]["completeness"] != "full",
                item["source_path"],
            ),
        )[0]
        for entry in group:
            entry["quality"]["duplicate_count"] = len(group)
            entry["relationships"]["duplicate_group"] = group_key
            entry["relationships"]["canonical_entry_id"] = canonical["entry_id"]


def build_library() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    authors = load_authors()
    profiles = load_profiles()
    source_sets = load_source_sets()
    entries: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []

    for path in sorted(RAW_DIR.rglob("*")):
        if not path.is_file() or should_skip(path):
            continue
        source_set = resolve_source_collection(path, source_sets)
        classification = classify_path(path)

        if classification == "asset":
            assets.append(build_asset(path, source_set))
            continue

        if classification == "bill_csv":
            entries.extend(load_bill_csv_entries(path, source_set, authors, profiles))
            continue

        if classification == "email_index":
            entries.extend(load_email_index_entries(path, source_set, authors, profiles))
            continue

        if classification == "codex_text":
            entries.append(load_text_entry(path, source_set, "codex_text", authors, profiles))
            continue

        if classification == "research_markdown":
            entries.append(load_text_entry(path, source_set, "research_markdown", authors, profiles))
            continue

        if classification == "web_markdown":
            entries.append(load_text_entry(path, source_set, "web_markdown", authors, profiles))
            continue

        if classification == "codex_html":
            author_key = detect_author(path, authors)
            content = html_to_text(read_text(path))
            entries.append(
                build_entry(
                    path=path,
                    source_set=source_set,
                    source_type="codex_html",
                    source_format="html",
                    title=path.stem.replace("_", " ").replace("-", " ").strip() or path.stem,
                    content=content,
                    author_key=author_key,
                    authors=authors,
                    profiles=profiles,
                )
            )
            continue

        if classification == "json_maybe_content":
            payload = load_json(path)
            rel = path.relative_to(ROOT).as_posix()
            if is_email_content_json(path, payload):
                entries.append(load_email_json_entry(path, payload, source_set, authors, profiles))
                continue
            if "/search/" in rel or "/resources/" in rel:
                assets.append(build_asset(path, source_set))
                continue
            doc_entry = load_json_content_doc(path, payload, source_set, authors, profiles)
            if doc_entry:
                entries.append(doc_entry)
            else:
                assets.append(build_asset(path, source_set))
            continue

        assets.append(build_asset(path, source_set))

    apply_duplicate_metadata(entries)
    canonical_entries = 0
    for entry in entries:
        is_canonical = entry["entry_id"] == entry["relationships"]["canonical_entry_id"]
        entry["is_canonical"] = is_canonical
        if is_canonical:
            canonical_entries += 1

    author_counts = Counter(entry["author_key"] for entry in entries if entry.get("author_key"))
    source_type_counts = Counter(entry["source_type"] for entry in entries)
    source_collection_counts = Counter(entry["source_collection"] for entry in entries)
    duplicate_groups = sum(1 for count in Counter(entry["fingerprint"] for entry in entries).values() if count > 1)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "library_entries": len(entries),
        "canonical_entries": canonical_entries,
        "asset_files": len(assets),
        "authors": dict(sorted(author_counts.items())),
        "source_types": dict(sorted(source_type_counts.items())),
        "source_collections": dict(sorted(source_collection_counts.items())),
        "duplicate_groups": duplicate_groups,
    }
    return entries, assets, summary


def make_lite_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in entry.items()
        if key != "content"
    }


def main() -> None:
    entries, assets, summary = build_library()
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    canonical_entries = [entry for entry in entries if entry["is_canonical"]]

    library_payload = {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "entries": entries,
    }
    library_lite_payload = {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "entries": [make_lite_entry(entry) for entry in entries],
    }
    canonical_payload = {
        "generated_at": summary["generated_at"],
        "summary": summary,
        "entries": canonical_entries,
    }

    write_json(NORMALIZED_DIR / "library.json", library_payload)
    write_json(NORMALIZED_DIR / "library-lite.json", library_lite_payload)
    write_json(NORMALIZED_DIR / "library-canonical.json", canonical_payload)
    write_json(
        NORMALIZED_DIR / "asset_inventory.json",
        {
            "generated_at": summary["generated_at"],
            "summary": {
                "asset_files": len(assets),
                "source_collections": dict(sorted(Counter(asset["source_collection"] for asset in assets).items())),
                "formats": dict(sorted(Counter(asset["source_format"] for asset in assets).items())),
            },
            "assets": assets,
        },
    )

    jsonl_path = NORMALIZED_DIR / "library.jsonl"
    with jsonl_path.open("w") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    canonical_jsonl_path = NORMALIZED_DIR / "library-canonical.jsonl"
    with canonical_jsonl_path.open("w") as handle:
        for entry in canonical_entries:
            handle.write(json.dumps(entry, ensure_ascii=True) + "\n")

    print(f"Wrote {len(entries)} library entries")
    print(f"Wrote {len(canonical_entries)} canonical library entries")
    print(f"Wrote {len(assets)} asset records")
    print(f"Library JSONL: {jsonl_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
