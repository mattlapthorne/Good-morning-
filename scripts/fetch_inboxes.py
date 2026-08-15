#!/usr/bin/env python3
"""
Fetches unread mail (last ~2 days) from three Gmail inboxes using saved
OAuth tokens and writes the raw data to data/inbox_raw.json.

Designed to run in GitHub Actions: reads each token from an env var
(GMAIL_TOKEN_PERSONAL, GMAIL_TOKEN_INTLY, GMAIL_TOKEN_WRG) containing the
full JSON produced by scripts/gmail_auth_setup.py. Locally, falls back to
reading token_<name>.json files from the repo root if the env var isn't set.

This script only fetches and writes raw data — it does NOT summarize or
categorize. That's done by the Claude routine, which reads this file.
"""
import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS = ["personal", "intly", "wrg"]
QUERY = "is:unread newer_than:2d in:inbox"
MAX_RESULTS = 50


def load_creds(name: str) -> Credentials:
    env_var = f"GMAIL_TOKEN_{name.upper()}"
    raw = os.environ.get(env_var)
    if raw:
        info = json.loads(raw)
    else:
        token_path = REPO_ROOT / f"token_{name}.json"
        if not token_path.exists():
            raise SystemExit(f"No {env_var} env var and no {token_path.name} found.")
        info = json.loads(token_path.read_text())

    creds = Credentials.from_authorized_user_info(info)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def fetch_account(name: str) -> dict:
    creds = load_creds(name)
    service = build("gmail", "v1", credentials=creds)

    profile = service.users().getProfile(userId="me").execute()
    email_address = profile.get("emailAddress", "unknown")

    results = service.users().messages().list(
        userId="me", q=QUERY, maxResults=MAX_RESULTS
    ).execute()
    message_ids = [m["id"] for m in results.get("messages", [])]

    messages = []
    for mid in message_ids:
        msg = service.users().messages().get(
            userId="me", id=mid, format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        messages.append({
            "id": mid,
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
        })

    return {
        "account": name,
        "email_address": email_address,
        "unread_total_estimate": results.get("resultSizeEstimate", len(messages)),
        "messages_fetched": len(messages),
        "messages": messages,
    }


def main():
    output = {"generated_at_utc": None, "accounts": {}}
    import datetime
    output["generated_at_utc"] = datetime.datetime.utcnow().isoformat() + "Z"

    for name in ACCOUNTS:
        try:
            output["accounts"][name] = fetch_account(name)
            print(f"OK: {name} -> {output['accounts'][name]['email_address']} "
                  f"({output['accounts'][name]['messages_fetched']} messages)")
        except Exception as e:
            output["accounts"][name] = {"account": name, "error": str(e)}
            print(f"FAILED: {name} -> {e}")

    data_dir = REPO_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    out_path = data_dir / "inbox_raw.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
