#!/usr/bin/env python3
"""Create a Google Form via Maton API.

Usage:
    python scripts/create_form.py --data form.json --connection CONN_ID

form.json schema:
    {
        "title":         "설문 제목",
        "description":   "설문 설명 (optional)",
        "collect_email": false,
        "questions": [
            { "type": "text",      "title": "이름",    "required": true },
            { "type": "paragraph", "title": "의견" },
            { "type": "radio",     "title": "학년",    "options": ["1학년","2학년","3학년"], "required": true },
            { "type": "checkbox",  "title": "과목",    "options": ["수학","영어","과학"] },
            { "type": "dropdown",  "title": "지역",    "options": ["서울","부산","대구"] },
            { "type": "scale",     "title": "만족도",  "low": 1, "high": 5,
                                   "low_label": "매우 불만족", "high_label": "매우 만족" },
            { "type": "date",      "title": "날짜" },
            { "type": "time",      "title": "시간" },
            { "type": "section",   "title": "섹션 제목", "description": "섹션 설명" }
        ]
    }

Prints edit URL and responder URL on success.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

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
            "Authorization":    f"Bearer {api_key}",
            "Content-Type":     "application/json",
            "Accept":           "application/json",
            "Maton-Connection": connection_id,
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")


# ── Item builders ─────────────────────────────────────────────────────────────

def _text_item(q: dict) -> dict:
    return {
        "title": q["title"],
        "questionItem": {"question": {
            "required": q.get("required", False),
            "textQuestion": {"paragraph": q.get("type") == "paragraph"},
        }},
    }


def _choice_item(q: dict, choice_type: str) -> dict:
    return {
        "title": q["title"],
        "questionItem": {"question": {
            "required": q.get("required", False),
            "choiceQuestion": {
                "type": choice_type,
                "options": [{"value": str(opt)} for opt in q.get("options", [])],
            },
        }},
    }


def _scale_item(q: dict) -> dict:
    return {
        "title": q["title"],
        "questionItem": {"question": {
            "required": q.get("required", False),
            "scaleQuestion": {
                "low":       q.get("low", 1),
                "high":      q.get("high", 5),
                "lowLabel":  q.get("low_label", ""),
                "highLabel": q.get("high_label", ""),
            },
        }},
    }


def _date_item(q: dict) -> dict:
    return {
        "title": q["title"],
        "questionItem": {"question": {
            "required": q.get("required", False),
            "dateQuestion": {"includeTime": q.get("include_time", False)},
        }},
    }


def _time_item(q: dict) -> dict:
    return {
        "title": q["title"],
        "questionItem": {"question": {
            "required": q.get("required", False),
            "timeQuestion": {"duration": q.get("duration", False)},
        }},
    }


def _section_item(q: dict) -> dict:
    item: dict = {"title": q["title"], "pageBreakItem": {}}
    if q.get("description"):
        item["description"] = q["description"]
    return item


_BUILDERS = {
    "text":      lambda q: _text_item(q),
    "paragraph": lambda q: _text_item(q),
    "radio":     lambda q: _choice_item(q, "RADIO"),
    "checkbox":  lambda q: _choice_item(q, "CHECKBOX"),
    "dropdown":  lambda q: _choice_item(q, "DROP_DOWN"),
    "scale":     lambda q: _scale_item(q),
    "date":      lambda q: _date_item(q),
    "time":      lambda q: _time_item(q),
    "section":   lambda q: _section_item(q),
}


def build_batch_requests(form_data: dict) -> list[dict]:
    requests: list[dict] = []

    if form_data.get("description"):
        requests.append({
            "updateFormInfo": {
                "info": {"description": form_data["description"]},
                "updateMask": "description",
            }
        })

    if form_data.get("collect_email", False):
        requests.append({
            "updateSettings": {
                "settings": {"emailCollectionType": "VERIFIED"},
                "updateMask": "emailCollectionType",
            }
        })

    for idx, q in enumerate(form_data.get("questions", [])):
        qtype = q.get("type", "text").lower()
        builder = _BUILDERS.get(qtype, _BUILDERS["text"])
        requests.append({
            "createItem": {
                "item": builder(q),
                "location": {"index": idx},
            }
        })

    return requests


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Google Form via Maton API.")
    parser.add_argument("--data",       required=True, help="UTF-8 JSON form definition file")
    parser.add_argument("--connection", required=True, help="Maton google-forms connection ID")
    parser.add_argument("--form-id",    default=None,  help="Update existing form instead of creating")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8-sig") as f:
        form_data = json.load(f)

    form_id: str | None = args.form_id

    if not form_id:
        print("Creating form...", file=sys.stderr)
        result = _post(
            "/google-forms/v1/forms",
            {"info": {"title": form_data.get("title", "Untitled Form")}},
            args.connection,
        )
        form_id = result["formId"]
        responder_uri = result.get("responderUri", "")
        print(f"  id: {form_id}", file=sys.stderr)
    else:
        print(f"Updating form: {form_id}", file=sys.stderr)
        responder_uri = f"https://docs.google.com/forms/d/e/{form_id}/viewform"

    batch = build_batch_requests(form_data)
    if batch:
        print(f"Adding {len(batch)} items...", file=sys.stderr)
        _post(
            f"/google-forms/v1/forms/{form_id}:batchUpdate",
            {"requests": batch},
            args.connection,
        )

    edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    print(f"Edit:    {edit_url}")
    print(f"Respond: {responder_uri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
