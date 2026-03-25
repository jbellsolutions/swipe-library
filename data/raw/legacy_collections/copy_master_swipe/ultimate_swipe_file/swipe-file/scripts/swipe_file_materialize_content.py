#!/usr/bin/env python3
"""Write embedded email bodies from swipe_database.json into per-email JSON files."""
import argparse
import json
import os
from pathlib import Path


def resolve_swipe_dir() -> Path:
    env_dir = os.environ.get("SWIPE_FILE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize content/{sender_key}/{message_id}.json files from swipe_database.json."
    )
    parser.add_argument("--sender", help="Only materialize one sender key.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing content files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    swipe_dir = resolve_swipe_dir()
    database_path = swipe_dir / "swipe_database.json"
    content_dir = swipe_dir / "content"

    with database_path.open() as f:
        database = json.load(f)

    written = 0
    skipped = 0
    for sender_key, sender_data in database.get("senders", {}).items():
        if args.sender and sender_key != args.sender:
            continue

        sender_dir = content_dir / sender_key
        sender_dir.mkdir(parents=True, exist_ok=True)

        for email in sender_data.get("emails", []):
            if not email.get("has_full_content"):
                continue

            record = {
                "id": email["id"],
                "subject": email.get("subject", ""),
                "date": email.get("date", ""),
                "sender": sender_data.get("email", ""),
                "body": email.get("body", ""),
            }
            destination = sender_dir / f"{email['id']}.json"
            if destination.exists() and not args.force:
                skipped += 1
                continue

            with destination.open("w") as f:
                json.dump(record, f, indent=2)
            written += 1

    print(f"Wrote {written} content files")
    print(f"Skipped {skipped} existing files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
