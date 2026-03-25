# Retrieval

## What “Good Retrieval” Means Here

A useful swipe library should not just filter by filename. It should retrieve by:

- author
- style
- intent
- format
- topic
- source quality

## Profiles

The repo uses retrieval profiles to bridge vague requests and concrete source material.

Examples:

- `story_lead`
- `curiosity_hook`
- `value_lesson`
- `mechanism_reveal`
- `nurture_relationship`
- `offer_breakdown`
- `cold_outreach`
- `landing_page`
- `mindset`
- `ai_automation`

These profiles are defined in `config/retrieval_profiles.json` and used by the query script for boosting.

## Scoring

The query tool ranks entries using:

- query-term overlap in title, tags, and content
- author matches
- explicit profile matches
- inferred profile matches
- source-type usefulness
- entry priority and completeness

This is deliberate. A full email or codex text should usually beat a metadata-only subject line when both match the request.

## Recommended Use

Use `library.jsonl` when you want to:

- upload into a model or vector store
- extract subsets by script
- keep source provenance attached to every chunk

Use `query_library.py` when you want to:

- explore the corpus quickly
- shortlist examples before copying them elsewhere
- answer “show me the strongest story-led Bill Mueller material” type requests

