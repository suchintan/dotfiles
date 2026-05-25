---
name: google-workspace
description: Use the gws CLI for Google Workspace APIs including Drive, Sheets, Docs, Slides, Gmail, Calendar, Forms, Tasks, and People.
argument-hint: "<service> <action> [details]"
---

# Google Workspace

Use the `gws` CLI for Google Workspace tasks instead of browser automation when possible.

## Auth

`gws` is installed globally by `install.sh` with:

```bash
npm install -g @googleworkspace/cli
```

Credentials are local. Do not print OAuth tokens, refresh tokens, client secrets, or credential files.

## ID Patterns

```text
https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
https://docs.google.com/document/d/<DOCUMENT_ID>/edit
https://docs.google.com/presentation/d/<PRESENTATION_ID>/edit
https://drive.google.com/file/d/<FILE_ID>/view
```

## Quick Reference

```bash
gws drive files list --params '{"pageSize": 10, "fields": "files(id,name,mimeType)"}'
gws sheets spreadsheets values get --params '{"spreadsheetId": "SPREADSHEET_ID", "range": "Sheet1!A1:Z100"}'
gws docs documents get --params '{"documentId": "DOCUMENT_ID"}'
gws slides presentations get --params '{"presentationId": "PRESENTATION_ID"}'
gws gmail users messages list --params '{"userId": "me", "maxResults": 10}'
gws calendar events list --params '{"calendarId": "primary", "maxResults": 10}'
```

## Sheets

Read values:

```bash
gws sheets spreadsheets values get \
  --params '{"spreadsheetId": "SPREADSHEET_ID", "range": "Sheet1"}'
```

Write values:

```bash
gws sheets spreadsheets values update \
  --params '{"spreadsheetId": "SPREADSHEET_ID", "range": "Sheet1!A1:B2", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["Header 1", "Header 2"], ["Value 1", "Value 2"]]}'
```

Append rows:

```bash
gws sheets spreadsheets values append \
  --params '{"spreadsheetId": "SPREADSHEET_ID", "range": "Sheet1", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["Value 1", "Value 2"]]}'
```

## Docs

Get text:

```bash
gws docs documents get --params '{"documentId": "DOCUMENT_ID"}' | \
  jq -r '.body.content[].paragraph?.elements[]?.textRun?.content // empty'
```

Insert text:

```bash
gws docs documents batchUpdate \
  --params '{"documentId": "DOCUMENT_ID"}' \
  --json '{"requests":[{"insertText":{"location":{"index":1},"text":"Text\\n"}}]}'
```

## Drive

Search files:

```bash
gws drive files list \
  --params '{"q": "name contains \"report\"", "pageSize": 10, "fields": "files(id,name,mimeType)"}'
```

Export a Google file:

```bash
gws drive files export \
  --params '{"fileId": "FILE_ID", "mimeType": "application/pdf"}' \
  --output ./exported.pdf
```

## Discover Schemas

```bash
gws schema drive.files.list
gws schema sheets.spreadsheets.values.get
gws schema docs.documents.batchUpdate --resolve-refs
gws schema slides.presentations.batchUpdate --resolve-refs
```
