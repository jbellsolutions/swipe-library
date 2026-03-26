# Eugene Schwartz Swipe Status

## Current Coverage (Local Folder Only)

- Direct Eugene entries indexed: `5`
- Eugene-related canonical swipe entries (direct + mentions): `37`
- Unique Eugene-related assets detected across dropped folders: `11`
- Total source file paths scanned for those assets: `29`

## Indexed Direct Eugene Text

- `data/raw/imports/eugene_schwartz/codex/eugene_schwartz/text/001-gene-schwartz-lost-interview.txt`
- `data/raw/imports/eugene_schwartz/codex/eugene_schwartz/text/002-breakthrough-advertising-cd1.txt`
- `data/raw/imports/eugene_schwartz/codex/eugene_schwartz/text/003-breakthrough-advertising-cd2.txt`
- `data/raw/imports/eugene_schwartz/codex/eugene_schwartz/text/004-breakthrough-advertising-cd3.txt`
- `data/raw/imports/eugene_schwartz/codex/eugene_schwartz/text/005-breakthrough-advertising-cd4.txt`

## Provenance + Exports

- Asset provenance inventory: `data/raw/imports/eugene_schwartz/source_inventory.json`
- Eugene-focused canonical export: `data/normalized/eugene_schwartz_swipe.json`
- Full normalized library: `data/normalized/library-canonical.json`

## Gap Notes

- A full text copy of the `Breakthrough Advertising` book was **not** found in this local folder snapshot.
- Current direct Eugene corpus is interview/transcription heavy.
- Existing Brian Kurtz materials contain many Eugene references and are included in the Eugene-focused export.

## Ongoing Add Workflow

1. Drop new Eugene text files into:
   - `data/raw/imports/eugene_schwartz/codex/eugene_schwartz/text/`
2. Rebuild library:
   - `python3 scripts/build_library.py`
3. Regenerate focused Eugene export (optional):
   - `python3 scripts/build_eugene_swipe.py`
