#!/usr/bin/env python3
"""
Fetch Gmail messages by ID and save them as structured swipe-file JSON.

Expected output layout:
  swipe-file/content/{sender_key}/{message_id}.json

The script reads sender inventories from swipe-file/ids/{sender_key}.json by
default, but you can also pass explicit Gmail message IDs.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IDS_DIR = PROJECT_ROOT / "ids"
CONTENT_DIR = PROJECT_ROOT / "content"


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


class _HTMLToText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
        elif tag in {"p", "div", "br", "tr", "li", "section", "header", "footer", "article"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in {"p", "div", "br", "tr", "li", "section", "header", "footer", "article"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(data)


def strip_html(html: str) -> str:
    parser = _HTMLToText()
    parser.feed(html)
    parser.close()
    text = unescape("".join(parser.parts))
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\u200b|\ufeff", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def decode_base64url(data: str) -> str:
    padding = "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(data + padding)
    return raw.decode("utf-8", errors="replace")


def get_header(headers: list[dict[str, Any]], name: str) -> str:
    wanted = name.lower()
    for header in headers:
        if header.get("name", "").lower() == wanted:
            return str(header.get("value", ""))
    return ""


def collect_parts(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    parts = payload.get("parts") or []
    if parts:
        for part in parts:
            yield from collect_parts(part)
    else:
        yield payload


def extract_body(payload: dict[str, Any]) -> str:
    candidates_plain: list[str] = []
    candidates_html: list[str] = []

    for part in collect_parts(payload):
        mime_type = part.get("mimeType", "")
        body = part.get("body", {}) or {}
        data = body.get("data")
        if not data:
            continue

        try:
            decoded = decode_base64url(str(data))
        except Exception:
            continue

        if mime_type == "text/plain":
            candidates_plain.append(clean_text(decoded))
        elif mime_type == "text/html":
            candidates_html.append(strip_html(decoded))

    if candidates_plain:
        return clean_text("\n\n".join(candidates_plain))
    if candidates_html:
        return clean_text("\n\n".join(candidates_html))

    body = payload.get("body", {}) or {}
    data = body.get("data")
    if data:
        try:
            decoded = decode_base64url(str(data))
            if payload.get("mimeType") == "text/html":
                return strip_html(decoded)
            return clean_text(decoded)
        except Exception:
            return ""

    return ""


def load_ids(sender_key: str) -> list[dict[str, Any]]:
    ids_file = IDS_DIR / f"{sender_key}.json"
    if not ids_file.exists():
        raise FileNotFoundError(f"Unknown sender '{sender_key}'. Expected file: {ids_file}")
    with ids_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Invalid sender file: {ids_file} (expected a JSON array)")
    return data


def parse_id_args(values: list[str]) -> list[str]:
    message_ids: list[str] = []
    for value in values:
        for chunk in re.split(r"[,\s]+", value.strip()):
            if chunk:
                message_ids.append(chunk)
    return message_ids


def ensure_dependencies() -> tuple[Any, Any, Any]:
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
    except ImportError as exc:
        raise SystemExit(
            "Missing Gmail API dependencies. Install google-api-python-client, "
            "google-auth-oauthlib, and google-auth-httplib2."
        ) from exc
    return Credentials, InstalledAppFlow, Request


def build_service(credentials_path: Path, token_path: Path, scopes: list[str]) -> Any:
    Credentials, InstalledAppFlow, Request = ensure_dependencies()
    from googleapiclient.discovery import build

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise FileNotFoundError(
                    f"OAuth client file not found: {credentials_path}. "
                    "Provide a Google OAuth desktop client JSON."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), scopes)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def fetch_message(service: Any, message_id: str, format_: str = "full") -> dict[str, Any]:
    return service.users().messages().get(userId="me", id=message_id, format=format_).execute()


def save_message(sender_key: str, message_id: str, message: dict[str, Any], overwrite: bool) -> Path:
    sender_dir = CONTENT_DIR / sender_key
    sender_dir.mkdir(parents=True, exist_ok=True)
    output_path = sender_dir / f"{message_id}.json"
    if output_path.exists() and not overwrite:
        return output_path

    payload = message.get("payload", {}) or {}
    headers = payload.get("headers", []) or []
    subject = get_header(headers, "Subject")
    from_header = get_header(headers, "From")
    to_header = get_header(headers, "To")
    cc_header = get_header(headers, "Cc")
    bcc_header = get_header(headers, "Bcc")
    date_header = get_header(headers, "Date")

    body_text = extract_body(payload)

    record = {
        "id": message.get("id", message_id),
        "threadId": message.get("threadId", ""),
        "labelIds": message.get("labelIds", []),
        "snippet": message.get("snippet", ""),
        "subject": subject,
        "date": date_header,
        "sender": from_header,
        "to": to_header,
        "cc": cc_header,
        "bcc": bcc_header,
        "body": body_text,
        "body_text": body_text,
        "raw": {
            "internalDate": message.get("internalDate", ""),
            "historyId": message.get("historyId", ""),
        },
    }

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)

    return output_path


def resolve_message_ids(args: argparse.Namespace) -> list[str]:
    if args.ids:
        return parse_id_args(args.ids)

    entries = load_ids(args.sender_key)
    if args.limit is not None:
        entries = entries[: args.limit]
    return [str(entry["id"]) for entry in entries if entry.get("id")]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Gmail messages into swipe-file JSON.")
    parser.add_argument("sender_key", help="Sender key matching swipe-file/ids/{sender_key}.json")
    parser.add_argument("--ids", nargs="*", help="Explicit Gmail message IDs (overrides ids file)")
    parser.add_argument("--limit", type=int, help="Limit the number of IDs processed from the sender file")
    parser.add_argument("--batch-size", type=int, default=1, help="Process messages in batches of N")
    parser.add_argument("--force", action="store_true", help="Overwrite existing content files")
    parser.add_argument(
        "--credentials",
        default=str(PROJECT_ROOT / "credentials.json"),
        help="Path to OAuth client secrets JSON",
    )
    parser.add_argument(
        "--token",
        default=str(PROJECT_ROOT / "token.json"),
        help="Path to cached user token JSON",
    )
    parser.add_argument(
        "--scopes",
        nargs="*",
        default=["https://www.googleapis.com/auth/gmail.readonly"],
        help="OAuth scopes to request",
    )
    parser.add_argument(
        "--format",
        default="full",
        choices=["full", "metadata", "minimal"],
        help="Gmail message format to request",
    )
    args = parser.parse_args(argv)

    try:
        message_ids = resolve_message_ids(args)
    except Exception as exc:
        eprint(f"Error: {exc}")
        return 2

    if not message_ids:
        eprint("No message IDs found.")
        return 1

    credentials_path = Path(args.credentials).expanduser().resolve()
    token_path = Path(args.token).expanduser().resolve()

    try:
        service = build_service(credentials_path, token_path, args.scopes)
    except Exception as exc:
        eprint(f"Failed to initialize Gmail API client: {exc}")
        return 2

    total = len(message_ids)
    processed = 0
    skipped = 0
    failed = 0

    for index in range(0, total, max(1, args.batch_size)):
        batch = message_ids[index : index + max(1, args.batch_size)]
        for message_id in batch:
            output_path = CONTENT_DIR / args.sender_key / f"{message_id}.json"
            if output_path.exists() and not args.force:
                skipped += 1
                continue

            try:
                message = fetch_message(service, message_id, format_=args.format)
                save_message(args.sender_key, message_id, message, overwrite=args.force)
                processed += 1
                print(f"[{processed + skipped}/{total}] saved {message_id}")
            except Exception as exc:
                failed += 1
                eprint(f"[{processed + skipped + failed}/{total}] failed {message_id}: {exc}")

    print(
        json.dumps(
            {
                "sender_key": args.sender_key,
                "total_ids": total,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "output_dir": str(CONTENT_DIR / args.sender_key),
            },
            indent=2,
        )
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
