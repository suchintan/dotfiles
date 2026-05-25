---
name: slack
description: Use Slack's Web API for public-safe Slack read/write workflows when a Slack token is available in the local environment.
---

# Slack

Use Slack Web API calls with `curl` when Slack MCP tools are unavailable or when direct API access is clearer.

## Auth

Requires `SLACK_BOT_TOKEN` in the environment. Optional: `SLACK_TEAM_ID`.

Never print token values. Do not read secret files unless the user explicitly asks.

## Common Calls

### Search Messages

```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/search.messages" \
  -d "query=QUERY&count=20&sort=timestamp&sort_dir=desc"
```

Useful query modifiers: `from:<@USER_ID>`, `in:<#CHANNEL_ID>`, `on:YYYY-MM-DD`, `before:YYYY-MM-DD`, `after:YYYY-MM-DD`.

### Read Channel History

```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.history?channel=CHANNEL_ID&limit=50"
```

Use channel IDs, not channel names. If a result is paginated, follow `response_metadata.next_cursor`.

### Read Thread Replies

```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.replies?channel=CHANNEL_ID&ts=THREAD_TS"
```

### List Channels

```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=200"
```

Always paginate before concluding a channel does not exist.

### List Users

```bash
curl -s -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/users.list"
```

### Post Message

Only post when the user has asked for a Slack write or approved the exact message.

```bash
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel":"CHANNEL_ID","text":"Message text"}'
```

### Reply To Thread

```bash
curl -s -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel":"CHANNEL_ID","thread_ts":"THREAD_TS","text":"Reply text"}'
```

### Add Reaction

```bash
curl -s -X POST "https://slack.com/api/reactions.add" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel":"CHANNEL_ID","timestamp":"MESSAGE_TS","name":"thumbsup"}'
```
