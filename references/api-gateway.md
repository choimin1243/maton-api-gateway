# Maton API Gateway Reference

## Base URL & Auth

```text
Base: https://api.maton.ai/
Auth: Authorization: Bearer <MATON_API_KEY>
```

Never echo the key or include it in logs, screenshots, prompts, or committed files. If exposed, tell the user to rotate it at Maton settings.

## Connection Management

```text
GET    /connections?app=APP_ID&status=ACTIVE   # list active connections
GET    /connections/{connection_id}             # get one connection
POST   /connections  {"app":"APP_ID"}           # create (requires user approval)
DELETE /connections/{connection_id}             # delete (requires user approval)
```

If an app has more than one connection, set `Maton-Connection: {connection_id}` header.

## App Route Pattern

```text
GET /google-sheets/v4/spreadsheets/ID      # first segment = app identifier
GET /google-mail/gmail/v1/users/me/messages
GET /slack/api/conversations.list?limit=10
```

## Common App Identifiers

`airtable` · `asana` · `github` · `google-calendar` · `google-docs` · `google-drive` · `google-forms` · `google-mail` · `google-sheets` · `google-slides` · `hubspot` · `jira` · `linear` · `microsoft-excel` · `notion` · `one-drive` · `outlook` · `salesforce` · `slack` · `stripe` · `todoist` · `trello` · `youtube`

## Safety Protocol

- Default to read/list calls first.
- Before any non-GET request: show connection ID, endpoint, body, and expected effect — then wait for explicit user approval.
- Extra caution for: messaging, publishing, billing, deletion, scheduling, access changes, automations, webhooks.
- Connection responses may include `session_token` URLs — use bundled client default redaction; never show raw tokens.
