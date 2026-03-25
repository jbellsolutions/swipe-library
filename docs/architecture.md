# Architecture

## Goal

Preserve source separation without forcing downstream users to understand the original folder chaos.

## Layers

### 1. Raw Layer

`data/raw/` keeps the original collections intact:

- `root_snapshot`: the loose working-folder export
- `legacy_collections/copy_master_swipe/ultimate_swipe_file`: the richer legacy build
- `legacy_collections/copy_master_swipe/swipe-file`: the older nested copy

This layer is for provenance and future reprocessing.

### 2. Normalized Layer

`data/normalized/` is the reusable library.

Each entry is normalized to one schema regardless of whether it came from:

- an email JSON
- an email subject index
- a CSV email export
- a research markdown file
- a web swipe markdown file
- a codex text file
- a scraped HTML page

## Entry Design

Each normalized entry answers five questions:

1. What is it?
2. Who is it from?
3. Where did it come from?
4. How useful is it for retrieval?
5. Is it a duplicate of something better?

That is why the schema carries:

- source metadata
- author metadata
- tags
- intent profiles
- quality/completeness
- duplicate grouping

## What Becomes A Library Entry

Included:

- full emails
- subject-line-only email metadata
- Bill Mueller CSV emails
- research markdown
- web swipe markdown
- codex text files
- codex raw HTML converted to text
- content-like JSON docs

Excluded from the library but preserved in `asset_inventory.json`:

- dashboards
- scripts
- aggregate database exports
- style-analysis exports
- project context files
- search/resource JSONs that are mostly URLs or operational metadata

## Why JSONL

`library.jsonl` is the best default handoff format because:

- each line is an independent record
- it is easy to append and diff
- it works well for uploads, chunking, embedding, and retrieval pipelines

`library.json` exists as a single-file export for simpler sharing when JSONL is inconvenient.

