#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LIBRARY_PATH = ROOT / "data" / "normalized" / "library-canonical.jsonl"
PROFILES_PATH = ROOT / "config" / "retrieval_profiles.json"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "how",
    "in",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def load_entries() -> list[dict[str, Any]]:
    with LIBRARY_PATH.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_profiles() -> dict[str, dict[str, Any]]:
    payload = json.loads(PROFILES_PATH.read_text())
    return {item["key"]: item for item in payload["profiles"]}


def tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS]


def contains_keyword(haystack: str, keyword: str) -> bool:
    lowered_haystack = haystack.lower()
    lowered_keyword = keyword.lower().strip()
    if not lowered_keyword:
        return False
    if re.fullmatch(r"[a-z0-9]+", lowered_keyword):
        return re.search(rf"\b{re.escape(lowered_keyword)}\b", lowered_haystack) is not None
    return lowered_keyword in lowered_haystack


def infer_profiles(query: str, profiles: dict[str, dict[str, Any]]) -> list[str]:
    lowered = query.lower()
    matched: list[str] = []
    for key, profile in profiles.items():
        if any(contains_keyword(lowered, keyword) for keyword in profile.get("keywords", [])):
            matched.append(key)
    return matched


def score_entry(
    entry: dict[str, Any],
    query_terms: list[str],
    author: str | None,
    explicit_profile: str | None,
    inferred_profiles: list[str],
    source_type: str | None,
    profiles: dict[str, dict[str, Any]],
) -> int:
    score = 0
    title = (entry.get("title") or "").lower()
    content = (entry.get("content") or "").lower()
    tags = set(entry.get("tags") or [])

    for term in query_terms:
        if term in title:
            score += 8
        if term in content:
            score += 3
        if any(term in tag for tag in tags):
            score += 5

    if author:
        if entry.get("author_key") == author:
            score += 80
        else:
            score -= 40

    profile_keys = set(inferred_profiles)
    if explicit_profile:
        profile_keys.add(explicit_profile)

    for key in profile_keys:
        if key in (entry.get("intent_profiles") or []):
            score += 25
        profile = profiles.get(key)
        if profile and entry.get("author_key") in profile.get("preferred_authors", []):
            score += 15
        if profile and any(tag in tags for tag in profile.get("preferred_tags", [])):
            score += 10

    if source_type:
        if entry.get("source_type") == source_type:
            score += 25
        else:
            score -= 10

    if entry.get("quality", {}).get("completeness") == "full":
        score += 18
    elif entry.get("quality", {}).get("completeness") == "metadata_only":
        score -= 18

    score += int(entry.get("priority", 0) / 10)
    score -= max(0, entry.get("quality", {}).get("duplicate_count", 1) - 1)
    return score


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the normalized swipe library.")
    parser.add_argument("query", help="Free-form query text.")
    parser.add_argument("--author", help="Author key, e.g. bill_mueller")
    parser.add_argument("--profile", help="Retrieval profile key, e.g. story_lead")
    parser.add_argument("--source-type", help="Filter/boost a specific source type.")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    entries = load_entries()
    profiles = load_profiles()
    query_terms = tokenize(args.query)
    inferred = infer_profiles(args.query, profiles)

    ranked = []
    for entry in entries:
        score = score_entry(
            entry,
            query_terms=query_terms,
            author=args.author,
            explicit_profile=args.profile,
            inferred_profiles=inferred,
            source_type=args.source_type,
            profiles=profiles,
        )
        if score > 0:
            ranked.append((score, entry))

    ranked.sort(key=lambda item: (-item[0], item[1]["title"]))
    results = []
    for score, entry in ranked[: args.limit]:
        results.append(
            {
                "score": score,
                "title": entry["title"],
                "author_key": entry.get("author_key"),
                "source_type": entry["source_type"],
                "source_collection": entry["source_collection"],
                "tags": entry.get("tags"),
                "intent_profiles": entry.get("intent_profiles"),
                "source_path": entry["source_path"],
                "excerpt": entry.get("excerpt"),
            }
        )

    if args.as_json:
        print(json.dumps({"query": args.query, "results": results}, indent=2))
        return

    print(f"Query: {args.query}")
    if args.author:
        print(f"Author filter: {args.author}")
    if args.profile:
        print(f"Profile boost: {args.profile}")
    if inferred:
        print(f"Inferred profiles: {', '.join(inferred)}")
    print()
    for result in results:
        print(f"[{result['score']}] {result['title']}")
        print(f"  author: {result['author_key']} | type: {result['source_type']} | source: {result['source_collection']}")
        print(f"  tags: {', '.join(result['tags'])}")
        print(f"  path: {result['source_path']}")
        if result["excerpt"]:
            print(f"  excerpt: {result['excerpt']}")
        print()


if __name__ == "__main__":
    main()
