#!/usr/bin/env python3
"""Generate beautiful Google Sheets batchUpdate request bodies.

Usage:
    python scripts/sheets_design.py --data data.json --output body.json [--theme blue] [--sheet-id 0]

data.json schema:
    {
        "title":       "표 제목 (optional)",
        "sheet_name":  "시트 탭 이름 (optional)",
        "headers":     ["열1", "열2", "열3"],
        "rows":        [["값1", 100, "값3"], ...],
        "col_widths":  [200, 120, 120],   // optional, pixels per column
        "row_height":  24,                 // optional, data row height (default 24)
        "freeze":      true,               // optional, freeze title+header rows (default true)
        "number_cols": [1, 2]              // optional, column indices to right-align
    }

Available themes: blue (default), teal, green, orange, purple, red
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any


# ── Color helpers ─────────────────────────────────────────────────────────────
def _rgb(hex_color: str) -> dict[str, float]:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return {"red": round(r / 255, 4), "green": round(g / 255, 4), "blue": round(b / 255, 4)}


WHITE = _rgb("FFFFFF")
DARK  = _rgb("212121")

THEMES: dict[str, dict[str, Any]] = {
    "blue": {
        "title_bg":  _rgb("1A237E"),   # deep navy
        "header_bg": _rgb("3949AB"),   # indigo 600
        "alt_bg":    _rgb("E8EAF6"),   # indigo 50
        "border":    _rgb("9FA8DA"),   # indigo 200
        "accent":    _rgb("3F51B5"),   # indigo 500
    },
    "teal": {
        "title_bg":  _rgb("004D40"),
        "header_bg": _rgb("00796B"),
        "alt_bg":    _rgb("E0F2F1"),
        "border":    _rgb("80CBC4"),
        "accent":    _rgb("009688"),
    },
    "green": {
        "title_bg":  _rgb("1B5E20"),
        "header_bg": _rgb("388E3C"),
        "alt_bg":    _rgb("E8F5E9"),
        "border":    _rgb("A5D6A7"),
        "accent":    _rgb("43A047"),
    },
    "orange": {
        "title_bg":  _rgb("BF360C"),
        "header_bg": _rgb("E64A19"),
        "alt_bg":    _rgb("FBE9E7"),
        "border":    _rgb("FFAB91"),
        "accent":    _rgb("FF5722"),
    },
    "purple": {
        "title_bg":  _rgb("4A148C"),
        "header_bg": _rgb("7B1FA2"),
        "alt_bg":    _rgb("F3E5F5"),
        "border":    _rgb("CE93D8"),
        "accent":    _rgb("9C27B0"),
    },
    "red": {
        "title_bg":  _rgb("B71C1C"),
        "header_bg": _rgb("D32F2F"),
        "alt_bg":    _rgb("FFEBEE"),
        "border":    _rgb("EF9A9A"),
        "accent":    _rgb("F44336"),
    },
}


# ── Cell format / value builders ─────────────────────────────────────────────
def _fmt(
    bg: dict | None = None,
    fg: dict | None = None,
    bold: bool = False,
    italic: bool = False,
    font_size: int = 10,
    h_align: str = "LEFT",
    v_align: str = "MIDDLE",
    wrap: bool = True,
) -> dict:
    result: dict[str, Any] = {
        "horizontalAlignment": h_align,
        "verticalAlignment": v_align,
        "wrapStrategy": "WRAP" if wrap else "OVERFLOW_CELL",
        "textFormat": {
            "bold": bold,
            "italic": italic,
            "fontSize": font_size,
            "foregroundColor": fg or DARK,
        },
    }
    if bg:
        result["backgroundColor"] = bg
    return result


def _val(v: Any) -> dict:
    if v is None or v == "":
        return {"stringValue": ""}
    if isinstance(v, bool):
        return {"boolValue": v}
    if isinstance(v, (int, float)):
        return {"numberValue": v}
    s = str(v)
    if s.startswith("="):
        return {"formulaValue": s}
    return {"stringValue": s}


def _update_cells(
    sheet_id: int,
    row_index: int,
    col_index: int,
    rows_data: list[list[Any]],
    rows_format: list[list[dict]],
) -> dict:
    rows = [
        {"values": [
            {"userEnteredValue": _val(v), "userEnteredFormat": f}
            for v, f in zip(row_vals, row_fmts)
        ]}
        for row_vals, row_fmts in zip(rows_data, rows_format)
    ]
    return {
        "updateCells": {
            "start": {"sheetId": sheet_id, "rowIndex": row_index, "columnIndex": col_index},
            "rows": rows,
            "fields": "userEnteredValue,userEnteredFormat",
        }
    }


def _dim(sheet_id: int, dim: str, start: int, end: int, px: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": dim, "startIndex": start, "endIndex": end},
            "properties": {"pixelSize": px},
            "fields": "pixelSize",
        }
    }


def _border_line(color: dict, width: int = 1, style: str = "SOLID") -> dict:
    return {"style": style, "width": width, "color": color}


# ── Main builder ─────────────────────────────────────────────────────────────
def build_requests(data: dict[str, Any], theme_name: str = "blue", sheet_id: int = 0) -> list[dict]:
    theme       = THEMES.get(theme_name, THEMES["blue"])
    headers     = data.get("headers", [])
    rows        = data.get("rows", [])
    title       = data.get("title")
    sheet_name  = data.get("sheet_name")
    col_widths  = data.get("col_widths")
    row_height  = int(data.get("row_height", 24))
    freeze      = data.get("freeze", True)
    number_cols: set[int] = set(data.get("number_cols", []))

    n_cols = max(len(headers), max((len(r) for r in rows), default=0), 1)
    has_title       = bool(title)
    header_row_idx  = 1 if has_title else 0
    data_start_idx  = header_row_idx + (1 if headers else 0)
    total_rows      = data_start_idx + len(rows)

    reqs: list[dict] = []

    # 1. Rename sheet tab
    if sheet_name:
        reqs.append({
            "updateSheetProperties": {
                "properties": {"sheetId": sheet_id, "title": sheet_name},
                "fields": "title",
            }
        })

    # 2. Column widths
    if col_widths:
        for i, w in enumerate(col_widths[:n_cols]):
            reqs.append(_dim(sheet_id, "COLUMNS", i, i + 1, w))
    else:
        reqs.append(_dim(sheet_id, "COLUMNS", 0, 1, 180))
        if n_cols > 1:
            reqs.append(_dim(sheet_id, "COLUMNS", 1, n_cols, 130))

    # 3. Row heights: title / header / data
    if has_title:
        reqs.append(_dim(sheet_id, "ROWS", 0, 1, 52))
    reqs.append(_dim(sheet_id, "ROWS", header_row_idx, header_row_idx + 1, 38))
    if rows:
        reqs.append(_dim(sheet_id, "ROWS", data_start_idx, data_start_idx + len(rows), row_height))

    # 4. Title row (merged, centered, large bold)
    if has_title:
        if n_cols > 1:
            reqs.append({
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0, "endRowIndex": 1,
                        "startColumnIndex": 0, "endColumnIndex": n_cols,
                    },
                    "mergeType": "MERGE_ALL",
                }
            })
        title_fmt = _fmt(bg=theme["title_bg"], fg=WHITE, bold=True, font_size=14, h_align="CENTER")
        title_row  = [title] + [""] * (n_cols - 1)
        reqs.append(_update_cells(sheet_id, 0, 0, [title_row], [[title_fmt] * n_cols]))

    # 5. Header row
    if headers:
        h_fmt = _fmt(bg=theme["header_bg"], fg=WHITE, bold=True, font_size=10, h_align="CENTER")
        padded = list(headers) + [""] * (n_cols - len(headers))
        reqs.append(_update_cells(sheet_id, header_row_idx, 0, [padded], [[h_fmt] * n_cols]))

    # 6. Data rows (alternating stripes)
    if rows:
        even_fmt = _fmt(fg=DARK, font_size=10)
        odd_fmt  = _fmt(bg=theme["alt_bg"], fg=DARK, font_size=10)

        all_vals: list[list[Any]] = []
        all_fmts: list[list[dict]] = []
        for i, row in enumerate(rows):
            base = even_fmt if i % 2 == 0 else odd_fmt
            padded_row = list(row) + [""] * (n_cols - len(row))
            row_fmts = []
            for col_i in range(n_cols):
                if col_i in number_cols:
                    row_fmts.append({**base, "horizontalAlignment": "RIGHT"})
                else:
                    row_fmts.append(base)
            all_vals.append(padded_row)
            all_fmts.append(row_fmts)

        reqs.append(_update_cells(sheet_id, data_start_idx, 0, all_vals, all_fmts))

    # 7. Borders (outer thick, inner thin)
    if total_rows > 0 and n_cols > 0:
        thin  = _border_line(theme["border"], width=1)
        thick = _border_line(theme["accent"], width=2)
        reqs.append({
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": n_cols,
                },
                "top": thick, "bottom": thick, "left": thick, "right": thick,
                "innerHorizontal": thin, "innerVertical": thin,
            }
        })

    # 8. Freeze title + header rows
    if freeze and data_start_idx > 0:
        reqs.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": data_start_idx},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        })

    return reqs


# ── Create-body builders (for POST /spreadsheets) ────────────────────────────

def build_create_body(
    data: dict[str, Any],
    theme_name: str = "blue",
    sheet_id: int = 0,
    spreadsheet_title: str | None = None,
) -> dict:
    """Return a POST /spreadsheets request body with embedded rowData, merges, and freeze."""
    theme       = THEMES.get(theme_name, THEMES["blue"])
    headers     = data.get("headers", [])
    rows        = data.get("rows", [])
    title       = data.get("title")
    sheet_name  = data.get("sheet_name")
    freeze      = data.get("freeze", True)
    number_cols: set[int] = set(data.get("number_cols", []))

    n_cols = max(len(headers), max((len(r) for r in rows), default=0), 1)
    has_title      = bool(title)
    header_row_idx = 1 if has_title else 0
    data_start_idx = header_row_idx + (1 if headers else 0)

    all_row_data: list[dict] = []
    merges: list[dict] = []

    def _cells(vals: list[Any], fmts: list[dict]) -> list[dict]:
        return [{"userEnteredValue": _val(v), "userEnteredFormat": f} for v, f in zip(vals, fmts)]

    # Title row
    if has_title:
        tf = _fmt(bg=theme["title_bg"], fg=WHITE, bold=True, font_size=14, h_align="CENTER")
        row = [title] + [""] * (n_cols - 1)
        all_row_data.append({"values": _cells(row, [tf] * n_cols)})
        if n_cols > 1:
            merges.append({
                "sheetId": sheet_id,
                "startRowIndex": 0, "endRowIndex": 1,
                "startColumnIndex": 0, "endColumnIndex": n_cols,
            })

    # Header row
    if headers:
        hf = _fmt(bg=theme["header_bg"], fg=WHITE, bold=True, font_size=10, h_align="CENTER")
        padded = list(headers) + [""] * (n_cols - len(headers))
        all_row_data.append({"values": _cells(padded, [hf] * n_cols)})

    # Data rows (alternating stripes)
    even_fmt = _fmt(fg=DARK, font_size=10)
    odd_fmt  = _fmt(bg=theme["alt_bg"], fg=DARK, font_size=10)
    for i, row in enumerate(rows):
        base       = even_fmt if i % 2 == 0 else odd_fmt
        padded_row = list(row) + [""] * (n_cols - len(row))
        fmts = [
            {**base, "horizontalAlignment": "RIGHT"} if ci in number_cols else base
            for ci in range(n_cols)
        ]
        all_row_data.append({"values": _cells(padded_row, fmts)})

    sheet_props: dict[str, Any] = {"sheetId": sheet_id}
    if sheet_name:
        sheet_props["title"] = sheet_name
    if freeze and data_start_idx > 0:
        sheet_props["gridProperties"] = {"frozenRowCount": data_start_idx}

    return {
        "properties": {"title": spreadsheet_title or title or "Untitled"},
        "sheets": [{
            "properties": sheet_props,
            "data": [{"rowData": all_row_data}],
            "merges": merges,
        }],
    }


def build_dimension_border_requests(
    data: dict[str, Any],
    sheet_id: int = 0,
    theme_name: str = "blue",
) -> dict:
    """Return a batchUpdate body with only dimension properties and borders."""
    theme      = THEMES.get(theme_name, THEMES["blue"])
    headers    = data.get("headers", [])
    rows       = data.get("rows", [])
    title      = data.get("title")
    col_widths = data.get("col_widths")
    row_height = int(data.get("row_height", 24))

    n_cols         = max(len(headers), max((len(r) for r in rows), default=0), 1)
    has_title      = bool(title)
    header_row_idx = 1 if has_title else 0
    data_start_idx = header_row_idx + (1 if headers else 0)
    total_rows     = data_start_idx + len(rows)

    reqs: list[dict] = []

    # Column widths
    if col_widths:
        for i, w in enumerate(col_widths[:n_cols]):
            reqs.append(_dim(sheet_id, "COLUMNS", i, i + 1, w))
    else:
        reqs.append(_dim(sheet_id, "COLUMNS", 0, 1, 180))
        if n_cols > 1:
            reqs.append(_dim(sheet_id, "COLUMNS", 1, n_cols, 130))

    # Row heights
    if has_title:
        reqs.append(_dim(sheet_id, "ROWS", 0, 1, 52))
    reqs.append(_dim(sheet_id, "ROWS", header_row_idx, header_row_idx + 1, 38))
    if rows:
        reqs.append(_dim(sheet_id, "ROWS", data_start_idx, data_start_idx + len(rows), row_height))

    # Borders
    if total_rows > 0 and n_cols > 0:
        thin  = _border_line(theme["border"], width=1)
        thick = _border_line(theme["accent"], width=2)
        reqs.append({
            "updateBorders": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0, "endRowIndex": total_rows,
                    "startColumnIndex": 0, "endColumnIndex": n_cols,
                },
                "top": thick, "bottom": thick, "left": thick, "right": thick,
                "innerHorizontal": thin, "innerVertical": thin,
            }
        })

    return {"requests": reqs}


# ── CLI ───────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Google Sheets batchUpdate body.")
    parser.add_argument("--data",     required=True,               help="UTF-8 JSON data file")
    parser.add_argument("--output",   required=True,               help="Output JSON file path")
    parser.add_argument("--theme",    default="blue", choices=list(THEMES), help="Color theme")
    parser.add_argument("--sheet-id", type=int, default=0,         help="Target sheet ID")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    requests = build_requests(data, theme_name=args.theme, sheet_id=args.sheet_id)
    body = {"requests": requests}

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=2)

    print(f"✓ {len(requests)} requests → {args.output}  (theme: {args.theme})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
