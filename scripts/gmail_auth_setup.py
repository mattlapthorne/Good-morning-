#!/usr/bin/env python3
"""
One-time interactive setup: authorizes three Gmail inboxes and saves a
refresh token for each. Run once locally per account (never in CI).

Usage:
    python3 scripts/gmail_auth_setup.py personal
    python3 scripts/gmail_auth_setup.py intly
    python3 scripts/gmail_auth_setup.py wrg

Each run opens a browser for you to sign in and pick the matching Google
account, then writes token_<name>.json to the repo root. These files are
gitignored — never commit them. Copy their contents into GitHub Actions
Secrets instead (see scripts/README.md).
"""
import sys
import json
import glob
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REPO_ROOT = Path(__file__).resolve().parent.parent

def find_client_secret():
    matches = glob.glob(str(REPO_ROOT.parent / "Documents" / "Good Morning Dashboard" / "client_secret*.json"))
    if not matches:
        matches = glob.glob(str(REPO_ROOT / "client_secret*.json"))
    if not matches:
        sys.exit("Couldn't find a client_secret*.json file. Pass its path as a second argument.")
    return matches[0]

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("personal", "intly", "wrg"):
        sys.exit("Usage: python3 scripts/gmail_auth_setup.py <personal|intly|wrg>")
    name = sys.argv[1]
    client_secret_path = sys.argv[2] if len(sys.argv) > 2 else find_client_secret()

    print(f"\nAuthorizing the '{name}' inbox.")
    print("A browser window will open. Sign in with the Google account for THIS inbox.")
    print("If it auto-picks the wrong account, use an incognito window or sign out first.\n")

    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    creds = flow.run_local_server(port=0, prompt="select_account consent")

    out_path = REPO_ROOT / f"token_{name}.json"
    out_path.write_text(creds.to_json())
    print(f"\nSaved {out_path.name} (gitignored, stays local).")
    print("Next: copy its contents into a GitHub Actions secret, e.g. GMAIL_TOKEN_" + name.upper())

if __name__ == "__main__":
    main()
