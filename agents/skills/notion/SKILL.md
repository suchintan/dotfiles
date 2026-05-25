---
name: notion
description: Use the Notion API for search, fetch, and page/block updates when a Notion API token is available locally.
---

# Notion

Use the Notion API directly when MCP tools are unavailable or when direct API calls are clearer.

## Auth

Requires `NOTION_API_KEY` in the environment. Never print token values.

Every request needs:

```bash
-H "Authorization: Bearer $NOTION_API_KEY"
-H "Notion-Version: 2022-06-28"
```

## Common Calls

Search:

```bash
curl -s -X POST "https://api.notion.com/v1/search" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"query":"search term","page_size":10}'
```

Fetch page metadata:

```bash
curl -s "https://api.notion.com/v1/pages/PAGE_ID" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28"
```

Fetch child blocks:

```bash
curl -s "https://api.notion.com/v1/blocks/BLOCK_ID/children?page_size=100" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28"
```

Append blocks:

```bash
curl -s -X PATCH "https://api.notion.com/v1/blocks/BLOCK_ID/children" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2022-06-28" \
  -H "Content-Type: application/json" \
  -d '{"children":[{"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":"Hello"}}]}}]}'
```
