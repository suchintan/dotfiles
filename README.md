# dotfiles

Personal macOS dotfiles and public-safe agent setup.

## Install

```bash
./install.sh
```

The installer symlinks shell, git, tmux, vim, Claude Code, Codex, omp, Herdr, and shared public agent skill files into `~`.

## Linked Worktree Setup

The post-checkout hook runs a reviewed setup entrypoint only for a registered
linked worktree that lacks the current version's success stamp. This also covers
worktrees whose first checkout was deferred with `--no-checkout` or `--orphan`.
Install it from the canonical dotfiles checkout with:

```bash
./git/hooks/install-post-checkout
```

The default targets are `$HOME/Development/rustwright` and
`$HOME/Development/Skyvern-cloud`. Pass repository paths to select other
repositories. The installer handles each repository independently and requires
Python 3.10+, Git 2.36+, and `/dev/fd` on macOS or Linux. The installer checks
the Git version before it touches a repository. Git 2.36 is required for
unambiguous NUL-delimited `worktree list --porcelain -z` metadata; neither
installer nor hook uses `rev-parse --path-format=absolute`.

The installer is also a POSIX-shell/Python polyglot. Its shell preamble ignores
`PATH` and selects Python 3.10+ only from `/opt/homebrew/bin`, `/usr/local/bin`,
or `/usr/bin`. It restarts with `-I -E` before Python imports. The installer
also pins Git only from those fixed system prefixes and records that executable's
absolute path and inode identity in each generated dispatcher. The installer
requires its sibling `git/hooks/post-checkout` template to be a mode-`0755`,
unfiltered file whose bytes, mode, and attributes match the installer source
checkout's `HEAD`. Commit and review template changes before installation.

Run the installer against a primary checkout. Every target must have a tracked,
unchanged, non-LFS `.superset/setup.sh` at mode `0755` in `HEAD` and the working
tree. `.superset/worktree_storage.py` is optional; when present, it must be a
tracked, unchanged, non-LFS mode-`0644` file. Deleted, sparse, symlinked, or
locally modified sources fail closed. The default Rustwright and Skyvern-cloud
targets must both merge their reviewed `.superset/setup.sh` entrypoints before
the default no-argument rollout is used.

The installer holds a persistent `flock` lock under the pinned common Git
directory. It builds an owner-only, content-addressed directory under
`.skyvern-worktree-hooks/` with directory-relative exclusive operations. A
complete version contains only generated `post-checkout`, `setup.sh`, `version`,
optional `worktree_storage.py`, and an optional pinned stock Git LFS hook. Final
modes are `0500` for the directory and runtime files and `0400` for setup,
helper, and version data. Exact interrupted content can resume; conflicting,
mode-damaged, or extra content remains for manual review. Nothing is recursively
deleted.

The installer never changes `core.hooksPath`. It pins the repository's existing
effective hooks directory and requires every registered worktree to resolve the
same path. The default common `hooks/` directory is supported. A configured path
must be absolute, contained in the common Git directory, free of symlinked or
shared-writable ancestors, and not worktree-local. Other hooks, including
`pre-commit`, remain unchanged and active.
Every installer Git child starts with inherited `GIT_*` variables removed and
`GIT_OPTIONAL_LOCKS=0`. Its `PATH` contains only the pinned Git directory and
fixed system directories; transient command configuration cannot redirect hook
inspection or publication.

Publication changes only `post-checkout`. An absent path is published with an
atomic no-clobber hard link. An exact stock Git LFS hook or a verified older
generated dispatcher is atomically exchanged with the prepared dispatcher by
`renameatx_np(RENAME_SWAP)` on macOS or `renameat2(RENAME_EXCHANGE)` on Linux.
The displaced inode stays at the unique prepared pathname as recovery evidence;
the installer never unlinks it. Any other existing hook is refused untouched.
There is an unavoidable same-user race between the last classification and the
exchange. Immediately after exchange, the installer compares both inodes and
bytes. If a custom hook raced into place, it conditionally exchanges the objects
back before doing other work, verifies the custom hook is effective and
unchanged, preserves the prepared dispatcher, and fails. If those rollback
preconditions also change, the installer stops and reports the observed paths
for manual recovery.

This safety model assumes cooperative same-user Git and hook managers use their
locks. macOS, Linux, and POSIX do not provide a pathname operation that compares
an expected inode and exchanges or unlinks it in one step. A malicious same-UID
process can change a reserved pathname after the final identity check or rewrite
an installed hook after the installer returns. That deliberate behavior is out
of scope. Objects detected at the supported pre-operation checks are restored
or preserved; the installer does not retry forever against a noncooperating
writer.

Without Git LFS, the generated dispatcher starts as a POSIX-shell/Python
polyglot. With Git LFS, the verified stock hook runs first and then starts the
same Python payload. Both paths select Python 3.10+ only from the fixed trusted
system candidates `/opt/homebrew/bin/python3`, `/usr/local/bin/python3`, and
`/usr/bin/python3`, then restart it with `-I -E`. Interpreter upgrades at those
trusted paths do not require reinstalling the hook. `PYTHONPATH`, user-site
startup, and adjacent import shadows cannot run first.
The isolated dispatcher verifies the closed bundle through retained file
descriptors. It does not discover Git through `PATH` or run Git to identify the
worktree. It pins its cwd first, opens the installed common Git directory by its
recorded path and inode, and compares the cwd inode with the primary root and each
`worktrees/*/gitdir` association. A linked match also requires the referenced
`.git` file to point back to the exact pinned admin-directory inode. Exactly one
association must match before setup can run or stamp. Git `gitdir` records lose
only their single final LF terminator, so legal CR and LF pathname bytes remain
part of the path. The dispatcher and installer accept both the traditional
absolute records and the relative records written by Git 2.48 or newer when
`worktree.useRelativePaths` enables `extensions.relativeWorktrees`. They resolve
relative records from the directory that contains each metadata file. Every
path component is opened without following symlinks, and the resolved inode
must match the pinned worktree or admin directory exactly.

For an LFS repository, the effective hook begins with the exact reviewed stock
Git LFS 3.7.1 hook bytes and pads that real prefix to the recognizer's 1024-byte
read limit. Git LFS therefore recognizes a normal reinstall or upgrade without
rewriting the setup dispatcher. The literal `git lfs post-checkout "$@"` command
runs once in Git's standard hook environment. Do not add the checkout directory
or `.` to hook `PATH`; standard Git LFS command lookup would then trust it. The
same stock bytes remain in the immutable content-addressed bundle and are
validated before setup dispatch. A nonzero LFS result stops setup and remains
the hook result. For a new linked worktree, the hook runs
the verified `setup.sh` snapshot as `/bin/bash --noprofile --norc -s --` with no
positional worktree path. The child receives only an absolute `HOME`, a fixed
system `PATH`, `C` locale, noninteractive mode flags, and the reserved Superset
descriptors. Variables such as `BASH_ENV`, `ENV`, `SHELLOPTS`, `BASHOPTS`,
`CDPATH`, `GLOBIGNORE`, and inherited `GIT_*` state are absent. The process
starts from the descriptor-pinned worktree and gets that capability only as
`SUPERSET_PINNED_WORKTREE_FD`. It never reads branch setup code. When the
optional helper exists, its exact snapshot is provided through
`SUPERSET_PINNED_STORAGE_FD`; the reviewed setup and helper must consume the
pinned descriptors, normally with isolated Python. Hook mode must skip agent
launches and `pre-commit install`; interactive setup can keep its normal
behavior. Because setup runs with the new worktree as its current directory, a
reviewed setup must not delegate to relative branch code unless that execution
is an explicit part of its trust contract. Setup errors remain non-fatal to
checkout and do not stamp success.

After publication, installation backfills existing linked worktrees until the
registered set is stable. Backfill pins each root first, then resolves Git with
`git -C .` from that descriptor-pinned current directory. It stamps only the Git
directory returned by that pinned association. All dispatcher versions and
installer backfills use one lock derived from the pinned per-worktree
Git-directory identity. The Bash setup child inherits the same open lock file
description. If the Python parent is killed, the lock remains held until setup
exits. Success stamps remain version-addressed. A success
stamp is written and fsynced under a unique temporary name, hard-linked without
replacement, and directory-fsynced. Before removing its private temporary link,
the process immediately rechecks the exact inode, owner, mode, and link count.
Uncertain temporary paths remain as recovery evidence. Recoverable incomplete
mode-`0600` stamps move atomically to unique evidence names; symlinked, foreign,
or unexpectedly hard-linked stamps remain untouched and block setup. The same
final-instruction same-UID limitation described above applies to this unlink.
This makes setup one-shot and serializes v1/v2 transitions.

## Agent Config

- `AGENTS.md` contains tool-agnostic repo instructions.
- `claude/` contains Claude Code instructions, settings, hooks, and MCP templates.
- `codex/` contains Codex user instructions, RTK guidance, agent profiles, hooks, and a MCP config template.
- `omp/` contains the Oh My Pi agent config and codex subagent definitions (`~/.omp/agent/`).
- `herdr/` contains the Herdr terminal-multiplexer config (`~/.config/herdr/config.toml`).
- `agents/skills/` contains public-safe skills shared by Claude Code and Codex.

Real MCP credentials are not committed. Use:

- `codex/config.toml.template` as a source for `~/.codex/config.toml`
- `claude/mcp_servers.json.template` and `claude/mcp-setup.md` as Claude Code setup references

Keep secrets in local-only files such as `~/.zshrc_secrets`, `~/.codex/config.toml`, and `~/.claude.json`.
