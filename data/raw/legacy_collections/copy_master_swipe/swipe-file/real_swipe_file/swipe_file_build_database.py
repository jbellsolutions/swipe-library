#!/usr/bin/env python3
"""
Build a consolidated swipe file database from all indexed emails.
Merges ID files (subject/date metadata) with any full content already pulled.
Outputs a single master JSON database.
"""
import json
import os
import glob

SWIPE_DIR = "/sessions/laughing-quirky-carson/swipe-file"
IDS_DIR = os.path.join(SWIPE_DIR, "ids")
CONTENT_DIR = os.path.join(SWIPE_DIR, "content")
OUTPUT_DB = os.path.join(SWIPE_DIR, "swipe_database.json")

SENDER_META = {
    "brian_kurtz": {"display": "Brian Kurtz", "email": "brian@briankurtz.net", "specialty": "Direct response, classic copywriting, lifetime value"},
    "jay_abraham": {"display": "Jay Abraham", "email": "jay@abraham.com", "specialty": "Strategy, leverage, growth hacking, partnerships"},
    "todd_brown": {"display": "Todd Brown", "email": "support@marketingfunnelautomation.com", "specialty": "Marketing funnels, unique mechanisms, E5 method"},
    "alex_hormozi": {"display": "Alex Hormozi", "email": "value@acquisition.com", "specialty": "Offers, scaling, business acquisition, value equations"},
    "tom_bilyeu": {"display": "Tom Bilyeu", "email": "tombilyeu@impacttheory.com", "specialty": "Mindset, motivation, personal development, impact"},
    "lead_gen_jay": {"display": "Lead Gen Jay", "email": "jay@leadgenjay.com", "specialty": "Cold email, lead generation, outbound, B2B"},
    "liam_ottley": {"display": "Liam Ottley", "email": "admin@liamottley.com", "specialty": "AI agencies, automation, scaling AI businesses"},
    "bill_mueller": {"display": "Bill Mueller", "email": "bill@storysalesmachine.com", "specialty": "Storytelling, story-based selling, email sequences"},
    "jon_buchan": {"display": "Jon Buchan", "email": "jon@charm-offensive.co.uk", "specialty": "Creative cold email, humor, pattern interrupts, charm"},
}

def build():
    database = {
        "version": "1.0",
        "total_emails": 0,
        "total_with_full_content": 0,
        "senders": {},
        "categories": {}
    }

    for sender_file in sorted(glob.glob(os.path.join(IDS_DIR, "*.json"))):
        sender_key = os.path.basename(sender_file).replace('.json', '')

        with open(sender_file) as f:
            id_list = json.load(f)

        meta = SENDER_META.get(sender_key, {"display": sender_key, "email": "", "specialty": ""})

        # Load any full content files
        content_map = {}
        content_dir = os.path.join(CONTENT_DIR, sender_key)
        if os.path.exists(content_dir):
            for cf in glob.glob(os.path.join(content_dir, "*.json")):
                with open(cf) as f:
                    content = json.load(f)
                content_map[content['id']] = content

        emails = []
        for entry in id_list:
            email_record = {
                "id": entry["id"],
                "subject": entry.get("subject", ""),
                "date": entry.get("date", ""),
                "has_full_content": entry["id"] in content_map,
            }
            if entry["id"] in content_map:
                email_record["body"] = content_map[entry["id"]].get("body", "")
                database["total_with_full_content"] += 1

            emails.append(email_record)

        database["senders"][sender_key] = {
            "display_name": meta["display"],
            "email": meta["email"],
            "specialty": meta["specialty"],
            "total_emails": len(emails),
            "full_content_count": len(content_map),
            "emails": emails
        }
        database["total_emails"] += len(emails)

    with open(OUTPUT_DB, 'w') as f:
        json.dump(database, f, indent=2)

    print(f"Database built: {OUTPUT_DB}")
    print(f"Total emails: {database['total_emails']}")
    print(f"With full content: {database['total_with_full_content']}")
    print(f"Senders: {len(database['senders'])}")

    # Also output a compact version for quick loading
    compact = {
        "version": "1.0",
        "total": database["total_emails"],
        "full_content": database["total_with_full_content"],
        "senders": {}
    }
    for sk, sv in database["senders"].items():
        compact["senders"][sk] = {
            "name": sv["display_name"],
            "specialty": sv["specialty"],
            "count": sv["total_emails"],
            "full": sv["full_content_count"],
            "subjects": [e["subject"] for e in sv["emails"]]
        }

    compact_path = os.path.join(SWIPE_DIR, "swipe_compact.json")
    with open(compact_path, 'w') as f:
        json.dump(compact, f)
    print(f"Compact index: {compact_path}")

if __name__ == '__main__':
    build()
