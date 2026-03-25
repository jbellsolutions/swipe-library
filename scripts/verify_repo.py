#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMALIZED_DIR = ROOT / "data" / "normalized"
AUDIT_PATH = NORMALIZED_DIR / "repo_audit.json"

IGNOREABLE_SUFFIXES = {".pyc"}
IGNOREABLE_PARTS = {".git-archive", "__pycache__"}
IGNOREABLE_NAMES = {".DS_Store"}


def tracked_files() -> set[str]:
    return set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())


def all_files() -> list[str]:
    results: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        posix = path.relative_to(ROOT).as_posix()
        if ".git/" in posix:
            continue
        results.append(posix)
    return sorted(results)


def significant_untracked(all_paths: list[str], tracked: set[str]) -> list[str]:
    missing: list[str] = []
    for path in all_paths:
        pure = Path(path)
        if path in tracked:
            continue
        if pure.name in IGNOREABLE_NAMES:
            continue
        if pure.suffix.lower() in IGNOREABLE_SUFFIXES:
            continue
        if any(part in IGNOREABLE_PARTS for part in pure.parts):
            continue
        missing.append(path)
    return missing


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text())["summary"]


def classify_tracked(tracked: set[str]) -> dict[str, int]:
    counts = Counter()
    for path in tracked:
        if path.startswith("data/raw/"):
            counts["raw_files"] += 1
        elif path.startswith("data/normalized/"):
            counts["normalized_files"] += 1
        elif path.startswith("scripts/"):
            counts["script_files"] += 1
        elif path.startswith("docs/"):
            counts["doc_files"] += 1
        elif path.startswith("config/"):
            counts["config_files"] += 1
        elif path.startswith("schemas/"):
            counts["schema_files"] += 1
        else:
            counts["top_level_files"] += 1
    return dict(sorted(counts.items()))


def main() -> None:
    tracked = tracked_files()
    all_paths = all_files()
    missing = significant_untracked(all_paths, tracked)
    library_summary = load_summary(NORMALIZED_DIR / "library-lite.json")
    asset_summary = load_summary(NORMALIZED_DIR / "asset_inventory.json")

    audit = {
        "tracked_file_count": len(tracked),
        "working_tree_file_count": len(all_paths),
        "tracked_breakdown": classify_tracked(tracked),
        "library_summary": library_summary,
        "asset_summary": asset_summary,
        "significant_untracked_files": missing,
        "significant_untracked_count": len(missing),
    }

    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_PATH.open("w") as handle:
        json.dump(audit, handle, indent=2)
        handle.write("\n")

    print(f"Tracked files: {len(tracked)}")
    print(f"Working tree files: {len(all_paths)}")
    print(f"Significant untracked files: {len(missing)}")
    print(f"Audit report: {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
