# Claude Code MCP Setup

This file documents the public-safe MCP setup mirrored from the active Claude/Codex environment. Keep real credentials in local Claude/Codex config only.

## OAuth / Remote Servers

```bash
claude mcp add linear --transport http https://mcp.linear.app/mcp
claude mcp add notion --transport http https://mcp.notion.com/mcp
claude mcp add hex --transport http https://hc.hex.tech/mcp
claude mcp add pylon --transport http https://mcp.usepylon.com
claude mcp add superhuman-mail --transport http https://mcp.mail.superhuman.com/mcp
claude mcp add figma --transport http https://mcp.figma.com/mcp
```

## Header-Based Servers

Use local placeholders only when adding these:

```bash
claude mcp add context7 --transport http https://mcp.context7.com/mcp \
  --header "CONTEXT7_API_KEY: <YOUR_CONTEXT7_API_KEY>"

claude mcp add skyvern --transport http https://api.skyvern.com/mcp/ \
  --header "x-api-key: <YOUR_SKYVERN_API_KEY>"

claude mcp add skyvern-staging --transport http https://api-staging.skyvern.com/mcp/ \
  --header "x-api-key: <YOUR_SKYVERN_STAGING_API_KEY>"

claude mcp add exa --transport http https://mcp.exa.ai/mcp \
  --header "x-api-key: <YOUR_EXA_API_KEY>"
```

## Stdio Servers

For Datadog and Slack, configure env vars locally in Claude Code or in a private rendered config:

```json
{
  "datadog": {
    "type": "stdio",
    "command": "npx",
    "args": ["datadog-mcp-server"],
    "env": {
      "DD_API_KEY": "<YOUR_DATADOG_API_KEY>",
      "DD_APP_KEY": "<YOUR_DATADOG_APP_KEY>",
      "DD_SITE": "us5.datadoghq.com"
    }
  },
  "slack-as-me": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-slack"],
    "env": {
      "SLACK_BOT_TOKEN": "<YOUR_SLACK_BOT_TOKEN>",
      "SLACK_TEAM_ID": "<YOUR_SLACK_TEAM_ID>"
    }
  },
  "awslabs.redshift-mcp-server": {
    "command": "uvx",
    "args": ["awslabs.redshift-mcp-server@latest"],
    "env": {
      "AWS_PROFILE": "default",
      "AWS_DEFAULT_REGION": "us-east-1",
      "FASTMCP_LOG_LEVEL": "INFO"
    }
  }
}
```

## Verify

```bash
claude mcp list
```
