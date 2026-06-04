# Google Forms Reference

## form.json — Full Schema

```json
{
  "title":         "설문 제목",
  "description":   "설문 설명 (optional)",
  "collect_email": false,
  "questions":     [ ...see question types below... ]
}
```

## Question Types

| type | Required fields | Optional fields |
|---|---|---|
| `text` | `title` | `required` |
| `paragraph` | `title` | `required` |
| `radio` | `title`, `options` | `required` |
| `checkbox` | `title`, `options` | `required` |
| `dropdown` | `title`, `options` | `required` |
| `scale` | `title`, `low`, `high` | `low_label`, `high_label`, `required` |
| `date` | `title` | `required`, `include_time` |
| `time` | `title` | `required`, `duration` |
| `section` | `title` | `description` |

### Examples

```json
{ "type": "text",      "title": "이름",     "required": true }
{ "type": "paragraph", "title": "의견" }
{ "type": "radio",     "title": "학년",     "options": ["1학년","2학년","3학년"], "required": true }
{ "type": "checkbox",  "title": "과목",     "options": ["수학","영어","과학"] }
{ "type": "dropdown",  "title": "지역",     "options": ["서울","부산","대구"] }
{ "type": "scale",     "title": "만족도",   "low": 1, "high": 5, "low_label": "불만족", "high_label": "만족" }
{ "type": "date",      "title": "날짜" }
{ "type": "time",      "title": "시간" }
{ "type": "section",   "title": "섹션 제목", "description": "섹션 설명" }
```

## create_form.py Options

```bash
python scripts/create_form.py \
  --data form.json \
  --connection CONNECTION_ID \
  [--form-id ID]   # update existing form instead of creating
```

Prints two URLs:
- **Edit**: `https://docs.google.com/forms/d/{formId}/edit`
- **Respond**: `https://docs.google.com/forms/d/e/{publishedId}/viewform`

## How It Works

1. `POST /google-forms/v1/forms` — creates the form with title.
2. `POST /google-forms/v1/forms/{formId}:batchUpdate` — adds all questions and sets description/email settings.

## API Paths

```text
POST /google-forms/v1/forms                         # create
POST /google-forms/v1/forms/{formId}:batchUpdate    # add/update items
GET  /google-forms/v1/forms/{formId}                # read form
GET  /google-forms/v1/forms/{formId}/responses      # read responses
```

## Find Connection ID

```bash
python scripts/maton_api.py GET /connections --param app=google-forms --param status=ACTIVE
```
