# RTK - Rust Token Killer

**Usage**: Token-optimized CLI proxy (60-90% savings on dev operations)

## ⚠️ Output Fidelity (read first)

The rtk hook intermittently returns cached, summarized, or **fabricated** output. Documented incidents: fabricated `git commit` success (HEAD never moved), silent hard-block of `gh pr create` (instant exit 1 — even for commands merely *containing* that substring), mangled long hashes/SHAs, SIGPIPE-killed `git push`/`uv sync` pipes, corrupted `curl | python` pipes, rewritten grep/tail output (`grep -v` ignored), and `rtk proxy` not propagating wrapped exit codes.

Rules:
- Run anything load-bearing via `rtk proxy <cmd>` AND verify with an independent read-back (`git log -1`, `git ls-remote`, `gh pr view`, API read-back).
- Never gate control flow on an exit code that passes through rtk; have tools write their own machine-readable output files (e.g. `--reporter=json --outputFile=...`) and parse them with python.
- Full failure catalog: memory `reference_rtk_hook_corrupts_verbatim_output`.

## Meta Commands (always use rtk directly)

```bash
rtk gain              # Show token savings analytics
rtk gain --history    # Show command usage history with savings
rtk discover          # Analyze Claude Code history for missed opportunities
rtk proxy <cmd>       # Execute raw command without filtering (for debugging)
```

## Installation Verification

```bash
rtk --version         # Should show: rtk X.Y.Z
rtk gain              # Should work (not "command not found")
which rtk             # Verify correct binary
```

⚠️ **Name collision**: If `rtk gain` fails, you may have reachingforthejack/rtk (Rust Type Kit) installed instead.

## Hook-Based Usage

All other commands are automatically rewritten by the Claude Code hook.
Example: `git status` → `rtk git status` (transparent, 0 tokens overhead)

Full command reference: `rtk --help`.
