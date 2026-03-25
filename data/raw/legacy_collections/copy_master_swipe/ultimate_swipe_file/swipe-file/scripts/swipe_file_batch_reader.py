#!/usr/bin/env python3
"""Inspect swipe-file sender progress and choose the next email batches to ingest."""
import json
import os
import sys
from pathlib import Path


def resolve_swipe_dir() -> Path:
    env_dir = os.environ.get("SWIPE_FILE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


SWIPE_DIR = resolve_swipe_dir()
IDS_DIR = SWIPE_DIR / "ids"
CONTENT_DIR = SWIPE_DIR / "content"
PROGRESS_FILE = SWIPE_DIR / "progress.json"

def load_progress():
    if PROGRESS_FILE.exists():
        with PROGRESS_FILE.open() as f:
            return json.load(f)
    return {}

def save_progress(progress):
    with PROGRESS_FILE.open('w') as f:
        json.dump(progress, f, indent=2)

def get_remaining(sender_key):
    """Get list of email IDs not yet processed for a sender."""
    ids_file = IDS_DIR / f"{sender_key}.json"
    content_dir = CONTENT_DIR / sender_key

    with ids_file.open() as f:
        all_emails = json.load(f)

    # Check which IDs already have content files
    processed = set()
    if content_dir.exists():
        for fname in os.listdir(content_dir):
            if fname.endswith('.json'):
                processed.add(fname.replace('.json', ''))

    remaining = [e for e in all_emails if e['id'] not in processed]
    return remaining

def status():
    """Print status of all senders."""
    senders = [f.replace('.json', '') for f in os.listdir(IDS_DIR) if f.endswith('.json')]
    total_all = 0
    done_all = 0
    for s in sorted(senders):
        ids_file = IDS_DIR / f"{s}.json"
        content_dir = CONTENT_DIR / s
        with ids_file.open() as f:
            total = len(json.load(f))
        done = len([f for f in os.listdir(content_dir) if f.endswith('.json')]) if content_dir.exists() else 0
        total_all += total
        done_all += done
        pct = (done/total*100) if total > 0 else 0
        bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
        print(f"  {s:20s} {bar} {done:5d}/{total:5d} ({pct:.1f}%)")
    pct_all = (done_all/total_all*100) if total_all > 0 else 0
    print(f"\n  {'TOTAL':20s} {done_all:5d}/{total_all:5d} ({pct_all:.1f}%)")

def next_batch(sender_key=None, batch_size=10):
    """Get next batch of email IDs to process."""
    if sender_key:
        senders = [sender_key]
    else:
        # Process in order: smallest backlog first for quick wins
        senders = [f.replace('.json', '') for f in os.listdir(IDS_DIR) if f.endswith('.json')]
        senders.sort(key=lambda s: len(get_remaining(s)))

    for s in senders:
        remaining = get_remaining(s)
        if remaining:
            batch = remaining[:batch_size]
            return s, [e['id'] for e in batch]

    return None, []

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'

    if cmd == 'status':
        print("\n📊 Swipe File Processing Status:\n")
        status()
    elif cmd == 'next':
        sender = sys.argv[2] if len(sys.argv) > 2 else None
        batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        s, ids = next_batch(sender, batch_size)
        if s:
            print(json.dumps({"sender": s, "ids": ids, "count": len(ids)}))
        else:
            print(json.dumps({"sender": None, "ids": [], "count": 0, "message": "All done!"}))
    elif cmd == 'remaining':
        sender = sys.argv[2]
        remaining = get_remaining(sender)
        print(f"{len(remaining)} remaining for {sender}")
