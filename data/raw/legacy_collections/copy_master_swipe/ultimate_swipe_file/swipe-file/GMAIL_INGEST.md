# Gmail Ingest

This script fetches Gmail messages by ID and writes one JSON file per message to:

`swipe-file/content/{sender_key}/{message_id}.json`

Default usage reads message IDs from `swipe-file/ids/{sender_key}.json`.

```bash
python3 swipe-file/scripts/swipe_file_gmail_ingest.py liam_ottley \
  --credentials /path/to/oauth_client.json \
  --token /path/to/token.json
```

You can also pass explicit IDs:

```bash
python3 swipe-file/scripts/swipe_file_gmail_ingest.py liam_ottley \
  --ids 19c94c81d44299a0 19c9273fde19b90d
```

The script prefers `text/plain`, falls back to stripped HTML, skips existing files
unless `--force` is set, and stores subject, sender, date, labels, snippet, and
full body text in each output JSON.
