# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#                                                                         #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, List, Protocol, Sequence, cast, runtime_checkable

# --------------------------------------------------------------------------- #
# Singleton backends                                                          #
# --------------------------------------------------------------------------- #
# There is exactly ONE ``command_runner`` and ONE ``filesystem`` global in the
# whole project, owned by this module. They are assigned (with explicit type
# annotations) at the bottom of this file, AFTER the default implementations
# are defined. ``utils.fs_utils`` and ``utils.sys_utils`` delegate to these
# singletons via the wrapper functions below, so tests patch a single place —
# ``core.backends.command_runner`` / ``core.backends.filesystem`` — instead of
# per-module duplicates


def run(cmd: str | List[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a command through the shared command runner."""
    return command_runner.run(cmd, **kwargs)


def check_output(cmd: str | List[str], **kwargs: Any) -> str | bytes:
    """Run a command and return its output through the shared command runner."""
    return command_runner.check_output(cmd, **kwargs)


def call(cmd: str | List[str], **kwargs: Any) -> int:
    """Run a command and return its exit code through the shared command runner."""
    return command_runner.call(cmd, **kwargs)


def popen(cmd: str | List[str], **kwargs: Any) -> subprocess.Popen:
    """Start a process through the shared command runner."""
    return command_runner.popen(cmd, **kwargs)


@runtime_checkable
class CommandRunner(Protocol):
    """Pluggable backend for executing system commands."""

    def run(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess: ...

    def check_output(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> str | bytes: ...

    def call(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> int: ...

    def popen(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> subprocess.Popen: ...


class SubprocessRunner:
    """Default command runner backed by the standard subprocess module."""

    def run(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(cmd, **kwargs)

    def check_output(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> str | bytes:
        return cast("str | bytes", subprocess.check_output(cmd, **kwargs))

    def call(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> int:
        return subprocess.call(cmd, **kwargs)

    def popen(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> subprocess.Popen:
        return subprocess.Popen(cmd, **kwargs)


@runtime_checkable
class FilesystemBackend(Protocol):
    """Pluggable backend for filesystem operations."""

    def exists(self, path: Path) -> bool: ...

    def is_dir(self, path: Path) -> bool: ...

    def is_file(self, path: Path) -> bool: ...

    def is_symlink(self, path: Path) -> bool: ...

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> None: ...

    def unlink(self, path: Path) -> None: ...

    def rmtree(self, path: Path) -> None: ...

    def read_text(self, path: Path) -> str: ...

    def write_text(self, path: Path, content: str) -> None: ...

    def copy(self, source: Path, target: Path) -> None: ...

    def home(self) -> Path: ...


class LocalFilesystemBackend:
    """Default filesystem backend backed by the local filesystem."""

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def is_symlink(self, path: Path) -> bool:
        return path.is_symlink()

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> None:
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def unlink(self, path: Path) -> None:
        path.unlink()

    def rmtree(self, path: Path) -> None:
        shutil.rmtree(path)

    def read_text(self, path: Path) -> str:
        return path.read_text()

    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content)

    def copy(self, source: Path, target: Path) -> None:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    def home(self) -> Path:
        return Path.home()


command_runner: CommandRunner = SubprocessRunner()
filesystem: FilesystemBackend = LocalFilesystemBackend()
