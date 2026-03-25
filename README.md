# Swipe Library

This repo turns the mixed swipe-file folder into a reusable project with two clear layers:

- `data/raw/`: preserved source material, kept separate by original collection
- `data/normalized/`: one canonical library you can upload, copy, share, remix, and query repeatedly

## Why This Structure

The original folder mixed together:

- partial email exports
- full-email JSON files
- author research notes
- web swipe markdown
- raw scraped HTML
- dashboards, scripts, and project context files
- duplicate copies of the same material from different folders

That is fine for collection, but weak for reuse. The normalized layer fixes that by giving every usable content item a consistent shape with:

- `author_key`
- `source_collection`
- `source_type`
- `title`
- `content`
- `tags`
- `intent_profiles`
- `quality` and duplicate metadata

## Repo Layout

```text
config/               Author metadata, source sets, retrieval profiles
data/raw/             Preserved original source collections
data/normalized/      Generated library outputs and inventories
docs/                 Architecture and retrieval guidance
schemas/              JSON schema for normalized entries
scripts/              Build and query tools
```

## Main Outputs

After running the builder, use these files first:

- `data/normalized/library.jsonl`: best for RAG, embeddings, and repeated prompt injection
- `data/normalized/library.json`: single-file JSON export of the normalized library
- `data/normalized/library-lite.json`: lighter metadata-first version for browsing
- `data/normalized/asset_inventory.json`: non-library files preserved for reference

## Rebuild

```bash
python3 scripts/build_library.py
```

## Query

```bash
python3 scripts/query_library.py "story-driven email about objection handling"
python3 scripts/query_library.py "landing page examples for offers" --author alex_hormozi
python3 scripts/query_library.py "cold email with personality" --profile cold_outreach
```

## Retrieval Philosophy

The goal is not just to store files. The goal is to make future retrieval stronger.

If someone asks for:

- a specific author, the query tool boosts that author and still looks across all preserved sources
- a style or use case, the tool maps the request to retrieval profiles like `story_lead`, `mechanism_reveal`, `cold_outreach`, or `landing_page`
- the “best parts,” the builder favors fuller sources and tracks duplicates so repeated copies do not dominate results

More detail is in [docs/architecture.md](/Users/home/Desktop/Sales%20Offers/Real%20Swipe%20File/docs/architecture.md) and [docs/retrieval.md](/Users/home/Desktop/Sales%20Offers/Real%20Swipe%20File/docs/retrieval.md).

