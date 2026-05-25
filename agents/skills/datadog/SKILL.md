---
name: datadog
description: Search Datadog logs and monitors with MCP or direct API calls, using public-safe query patterns.
---

# Datadog

Use Datadog MCP tools when available. Use direct API calls only when local `DD_API_KEY` and `DD_APP_KEY` are available.

Never print API or application key values.

## Log Search

Use `@` for indexed fields:

```text
@workflow_run_id:wr_123
@task_id:tsk_123
@task_v2_id:tsk_v2_123
@workflow_permanent_id:wpid_123
@organization_id:o_123
@step_id:stp_123
@run_id:wr_123
```

Direct API example:

```bash
curl -s -X POST "https://api.us5.datadoghq.com/api/v2/logs/events/search" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filter":{"query":"@workflow_run_id:wr_123","from":"now-1h","to":"now"}}'
```

Get monitors:

```bash
curl -s "https://api.us5.datadoghq.com/api/v1/monitor" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY"
```
