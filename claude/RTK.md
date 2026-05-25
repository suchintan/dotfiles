# RTK - Rust Token Killer

**Usage**: Token-optimized CLI proxy for shell commands.

## Meta Commands

```bash
rtk gain
rtk gain --history
rtk discover
rtk proxy <cmd>
```

## Hook-Based Usage

Claude Code uses the `rtk hook claude` PreToolUse hook from `claude/settings.json`, so Bash commands are rewritten automatically when the hook is active.

## Verification

```bash
rtk --version
rtk gain
which rtk
```
