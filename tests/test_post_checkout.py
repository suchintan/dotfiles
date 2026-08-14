#!/usr/bin/env python3
"""Black-box tests for the immutable linked-worktree hook installer."""

from __future__ import annotations

import ast
import ctypes
import errno
import os
import re
import shlex
import signal
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import types
import unittest
from unittest import mock
from pathlib import Path
from typing import Any, Callable, Literal, cast


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "git/hooks/install-post-checkout"
NULL_OID = "0" * 40
STOCK_LFS_HOOK = """#!/bin/sh
command -v git-lfs >/dev/null 2>&1 || { printf >&2 "\\n%s\\n\\n" "This repository is configured for Git LFS but 'git-lfs' was not found on your path. If you no longer wish to use Git LFS, remove this hook by deleting the 'post-checkout' file in the hooks directory (set by 'core.hookspath'; usually '.git/hooks')."; exit 2; }
git lfs post-checkout "$@"
"""
SETUP_ONLY = r"""#!/bin/bash
set -euo pipefail
if [[ "${SUPERSET_POST_CHECKOUT:-0}" == "1" ]]; then
  [[ "${CI:-}" == "1" ]]
  [[ "${NONINTERACTIVE:-}" == "1" ]]
  [[ "${GIT_TERMINAL_PROMPT:-}" == "0" ]]
  [[ "${SUPERSET_NO_AGENTS:-}" == "1" ]]
  [[ -z "${SUPERSET_PINNED_STORAGE_FD:-}" ]]
  [[ -d "/dev/fd/${SUPERSET_PINNED_WORKTREE_FD:?}" ]]
else
  pre-commit install
fi
[[ "$#" == "0" ]]
if [[ "${FAIL_SETUP:-0}" == "1" ]]; then
  exit 7
fi
if [[ -n "${SETUP_HOLD_FILE:-}" ]]; then
  : > "${SETUP_HOLD_FILE}.entered"
  while [[ ! -e "${SETUP_HOLD_FILE}.release" ]]; do
    sleep 0.02
  done
fi
printf 'setup-only snapshot\n' > .setup-ran
"""
HELPER_SETUP = r"""#!/bin/bash
set -euo pipefail
if [[ "${SUPERSET_POST_CHECKOUT:-0}" == "1" ]]; then
  [[ "${CI:-}" == "1" ]]
  [[ "${NONINTERACTIVE:-}" == "1" ]]
  [[ "${SUPERSET_NO_AGENTS:-}" == "1" ]]
else
  pre-commit install
fi
[[ "$#" == "0" ]]
storage_fd="${SUPERSET_PINNED_STORAGE_FD:?missing pinned helper}"
python3 -I -c 'import sys; source=sys.stdin.buffer.read(); sys.argv=["worktree_storage.py"]; namespace={"__name__":"__main__", "__file__":"worktree_storage.py"}; exec(compile(source, "worktree_storage.py", "exec"), namespace, namespace)' <&"$storage_fd"
"""
HELPER_SOURCE = r"""#!/usr/bin/env python3
import os
import sys

forbidden = os.environ.get("FORBIDDEN_PYTHONPATH")
if forbidden and any(
    entry and os.path.realpath(entry) == os.path.realpath(forbidden)
    for entry in sys.path
):
    raise SystemExit(13)
if len(sys.argv) != 1:
    raise SystemExit(9)
root_fd = int(os.environ["SUPERSET_PINNED_WORKTREE_FD"])
root_status = os.fstat(root_fd)
cwd_status = os.stat(".")
if (root_status.st_dev, root_status.st_ino) != (cwd_status.st_dev, cwd_status.st_ino):
    raise SystemExit(10)
if os.environ.get("FAIL_SETUP") == "1":
    raise SystemExit(7)
descriptor = os.open(
    ".setup-ran", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644, dir_fd=root_fd
)
os.write(descriptor, b"helper snapshot\n")
os.close(descriptor)
"""


class HookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="post-checkout-tests-", dir=REPO_ROOT
        )
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.lfs_log = self.root / "git-lfs.log"
        self.precommit_log = self.root / "pre-commit.log"
        self.lfs_log.write_text("")
        self.precommit_log.write_text("")
        self.write_executable(
            self.bin / "git-lfs",
            """#!/usr/bin/env python3
import os
import sys
with open(os.environ["LFS_LOG"], "a", encoding="utf-8") as output:
    output.write(" ".join(sys.argv[1:]) + "\\n")
raise SystemExit(int(os.environ.get("FAKE_LFS_RC", "0")))
""",
        )
        self.write_executable(
            self.bin / "pre-commit",
            """#!/usr/bin/env python3
import os
import sys
with open(os.environ["PRECOMMIT_LOG"], "a", encoding="utf-8") as output:
    output.write(" ".join(sys.argv[1:]) + "\\n")
""",
        )
        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_NOSYSTEM": "1",
                "LFS_LOG": str(self.lfs_log),
                "PRECOMMIT_LOG": str(self.precommit_log),
                "PATH": f"{self.bin}:{self.env['PATH']}",
            }
        )
        self.installer_source = self.new_repository("installer source")
        source_hooks = self.installer_source / "git/hooks"
        source_hooks.mkdir(parents=True)
        shutil.copyfile(INSTALLER, source_hooks / "install-post-checkout")
        shutil.copyfile(
            REPO_ROOT / "git/hooks/post-checkout", source_hooks / "post-checkout"
        )
        (source_hooks / "install-post-checkout").chmod(0o755)
        (source_hooks / "post-checkout").chmod(0o755)
        self.git(self.installer_source, "add", "git/hooks")
        self.git(self.installer_source, "commit", "-qm", "add installer source")
        self.installer = source_hooks / "install-post-checkout"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def write_executable(path: Path, content: str) -> None:
        path.write_text(textwrap.dedent(content))
        path.chmod(0o755)

    def run_command(
        self,
        arguments: list[str | Path],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command_env = self.env.copy()
        if env:
            command_env.update(env)
        result = subprocess.run(
            [str(argument) for argument in arguments],
            cwd=cwd,
            env=command_env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and result.returncode != 0:
            self.fail(
                f"command failed ({result.returncode}): {' '.join(map(str, arguments))}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def git(
        self, repository: Path, *arguments: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return self.run_command(["git", "-C", repository, *arguments], check=check)

    @staticmethod
    def record(output: str) -> str:
        if not output.endswith("\n"):
            raise AssertionError("Git record lacks a line feed")
        value = output[:-1]
        if value.endswith("\r"):
            value = value[:-1]
        return value

    def new_repository(self, name: str, *, object_format: str | None = None) -> Path:
        repository = self.root / name
        command: list[str | Path] = ["git", "init", "-q"]
        if object_format is not None:
            command.append(f"--object-format={object_format}")
        command.append(repository)
        self.run_command(command)
        self.git(repository, "config", "user.name", "Hook Test")
        self.git(repository, "config", "user.email", "hook-test@example.com")
        (repository / "seed.txt").write_text("seed\n")
        self.git(repository, "add", "seed.txt")
        self.git(repository, "commit", "-qm", "seed")
        return repository

    def add_sources(self, repository: Path, *, helper: bool = False) -> None:
        superset = repository / ".superset"
        superset.mkdir(exist_ok=True)
        setup = superset / "setup.sh"
        setup.write_text(HELPER_SETUP if helper else SETUP_ONLY)
        setup.chmod(0o755)
        paths = [".superset/setup.sh"]
        if helper:
            storage = superset / "worktree_storage.py"
            storage.write_text(HELPER_SOURCE)
            storage.chmod(0o644)
            paths.append(".superset/worktree_storage.py")
        self.git(repository, "add", *paths)
        self.git(repository, "commit", "-qm", "add reviewed setup bundle")

    def install(
        self,
        *repositories: Path,
        env: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_command([self.installer, *repositories], env=env, check=check)

    def use_test_git(self, executable: Path) -> None:
        source = self.installer.read_text()
        replacement = f"TRUSTED_GIT_CANDIDATES = ({str(executable)!r},)"
        updated, count = re.subn(
            r"TRUSTED_GIT_CANDIDATES = .*?\nTEMPLATE_GIT_PATH_LINE",
            replacement + "\nTEMPLATE_GIT_PATH_LINE",
            source,
            flags=re.DOTALL,
        )
        self.assertEqual(count, 1)
        self.installer.write_text(updated)
        self.installer.chmod(0o755)

    def common_dir(self, repository: Path) -> Path:
        raw = self.record(self.git(repository, "rev-parse", "--git-common-dir").stdout)
        return Path(raw) if os.path.isabs(raw) else (repository / raw).resolve()

    def git_dir(self, repository: Path) -> Path:
        git_entry = repository / ".git"
        if git_entry.is_dir():
            return git_entry.resolve()
        content = git_entry.read_bytes()
        prefix = b"gitdir: "
        if not content.startswith(prefix) or not content.endswith(b"\n"):
            raise AssertionError("malformed test .git file")
        raw = os.fsdecode(content[len(prefix) : -1])
        return Path(raw) if os.path.isabs(raw) else (repository / raw).resolve()

    def hooks_dir(self, repository: Path) -> Path:
        raw = self.record(
            self.git(repository, "rev-parse", "--git-path", "hooks").stdout
        )
        return Path(raw) if os.path.isabs(raw) else (repository / raw).resolve()

    def hook(self, repository: Path) -> Path:
        return self.hooks_dir(repository) / "post-checkout"

    @staticmethod
    def bundle_from_hook(hook: Path) -> Path:
        match = re.search(
            rb'^BUNDLE_PATH_HEX = "([0-9a-f]+)"$',
            hook.read_bytes(),
            re.MULTILINE,
        )
        if match is None:
            raise AssertionError("dispatcher has no bundle path")
        return Path(os.fsdecode(bytes.fromhex(os.fsdecode(match.group(1)))))

    def prepared(self, repository: Path) -> list[Path]:
        return sorted(self.hooks_dir(repository).glob(".post-checkout.skyvern-*"))

    def add_linked_worktree(
        self,
        repository: Path,
        name: str,
        *,
        branch: str | None = None,
        env: dict[str, str] | None = None,
    ) -> Path:
        branch_name = branch or f"branch-{name}"
        if branch is None:
            self.git(repository, "branch", branch_name)
        linked = self.root / f"{name}-worktree"
        result = self.run_command(
            ["git", "-C", repository, "worktree", "add", "-q", linked, branch_name],
            env=env,
            check=False,
        )
        self.last_worktree_add = result
        self.assertEqual(result.returncode, 0, result.stderr)
        return linked

    def invoke_hook(
        self,
        hook: Path,
        cwd: Path,
        *,
        old_oid: str = NULL_OID,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self.run_command(
            [hook, old_oid, "1" * len(old_oid), "1"],
            cwd=cwd,
            env=env,
            check=False,
        )

    def stamps(self, worktree: Path) -> list[Path]:
        return list(self.git_dir(worktree).glob("dotfiles-worktree-setup-success.*"))

    def rewrite_link_records(
        self,
        worktree: Path,
        *,
        relative_root: bool,
        relative_admin: bool,
    ) -> Path:
        admin = self.git_dir(worktree)
        root_entry = worktree / ".git"
        if relative_root:
            root_target = os.path.relpath(admin, worktree)
            root_entry.write_bytes(b"gitdir: " + os.fsencode(root_target) + b"\n")
        if relative_admin:
            backlink = os.path.relpath(root_entry, admin)
            (admin / "gitdir").write_bytes(os.fsencode(backlink) + b"\n")
        return admin

    def add_hostile_modules(self, directory: Path, sentinel: Path) -> None:
        directory.mkdir(exist_ok=True)
        for module in (
            "hashlib",
            "subprocess",
            "dataclasses",
            "platform",
            "sitecustomize",
        ):
            (directory / f"{module}.py").write_text(
                f"with open({str(sentinel)!r}, 'a') as output:\n"
                f"    output.write({module!r} + '\\n')\n"
                f"raise RuntimeError('hostile {module} imported')\n"
            )

    def assert_relative_runtime_case(
        self, name: str, *, relative_root: bool, relative_admin: bool
    ) -> None:
        repository = self.new_repository(f"relative runtime {name}")
        self.add_sources(repository)
        self.install(repository)
        self.git(repository, "branch", "relative-runtime-branch")
        linked = self.add_linked_worktree(
            repository, name, branch="relative-runtime-branch"
        )
        for stamp in self.stamps(linked):
            stamp.unlink()
        (linked / ".setup-ran").unlink()
        self.rewrite_link_records(
            linked,
            relative_root=relative_root,
            relative_admin=relative_admin,
        )
        result = self.invoke_hook(self.hook(repository), linked)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

    def use_fixture_worktree_list(
        self, repository: Path, worktrees: list[Path]
    ) -> None:
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        fake_bin = self.root / f"relative-fixture-git-{len(list(self.root.iterdir()))}"
        fake_bin.mkdir()
        payload = b"".join(
            b"worktree " + os.fsencode(path) + b"\0\0"
            for path in [repository, *worktrees]
        )
        self.write_executable(
            fake_bin / "git",
            f"""#!/usr/bin/env python3
import os
import sys
arguments = sys.argv[1:]
if arguments == ["-C", ".", "worktree", "list", "--porcelain", "-z"]:
    current = os.stat(".")
    primary = os.stat({str(repository)!r})
    if (current.st_dev, current.st_ino) == (primary.st_dev, primary.st_ino):
        os.write(1, {payload!r})
        raise SystemExit(0)
os.execv({real_git!r}, [{real_git!r}, *arguments])
""",
        )
        self.use_test_git(fake_bin / "git")

    def linux_helper_namespace(self, path: Path) -> dict[str, Any]:
        source = path.read_text()
        tree = ast.parse(source, filename=str(path))
        selected: list[ast.stmt] = []
        constant_names = {"ELF_RENAMEAT2_SYSCALLS"}
        function_names = {
            "linux_renameat2_syscall_number",
            "linux_process_elf_header",
            "linux_renameat2",
        }
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in constant_names
                for target in node.targets
            ):
                selected.append(node)
            if isinstance(node, ast.FunctionDef) and node.name in function_names:
                selected.append(node)
        self.assertEqual(len(selected), 4)
        namespace: dict[str, Any] = {
            "ctypes": ctypes,
            "errno": errno,
            "os": os,
            "stat": stat,
        }
        exec(compile(ast.Module(selected, []), str(path), "exec"), namespace)
        return namespace

    def elf_header(
        self,
        elf_class: int,
        elf_data: int,
        machine: int,
        *,
        flags: int | None = None,
        elf_type: int = 3,
        version: int = 1,
        osabi: int = 0,
        abi_version: int = 0,
        header_size: int | None = None,
    ) -> bytes:
        size = 52 if elf_class == 1 else 64
        byte_order: Literal["little", "big"] = "little" if elf_data == 1 else "big"
        content = bytearray(size)
        content[:4] = b"\x7fELF"
        content[4:9] = bytes((elf_class, elf_data, 1, osabi, abi_version))

        def put(offset: int, width: int, value: int) -> None:
            content[offset : offset + width] = value.to_bytes(width, byte_order)

        put(16, 2, elf_type)
        put(18, 2, machine)
        put(20, 4, version)
        flags_offset = 36 if elf_class == 1 else 48
        if flags is None:
            flags = 0x05000000 if machine == 40 else 0
        put(flags_offset, 4, flags)
        put(40 if elf_class == 1 else 52, 2, header_size or size)
        return bytes(content)

    def elf_file(
        self, header: bytes, name: str = "synthetic-python"
    ) -> tuple[bytes, tuple[int, int]]:
        path = self.root / f"{name}-{len(list(self.root.iterdir()))}"
        path.write_bytes(header)
        path.chmod(0o755)
        status = path.stat()
        return os.fsencode(path), (status.st_dev, status.st_ino)

    def lfs_371_recognizes(self, content: bytes) -> bool:
        # git-lfs v3.7.1 lfs/hook.go matchesCurrent: LimitReader(1024),
        # tools.Undent, then strings.TrimSpace and exact hookBaseContent equality.
        inspected = textwrap.dedent(content[:1024].decode()).strip()
        return inspected == STOCK_LFS_HOOK.strip()

    def test_setup_only_preserves_config_and_other_hooks(self) -> None:
        repository = self.new_repository("setup only")
        self.add_sources(repository)
        self.run_command(["/bin/bash", ".superset/setup.sh"], cwd=repository)
        self.assertEqual(self.precommit_log.read_text(), "install\n")
        self.precommit_log.write_text("")
        (repository / ".setup-ran").unlink()
        pre_commit = self.hooks_dir(repository) / "pre-commit"
        pre_commit.write_text("#!/bin/sh\nexit 0\n")
        pre_commit.chmod(0o755)
        config_before = (self.common_dir(repository) / "config").read_bytes()

        result = self.install(repository)
        self.assertIn("installed ", result.stdout)
        self.assertEqual(
            (self.common_dir(repository) / "config").read_bytes(), config_before
        )
        self.assertEqual(pre_commit.read_text(), "#!/bin/sh\nexit 0\n")
        hook = self.hook(repository)
        self.assertTrue(hook.is_file())
        prepared_count = len(self.prepared(repository))

        again = self.install(repository)
        self.assertIn("already current", again.stdout)
        self.assertEqual(len(self.prepared(repository)), prepared_count)
        linked = self.add_linked_worktree(repository, "setup-only")
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)
        self.assertEqual(self.precommit_log.read_text(), "")

        (linked / ".setup-ran").unlink()
        ordinary = self.invoke_hook(hook, linked, old_oid="1" * 40)
        self.assertEqual(ordinary.returncode, 0)
        self.assertFalse((linked / ".setup-ran").exists())
        self.git(linked, "switch", "--orphan", "orphan")
        self.assertFalse((linked / ".setup-ran").exists())

        clone = self.root / "full clone"
        self.run_command(["git", "clone", "-q", repository, clone])
        full_clone = self.invoke_hook(hook, clone)
        self.assertEqual(full_clone.returncode, 0)
        self.assertFalse((clone / ".setup-ran").exists())
        sources = (REPO_ROOT / "git/hooks/post-checkout").read_text() + (
            REPO_ROOT / "git/hooks/install-post-checkout"
        ).read_text()
        self.assertNotIn("--path-format=absolute", sources)

    def test_no_checkout_worktree_runs_setup_on_later_checkout(self) -> None:
        repository = self.new_repository("no checkout lifecycle")
        self.add_sources(repository)
        self.install(repository)
        branch = "no-checkout-branch"
        self.git(repository, "branch", branch)
        linked = self.root / "no-checkout-worktree"
        added = self.run_command(
            [
                "git",
                "-C",
                repository,
                "worktree",
                "add",
                "-q",
                "--no-checkout",
                linked,
                branch,
            ],
            check=False,
        )
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertFalse((linked / ".setup-ran").exists())
        self.assertEqual(self.stamps(linked), [])

        checked_out = self.git(linked, "checkout", "-q", "-f", "HEAD", check=False)
        self.assertEqual(checked_out.returncode, 0, checked_out.stderr)
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

    def test_orphan_worktree_runs_setup_on_later_checkout_when_supported(self) -> None:
        repository = self.new_repository("orphan lifecycle")
        self.add_sources(repository)
        self.install(repository)
        return_branch = "orphan-return-branch"
        self.git(repository, "branch", return_branch)
        linked = self.root / "orphan-worktree"
        added = self.run_command(
            [
                "git",
                "-C",
                repository,
                "worktree",
                "add",
                "-q",
                "--orphan",
                "-b",
                "orphan-lifecycle-branch",
                linked,
            ],
            check=False,
        )
        if added.returncode != 0 and re.search(
            r"(?:unknown|unrecognized) option.*orphan", added.stderr
        ):
            self.skipTest("installed Git does not support worktree add --orphan")
        self.assertEqual(added.returncode, 0, added.stderr)
        self.assertFalse((linked / ".setup-ran").exists())
        self.assertEqual(self.stamps(linked), [])
        (linked / "orphan.txt").write_text("orphan\n")
        self.git(linked, "add", "orphan.txt")
        self.git(linked, "commit", "-qm", "orphan seed")

        checked_out = self.git(
            linked, "checkout", "-q", return_branch, check=False
        )
        self.assertEqual(checked_out.returncode, 0, checked_out.stderr)
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

    def test_git_236_minimum_is_enforced_before_repository_work(self) -> None:
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)

        def fake_git(version: str, directory: Path) -> Path:
            directory.mkdir()
            self.write_executable(
                directory / "git",
                f"""#!/usr/bin/env python3
import os
import sys
if sys.argv[1:] == ["version"]:
    print("git version {version}")
else:
    os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])
""",
            )
            return directory / "git"

        old_repository = self.new_repository("git 235 rejected")
        self.add_sources(old_repository)
        self.use_test_git(fake_git("2.35.9", self.root / "git-235"))
        rejected = self.install(old_repository, check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("Git 2.36 or newer is required", rejected.stderr)
        self.assertFalse(self.hook(old_repository).exists())
        self.assertFalse(
            (self.common_dir(old_repository) / ".skyvern-worktree-hooks.lock").exists()
        )

        supported = self.new_repository("git 236 accepted")
        self.add_sources(supported)
        self.use_test_git(fake_git("2.36.0", self.root / "git-236"))
        accepted = self.install(supported)
        self.assertIn("installed ", accepted.stdout)
        self.assertTrue(self.hook(supported).is_file())

    def test_installer_isolated_startup_ignores_path_and_pythonpath(self) -> None:
        repository = self.new_repository("isolated installer startup")
        self.add_sources(repository)
        hostile = self.root / "hostile installer startup"
        sentinel = self.root / "hostile-installer-sentinel"
        self.add_hostile_modules(hostile, sentinel)
        self.write_executable(
            hostile / "python3",
            f"""#!/bin/sh
printf 'PATH python ran\n' >> {shlex.quote(str(sentinel))}
exit 91
""",
        )
        result = self.install(
            repository,
            env={
                "PATH": f"{hostile}:{self.env['PATH']}",
                "PYTHONPATH": str(hostile),
            },
        )
        self.assertIn("installed ", result.stdout)
        self.assertFalse(sentinel.exists())

    def test_dispatcher_template_requires_exact_head_provenance(self) -> None:
        repository = self.new_repository("template provenance target")
        self.add_sources(repository)
        template = self.installer_source / "git/hooks/post-checkout"
        original = template.read_bytes()

        template.write_bytes(original + b"# dirty template\n")
        dirty = self.install(repository, check=False)
        self.assertNotEqual(dirty.returncode, 0)
        self.assertIn("differs from its exact HEAD blob", dirty.stderr)
        self.assertFalse(self.hook(repository).exists())

        template.write_bytes(original)
        template.chmod(0o644)
        damaged_mode = self.install(repository, check=False)
        self.assertNotEqual(damaged_mode.returncode, 0)
        self.assertIn("mode-0755 regular file", damaged_mode.stderr)
        self.assertFalse(self.hook(repository).exists())

        template.chmod(0o755)
        attributes = self.installer_source / ".gitattributes"
        attributes.write_text("git/hooks/post-checkout filter=lfs\n")
        dirty_attributes = self.install(repository, check=False)
        self.assertNotEqual(dirty_attributes.returncode, 0)
        self.assertIn("attributes differ from HEAD", dirty_attributes.stderr)
        self.assertFalse(self.hook(repository).exists())

    def test_old_git_attribute_fallback_requires_clean_whole_index(self) -> None:
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        fake_bin = self.root / "old-check-attr-git"
        fake_bin.mkdir()
        self.write_executable(
            fake_bin / "git",
            f"""#!/usr/bin/env python3
import os
import sys
arguments = sys.argv[1:]
if "check-attr" in arguments and "--source=HEAD" in arguments:
    os.write(2, b"error: unknown option `source=HEAD'\\n")
    raise SystemExit(129)
os.execv({real_git!r}, [{real_git!r}, *arguments])
""",
        )
        self.use_test_git(fake_bin / "git")

        attributes = self.installer_source / ".gitattributes"
        attributes.write_text("git/hooks/post-checkout filter=lfs\n")
        self.git(self.installer_source, "add", ".gitattributes")
        self.git(
            self.installer_source,
            "diff",
            "--quiet",
            "HEAD",
            "--",
            "git/hooks/post-checkout",
        )
        self.git(
            self.installer_source,
            "diff",
            "--cached",
            "--quiet",
            "HEAD",
            "--",
            "git/hooks/post-checkout",
        )

        dirty_target = self.new_repository("old attr dirty index")
        self.add_sources(dirty_target)
        rejected = self.install(dirty_target, check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn(
            "Git lacks check-attr --source and the index differs from HEAD",
            rejected.stderr,
        )
        self.assertFalse(self.hook(dirty_target).exists())

        self.git(
            self.installer_source,
            "reset",
            "-q",
            "HEAD",
            "--",
            ".gitattributes",
        )
        attributes.unlink()
        clean_target = self.new_repository("old attr clean index")
        self.add_sources(clean_target)
        accepted = self.install(clean_target)
        self.assertIn("installed ", accepted.stdout)
        self.assertTrue(self.hook(clean_target).is_file())

    def test_primary_linked_and_source_paths_preserve_cr_lf_bytes(self) -> None:
        moved_source = self.root / "installer\nsource\rroot"
        os.rename(self.installer_source, moved_source)
        self.installer_source = moved_source
        self.installer = moved_source / "git/hooks/install-post-checkout"

        repository = self.new_repository("primary\nline\rreturn")
        self.add_sources(repository)
        nested = repository / "nested\nsubdir\r"
        nested.mkdir()
        self.install(nested)
        self.assertTrue(self.hook(repository).is_file())

        branch = "cr-lf-linked-branch"
        self.git(repository, "branch", branch)
        linked = self.add_linked_worktree(
            repository,
            "linked\nline\rreturn",
            branch=branch,
        )
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

    def test_helper_snapshot_ignores_unreviewed_branch_and_pythonpath(self) -> None:
        repository = self.new_repository("helper source")
        self.add_sources(repository, helper=True)
        self.install(repository)
        initial_branch = self.record(
            self.git(repository, "branch", "--show-current").stdout
        )
        self.git(repository, "switch", "-qc", "malicious-branch")
        branch_setup = repository / ".superset/setup.sh"
        branch_helper = repository / ".superset/worktree_storage.py"
        branch_setup.write_text("#!/bin/bash\nprintf branch > branch-ran\n")
        branch_setup.chmod(0o755)
        branch_helper.write_text("open('branch-helper-ran','w').write('bad')\n")
        self.git(repository, "add", ".superset")
        self.git(repository, "commit", "-qm", "unreviewed branch setup")
        self.git(repository, "switch", "-q", initial_branch)

        hostile = self.root / "hostile pythonpath"
        sentinel = self.root / "hostile-imported"
        self.add_hostile_modules(hostile, sentinel)
        linked = self.add_linked_worktree(
            repository,
            "malicious-branch",
            branch="malicious-branch",
            env={
                "PYTHONPATH": str(hostile),
                "FORBIDDEN_PYTHONPATH": str(hostile),
            },
        )
        self.assertEqual((linked / ".setup-ran").read_text(), "helper snapshot\n")
        self.assertFalse((linked / "branch-ran").exists())
        self.assertFalse((linked / "branch-helper-ran").exists())
        self.assertFalse(sentinel.exists())

    def test_setup_shell_ignores_startup_and_redirect_environment(self) -> None:
        bash_environment = self.root / "hostile-bash-env"
        sentinel = self.root / "bash-env-sentinel"
        bash_environment.write_text(
            f"printf 'BASH_ENV ran\\n' >> {shlex.quote(str(sentinel))}\nexit 0\n"
        )
        hostile_environment = {
            "BASH_ENV": str(bash_environment),
            "ENV": str(bash_environment),
            "CDPATH": str(self.root),
            "GLOBIGNORE": "*",
            "SHELLOPTS": "xtrace",
            "BASHOPTS": "extdebug",
        }

        hook_repository = self.new_repository("bash env hook")
        self.add_sources(hook_repository)
        self.install(hook_repository)
        linked = self.add_linked_worktree(
            hook_repository, "bash-env-hook", env=hostile_environment
        )
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertFalse(sentinel.exists())

        backfill_repository = self.new_repository("bash env backfill")
        self.add_sources(backfill_repository)
        backfill = self.add_linked_worktree(backfill_repository, "bash-env-backfill")
        self.install(backfill_repository, env=hostile_environment)
        self.assertEqual((backfill / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertFalse(sentinel.exists())

    def test_source_provenance_separate_git_dir_subdirectory_and_spaces(self) -> None:
        source = self.new_repository("source provenance")
        self.add_sources(source, helper=True)
        separate = self.root / "separate metadata  "
        canonical = self.root / "canonical checkout  "
        self.run_command(
            ["git", "clone", "-q", "--separate-git-dir", separate, source, canonical]
        )
        nested = canonical / "nested path"
        nested.mkdir()
        config_before = (separate / "config").read_bytes()
        self.install(nested)
        self.assertEqual(self.hook(canonical).parent, separate / "hooks")
        self.assertEqual((separate / "config").read_bytes(), config_before)

        modified = self.new_repository("modified setup")
        self.add_sources(modified)
        with (modified / ".superset/setup.sh").open("a") as output:
            output.write("# unreviewed\n")
        result = self.install(modified, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("differs from HEAD", result.stderr)
        self.assertFalse(self.hook(modified).exists())

        deleted = self.new_repository("deleted helper")
        self.add_sources(deleted, helper=True)
        (deleted / ".superset/worktree_storage.py").unlink()
        result = self.install(deleted, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("deleted, sparse, or unavailable", result.stderr)

        missing = self.new_repository("missing setup")
        result = self.install(missing, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical .superset", result.stderr)

    def test_gitfile_swap_fails_without_mutating_other_config(self) -> None:
        source = self.new_repository("gitfile source")
        self.add_sources(source)
        separate = self.root / "gitfile metadata"
        canonical = self.root / "gitfile canonical"
        self.run_command(
            ["git", "clone", "-q", "--separate-git-dir", separate, source, canonical]
        )
        unrelated = self.new_repository("unrelated config")
        unrelated_config = (unrelated / ".git/config").read_bytes()
        callback = self.root / "swap-gitfile.py"
        self.write_executable(
            callback,
            f"""#!/usr/bin/env python3
import os
import pathlib
root = pathlib.Path({str(canonical)!r})
gitfile = root / ".git"
os.rename(gitfile, root / ".git.pinned-original")
gitfile.write_text("gitdir: {str(unrelated / '.git')}\\n")
""",
        )
        result = self.install(
            canonical,
            env={"INSTALL_POST_CHECKOUT_TEST_BEFORE_PUBLICATION_CHECKS": str(callback)},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".git entry changed", result.stderr)
        self.assertEqual((unrelated / ".git/config").read_bytes(), unrelated_config)
        self.assertFalse(self.hook(unrelated).exists())

    def test_lfs_filtered_sources_are_rejected(self) -> None:
        pointer = self.new_repository("lfs pointer")
        self.add_sources(pointer)
        (pointer / ".superset/setup.sh").write_text(
            "version https://git-lfs.github.com/spec/v1\n"
            f"oid sha256:{'1' * 64}\nsize 123\n"
        )
        (pointer / ".superset/setup.sh").chmod(0o755)
        (pointer / ".gitattributes").write_text(".superset/setup.sh filter=lfs\n")
        self.git(pointer, "add", ".gitattributes", ".superset/setup.sh")
        self.git(pointer, "commit", "-qm", "LFS pointer setup")

        smudged = self.new_repository("lfs smudged helper")
        self.add_sources(smudged, helper=True)
        (smudged / ".gitattributes").write_text(
            ".superset/worktree_storage.py filter=lfs\n"
        )
        self.git(smudged, "add", ".gitattributes")
        self.git(smudged, "commit", "-qm", "LFS smudged helper")

        result = self.install(pointer, smudged, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr.count("Git LFS-filtered"), 2)
        self.assertFalse(self.hook(pointer).exists())
        self.assertFalse(self.hook(smudged).exists())

    def test_hooks_path_scope_and_non_post_checkout_hooks(self) -> None:
        relative = self.new_repository("relative hooks")
        self.add_sources(relative)
        self.git(relative, "config", "core.hooksPath", ".githooks")
        result = self.install(relative, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("relative core.hooksPath is unsafe", result.stderr)

        outside = self.new_repository("outside hooks")
        self.add_sources(outside)
        outside_hooks = self.root / "shared hooks"
        outside_hooks.mkdir()
        self.git(outside, "config", "core.hooksPath", str(outside_hooks))
        result = self.install(outside, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the common Git directory", result.stderr)

        contained = self.new_repository("contained hooks")
        self.add_sources(contained)
        contained_hooks = contained / ".git/repo-hooks"
        contained_hooks.mkdir(mode=0o755)
        pre_commit = contained_hooks / "pre-commit"
        pre_commit.write_text("#!/bin/sh\nexit 0\n")
        pre_commit.chmod(0o755)
        self.git(contained, "config", "core.hooksPath", str(contained_hooks))
        contained_linked = self.add_linked_worktree(contained, "contained-hooks-before")
        config_before = (contained / ".git/config").read_bytes()
        self.install(contained)
        self.assertEqual(self.hook(contained).parent, contained_hooks)
        self.assertEqual(pre_commit.read_text(), "#!/bin/sh\nexit 0\n")
        self.assertEqual((contained / ".git/config").read_bytes(), config_before)
        self.assertTrue((contained_linked / ".setup-ran").is_file())

        writable = self.new_repository("writable hooks ancestor")
        self.add_sources(writable)
        writable_hooks = writable / ".git/writable/hooks"
        writable_hooks.mkdir(parents=True)
        (writable / ".git/writable").chmod(0o775)
        self.git(writable, "config", "core.hooksPath", str(writable_hooks))
        result = self.install(writable, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("group/world writable", result.stderr)

        common_writable = self.new_repository("writable common git")
        self.add_sources(common_writable)
        (common_writable / ".git").chmod(0o775)
        result = self.install(common_writable, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("group/world writable", result.stderr)
        self.assertFalse(
            (common_writable / ".git/.skyvern-worktree-hooks.lock").exists()
        )

        local = self.new_repository("worktree local hooks")
        self.add_sources(local)
        linked = self.add_linked_worktree(local, "local-config-before")
        self.git(local, "config", "extensions.worktreeConfig", "true")
        primary_only = local / ".git/primary-only-hooks"
        primary_only.mkdir()
        self.git(
            local,
            "config",
            "--worktree",
            "core.hooksPath",
            str(primary_only),
        )
        self.assertNotEqual(self.hooks_dir(local), self.hooks_dir(linked))
        result = self.install(local, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("worktree-local core.hooksPath is unsafe", result.stderr)

    def test_transient_git_environment_cannot_redirect_hooks(self) -> None:
        repository = self.new_repository("transient git environment")
        self.add_sources(repository)
        redirected = repository / ".git/transient-hooks"
        redirected.mkdir()
        transient = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": str(redirected),
            "GIT_DIR": str(self.root / "foreign-git-dir"),
            "GIT_WORK_TREE": str(self.root / "foreign-worktree"),
            "GIT_COMMON_DIR": str(self.root / "foreign-common"),
            "GIT_INDEX_FILE": str(self.root / "foreign-index"),
            "GIT_OBJECT_DIRECTORY": str(self.root / "foreign-objects"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(self.root / "foreign-alt"),
            "GIT_CONFIG_GLOBAL": str(self.root / "foreign-global-config"),
            "GIT_CONFIG_SYSTEM": str(self.root / "foreign-system-config"),
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        self.install(repository, env=transient)
        self.assertTrue((repository / ".git/hooks/post-checkout").is_file())
        self.assertFalse((redirected / "post-checkout").exists())

        command_scope = self.new_repository("command scope hooks")
        self.add_sources(command_scope)
        fake_bin = self.root / "command-scope-git"
        fake_bin.mkdir()
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        self.write_executable(
            fake_bin / "git",
            f"""#!/usr/bin/env python3
import os
import sys
if "--show-scope" in sys.argv and sys.argv[-1] == "core.hooksPath":
    os.write(1, b"command\\0command line:\\0/tmp/command-hooks\\0")
    raise SystemExit(0)
os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])
""",
        )
        self.use_test_git(fake_bin / "git")
        result = self.install(command_scope, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("command-scope core.hooksPath is unsafe", result.stderr)
        self.assertFalse(self.hook(command_scope).exists())

    def test_stock_lfs_exchange_exit_and_generated_update(self) -> None:
        repository = self.new_repository("stock lfs")
        self.add_sources(repository)
        pinned_git_dir = self.root / "pinned-lfs-git"
        pinned_git_dir.mkdir()
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        self.write_executable(
            pinned_git_dir / "git",
            f"""#!/bin/sh
exec {shlex.quote(str(real_git))} "$@"
""",
        )
        self.write_executable(pinned_git_dir / "git-lfs", "#!/bin/sh\nexit 0\n")
        self.use_test_git(pinned_git_dir / "git")
        hook = self.hook(repository)
        hook.write_text(STOCK_LFS_HOOK)
        hook.chmod(0o755)
        self.install(repository)
        self.assertNotEqual(hook.read_text(), STOCK_LFS_HOOK)
        backups = self.prepared(repository)
        self.assertTrue(any(path.read_text() == STOCK_LFS_HOOK for path in backups))
        bundle = self.bundle_from_hook(hook)
        self.assertEqual((bundle / "post-checkout-lfs").read_text(), STOCK_LFS_HOOK)

        linked = self.add_linked_worktree(repository, "lfs-linked")
        (linked / ".setup-ran").unlink()
        for stamp in self.stamps(linked):
            stamp.unlink()
        failed_lfs = self.invoke_hook(hook, linked, env={"FAKE_LFS_RC": "23"})
        self.assertEqual(failed_lfs.returncode, 23)
        self.assertFalse((linked / ".setup-ran").exists())
        self.assertEqual(self.stamps(linked), [])
        routing_sentinel = self.root / "branch-local-git-ran"
        self.write_executable(
            linked / "git",
            f"""#!/bin/sh
printf 'branch git ran\n' > {shlex.quote(str(routing_sentinel))}
exit 99
""",
        )
        routed = self.invoke_hook(
            hook,
            linked,
            env={
                "GIT_DIR": str(self.root / "decoy-git-dir"),
                "GIT_WORK_TREE": str(self.root / "decoy-worktree"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.worktree",
                "GIT_CONFIG_VALUE_0": str(self.root / "decoy-core-worktree"),
            },
        )
        self.assertEqual(routed.returncode, 0, routed.stderr)
        self.assertFalse(routing_sentinel.exists())
        self.assertTrue((linked / ".setup-ran").is_file())
        self.assertEqual(len(self.stamps(linked)), 1)

        old_dispatcher = hook.read_bytes()
        with (repository / ".superset/setup.sh").open("a") as output:
            output.write("# reviewed v2\n")
        self.git(repository, "add", ".superset/setup.sh")
        self.git(repository, "commit", "-qm", "review setup v2")
        self.install(repository)
        self.assertNotEqual(hook.read_bytes(), old_dispatcher)
        self.assertTrue(
            any(
                path.read_bytes() == old_dispatcher
                for path in self.prepared(repository)
            )
        )

        updated_bundle = self.bundle_from_hook(hook)
        lfs_path = updated_bundle / "post-checkout-lfs"
        original_lfs = lfs_path.read_bytes()
        sentinel = self.root / "mutated-lfs-ran"
        replacement = (
            f"#!/bin/sh\nprintf hacked > {str(sentinel)!r}\nexit 0\n".encode()
        ).ljust(len(original_lfs), b"#")[: len(original_lfs)]
        callback = self.root / "pwrite-lfs.py"
        self.write_executable(
            callback,
            f"""#!/usr/bin/env python3
import os
import pathlib
path = pathlib.Path({str(lfs_path)!r})
path.chmod(0o700)
descriptor = os.open(path, os.O_WRONLY)
content = bytes.fromhex({replacement.hex()!r})
os.pwrite(descriptor, content, 0)
os.ftruncate(descriptor, len(content))
os.close(descriptor)
path.chmod(0o500)
""",
        )
        for stamp in self.stamps(linked):
            stamp.unlink()
        current = self.invoke_hook(
            hook,
            linked,
            env={"POST_CHECKOUT_TEST_AFTER_VERIFY": str(callback)},
        )
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertFalse(sentinel.exists())
        for stamp in self.stamps(linked):
            stamp.unlink()
        (linked / ".setup-ran").unlink()
        refused = self.invoke_hook(hook, linked)
        self.assertNotEqual(refused.returncode, 0)
        self.assertFalse(sentinel.exists())

    def test_generated_lfs_dispatcher_matches_upstream_371_recognizer(self) -> None:
        repository = self.new_repository("lfs recognizer")
        self.add_sources(repository)
        hook = self.hook(repository)
        hook.write_text(STOCK_LFS_HOOK)
        hook.chmod(0o755)
        self.install(repository)
        content = hook.read_bytes()
        stock = STOCK_LFS_HOOK.encode()
        self.assertEqual(content[: len(stock)], stock)
        self.assertEqual(content[:1024].rstrip(), stock.rstrip())
        self.assertTrue(self.lfs_371_recognizes(content))
        self.assertEqual(
            (self.bundle_from_hook(hook) / "post-checkout-lfs").read_bytes(),
            stock,
        )

    def test_normal_git_lfs_reinstall_preserves_dispatch_and_runs_once(self) -> None:
        repository = self.new_repository("lfs reinstall")
        self.add_sources(repository)
        hook = self.hook(repository)
        hook.write_text(STOCK_LFS_HOOK)
        hook.chmod(0o755)
        self.install(repository)
        installed = hook.read_bytes()

        # Faithful v3.7.1 Upgrade behavior: match=true means no rewrite.
        for _attempt in range(2):
            self.assertTrue(self.lfs_371_recognizes(hook.read_bytes()))
            self.assertEqual(hook.read_bytes(), installed)

        real_lfs = shutil.which("git-lfs")
        if real_lfs is not None:
            version = self.run_command([real_lfs, "version"]).stdout
            if version.startswith("git-lfs/3.7.1 "):
                for _attempt in range(2):
                    result = self.run_command(
                        [real_lfs, "install", "--local"], cwd=repository
                    )
                    self.assertIn("Git LFS initialized", result.stdout)
                    self.assertEqual(hook.read_bytes(), installed)

        self.lfs_log.write_text("")
        linked = self.add_linked_worktree(repository, "lfs-reinstall-linked")
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        lfs_calls = [
            line
            for line in self.lfs_log.read_text().splitlines()
            if line.startswith("post-checkout ")
        ]
        self.assertEqual(len(lfs_calls), 1, self.lfs_log.read_text())

    def test_custom_hook_refused_and_repositories_are_independent(self) -> None:
        good = self.new_repository("independent good")
        bad = self.new_repository("independent custom")
        self.add_sources(good)
        self.add_sources(bad)
        custom = self.hook(bad)
        original = b"#!/bin/sh\nprintf custom\\n\n"
        custom.write_bytes(original)
        custom.chmod(0o755)
        result = self.install(good, bad, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.hook(good).is_file())
        self.assertEqual(custom.read_bytes(), original)
        self.assertIn("manual review", result.stderr)

    def test_bundle_closure_modes_partial_resume_and_damage(self) -> None:
        repository = self.new_repository("bundle modes")
        self.add_sources(repository, helper=True)
        self.install(repository)
        bundle = self.bundle_from_hook(self.hook(repository))
        self.assertEqual(
            {entry.name for entry in bundle.iterdir()},
            {"post-checkout", "setup.sh", "worktree_storage.py", "version"},
        )
        self.assertEqual(stat.S_IMODE(bundle.stat().st_mode), 0o500)
        self.assertEqual(stat.S_IMODE((bundle / "post-checkout").stat().st_mode), 0o500)
        self.assertEqual(stat.S_IMODE((bundle / "setup.sh").stat().st_mode), 0o400)
        self.assertEqual(
            stat.S_IMODE((bundle / "worktree_storage.py").stat().st_mode), 0o400
        )
        self.assertEqual(stat.S_IMODE((bundle / "version").stat().st_mode), 0o400)

        (bundle / "setup.sh").chmod(0o600)
        damaged = self.install(repository, check=False)
        self.assertNotEqual(damaged.returncode, 0)
        self.assertIn("mode 0400", damaged.stderr)

        partial = self.new_repository("partial bundle")
        self.add_sources(partial, helper=True)
        interrupted = self.install(
            partial,
            env={"INSTALL_POST_CHECKOUT_TEST_INTERRUPT_AFTER_ENTRY": "setup.sh"},
            check=False,
        )
        self.assertNotEqual(interrupted.returncode, 0)
        self.assertFalse(self.hook(partial).exists())
        version = next((partial / ".git/.skyvern-worktree-hooks").iterdir())
        self.assertEqual({entry.name for entry in version.iterdir()}, {"setup.sh"})
        self.install(partial)

        bad_partial = self.new_repository("bad partial bundle")
        self.add_sources(bad_partial)
        self.install(
            bad_partial,
            env={"INSTALL_POST_CHECKOUT_TEST_INTERRUPT_AFTER_ENTRY": "setup.sh"},
            check=False,
        )
        bad_version = next((bad_partial / ".git/.skyvern-worktree-hooks").iterdir())
        (bad_version / "unexpected").write_text("preserve\n")
        retry = self.install(bad_partial, check=False)
        self.assertNotEqual(retry.returncode, 0)
        self.assertTrue((bad_version / "unexpected").exists())
        self.assertFalse(self.hook(bad_partial).exists())

    def test_import_isolation_and_runtime_closure_tamper(self) -> None:
        repository = self.new_repository("import isolation")
        self.add_sources(repository)
        self.install(repository)
        hook = self.hook(repository)
        hostile = self.root / "hostile PYTHONPATH"
        sentinel = self.root / "hostile-import-sentinel"
        self.add_hostile_modules(hostile, sentinel)
        result = self.run_command(
            [hook, "1" * 40, "2" * 40, "1"],
            cwd=repository,
            env={"PYTHONPATH": str(hostile)},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel.exists())

        bundle = self.bundle_from_hook(hook)
        bundle.chmod(0o700)
        self.add_hostile_modules(bundle, sentinel)
        bundle.chmod(0o500)
        tampered = self.invoke_hook(hook, repository)
        self.assertNotEqual(tampered.returncode, 0)
        self.assertIn("not closed", tampered.stderr)
        self.assertFalse(sentinel.exists())

    def test_snapshot_execution_survives_same_inode_pwrite_then_refuses(self) -> None:
        repository = self.new_repository("snapshot pwrite")
        self.add_sources(repository, helper=True)
        self.install(repository)
        hook = self.hook(repository)
        bundle = self.bundle_from_hook(hook)
        callback = self.root / "pwrite-bundle.py"
        sentinel = self.root / "mutated-snapshot-ran"
        original_setup = (bundle / "setup.sh").read_bytes()
        original_helper = (bundle / "worktree_storage.py").read_bytes()
        replacement_setup = (
            f"#!/bin/bash\nprintf hacked > {str(sentinel)!r}\nexit 0\n".encode()
        ).ljust(len(original_setup), b"#")[: len(original_setup)]
        replacement_helper = (
            f"open({str(sentinel)!r}, 'w').write('hacked')\n".encode()
        ).ljust(len(original_helper), b"#")[: len(original_helper)]
        self.write_executable(
            callback,
            f"""#!/usr/bin/env python3
import os
import pathlib
bundle = pathlib.Path({str(bundle)!r})
for name, content, mode in (
    ("setup.sh", bytes.fromhex({replacement_setup.hex()!r}), 0o400),
    ("worktree_storage.py", bytes.fromhex({replacement_helper.hex()!r}), 0o400),
):
    path = bundle / name
    path.chmod(0o600)
    descriptor = os.open(path, os.O_WRONLY)
    os.pwrite(descriptor, content, 0)
    os.ftruncate(descriptor, len(content))
    os.close(descriptor)
    path.chmod(mode)
""",
        )
        branch = "pwrite-branch"
        self.git(repository, "branch", branch)
        linked = self.root / "pwrite-worktree"
        result = self.run_command(
            ["git", "-C", repository, "worktree", "add", "-q", linked, branch],
            env={"POST_CHECKOUT_TEST_AFTER_VERIFY": str(callback)},
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((linked / ".setup-ran").read_text(), "helper snapshot\n")
        self.assertFalse(sentinel.exists())
        for stamp in self.stamps(linked):
            stamp.unlink()
        (linked / ".setup-ran").unlink()
        refused = self.invoke_hook(hook, linked)
        self.assertNotEqual(refused.returncode, 0)
        self.assertFalse((linked / ".setup-ran").exists())

    def test_setup_uses_pinned_worktree_fd_after_path_replacement(self) -> None:
        repository = self.new_repository("pinned worktree authority")
        self.add_sources(repository, helper=True)
        self.install(repository)
        linked = self.add_linked_worktree(repository, "pinned-authority")
        linked_git_dir = self.git_dir(linked)
        for stamp in self.stamps(linked):
            stamp.unlink()
        (linked / ".setup-ran").unlink()
        moved = self.root / "pinned-authority-moved"
        callback = self.root / "replace-worktree-root.py"
        self.write_executable(
            callback,
            f"""#!/usr/bin/env python3
import os
import pathlib
original = pathlib.Path({str(linked)!r})
os.rename(original, {str(moved)!r})
original.mkdir()
(original / "replacement-sentinel").write_text("untouched\\n")
""",
        )
        result = self.invoke_hook(
            self.hook(repository),
            linked,
            env={"POST_CHECKOUT_TEST_AFTER_WORKTREE_PIN": str(callback)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((moved / ".setup-ran").read_text(), "helper snapshot\n")
        self.assertEqual(
            {entry.name for entry in linked.iterdir()}, {"replacement-sentinel"}
        )
        self.assertEqual(
            len(list(linked_git_dir.glob("dotfiles-worktree-setup-success.*"))), 1
        )

        backfill_repo = self.new_repository("pinned backfill authority")
        self.add_sources(backfill_repo, helper=True)
        backfill = self.add_linked_worktree(backfill_repo, "pinned-backfill-before")
        backfill_git_dir = self.git_dir(backfill)
        backfill_moved = self.root / "pinned-backfill-moved"
        resolution_marker = self.root / "backfill-resolution-after-pin"
        backfill_callback = self.root / "replace-backfill-root.py"
        self.write_executable(
            backfill_callback,
            f"""#!/usr/bin/env python3
import os
import pathlib
pathlib.Path({str(resolution_marker)!r}).write_text("pinned\\n")
original = pathlib.Path({str(backfill)!r})
root_fd = int(os.environ["INSTALL_POST_CHECKOUT_TEST_PINNED_WORKTREE_FD"])
root_status = os.fstat(root_fd)
original_status = os.stat(original)
if (root_status.st_dev, root_status.st_ino) != (
    original_status.st_dev,
    original_status.st_ino,
):
    raise SystemExit(0)
os.rename(original, {str(backfill_moved)!r})
pathlib.Path({str(backfill_git_dir / "gitdir")!r}).write_text(
    {str(backfill_moved / ".git")!r} + "\\n"
)
original.mkdir()
(original / ".git").mkdir()
(original / "replacement-sentinel").write_text("untouched\\n")
""",
        )
        guarded_bin = self.root / "backfill-git-guard"
        guarded_bin.mkdir()
        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        self.write_executable(
            guarded_bin / "git",
            f"""#!/usr/bin/env python3
import os
import pathlib
import sys
arguments = sys.argv[1:]
if arguments[-2:] == ["rev-parse", "--git-dir"] and arguments[:2] in (
    ["-C", {str(backfill)!r}],
    ["-C", "."],
):
    if not pathlib.Path({str(resolution_marker)!r}).exists():
        raise SystemExit(87)
os.execv({real_git!r}, [{real_git!r}, *arguments])
""",
        )
        self.use_test_git(guarded_bin / "git")
        install = self.install(
            backfill_repo,
            env={
                "INSTALL_POST_CHECKOUT_TEST_AFTER_WORKTREE_PIN": str(backfill_callback),
            },
            check=False,
        )
        self.assertEqual(install.returncode, 0, install.stderr)
        self.assertTrue((backfill_moved / ".setup-ran").is_file(), install.stderr)
        self.assertEqual(
            (backfill_moved / ".setup-ran").read_text(), "helper snapshot\n"
        )
        self.assertEqual(
            {entry.name for entry in backfill.iterdir()},
            {".git", "replacement-sentinel"},
        )
        self.assertEqual(list((backfill / ".git").iterdir()), [])
        self.assertEqual(
            len(list(backfill_git_dir.glob("dotfiles-worktree-setup-success.*"))),
            1,
        )

    def test_offline_locked_worktrees_are_skipped_before_current_match(self) -> None:
        repository = self.new_repository("offline association")
        self.add_sources(repository)
        self.install(repository)

        missing = self.add_linked_worktree(repository, "000-missing")
        self.git(repository, "worktree", "lock", str(missing))
        moved_missing = self.root / "moved-missing-worktree"
        missing.rename(moved_missing)
        self.assertFalse(missing.exists())

        restricted_parent = self.root / "restricted-offline"
        restricted_parent.mkdir()
        restricted = restricted_parent / "001-permission-worktree"
        self.git(repository, "branch", "branch-001-permission")
        self.run_command(
            [
                "git",
                "-C",
                repository,
                "worktree",
                "add",
                "-q",
                restricted,
                "branch-001-permission",
            ]
        )
        self.git(repository, "worktree", "lock", str(restricted))
        restricted_parent.chmod(0)
        try:
            with self.assertRaises(PermissionError):
                restricted.stat()
            current = self.add_linked_worktree(repository, "zzz-current")
        finally:
            restricted_parent.chmod(0o700)

        self.assertEqual((current / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(current)), 1)
        self.assertNotIn(
            "worktree storage setup reported errors", self.last_worktree_add.stderr
        )

        common_worktrees = self.common_dir(repository) / "worktrees"
        admin_names = sorted(entry.name for entry in common_worktrees.iterdir())
        self.assertLess(
            admin_names.index("000-missing-worktree"),
            admin_names.index("zzz-current-worktree"),
        )
        self.assertLess(
            admin_names.index("001-permission-worktree"),
            admin_names.index("zzz-current-worktree"),
        )
        self.assertTrue(
            (common_worktrees / "000-missing-worktree" / "locked").is_file()
        )
        self.assertTrue(
            (common_worktrees / "001-permission-worktree" / "locked").is_file()
        )

    def test_current_malformed_or_ambiguous_admin_fails_closed(self) -> None:
        repository = self.new_repository("closed association")
        self.add_sources(repository)
        self.install(repository)
        linked = self.add_linked_worktree(repository, "current-association")
        hook = self.hook(repository)
        admin = self.git_dir(linked)
        gitdir = admin / "gitdir"
        original_gitdir = gitdir.read_bytes()

        for stamp in self.stamps(linked):
            stamp.unlink()
        (linked / ".setup-ran").unlink()
        gitdir.write_bytes(b"relative/\x01/.git\n")
        malformed = self.invoke_hook(hook, linked)
        self.assertEqual(malformed.returncode, 0)
        self.assertIn(
            "admin gitdir record contains invalid control bytes", malformed.stderr
        )
        self.assertFalse((linked / ".setup-ran").exists())
        self.assertEqual(self.stamps(linked), [])
        gitdir.write_bytes(original_gitdir)

        ambiguous = self.common_dir(repository) / "worktrees/000-ambiguous-current"
        ambiguous.mkdir()
        (ambiguous / "gitdir").write_bytes(original_gitdir)
        ambiguous_result = self.invoke_hook(hook, linked)
        self.assertEqual(ambiguous_result.returncode, 0)
        self.assertIn(
            "linked worktree .git points to a sibling admin",
            ambiguous_result.stderr,
        )
        self.assertFalse((linked / ".setup-ran").exists())
        self.assertEqual(self.stamps(linked), [])
        (ambiguous / "gitdir").unlink()
        ambiguous.rmdir()

        matched = self.invoke_hook(hook, linked)
        self.assertEqual(matched.returncode, 0, matched.stderr)
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

    def test_relative_root_gitfile_runtime(self) -> None:
        self.assert_relative_runtime_case(
            "relative-root", relative_root=True, relative_admin=False
        )

    def test_relative_admin_backlink_runtime(self) -> None:
        self.assert_relative_runtime_case(
            "relative-admin", relative_root=False, relative_admin=True
        )

    def test_relative_both_runtime_preserves_cr_lf_paths(self) -> None:
        self.assert_relative_runtime_case(
            "relative\nline\rreturn",
            relative_root=True,
            relative_admin=True,
        )

    def test_relative_records_backfill_and_move(self) -> None:
        repository = self.new_repository("relative backfill")
        self.add_sources(repository)
        linked = self.add_linked_worktree(repository, "relative-backfill")
        self.rewrite_link_records(linked, relative_root=True, relative_admin=True)
        self.use_fixture_worktree_list(repository, [linked])
        installed = self.install(repository)
        self.assertIn("installed ", installed.stdout)
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

        moved_repository = self.new_repository("relative moved")
        self.add_sources(moved_repository)
        moved_linked = self.add_linked_worktree(
            moved_repository, "relative-before-move"
        )
        admin = self.git_dir(moved_linked)
        destination = self.root / "relative-after-move-worktree"
        moved_linked.rename(destination)
        (destination / ".git").write_bytes(
            b"gitdir: " + os.fsencode(os.path.relpath(admin, destination)) + b"\n"
        )
        (admin / "gitdir").write_bytes(
            os.fsencode(os.path.relpath(destination / ".git", admin)) + b"\n"
        )
        self.use_fixture_worktree_list(moved_repository, [destination])
        moved_result = self.install(moved_repository)
        self.assertIn("installed ", moved_result.stdout)
        self.assertEqual(
            (destination / ".setup-ran").read_text(), "setup-only snapshot\n"
        )
        self.assertEqual(len(self.stamps(destination)), 1)

    def test_relative_records_reject_escape_symlink_sibling_and_control(self) -> None:
        def prepared(name: str) -> tuple[Path, Path, Path, bytes]:
            repository = self.new_repository(name)
            self.add_sources(repository)
            self.install(repository)
            self.git(repository, "branch", "relative-fixture-branch")
            linked = self.add_linked_worktree(
                repository, name, branch="relative-fixture-branch"
            )
            admin = self.git_dir(linked)
            original = (linked / ".git").read_bytes()
            for stamp in self.stamps(linked):
                stamp.unlink()
            (linked / ".setup-ran").unlink()
            return repository, linked, admin, original

        repository, linked, admin, _original = prepared("relative escape")
        depth = len(os.fsencode(linked).split(b"/")) - 1
        escaped = b"../" * depth + os.fsencode(admin).lstrip(b"/")
        (linked / ".git").write_bytes(b"gitdir: " + escaped + b"\n")
        result = self.invoke_hook(self.hook(repository), linked)
        self.assertEqual(result.returncode, 0)
        self.assertIn("escapes its expected domain", result.stderr)
        self.assertFalse((linked / ".setup-ran").exists())

        repository, linked, admin, _original = prepared("relative symlink")
        jump = linked / "admin-link"
        jump.symlink_to(admin.parent, target_is_directory=True)
        (linked / ".git").write_bytes(
            b"gitdir: admin-link/" + os.fsencode(admin.name) + b"\n"
        )
        result = self.invoke_hook(self.hook(repository), linked)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((linked / ".setup-ran").exists())

        repository, linked, _admin, _original = prepared("relative sibling")
        sibling = self.add_linked_worktree(repository, "relative-sibling-other")
        sibling_admin = self.git_dir(sibling)
        (linked / ".git").write_bytes(
            b"gitdir: " + os.fsencode(os.path.relpath(sibling_admin, linked)) + b"\n"
        )
        result = self.invoke_hook(self.hook(repository), linked)
        self.assertEqual(result.returncode, 0)
        self.assertFalse((linked / ".setup-ran").exists())

        repository, linked, _admin, _original = prepared("relative control")
        (linked / ".git").write_bytes(b"gitdir: ../bad\x01/admin\n")
        result = self.invoke_hook(self.hook(repository), linked)
        self.assertEqual(result.returncode, 0)
        self.assertIn("invalid control bytes", result.stderr)
        self.assertFalse((linked / ".setup-ran").exists())

    def test_relative_records_require_canonical_components(self) -> None:
        repository = self.new_repository("relative canonical")
        self.add_sources(repository)
        self.install(repository)
        self.git(repository, "branch", "relative-canonical-branch")
        linked = self.add_linked_worktree(
            repository,
            "relative-canonical-linked",
            branch="relative-canonical-branch",
        )
        admin = self.git_dir(linked)
        for stamp in self.stamps(linked):
            stamp.unlink()
        (linked / ".setup-ran").unlink()
        relative = os.fsencode(os.path.relpath(admin, linked))
        self.assertTrue(relative.startswith(b"../"))
        aliases = (
            (b"./" + relative, "path is not canonical"),
            (relative.replace(b"/", b"//", 1), "path has malformed components"),
            (b"alias/../" + relative, "path is not canonical"),
        )
        for alias, expected_error in aliases:
            with self.subTest(alias=alias):
                (linked / ".git").write_bytes(b"gitdir: " + alias + b"\n")
                result = self.invoke_hook(self.hook(repository), linked)
                self.assertEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)
                self.assertFalse((linked / ".setup-ran").exists())
                self.assertEqual(self.stamps(linked), [])

        (linked / ".git").write_bytes(b"gitdir: " + relative + b"\n")
        canonical = self.invoke_hook(self.hook(repository), linked)
        self.assertEqual(canonical.returncode, 0, canonical.stderr)
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

    def test_real_git_relative_worktrees_when_supported(self) -> None:
        version = self.record(self.run_command(["git", "version"]).stdout)
        match = re.match(r"git version (\d+)\.(\d+)", version)
        self.assertIsNotNone(match)
        assert match is not None
        if (int(match.group(1)), int(match.group(2))) < (2, 48):
            self.skipTest("installed Git predates relative-worktree support")
        repository = self.new_repository("real relative worktree")
        self.add_sources(repository)
        self.git(repository, "config", "worktree.useRelativePaths", "true")
        linked = self.add_linked_worktree(repository, "real-relative")
        admin = self.git_dir(linked)
        self.assertFalse(
            os.path.isabs(
                os.fsdecode((linked / ".git").read_bytes()[len(b"gitdir: ") : -1])
            )
        )
        self.assertFalse(
            os.path.isabs(os.fsdecode((admin / "gitdir").read_bytes()[:-1]))
        )
        self.install(repository)
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")

    def test_concurrent_installs_use_persistent_flock(self) -> None:
        repository = self.new_repository("concurrent install")
        self.add_sources(repository)
        callback = self.root / "hold-lock.py"
        self.write_executable(
            callback,
            """#!/usr/bin/env python3
import time
time.sleep(0.35)
""",
        )
        environment = self.env.copy()
        environment["INSTALL_POST_CHECKOUT_TEST_AFTER_LOCK"] = str(callback)
        first = subprocess.Popen(
            [self.installer, repository],
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(0.08)
        second = subprocess.Popen(
            [self.installer, repository],
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        first_output = first.communicate(timeout=10)
        second_output = second.communicate(timeout=10)
        self.assertEqual(
            (first.returncode, second.returncode),
            (0, 0),
            first_output + second_output,
        )
        lock = repository / ".git/.skyvern-worktree-hooks.lock"
        self.assertTrue(lock.is_file())
        self.assertEqual(stat.S_IMODE(lock.stat().st_mode), 0o600)

    def test_linux_renameat2_helper_is_shared_and_prefers_wrapper(self) -> None:
        installer_source = INSTALLER.read_text()
        runtime_source = (REPO_ROOT / "git/hooks/post-checkout").read_text()

        def helper_source(source: str) -> str:
            tree = ast.parse(source)
            names = {
                "ELF_RENAMEAT2_SYSCALLS",
                "linux_renameat2_syscall_number",
                "linux_process_elf_header",
                "linux_renameat2",
            }
            segments = []
            for node in tree.body:
                selected = isinstance(node, ast.FunctionDef) and node.name in names
                if isinstance(node, ast.Assign):
                    selected = any(
                        isinstance(target, ast.Name) and target.id in names
                        for target in node.targets
                    )
                if selected:
                    segment = ast.get_source_segment(source, node)
                    self.assertIsNotNone(segment)
                    assert segment is not None
                    segments.append(segment)
            self.assertEqual(len(segments), 4)
            return "\n".join(segments)

        self.assertEqual(helper_source(installer_source), helper_source(runtime_source))
        namespace = self.linux_helper_namespace(INSTALLER)
        function = cast(Callable[..., int], namespace["linux_renameat2"])
        wrapper = mock.Mock(return_value=0)
        library = types.SimpleNamespace(renameat2=wrapper)
        result = function(library, 3, b"old", 4, b"new", 2, b"", (0, 0))
        self.assertEqual(result, 0)
        wrapper.assert_called_once_with(3, b"old", 4, b"new", 2)

    def test_linux_renameat2_elf_x86_64_x32_and_i386_are_distinct(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int],
            namespace["linux_renameat2_syscall_number"],
        )
        expected = {
            (2, 1, 62): 316,
            (1, 1, 62): 0x40000000 | 316,
            (1, 1, 3): 353,
        }
        for identity, syscall_number in expected.items():
            with self.subTest(identity=identity):
                self.assertEqual(selector(self.elf_header(*identity)), syscall_number)

    def test_linux_renameat2_elf_arm_and_aarch64_native_compat(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int],
            namespace["linux_renameat2_syscall_number"],
        )
        for identity, syscall_number in (
            ((1, 1, 40), 382),
            ((1, 2, 40), 382),
            ((2, 1, 183), 276),
            ((2, 2, 183), 276),
        ):
            with self.subTest(identity=identity):
                self.assertEqual(selector(self.elf_header(*identity)), syscall_number)

    def test_linux_renameat2_elf_powerpc_native_compat_and_endian(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int],
            namespace["linux_renameat2_syscall_number"],
        )
        for identity in (
            (1, 1, 20),
            (1, 2, 20),
            (2, 1, 21),
            (2, 2, 21),
        ):
            with self.subTest(identity=identity):
                self.assertEqual(selector(self.elf_header(*identity)), 357)

    def test_linux_renameat2_elf_s390_and_riscv_native_compat(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int], namespace["linux_renameat2_syscall_number"]
        )
        for identity, syscall_number in (
            ((1, 2, 22), 347),
            ((2, 2, 22), 347),
            ((1, 1, 243), 276),
            ((2, 1, 243), 276),
        ):
            with self.subTest(identity=identity):
                self.assertEqual(selector(self.elf_header(*identity)), syscall_number)

    def test_linux_renameat2_elf_rejects_unknown_identity(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int], namespace["linux_renameat2_syscall_number"]
        )
        for header in (
            self.elf_header(2, 1, 999),
            self.elf_header(2, 2, 62),
            self.elf_header(1, 1, 183),
        ):
            with self.subTest(header=header[:24]):
                with self.assertRaisesRegex(OSError, "unsupported for current ELF"):
                    selector(header)

    def test_linux_renameat2_elf_rejects_magic_class_data_and_truncation(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int], namespace["linux_renameat2_syscall_number"]
        )
        valid = self.elf_header(2, 1, 62)
        malformed = [
            b"not-elf",
            valid[:32],
            valid[:4] + b"\x00" + valid[5:],
            valid[:5] + b"\x03" + valid[6:],
        ]
        for header in malformed:
            with self.subTest(header=header[:16]):
                with self.assertRaises(OSError) as error:
                    selector(header)
                self.assertEqual(error.exception.errno, errno.ENOSYS)

    def test_linux_renameat2_elf_rejects_unsupported_abi_metadata(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int], namespace["linux_renameat2_syscall_number"]
        )
        malformed = [
            self.elf_header(2, 1, 62, osabi=9),
            self.elf_header(2, 1, 62, abi_version=1),
            self.elf_header(2, 1, 62, elf_type=1),
            self.elf_header(2, 1, 62, version=0),
            self.elf_header(2, 1, 62, header_size=63),
        ]
        for header in malformed:
            with self.subTest(header=header):
                with self.assertRaises(OSError) as error:
                    selector(header)
                self.assertEqual(error.exception.errno, errno.ENOSYS)

    def test_linux_renameat2_elf_rejects_arm_oabi(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        selector = cast(
            Callable[[bytes], int], namespace["linux_renameat2_syscall_number"]
        )
        with self.assertRaisesRegex(OSError, "does not use EABI") as error:
            selector(self.elf_header(1, 1, 40, flags=0))
        self.assertEqual(error.exception.errno, errno.ENOSYS)

    def test_linux_process_elf_fallback_requires_exact_current_identity(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        reader = cast(
            Callable[[bytes, tuple[int, int], bytes], bytes],
            namespace["linux_process_elf_header"],
        )
        header = self.elf_header(2, 1, 62)
        path, identity = self.elf_file(header)
        self.assertEqual(reader(path, identity, b"/missing-proc-self-exe"), header)
        with self.assertRaisesRegex(OSError, "does not match its expected identity"):
            reader(path, (identity[0], identity[1] + 1), b"/missing-proc-self-exe")

    def test_linux_process_elf_fallback_rejects_unreadable_or_invalid_path(
        self,
    ) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        reader = cast(
            Callable[[bytes, tuple[int, int], bytes], bytes],
            namespace["linux_process_elf_header"],
        )
        with self.assertRaises(OSError):
            reader(b"/missing-pinned-python", (1, 1), b"/missing-proc-self-exe")
        with self.assertRaisesRegex(OSError, "current executable path is invalid"):
            reader(b"relative-python", (1, 1), b"/missing-proc-self-exe")

    def test_linux_renameat2_syscall_fallback_success(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        function = cast(Callable[..., int], namespace["linux_renameat2"])
        syscall = mock.Mock(return_value=0)
        library = types.SimpleNamespace(syscall=syscall)
        path, identity = self.elf_file(self.elf_header(2, 1, 62))
        result = function(
            library,
            5,
            b"first",
            6,
            b"second",
            1,
            path,
            identity,
            b"/missing-proc-self-exe",
        )
        self.assertEqual(result, 0)
        arguments = syscall.call_args.args
        self.assertEqual(arguments[0].value, 316)
        self.assertEqual(arguments[1].value, 5)
        self.assertEqual(arguments[2].value, b"first")
        self.assertEqual(arguments[3].value, 6)
        self.assertEqual(arguments[4].value, b"second")
        self.assertEqual(arguments[5].value, 1)

    def test_linux_renameat2_syscall_fallback_selects_x32_bit(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        function = cast(Callable[..., int], namespace["linux_renameat2"])
        syscall = mock.Mock(return_value=0)
        library = types.SimpleNamespace(syscall=syscall)
        path, identity = self.elf_file(self.elf_header(1, 1, 62), "x32-python")
        result = function(
            library,
            5,
            b"first",
            6,
            b"second",
            1,
            path,
            identity,
            b"/missing-proc-self-exe",
        )
        self.assertEqual(result, 0)
        self.assertEqual(syscall.call_args.args[0].value, 0x40000000 | 316)

    def test_linux_renameat2_syscall_fallback_never_guesses_from_bad_elf(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        function = cast(Callable[..., int], namespace["linux_renameat2"])
        syscall = mock.Mock(return_value=0)
        path, identity = self.elf_file(b"not an ELF executable", "bad-python")
        with self.assertRaisesRegex(OSError, "invalid ELF header"):
            function(
                types.SimpleNamespace(syscall=syscall),
                1,
                b"a",
                1,
                b"b",
                2,
                path,
                identity,
                b"/missing-proc-self-exe",
            )
        syscall.assert_not_called()

    def test_linux_renameat2_syscall_fallback_preserves_errno(self) -> None:
        namespace = self.linux_helper_namespace(INSTALLER)
        function = cast(Callable[..., int], namespace["linux_renameat2"])

        def fail_syscall(*_arguments: object) -> int:
            ctypes.set_errno(errno.ENOSYS)
            return -1

        library = types.SimpleNamespace(syscall=mock.Mock(side_effect=fail_syscall))
        path, identity = self.elf_file(self.elf_header(2, 1, 62))
        ctypes.set_errno(0)
        self.assertEqual(
            function(
                library,
                5,
                b"first",
                6,
                b"second",
                2,
                path,
                identity,
                b"/missing-proc-self-exe",
            ),
            -1,
        )
        self.assertEqual(ctypes.get_errno(), errno.ENOSYS)

    def test_v1_dispatcher_and_v2_backfill_share_stable_worktree_lock(self) -> None:
        repository = self.new_repository("stable worktree lock")
        hold = self.root / "hold-v1-setup"
        self.add_sources(repository)
        setup = repository / ".superset/setup.sh"
        setup.write_text(
            setup.read_text().replace(
                'if [[ "${SUPERSET_POST_CHECKOUT:-0}" == "1" ]]; then',
                f"""if [[ -e .hold-setup ]]; then
  : > {shlex.quote(str(hold))}.entered
  while [[ ! -e {shlex.quote(str(hold))}.release ]]; do
    sleep 0.02
  done
fi
if [[ "${{SUPERSET_POST_CHECKOUT:-0}}" == "1" ]]; then""",
            )
        )
        self.git(repository, "add", ".superset/setup.sh")
        self.git(repository, "commit", "-qm", "add setup hold fixture")
        self.install(repository)
        hook = self.hook(repository)
        linked = self.add_linked_worktree(repository, "stable-lock-linked")
        for stamp in self.stamps(linked):
            stamp.unlink()
        (linked / ".setup-ran").unlink()
        (linked / ".hold-setup").write_text("")

        old_environment = self.env.copy()
        old_hook = subprocess.Popen(
            [hook, NULL_OID, "1" * 40, "1"],
            cwd=linked,
            env=old_environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 5
        while not Path(f"{hold}.entered").exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(Path(f"{hold}.entered").exists())

        with (repository / ".superset/setup.sh").open("a") as output:
            output.write("# reviewed v2 for lock serialization\n")
        self.git(repository, "add", ".superset/setup.sh")
        self.git(repository, "commit", "-qm", "review setup v2 for lock")
        installer = subprocess.Popen(
            [self.installer, repository],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(0.3)
        self.assertIsNone(installer.poll(), "v2 backfill bypassed the v1 setup lock")
        Path(f"{hold}.release").write_text("")
        old_output = old_hook.communicate(timeout=10)
        installer_output = installer.communicate(timeout=10)
        self.assertEqual(old_hook.returncode, 0, old_output)
        self.assertEqual(installer.returncode, 0, installer_output)
        self.assertEqual(len(self.stamps(linked)), 2)
        locks = list(self.git_dir(linked).glob("dotfiles-worktree-setup-lock.*"))
        self.assertEqual(len(locks), 1)

    def test_setup_child_retains_lock_after_parent_sigkill(self) -> None:
        def reviewed_hold_setup(repository: Path, control: Path) -> None:
            self.add_sources(repository)
            setup = repository / ".superset/setup.sh"
            setup.write_text(
                setup.read_text().replace(
                    'if [[ "${SUPERSET_POST_CHECKOUT:-0}" == "1" ]]; then',
                    f"""if [[ -e .hold-lock-child ]]; then
  printf '%s\\n' "$$" >> {shlex.quote(str(control))}.entries
  while [[ ! -e {shlex.quote(str(control))}.release ]]; do
    sleep 0.02
  done
fi
if [[ "${{SUPERSET_POST_CHECKOUT:-0}}" == "1" ]]; then""",
                )
            )
            self.git(repository, "add", ".superset/setup.sh")
            self.git(repository, "commit", "-qm", "add lock lifetime fixture")

        def wait_for_entry(control: Path) -> None:
            entries = Path(f"{control}.entries")
            deadline = time.monotonic() + 8
            while not entries.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(entries.exists())

        def assert_one_entry(control: Path) -> None:
            entries = Path(f"{control}.entries").read_text().splitlines()
            self.assertEqual(len(entries), 1)

        runtime_repository = self.new_repository("runtime child lock lifetime")
        runtime_control = self.root / "runtime-child-lock"
        reviewed_hold_setup(runtime_repository, runtime_control)
        self.install(runtime_repository)
        runtime_linked = self.add_linked_worktree(
            runtime_repository, "runtime-child-lock"
        )
        for stamp in self.stamps(runtime_linked):
            stamp.unlink()
        (runtime_linked / ".setup-ran").unlink()
        (runtime_linked / ".hold-lock-child").write_text("")
        first = subprocess.Popen(
            [self.hook(runtime_repository), NULL_OID, "1" * 40, "1"],
            cwd=runtime_linked,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        wait_for_entry(runtime_control)
        first.kill()
        first.wait(timeout=5)
        contender = subprocess.Popen(
            [self.hook(runtime_repository), NULL_OID, "1" * 40, "1"],
            cwd=runtime_linked,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.35)
        self.assertIsNone(contender.poll())
        assert_one_entry(runtime_control)
        Path(f"{runtime_control}.release").write_text("")
        contender_output = contender.communicate(timeout=10)
        first.communicate(timeout=5)
        self.assertEqual(contender.returncode, 0, contender_output)
        self.assertEqual(
            len(Path(f"{runtime_control}.entries").read_text().splitlines()), 2
        )

        backfill_repository = self.new_repository("backfill child lock lifetime")
        backfill_control = self.root / "backfill-child-lock"
        reviewed_hold_setup(backfill_repository, backfill_control)
        backfill_linked = self.add_linked_worktree(
            backfill_repository, "backfill-child-lock"
        )
        (backfill_linked / ".hold-lock-child").write_text("")
        installer = subprocess.Popen(
            [self.installer, backfill_repository],
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        wait_for_entry(backfill_control)
        installer.kill()
        installer.wait(timeout=5)
        contender = subprocess.Popen(
            [self.hook(backfill_repository), NULL_OID, "1" * 40, "1"],
            cwd=backfill_linked,
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.35)
        self.assertIsNone(contender.poll())
        assert_one_entry(backfill_control)
        Path(f"{backfill_control}.release").write_text("")
        contender_output = contender.communicate(timeout=10)
        installer.communicate(timeout=5)
        self.assertEqual(contender.returncode, 0, contender_output)
        self.assertEqual(
            len(Path(f"{backfill_control}.entries").read_text().splitlines()), 2
        )

    def test_backfill_requires_exact_registered_association(self) -> None:
        primary = self.new_repository("primary association")
        self.add_sources(primary)
        self.install(primary)
        self.assertTrue(self.hook(primary).is_file())
        self.assertFalse((primary / ".setup-ran").exists())
        self.assertEqual(self.stamps(primary), [])

        sibling_repo = self.new_repository("sibling admin substitution")
        self.add_sources(sibling_repo)
        sibling_current = self.add_linked_worktree(sibling_repo, "sibling-current")
        sibling_other = self.add_linked_worktree(sibling_repo, "sibling-other")
        sibling_other_admin = self.git_dir(sibling_other)

        common_repo = self.new_repository("common dir substitution")
        self.add_sources(common_repo)
        common_current = self.add_linked_worktree(common_repo, "common-current")
        substituted_common = self.common_dir(common_repo)

        real_git = shutil.which("git")
        self.assertIsNotNone(real_git)
        fake_bin = self.root / "backfill-association-git"
        fake_bin.mkdir()
        self.write_executable(
            fake_bin / "git",
            f"""#!/usr/bin/env python3
import os
import sys
arguments = sys.argv[1:]
if arguments == ["-C", ".", "rev-parse", "--git-dir"]:
    current = os.stat(".")
    sibling = os.stat({str(sibling_current)!r})
    common = os.stat({str(common_current)!r})
    if (current.st_dev, current.st_ino) == (sibling.st_dev, sibling.st_ino):
        print({str(sibling_other_admin)!r})
        raise SystemExit(0)
    if (current.st_dev, current.st_ino) == (common.st_dev, common.st_ino):
        print({str(substituted_common)!r})
        raise SystemExit(0)
os.execv({real_git!r}, [{real_git!r}, *arguments])
""",
        )
        self.use_test_git(fake_bin / "git")

        sibling_result = self.install(sibling_repo, check=False)
        self.assertNotEqual(sibling_result.returncode, 0)
        self.assertIn(
            "reported worktree Git directory does not match its .git entry",
            sibling_result.stderr,
        )
        self.assertFalse((sibling_current / ".setup-ran").exists())
        self.assertEqual(self.stamps(sibling_current), [])
        self.assertEqual(self.stamps(sibling_other), [])

        common_result = self.install(common_repo, check=False)
        self.assertNotEqual(common_result.returncode, 0)
        self.assertIn(
            "reported worktree Git directory does not match its .git entry",
            common_result.stderr,
        )
        self.assertFalse((common_current / ".setup-ran").exists())
        self.assertEqual(self.stamps(common_current), [])

    def test_worktree_backfill_before_and_during_publication(self) -> None:
        existing_repo = self.new_repository("existing backfill")
        self.add_sources(existing_repo)
        existing = self.add_linked_worktree(existing_repo, "existing-unconfigured")
        self.assertFalse((existing / ".setup-ran").exists())
        self.install(existing_repo)
        self.assertEqual((existing / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(existing)), 1)

        during_repo = self.new_repository("during publication")
        self.add_sources(during_repo)
        branch = "during-branch"
        self.git(during_repo, "branch", branch)
        linked = self.root / "during-publication-worktree"
        callback = self.root / "add-during.py"
        self.write_executable(
            callback,
            f"""#!/usr/bin/env python3
import subprocess
subprocess.run(["git", "-C", {str(during_repo)!r}, "worktree", "add", "-q", {str(linked)!r}, {branch!r}], check=True)
""",
        )
        self.install(
            during_repo,
            env={"INSTALL_POST_CHECKOUT_TEST_BEFORE_PUBLICATION": str(callback)},
        )
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertEqual(len(self.stamps(linked)), 1)

        after_repo = self.new_repository("after publication")
        self.add_sources(after_repo)
        after_branch = "after-branch"
        self.git(after_repo, "branch", after_branch)
        after_linked = self.root / "after-publication-worktree"
        after_callback = self.root / "add-after.py"
        self.write_executable(
            after_callback,
            f"""#!/usr/bin/env python3
import subprocess
subprocess.run(["git", "-C", {str(after_repo)!r}, "worktree", "add", "-q", {str(after_linked)!r}, {after_branch!r}], check=True)
""",
        )
        self.install(
            after_repo,
            env={"INSTALL_POST_CHECKOUT_TEST_AFTER_PUBLICATION": str(after_callback)},
        )
        self.assertEqual(
            (after_linked / ".setup-ran").read_text(), "setup-only snapshot\n"
        )
        self.assertEqual(len(self.stamps(after_linked)), 1)

        changed_repo = self.new_repository("before checks material")
        self.add_sources(changed_repo)
        changed_branch = "changed-branch"
        self.git(changed_repo, "branch", changed_branch)
        changed_linked = self.root / "before-checks-worktree"
        changed_callback = self.root / "add-before-checks.py"
        self.write_executable(
            changed_callback,
            f"""#!/usr/bin/env python3
import subprocess
subprocess.run(["git", "-C", {str(changed_repo)!r}, "worktree", "add", "-q", {str(changed_linked)!r}, {changed_branch!r}], check=True)
""",
        )
        failed = self.install(
            changed_repo,
            env={
                "INSTALL_POST_CHECKOUT_TEST_BEFORE_PUBLICATION_CHECKS": str(
                    changed_callback
                )
            },
            check=False,
        )
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("hooks state changed", failed.stderr)
        self.assertFalse(self.hook(changed_repo).exists())
        self.install(changed_repo)
        self.assertEqual(
            (changed_linked / ".setup-ran").read_text(), "setup-only snapshot\n"
        )

    def test_publication_crash_evidence_parent_and_final_races(self) -> None:
        before = self.new_repository("crash before")
        self.add_sources(before)
        killer = self.root / "kill-parent.py"
        self.write_executable(
            killer,
            """#!/usr/bin/env python3
import os
import signal
os.kill(os.getppid(), signal.SIGKILL)
""",
        )
        crashed = self.install(
            before,
            env={"INSTALL_POST_CHECKOUT_TEST_BEFORE_PUBLICATION": str(killer)},
            check=False,
        )
        self.assertNotEqual(crashed.returncode, 0)
        self.assertFalse(self.hook(before).exists())
        self.assertGreaterEqual(len(self.prepared(before)), 1)

        after = self.new_repository("crash after")
        self.add_sources(after)
        stock = self.hook(after)
        stock.write_text(STOCK_LFS_HOOK)
        stock.chmod(0o755)
        crashed = self.install(
            after,
            env={"INSTALL_POST_CHECKOUT_TEST_AFTER_PUBLICATION": str(killer)},
            check=False,
        )
        self.assertNotEqual(crashed.returncode, 0)
        self.assertNotEqual(stock.read_text(), STOCK_LFS_HOOK)
        self.assertTrue(
            any(path.read_text() == STOCK_LFS_HOOK for path in self.prepared(after))
        )

        parent = self.new_repository("parent replacement")
        self.add_sources(parent)
        hooks = self.hooks_dir(parent)
        moved = hooks.with_name("hooks-pinned")
        callback = self.root / "replace-parent.py"
        self.write_executable(
            callback,
            f"""#!/usr/bin/env python3
import os
os.rename({str(hooks)!r}, {str(moved)!r})
os.mkdir({str(hooks)!r}, 0o755)
""",
        )
        result = self.install(
            parent,
            env={"INSTALL_POST_CHECKOUT_TEST_BEFORE_PUBLICATION": str(callback)},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((hooks / "post-checkout").exists())
        self.assertTrue((moved / "post-checkout").exists())

        post_exchange = self.new_repository("post exchange replacement")
        self.add_sources(post_exchange)
        post_hook = self.hook(post_exchange)
        post_callback = self.root / "replace-after-exchange.py"
        self.write_executable(
            post_callback,
            f"""#!/usr/bin/env python3
import os
import pathlib
path = pathlib.Path({str(post_hook)!r})
os.rename(path, str(path) + '.published-dispatcher')
path.write_text('foreign after exchange\\n')
path.chmod(0o755)
""",
        )
        result = self.install(
            post_exchange,
            env={"INSTALL_POST_CHECKOUT_TEST_AFTER_PUBLICATION": str(post_callback)},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(post_hook.read_text(), "foreign after exchange\n")
        self.assertTrue(Path(str(post_hook) + ".published-dispatcher").is_file())

        for kind in ("file", "directory", "symlink"):
            with self.subTest(replacement=kind):
                repository = self.new_repository(f"final race {kind}")
                self.add_sources(repository)
                hook = self.hook(repository)
                hook.write_text(STOCK_LFS_HOOK)
                hook.chmod(0o755)
                callback = self.root / f"replace-final-{kind}.py"
                identity_record = self.root / f"replace-final-{kind}.identity"
                body = {
                    "file": "path.write_text('foreign file\\n')",
                    "directory": "path.mkdir()",
                    "symlink": "path.symlink_to('foreign-target')",
                }[kind]
                self.write_executable(
                    callback,
                    f"""#!/usr/bin/env python3
import os
import pathlib
path = pathlib.Path({str(hook)!r})
os.rename(path, str(path) + '.classified')
{body}
status = os.lstat(path)
pathlib.Path({str(identity_record)!r}).write_text(f"{{status.st_dev}}:{{status.st_ino}}")
""",
                )
                result = self.install(
                    repository,
                    env={
                        "INSTALL_POST_CHECKOUT_TEST_BEFORE_PUBLICATION": str(callback)
                    },
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(Path(str(hook) + ".classified").exists())
                final_status = os.lstat(hook)
                self.assertEqual(
                    identity_record.read_text(),
                    f"{final_status.st_dev}:{final_status.st_ino}",
                )
                evidence = self.prepared(repository)
                self.assertGreaterEqual(len(evidence), 1)
                if kind == "file":
                    self.assertEqual(hook.read_text(), "foreign file\n")
                elif kind == "directory":
                    self.assertTrue(hook.is_dir())
                else:
                    self.assertTrue(hook.is_symlink())
                    self.assertEqual(os.readlink(hook), "foreign-target")
                self.assertTrue(
                    any(
                        path.is_file() and b"DISPATCHER_FORMAT = 1" in path.read_bytes()
                        for path in evidence
                    )
                )
                self.assertIn("restored unchanged", result.stderr)

    def test_setup_failure_is_checkout_usable_and_not_stamped(self) -> None:
        repository = self.new_repository("setup failure")
        self.add_sources(repository)
        setup = repository / ".superset/setup.sh"
        setup.write_text("#!/bin/bash\nset -euo pipefail\nexit 7\n")
        setup.chmod(0o755)
        self.git(repository, "add", ".superset/setup.sh")
        self.git(repository, "commit", "-qm", "review failing setup")
        self.install(repository)
        linked = self.add_linked_worktree(repository, "failing-setup")
        self.assertFalse((linked / ".setup-ran").exists())
        self.assertEqual(self.stamps(linked), [])

    def test_crash_safe_stamp_publication_and_recovery(self) -> None:
        killer = self.root / "kill-stamp-parent.py"
        self.write_executable(
            killer,
            """#!/usr/bin/env python3
import os
import signal
os.kill(os.getppid(), signal.SIGKILL)
""",
        )
        for stage in ("create", "write", "fsync", "publish"):
            with self.subTest(dispatcher_stage=stage):
                repository = self.new_repository(f"dispatcher stamp {stage}")
                self.add_sources(repository)
                self.install(repository)
                linked = self.add_linked_worktree(
                    repository, f"dispatcher-stamp-{stage}"
                )
                for stamp in self.stamps(linked):
                    stamp.unlink()
                (linked / ".setup-ran").unlink()
                crashed = self.invoke_hook(
                    self.hook(repository),
                    linked,
                    env={f"POST_CHECKOUT_TEST_STAMP_{stage.upper()}": str(killer)},
                )
                self.assertNotEqual(crashed.returncode, 0)
                if (linked / ".setup-ran").exists():
                    (linked / ".setup-ran").unlink()
                recovered = self.invoke_hook(self.hook(repository), linked)
                self.assertEqual(recovered.returncode, 0, recovered.stderr)
                published_stamps = self.stamps(linked)
                self.assertEqual(len(published_stamps), 1)
                status = published_stamps[0].stat()
                self.assertEqual(stat.S_IMODE(status.st_mode), 0o600)
                self.assertEqual(status.st_nlink, 1)
                if stage == "publish":
                    self.assertFalse((linked / ".setup-ran").exists())
                else:
                    self.assertTrue((linked / ".setup-ran").is_file())

            with self.subTest(backfill_stage=stage):
                repository = self.new_repository(f"backfill stamp {stage}")
                self.add_sources(repository)
                linked = self.add_linked_worktree(repository, f"backfill-stamp-{stage}")
                crashed = self.install(
                    repository,
                    env={
                        f"INSTALL_POST_CHECKOUT_TEST_STAMP_{stage.upper()}": str(killer)
                    },
                    check=False,
                )
                self.assertNotEqual(crashed.returncode, 0)
                self.install(repository)
                backfill_stamps = self.stamps(linked)
                self.assertEqual(len(backfill_stamps), 1)
                status = backfill_stamps[0].stat()
                self.assertEqual(stat.S_IMODE(status.st_mode), 0o600)
                self.assertEqual(status.st_nlink, 1)

        invalid_repo = self.new_repository("invalid stamp recovery")
        self.add_sources(invalid_repo)
        self.install(invalid_repo)
        linked = self.add_linked_worktree(invalid_repo, "invalid-stamp")
        stamp = self.stamps(linked)[0]
        stamp.unlink()
        stamp.write_bytes(b"incomplete")
        stamp.chmod(0o600)
        (linked / ".setup-ran").unlink()
        result = self.invoke_hook(self.hook(invalid_repo), linked)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stamps(linked)[0].stat().st_nlink, 1)
        recoveries = list(
            self.git_dir(linked).glob("dotfiles-worktree-setup-stamp-recovery.*")
        )
        self.assertEqual(len(recoveries), 1)
        self.assertEqual(recoveries[0].read_bytes(), b"incomplete")

        symlink_repo = self.new_repository("foreign stamp")
        self.add_sources(symlink_repo)
        self.install(symlink_repo)
        linked = self.add_linked_worktree(symlink_repo, "foreign-stamp")
        stamp = self.stamps(linked)[0]
        stamp.unlink()
        target = self.root / "foreign-stamp-target"
        target.write_text("foreign\n")
        stamp.symlink_to(target)
        (linked / ".setup-ran").unlink()
        result = self.invoke_hook(self.hook(symlink_repo), linked)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(stamp.is_symlink())
        self.assertEqual(target.read_text(), "foreign\n")
        self.assertFalse((linked / ".setup-ran").exists())
        stamp.unlink()
        anchor = self.root / "hardlinked-stamp-anchor"
        anchor.write_bytes(b"foreign hardlink")
        anchor.chmod(0o600)
        os.link(anchor, stamp)
        result = self.invoke_hook(self.hook(symlink_repo), linked)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(stamp.read_bytes(), b"foreign hardlink")
        self.assertEqual(stamp.stat().st_nlink, 2)
        self.assertFalse((linked / ".setup-ran").exists())

    def test_uncertain_stamp_temp_cleanup_preserves_replacement(self) -> None:
        def cleanup_racer(name: str, descriptor_variable: str) -> tuple[Path, Path]:
            callback = self.root / f"{name}-cleanup-racer.py"
            record = self.root / f"{name}-temporary-name"
            self.write_executable(
                callback,
                f"""#!/usr/bin/env python3
import os
import pathlib
import sys
directory_fd = int(os.environ[{descriptor_variable!r}])
temporary = sys.argv[2]
pathlib.Path({str(record)!r}).write_text(sys.argv[2])
os.rename(
    temporary,
    "owned-" + temporary,
    src_dir_fd=directory_fd,
    dst_dir_fd=directory_fd,
)
descriptor = os.open(
    temporary,
    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
    0o600,
    dir_fd=directory_fd,
)
os.write(descriptor, b"foreign replacement")
os.close(descriptor)
""",
            )
            return callback, record

        runtime_repository = self.new_repository("runtime cleanup race")
        self.add_sources(runtime_repository)
        self.install(runtime_repository)
        runtime_linked = self.add_linked_worktree(
            runtime_repository, "runtime-cleanup-race"
        )
        for published in self.stamps(runtime_linked):
            published.unlink()
        (runtime_linked / ".setup-ran").unlink()
        callback, record = cleanup_racer("runtime", "POST_CHECKOUT_TEST_PINNED_GIT_FD")
        result = self.invoke_hook(
            self.hook(runtime_repository),
            runtime_linked,
            env={"POST_CHECKOUT_TEST_STAMP_CLEANUP": str(callback)},
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("recovery evidence was left", result.stderr)
        temporary_name = record.read_text()
        runtime_git_dir = self.git_dir(runtime_linked)
        self.assertEqual(
            (runtime_git_dir / temporary_name).read_bytes(), b"foreign replacement"
        )
        self.assertTrue((runtime_git_dir / ("owned-" + temporary_name)).is_file())
        self.assertEqual(len(self.stamps(runtime_linked)), 1)

        backfill_repository = self.new_repository("backfill cleanup race")
        self.add_sources(backfill_repository)
        backfill_linked = self.add_linked_worktree(
            backfill_repository, "backfill-cleanup-race"
        )
        callback, record = cleanup_racer(
            "backfill", "INSTALL_POST_CHECKOUT_TEST_PINNED_GIT_FD"
        )
        result = self.install(
            backfill_repository,
            env={"INSTALL_POST_CHECKOUT_TEST_STAMP_CLEANUP": str(callback)},
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("recovery evidence was left", result.stderr)
        temporary_name = record.read_text()
        backfill_git_dir = self.git_dir(backfill_linked)
        self.assertEqual(
            (backfill_git_dir / temporary_name).read_bytes(),
            b"foreign replacement",
        )
        self.assertTrue((backfill_git_dir / ("owned-" + temporary_name)).is_file())
        self.assertEqual(len(self.stamps(backfill_linked)), 1)

    def test_sha256_null_oid_when_supported(self) -> None:
        probe = self.run_command(
            ["git", "init", "-q", "--object-format=sha256", self.root / "sha256-probe"],
            check=False,
        )
        if probe.returncode != 0:
            self.skipTest("installed Git does not support SHA-256 repositories")
        repository = self.root / "sha256-probe"
        self.git(repository, "config", "user.name", "Hook Test")
        self.git(repository, "config", "user.email", "hook-test@example.com")
        (repository / "seed.txt").write_text("seed\n")
        self.git(repository, "add", "seed.txt")
        self.git(repository, "commit", "-qm", "seed")
        self.add_sources(repository)
        self.install(repository)
        linked = self.add_linked_worktree(repository, "sha256")
        self.assertEqual((linked / ".setup-ran").read_text(), "setup-only snapshot\n")
        self.assertNotIn(
            "--path-format=absolute",
            (REPO_ROOT / "git/hooks/post-checkout").read_text()
            + (REPO_ROOT / "git/hooks/install-post-checkout").read_text(),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
