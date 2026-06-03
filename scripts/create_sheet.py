#!/usr/bin/env python3
"""Create and style a Google Sheet in one command via Maton API.

Usage:
    # Create new sheet (most common)
    python scripts/create_sheet.py --data data.json --connection CONN_ID [--theme blue]

    # Update existing sheet
    python scripts/create_sheet.py --data data.json --connection CONN_ID --spreadsheet-id SPREADSHEET_ID [--sheet-id 0]

Prints the Google Sheets URL on success.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sheets_design import THEMES, build_create_body, build_dimension_border_requests

BASE_URL = "https://api.maton.ai"


def _get_api_key() -> str | None:
    key = os.environ.get("MATON_API_KEY")
    if key or os.name != "nt":
        return key
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            value, _ = winreg.QueryValueEx(k, "MATON_API_KEY")
            return value
    except OSError:
        return None


def _post(path: str, body: dict, connection_id: str) -> dict:
    api_key = _get_api_key()
    if not api_key:
        raise SystemExit("MATON_API_KEY is not set.")

    url  = f"{BASE_URL}/{path.lstrip('/')}"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Authorization":  f"Bearer {api_key}",
            "Content-Type":   "application/json",
            "Accept":         "application/json",
            "Maton-Connection": connection_id,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and style a Google Sheet in one command.")
    parser.add_argument("--data",           required=True,
                        help="UTF-8 JSON data file (see SKILL.md for schema)")
    parser.add_argument("--connection",     required=True,
                        help="Maton Google Sheets connection ID")
    parser.add_argument("--theme",          default="blue", choices=list(THEMES),
                        help="Color theme (default: blue)")
    parser.add_argument("--title",          default=None,
                        help="Override spreadsheet title (default: use data.json title)")
    parser.add_argument("--spreadsheet-id", default=None,
                        help="Update existing spreadsheet instead of creating a new one")
    parser.add_argument("--sheet-id",       type=int, default=0,
                        help="Sheet tab ID to target (default: 0)")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    spreadsheet_id: str | None = args.spreadsheet_id

    # ── Step 1: create (or skip if updating existing) ────────────────────────
    if not spreadsheet_id:
        print("Creating spreadsheet…", file=sys.stderr)
        create_body = build_create_body(
            data,
            theme_name=args.theme,
            sheet_id=args.sheet_id,
            spreadsheet_title=args.title,
        )
        result = _post("/google-sheets/v4/spreadsheets", create_body, args.connection)
        spreadsheet_id = result["spreadsheetId"]
        print(f"  id: {spreadsheet_id}", file=sys.stderr)
    else:
        print(f"Updating: {spreadsheet_id}", file=sys.stderr)

    # ── Step 2: dimensions + borders ─────────────────────────────────────────
    print("Applying dimensions & borders…", file=sys.stderr)
    dim_body = build_dimension_border_requests(
        data, sheet_id=args.sheet_id, theme_name=args.theme
    )
    _post(
        f"/google-sheets/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
        dim_body,
        args.connection,
    )

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
