#!/usr/bin/env python3
"""Small Maton API Gateway client using MATON_API_KEY."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE_URL = "https://api.maton.ai"
SENSITIVE_KEY_PARTS = ("api_key", "authorization", "password", "secret", "session_token", "token")


def get_api_key() -> str | None:
    api_key = os.environ.get("MATON_API_KEY")
    if api_key or os.name != "nt":
        return api_key
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, "MATON_API_KEY")
            return value
    except OSError:
        return None


def parse_kv(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"Expected KEY=VALUE, got: {value}")
        key, item = value.split("=", 1)
        result[key] = item
    return result


def build_url(path: str, params: dict[str, str]) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        url = f"{BASE_URL}/{path.lstrip('/')}"
    if params:
        separator = "&" if urllib.parse.urlsplit(url).query else "?"
        url = f"{url}{separator}{urllib.parse.urlencode(params)}"
    return url


def redact(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = key.lower()
            if any(part in lowered for part in SENSITIVE_KEY_PARTS):
                result[key] = "[REDACTED]"
            elif lowered == "url" and isinstance(item, str) and "session_token=" in item:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Call Maton API Gateway routes.")
    parser.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    parser.add_argument("path", help="Path such as /connections or /slack/api/...")
    parser.add_argument("--param", action="append", default=[], help="Query parameter KEY=VALUE")
    parser.add_argument("--header", action="append", default=[], help="Extra header KEY=VALUE")
    parser.add_argument("--connection", help="Maton connection ID for Maton-Connection header")
    parser.add_argument("--json", dest="json_body", help="JSON request body")
    parser.add_argument("--json-file", help="Read JSON request body from a UTF-8 file")
    parser.add_argument("--raw", action="store_true", help="Print unredacted response")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("MATON_API_KEY is not set.", file=sys.stderr)
        return 2

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    headers.update(parse_kv(args.header))
    if args.connection:
        headers["Maton-Connection"] = args.connection

    data = None
    if args.json_body is not None and args.json_file is not None:
        print("Use either --json or --json-file, not both.", file=sys.stderr)
        return 2
    if args.json_body is not None or args.json_file is not None:
        if args.json_file is not None:
            with open(args.json_file, "r", encoding="utf-8") as file:
                parsed = json.load(file)
        else:
            parsed = json.loads(args.json_body)
        data = json.dumps(parsed).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        build_url(args.path, parse_kv(args.param)),
        data=data,
        method=args.method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(body, file=sys.stderr)
        return 1

    if not raw:
        return 0

    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
        if not args.raw:
            payload = redact(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    except json.JSONDecodeError:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
