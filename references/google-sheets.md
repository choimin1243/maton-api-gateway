# Google Sheets Reference

## data.json — Full Schema

| Field | Required | Description |
|---|---|---|
| `title` | no | Merged title row at top (14pt bold, theme color) |
| `sheet_name` | no | Sheet tab name |
| `headers` | yes | Column header labels |
| `rows` | yes | 2-D array of values — strings, numbers, or `=formula` |
| `col_widths` | no | Pixel width per column (default: first col 180px, rest 130px) |
| `row_height` | no | Data row height in px (default 24) |
| `freeze` | no | Freeze title+header rows (default true) |
| `number_cols` | no | Column indices to right-align for numbers |

## Themes

| Theme | Title bg | Header bg | Stripe bg |
|---|---|---|---|
| `blue` (default) | `#1A237E` | `#3949AB` | `#E8EAF6` |
| `teal` | `#004D40` | `#00796B` | `#E0F2F1` |
| `green` | `#1B5E20` | `#388E3C` | `#E8F5E9` |
| `orange` | `#BF360C` | `#E64A19` | `#FBE9E7` |
| `purple` | `#4A148C` | `#7B1FA2` | `#F3E5F5` |
| `red` | `#B71C1C` | `#D32F2F` | `#FFEBEE` |

All themes: title 14pt bold white, header 10pt bold white, alternating stripes, thick outer border + thin inner grid, frozen header rows.

## create_sheet.py Options

```bash
python scripts/create_sheet.py \
  --data data.json \
  --connection CONNECTION_ID \
  [--theme blue] \
  [--title "Override Title"] \
  [--spreadsheet-id ID]   # update existing instead of creating
```

## How It Works

1. `POST /google-sheets/v4/spreadsheets` — creates spreadsheet with embedded `rowData`, `merges`, and frozen rows.
2. `POST /google-sheets/v4/spreadsheets/{id}:batchUpdate` — applies column widths, row heights, and borders.

## Find Connection ID

```bash
python scripts/maton_api.py GET /connections --param app=google-sheets --param status=ACTIVE
```

## Encoding Note

Never use the `values/{range}?valueInputOption=...` path through Maton for Korean/spaced range names — use `batchUpdate` with numeric `sheetId` ranges. When writing JSON files from PowerShell, use `Out-File -Encoding utf8`; the bundled scripts read with `utf-8-sig` to handle BOM.
