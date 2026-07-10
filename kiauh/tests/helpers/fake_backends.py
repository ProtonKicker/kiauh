# ======================================================================= #
#  Test-only backends. Not imported by production code.                   #
# ======================================================================= #
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


class FakeCommandRunner:
    """Command runner for tests. Records calls and returns scripted responses.

    By default, running a command that was not explicitly scripted raises an
    error so missing mocks are caught during development. Pass
    ``strict=False`` to restore the legacy "default success" behavior.
    """

    def __init__(
        self,
        responses: Dict[Tuple[str, ...], subprocess.CompletedProcess] | None = None,
        *,
        strict: bool = True,
    ) -> None:
        self.calls: List[Tuple[str | Sequence[str], Dict[str, Any]]] = []
        self.responses = responses or {}
        self.strict = strict

    @staticmethod
    def _key(cmd: str | Sequence[str]) -> Tuple[str, ...]:
        if isinstance(cmd, str):
            return (cmd,)
        return tuple(str(c) for c in cmd)

    def _make_response(
        self, cmd: str | Sequence[str], returncode: int = 0
    ) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=returncode,
            stdout="",
            stderr="",
        )

    def _unscripted(self, cmd: str | Sequence[str]) -> subprocess.CompletedProcess:
        if self.strict:
            raise RuntimeError(f"Unscripted command: {cmd}")
        return self._make_response(cmd)

    def run(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> subprocess.CompletedProcess:
        self.calls.append((cmd, kwargs))
        key = self._key(cmd)
        if key in self.responses:
            return self.responses[key]
        return self._unscripted(cmd)

    def check_output(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> str | bytes:
        self.calls.append((cmd, kwargs))
        key = self._key(cmd)
        if key in self.responses:
            return self.responses[key].stdout  # type: ignore[no-any-return]
        if self.strict:
            raise RuntimeError(f"Unscripted command: {cmd}")
        return ""

    def call(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> int:
        self.calls.append((cmd, kwargs))
        key = self._key(cmd)
        if key in self.responses:
            return self.responses[key].returncode
        if self.strict:
            raise RuntimeError(f"Unscripted command: {cmd}")
        return 0

    def popen(
        self,
        cmd: str | Sequence[str],
        **kwargs: Any,
    ) -> subprocess.Popen:
        raise NotImplementedError("FakeCommandRunner.popen is not implemented")


class FakeFilesystemBackend:
    """In-memory filesystem backend for tests."""

    def __init__(self) -> None:
        self.dirs: set[str] = set()
        self.files: Dict[str, str] = {}
        self.symlinks: Dict[str, str] = {}
        self._home: Path = Path("/home/test")

    def _path(self, path: Path) -> str:
        return str(Path(path).resolve())

    def exists(self, path: Path) -> bool:
        key = self._path(path)
        return key in self.dirs or key in self.files or key in self.symlinks

    def is_dir(self, path: Path) -> bool:
        return self._path(path) in self.dirs

    def is_file(self, path: Path) -> bool:
        return self._path(path) in self.files

    def is_symlink(self, path: Path) -> bool:
        return self._path(path) in self.symlinks

    def mkdir(
        self, path: Path, *, parents: bool = False, exist_ok: bool = False
    ) -> None:
        key = self._path(path)
        if key in self.files and not exist_ok:
            raise FileExistsError(key)
        if key in self.dirs and not exist_ok:
            raise FileExistsError(key)
        if parents:
            for parent in reversed(Path(key).parents):
                self.dirs.add(str(parent))
        self.dirs.add(key)

    def unlink(self, path: Path) -> None:
        key = self._path(path)
        if key in self.files:
            del self.files[key]
        elif key in self.symlinks:
            del self.symlinks[key]
        else:
            raise FileNotFoundError(key)

    def rmtree(self, path: Path) -> None:
        key = self._path(path)
        if key not in self.dirs:
            raise FileNotFoundError(key)
        prefix = key + "/"
        self.dirs = {d for d in self.dirs if not (d == key or d.startswith(prefix))}
        self.files = {k: v for k, v in self.files.items() if not k.startswith(prefix)}
        self.symlinks = {
            k: v for k, v in self.symlinks.items() if not k.startswith(prefix)
        }

    def read_text(self, path: Path) -> str:
        key = self._path(path)
        if key not in self.files:
            raise FileNotFoundError(key)
        return self.files[key]

    def write_text(self, path: Path, content: str) -> None:
        key = self._path(path)
        self.files[key] = content
        self.dirs.discard(key)

    def copy(self, source: Path, target: Path) -> None:
        content = self.read_text(source)
        self.write_text(target, content)

    def home(self) -> Path:
        return self._home

    def add_dir(self, path: Path) -> None:
        self.dirs.add(self._path(path))

    def add_file(self, path: Path, content: str = "") -> None:
        self.files[self._path(path)] = content

    def add_symlink(self, path: Path, target: Path) -> None:
        self.symlinks[self._path(path)] = str(target)
