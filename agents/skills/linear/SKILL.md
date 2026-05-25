---
name: linear
description: Work with Linear issues through MCP or the Linear GraphQL API when a token is available locally.
argument-hint: "[issue-id]"
---

# Linear

Prefer Linear MCP tools when configured. Use the GraphQL API when `LINEAR_API_KEY` is available locally.

Never print API key values.

## Fetch Issue

```bash
curl -s https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"query($id:String!){ issue(id:$id){ id identifier title description state { name } assignee { name } url } }","variables":{"id":"ISSUE_ID"}}'
```

## My Active Issues

```bash
curl -s https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { assignedIssues(first:20, filter:{state:{type:{nin:[completed,canceled]}}}) { nodes { identifier title state { name } url } } } }"}'
```

## Search Issues

```bash
curl -s https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"query($term:String!){ issues(first:20, filter:{title:{containsIgnoreCase:$term}}) { nodes { identifier title state { name } url } } }","variables":{"term":"SEARCH_TERM"}}'
```
