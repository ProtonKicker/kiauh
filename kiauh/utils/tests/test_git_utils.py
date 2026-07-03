from __future__ import annotations

from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, List

import pytest
from utils.git_utils import (
    GitException,
    compare_semver_tags,
    get_current_branch,
    get_latest_remote_tag,
    get_latest_unstable_tag,
    get_local_commit,
    get_local_tags,
    get_remote_commit,
    get_remote_tags,
    get_repo_name,
    get_repo_url,
    git_clone_wrapper,
    git_cmd_checkout,
    git_cmd_clone,
    git_cmd_pull,
    git_pull_wrapper,
    rollback_repository,
)
from utils.instance_type import InstanceType


class TestGitCmdPull:
    def test_missing_dir_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        with pytest.raises(GitException):
            git_cmd_pull(missing)

    def test_dir_without_git_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "no-git"
        empty.mkdir()
        with pytest.raises(GitException):
            git_cmd_pull(empty)

    def test_success_runs_git_pull(self, monkeypatch) -> None:
        repo = Path("/fake/repo")
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.git_utils.Path.exists", lambda self: True)
        monkeypatch.setattr(
            "utils.git_utils.Path.joinpath", lambda self, name: repo / name
        )
        monkeypatch.setattr("utils.git_utils.run", fake_run)

        git_cmd_pull(repo)
        assert runs == [["git", "pull"]]


class TestGitCmdCheckout:
    def test_missing_dir_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        with pytest.raises(GitException):
            git_cmd_checkout("main", missing)

    def test_dir_without_git_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "no-git"
        empty.mkdir()
        with pytest.raises(GitException):
            git_cmd_checkout("main", empty)

    def test_none_branch_returns(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.git_utils.run",
            lambda *a, **k: pytest.fail("should not run checkout for None branch"),
        )
        git_cmd_checkout(None, Path("/repo"))


class TestGitPullWrapper:
    def test_missing_dir_does_not_raise(self, tmp_path: Path) -> None:
        missing = tmp_path / "does-not-exist"
        git_pull_wrapper(missing)

    def test_dir_without_git_does_not_raise(self, tmp_path: Path) -> None:
        empty = tmp_path / "no-git"
        empty.mkdir()
        git_pull_wrapper(empty)

    def test_success_calls_git_pull(self, monkeypatch) -> None:
        repo = Path("/fake/repo")
        called: List[Path] = []

        def fake_git_cmd_pull(path: Path) -> None:
            called.append(path)

        monkeypatch.setattr("utils.git_utils.git_cmd_pull", fake_git_cmd_pull)
        git_pull_wrapper(repo)
        assert called == [repo]


class TestRollbackRepository:
    def test_missing_dir_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        missing = tmp_path / "does-not-exist"
        called: list[bool] = []
        monkeypatch.setattr(
            "utils.git_utils.get_number_input",
            lambda *_a, **_k: called.append(True) or 1,
        )
        with pytest.raises(GitException):
            rollback_repository(missing, InstanceType)
        assert not called

    def test_dir_without_git_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        empty = tmp_path / "no-git"
        empty.mkdir()
        called: list[bool] = []
        monkeypatch.setattr(
            "utils.git_utils.get_number_input",
            lambda *_a, **_k: called.append(True) or 1,
        )
        with pytest.raises(GitException):
            rollback_repository(empty, InstanceType)
        assert not called

    def test_aborts_when_not_confirmed(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        monkeypatch.setattr("utils.git_utils.get_number_input", lambda *a, **k: 2)
        monkeypatch.setattr("utils.git_utils.get_confirm", lambda *a, **k: False)
        monkeypatch.setattr(
            "utils.git_utils.get_instances", lambda *a, **k: ["instance"]
        )
        monkeypatch.setattr(
            "utils.git_utils.InstanceManager.stop_all",
            lambda *a, **k: pytest.fail("should not stop when aborted"),
        )
        monkeypatch.setattr(
            "utils.git_utils.run",
            lambda *a, **k: pytest.fail("should not reset when aborted"),
        )
        monkeypatch.setattr(
            "utils.git_utils.InstanceManager.start_all",
            lambda *a, **k: pytest.fail("should not start when aborted"),
        )

        rollback_repository(repo, InstanceType)

    def test_resets_and_restarts_when_confirmed(self, tmp_path: Path, monkeypatch) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        stops: List[List[Any]] = []
        starts: List[List[Any]] = []
        resets: List[List[str]] = []

        monkeypatch.setattr("utils.git_utils.get_number_input", lambda *a, **k: 3)
        monkeypatch.setattr("utils.git_utils.get_confirm", lambda *a, **k: True)
        monkeypatch.setattr(
            "utils.git_utils.get_instances", lambda *a, **k: ["instance"]
        )
        monkeypatch.setattr(
            "utils.git_utils.InstanceManager.stop_all",
            lambda instances: stops.append(instances),
        )
        monkeypatch.setattr(
            "utils.git_utils.InstanceManager.start_all",
            lambda instances: starts.append(instances),
        )

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            resets.append(cmd)
            return None

        monkeypatch.setattr("utils.git_utils.run", fake_run)

        rollback_repository(repo, InstanceType)

        assert stops == [["instance"]]
        assert resets == [["git", "reset", "--hard", "HEAD~3"]]
        assert starts == [["instance"]]


class TestGetRepoName:
    def test_extracts_org_and_repo(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        monkeypatch.setattr(
            "utils.git_utils.check_output",
            lambda *a, **k: b"https://github.com/dw-0/kiauh.git\n",
        )
        assert get_repo_name(repo) == ("dw-0", "kiauh")

    def test_returns_none_for_missing_repo(self, tmp_path: Path) -> None:
        assert get_repo_name(tmp_path / "missing") == (None, None)

    def test_returns_none_on_git_error(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        monkeypatch.setattr(
            "utils.git_utils.check_output",
            lambda *a, **k: (_ for _ in ()).throw(CalledProcessError(1, "git")),
        )
        assert get_repo_name(repo) == (None, None)


class TestGetCurrentBranch:
    def test_returns_branch(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        monkeypatch.setattr(
            "utils.git_utils.check_output", lambda *a, **k: b"feature-x\n"
        )
        assert get_current_branch(repo) == "feature-x"

    def test_returns_none_for_missing_repo(self, tmp_path: Path) -> None:
        assert get_current_branch(tmp_path / "missing") is None


class TestGetLocalTags:
    def test_sorts_semver(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        monkeypatch.setattr(
            "utils.git_utils.check_output",
            lambda *a, **k: b"v1.0.0\nv1.0.1\nv1.0.10\nv1.0.2\nv2.0.0-beta.1\n",
        )
        assert get_local_tags(repo) == [
            "v1.0.0",
            "v1.0.1",
            "v1.0.2",
            "v1.0.10",
            "v2.0.0-beta.1",
        ]

    def test_returns_empty_for_missing_repo(self, tmp_path: Path) -> None:
        assert get_local_tags(tmp_path / "missing") == []


class _FakeResponse:
    def __init__(self, code: int, body: bytes = b""):
        self._code = code
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def getcode(self) -> int:
        return self._code

    def read(self) -> bytes:
        return self._body


class TestGetRemoteTags:
    def test_parses_github_api(self, monkeypatch) -> None:
        body = b'[{"name":"v1.0.0"},{"name":"v1.1.0"}]'

        class FakeUrlLib:
            @staticmethod
            def urlopen(url: str):
                return _FakeResponse(200, body)

        monkeypatch.setattr("utils.git_utils.urllib.request", FakeUrlLib())
        assert get_remote_tags("dw-0/kiauh") == ["v1.0.0", "v1.1.0"]

    def test_returns_empty_on_http_error(self, monkeypatch) -> None:
        class FakeUrlLib:
            @staticmethod
            def urlopen(url: str):
                return _FakeResponse(404)

        monkeypatch.setattr("utils.git_utils.urllib.request", FakeUrlLib())
        assert get_remote_tags("dw-0/kiauh") == []


class TestGetLatestRemoteTag:
    def test_returns_first_tag(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.git_utils.get_remote_tags", lambda *_a, **_k: ["v2.0.0", "v1.0.0"]
        )
        assert get_latest_remote_tag("dw-0/kiauh") == "v2.0.0"

    def test_returns_empty_when_no_tags(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.git_utils.get_remote_tags", lambda *_a, **_k: [])
        assert get_latest_remote_tag("dw-0/kiauh") == ""


class TestGetLatestUnstableTag:
    def test_filters_prereleases(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.git_utils.get_remote_tags",
            lambda *_a, **_k: ["v2.0.0", "v2.0.0-rc.1", "v1.0.0-beta.2"],
        )
        assert get_latest_unstable_tag("dw-0/kiauh") == "v2.0.0-rc.1"

    def test_returns_empty_when_stable_only(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.git_utils.get_remote_tags", lambda *_a, **_k: ["v2.0.0", "v1.0.0"]
        )
        assert get_latest_unstable_tag("dw-0/kiauh") == ""


class TestCompareSemverTags:
    @pytest.mark.parametrize(
        "tag1,tag2,expected",
        [
            ("v1.0.0", "v1.0.1", False),
            ("v1.1.0", "v1.0.1", True),
            ("v1.0.0", "v1.0.0", False),
            ("v2.0.0", "v1.9.9", True),
        ],
    )
    def test_comparison(self, tag1: str, tag2: str, expected: bool) -> None:
        assert compare_semver_tags(tag1, tag2) is expected


class TestGetLocalCommit:
    def test_describes_head(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        monkeypatch.setattr(
            "utils.git_utils.check_output",
            lambda *a, **k: "v1.0.0-0-gabc1234",
        )
        assert get_local_commit(repo) == "v1.0.0-0-gabc1234"

    def test_returns_none_for_missing_repo(self, tmp_path: Path) -> None:
        assert get_local_commit(tmp_path / "missing") is None


class TestGetRemoteCommit:
    def test_describes_origin(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        def fake_check_output(cmd: str, **kwargs: Any) -> str:
            if "HEAD" in cmd:
                return "v1.0.0"
            return "origin/main"

        monkeypatch.setattr(
            "utils.git_utils.get_current_branch", lambda *_a, **_k: "main"
        )
        monkeypatch.setattr("utils.git_utils.check_output", fake_check_output)
        assert get_remote_commit(repo) == "origin/main"

    def test_returns_none_for_missing_repo(self, tmp_path: Path) -> None:
        assert get_remote_commit(tmp_path / "missing") is None


class TestGitCmdClone:
    def test_without_blobless(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.git_utils.run", fake_run)
        git_cmd_clone("https://github.com/dw-0/kiauh", Path("/target"))
        assert runs == [["git", "clone", "https://github.com/dw-0/kiauh", "/target"]]

    def test_with_blobless(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.git_utils.run", fake_run)
        git_cmd_clone(
            "https://github.com/dw-0/kiauh", Path("/target"), blobless=True
        )
        assert runs == [
            [
                "git",
                "clone",
                "--filter=blob:none",
                "https://github.com/dw-0/kiauh",
                "/target",
            ]
        ]


class TestGitCmdCheckoutSingle:
    def test_runs_git_checkout(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.git_utils.run", fake_run)
        git_cmd_checkout("dev", repo)
        assert runs == [["git", "checkout", "dev"]]


class TestGetRepoUrl:
    def test_extracts_remote_url(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        class FakeResult:
            stdout = "https://github.com/dw-0/kiauh.git\n"

        monkeypatch.setattr("utils.git_utils.run", lambda *a, **k: FakeResult())
        assert get_repo_url(repo) == "https://github.com/dw-0/kiauh.git"

    def test_returns_none_for_missing_repo(self, tmp_path: Path) -> None:
        assert get_repo_url(tmp_path / "missing") is None

    def test_returns_none_on_git_error(self, monkeypatch, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()

        monkeypatch.setattr(
            "utils.git_utils.run",
            lambda *a, **k: (_ for _ in ()).throw(CalledProcessError(1, "git")),
        )
        assert get_repo_url(repo) is None


class _CloneRecorder:
    def __init__(self):
        self.calls: List[tuple] = []
        self.checkouts: List[tuple] = []
        self.removed: List[Path] = []

    def fake_clone(self, repo: str, target: Path, blobless: bool = False) -> None:
        self.calls.append((repo, target, blobless))

    def fake_checkout(self, branch: str | None, target: Path) -> None:
        self.checkouts.append((branch, target))


class TestGitCloneWrapper:
    def test_clones_when_target_missing(self, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "kiauh"
        recorder = _CloneRecorder()
        monkeypatch.setattr("utils.git_utils.git_cmd_clone", recorder.fake_clone)
        monkeypatch.setattr("utils.git_utils.git_cmd_checkout", recorder.fake_checkout)

        git_clone_wrapper("https://github.com/dw-0/kiauh", target, branch="dev")

        assert recorder.calls == [("https://github.com/dw-0/kiauh", target, True)]
        assert recorder.checkouts == [("dev", target)]

    def test_skips_checkout_for_main(self, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "kiauh"
        recorder = _CloneRecorder()
        monkeypatch.setattr("utils.git_utils.git_cmd_clone", recorder.fake_clone)
        monkeypatch.setattr("utils.git_utils.git_cmd_checkout", recorder.fake_checkout)

        git_clone_wrapper("https://github.com/dw-0/kiauh", target, branch="main")

        assert recorder.checkouts == []

    def test_prompts_before_overwrite(self, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "kiauh"
        target.mkdir()
        recorder = _CloneRecorder()
        removed: List[Path] = []

        monkeypatch.setattr("utils.git_utils.git_cmd_clone", recorder.fake_clone)
        monkeypatch.setattr("utils.git_utils.git_cmd_checkout", recorder.fake_checkout)
        monkeypatch.setattr("utils.git_utils.shutil.rmtree", lambda p: removed.append(p))
        monkeypatch.setattr("utils.git_utils.get_confirm", lambda *a, **k: True)

        git_clone_wrapper("https://github.com/dw-0/kiauh", target, branch="dev")

        assert removed == [target]
        assert recorder.calls == [("https://github.com/dw-0/kiauh", target, True)]

    def test_respects_decline_to_overwrite(self, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "kiauh"
        target.mkdir()
        recorder = _CloneRecorder()

        monkeypatch.setattr("utils.git_utils.git_cmd_clone", recorder.fake_clone)
        monkeypatch.setattr("utils.git_utils.git_cmd_checkout", recorder.fake_checkout)
        monkeypatch.setattr(
            "utils.git_utils.shutil.rmtree",
            lambda *a, **k: pytest.fail("should not remove"),
        )
        monkeypatch.setattr("utils.git_utils.get_confirm", lambda *a, **k: False)

        git_clone_wrapper("https://github.com/dw-0/kiauh", target)

        assert recorder.calls == []

    def test_force_overwrites_without_prompt(self, monkeypatch, tmp_path: Path) -> None:
        target = tmp_path / "kiauh"
        target.mkdir()
        recorder = _CloneRecorder()
        removed: List[Path] = []

        monkeypatch.setattr("utils.git_utils.git_cmd_clone", recorder.fake_clone)
        monkeypatch.setattr("utils.git_utils.git_cmd_checkout", recorder.fake_checkout)
        monkeypatch.setattr("utils.git_utils.shutil.rmtree", lambda p: removed.append(p))
        monkeypatch.setattr(
            "utils.git_utils.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt when forced"),
        )

        git_clone_wrapper("https://github.com/dw-0/kiauh", target, force=True)

        assert removed == [target]
        assert recorder.calls == [("https://github.com/dw-0/kiauh", target, True)]
