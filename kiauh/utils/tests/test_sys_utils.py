# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <dev.dw-0@proton.me>         #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #

from __future__ import annotations

import builtins
from io import StringIO
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, List

import pytest
from utils.sys_utils import (
    VenvCreationFailedException,
    check_package_install,
    check_python_version,
    cmd_sysctl_manage,
    cmd_sysctl_service,
    create_env_file,
    create_python_venv,
    create_service_file,
    download_file,
    download_progress,
    get_current_user,
    get_distro_info,
    get_ipv4_addr,
    get_service_file_path,
    get_system_timezone,
    get_upgradable_packages,
    get_user_groups,
    install_python_packages,
    install_python_requirements,
    install_system_packages,
    kill,
    log_process,
    parse_packages_from_file,
    remove_system_service,
    set_nginx_permissions,
    unit_file_exists,
    update_python_pip,
    update_system_package_lists,
    upgrade_system_packages,
)


class TestKill:
    def test_exits_with_error(self, monkeypatch) -> None:
        exited: List[int] = []

        def fake_exit(code: int) -> None:
            exited.append(code)
            raise SystemExit(code)

        monkeypatch.setattr("utils.sys_utils.sys.exit", fake_exit)
        with pytest.raises(SystemExit):
            kill("boom")
        assert exited == [1]


class TestCheckPythonVersion:
    def test_old(self, monkeypatch) -> None:
        info = type("VI", (), {"major": 3, "minor": 7})()
        monkeypatch.setattr("utils.sys_utils.sys.version_info", info)
        assert check_python_version(3, 8) is False

    def test_current(self, monkeypatch) -> None:
        info = type("VI", (), {"major": 3, "minor": 9})()
        monkeypatch.setattr("utils.sys_utils.sys.version_info", info)
        assert check_python_version(3, 8) is True


class TestParsePackagesFromFile:
    def test_reads_pkglist(self, tmp_path: Path) -> None:
        script = tmp_path / "install.sh"
        script.write_text('PKGLIST="git curl wget"\nOTHER="x"\n')
        assert parse_packages_from_file(script) == ["git", "curl", "wget"]


class TestCreatePythonVenv:
    def test_creates_when_missing(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        target = Path("/tmp/venv")

        assert create_python_venv(target) is True
        assert runs == [
            ["virtualenv", "-p", "/usr/bin/python3", "/tmp/venv"],
        ]

    def test_declines_recreate(self, monkeypatch) -> None:
        target = Path("/tmp/venv")
        monkeypatch.setattr("utils.sys_utils.Path.exists", lambda self: self == target)
        monkeypatch.setattr("utils.sys_utils.get_confirm", lambda *a, **k: False)
        monkeypatch.setattr(
            "utils.sys_utils.run",
            lambda *a, **k: pytest.fail("should not recreate when declined"),
        )

        assert create_python_venv(target) is False

    def test_confirms_recreate(self, monkeypatch) -> None:
        target = Path("/tmp/venv")
        state = {"exists": True}
        removed: List[Path] = []
        runs: List[List[str]] = []

        def fake_exists(self: Path) -> bool:
            return state["exists"] and str(self) == str(target)

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        def fake_rmtree(p: Path) -> None:
            removed.append(p)
            state["exists"] = False

        monkeypatch.setattr("utils.sys_utils.Path.exists", fake_exists)
        monkeypatch.setattr("utils.sys_utils.get_confirm", lambda *a, **k: True)
        monkeypatch.setattr("utils.sys_utils.shutil.rmtree", fake_rmtree)
        monkeypatch.setattr("utils.sys_utils.run", fake_run)

        assert (
            create_python_venv(target, allow_access_to_system_site_packages=True)
            is True
        )
        assert removed == [target]
        assert runs == [
            [
                "virtualenv",
                "-p",
                "/usr/bin/python3",
                "/tmp/venv",
                "--system-site-packages",
            ],
        ]

    def test_force_recreate(self, monkeypatch) -> None:
        target = Path("/tmp/venv")
        state = {"exists": True}
        removed: List[Path] = []

        def fake_exists(self: Path) -> bool:
            return state["exists"] and str(self) == str(target)

        def fake_rmtree(p: Path) -> None:
            removed.append(p)
            state["exists"] = False

        monkeypatch.setattr("utils.sys_utils.Path.exists", fake_exists)
        monkeypatch.setattr(
            "utils.sys_utils.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt when forced"),
        )
        monkeypatch.setattr("utils.sys_utils.shutil.rmtree", fake_rmtree)
        monkeypatch.setattr("utils.sys_utils.run", lambda *a, **k: None)

        assert create_python_venv(target, force=True) is True
        assert removed == [target]

    def test_headless_skips_recreate_without_prompting(self, monkeypatch) -> None:
        target = Path("/tmp/venv")

        monkeypatch.setattr("utils.sys_utils.Path.exists", lambda self: self == target)
        monkeypatch.setattr(
            "utils.sys_utils.get_confirm",
            lambda *a, **k: pytest.fail("should not prompt in headless mode"),
        )
        monkeypatch.setattr(
            "utils.sys_utils.shutil.rmtree",
            lambda *a, **k: pytest.fail("should not rmtree in headless mode"),
        )
        monkeypatch.setattr(
            "utils.sys_utils.run",
            lambda *a, **k: pytest.fail("should not recreate in headless mode"),
        )

        assert create_python_venv(target, interactive=False) is False

    def test_creation_failure(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.sys_utils.run",
            lambda *a, **k: (_ for _ in ()).throw(CalledProcessError(1, "virtualenv")),
        )
        assert create_python_venv(Path("/tmp/venv")) is False

    def test_remove_failure(self, monkeypatch) -> None:
        target = Path("/tmp/venv")

        def fake_exists(self: Path) -> bool:
            return str(self) == str(target)

        monkeypatch.setattr("utils.sys_utils.Path.exists", fake_exists)
        monkeypatch.setattr("utils.sys_utils.get_confirm", lambda *a, **k: True)
        monkeypatch.setattr(
            "utils.sys_utils.shutil.rmtree",
            lambda *a, **k: (_ for _ in ()).throw(OSError("locked")),
        )

        assert create_python_venv(target) is False


class TestUpdatePythonPip:
    def test_raises_when_pip_missing(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.check_file_exist", lambda *a, **k: False)
        with pytest.raises(FileNotFoundError):
            update_python_pip(Path("/tmp/venv"))

    def test_runs_upgrade(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return type("R", (), {"returncode": 0, "stderr": ""})()

        monkeypatch.setattr("utils.sys_utils.check_file_exist", lambda *a, **k: True)
        monkeypatch.setattr("utils.sys_utils.run", fake_run)

        update_python_pip(Path("/tmp/venv"))
        assert runs == [["/tmp/venv/bin/pip", "install", "-U", "pip"]]

    def test_succeeds_when_returncode_and_stderr_are_clean(self, monkeypatch) -> None:
        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            return type("R", (), {"returncode": 0, "stderr": ""})()

        monkeypatch.setattr("utils.sys_utils.check_file_exist", lambda *a, **k: True)
        monkeypatch.setattr("utils.sys_utils.run", fake_run)

        update_python_pip(Path("/tmp/venv"))

    def test_failure_raises(self, monkeypatch) -> None:
        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            return type("R", (), {"returncode": 1, "stderr": "nope"})()

        monkeypatch.setattr("utils.sys_utils.check_file_exist", lambda *a, **k: True)
        monkeypatch.setattr("utils.sys_utils.run", fake_run)

        with pytest.raises(RuntimeError, match="Updating pip failed"):
            update_python_pip(Path("/tmp/venv"))


class TestInstallPythonRequirements:
    def test_success(self, monkeypatch) -> None:
        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            return type("R", (), {"returncode": 0, "stderr": ""})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        install_python_requirements(Path("/tmp/venv"), Path("/tmp/req.txt"))

    def test_failure(self, monkeypatch) -> None:
        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            return type("R", (), {"returncode": 1, "stderr": "nope"})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        with pytest.raises(VenvCreationFailedException):
            install_python_requirements(Path("/tmp/venv"), Path("/tmp/req.txt"))


class TestInstallPythonPackages:
    def test_success(self, monkeypatch) -> None:
        captured: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            captured.append(cmd)
            return type("R", (), {"returncode": 0, "stderr": ""})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        install_python_packages(Path("/tmp/venv"), ["a", "b"])
        assert captured == [["/tmp/venv/bin/pip", "install", "a", "b"]]


class TestUpdateSystemPackageLists:
    def test_skips_when_recent(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.time.time", lambda: 1000)
        monkeypatch.setattr("utils.sys_utils.os.path.getmtime", lambda p: 900)
        monkeypatch.setattr(
            "utils.sys_utils.run",
            lambda *a, **k: pytest.fail("should not update when recent"),
        )

        update_system_package_lists(silent=True)

    def test_runs_when_old(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.time.time", lambda: 100_000)
        monkeypatch.setattr("utils.sys_utils.os.path.getmtime", lambda p: 0)

        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return type("R", (), {"returncode": 0, "stderr": ""})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        update_system_package_lists(silent=True)

        assert runs == [["sudo", "apt-get", "update"]]

    def test_allows_releaseinfo_change(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.time.time", lambda: 100_000)
        monkeypatch.setattr("utils.sys_utils.os.path.getmtime", lambda p: 0)

        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return type("R", (), {"returncode": 0, "stderr": ""})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        update_system_package_lists(silent=True, rls_info_change=True)

        assert runs == [["sudo", "apt-get", "update", "--allow-releaseinfo-change"]]

    def test_failure_raises(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.time.time", lambda: 100_000)
        monkeypatch.setattr("utils.sys_utils.os.path.getmtime", lambda p: 0)

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            return type("R", (), {"returncode": 1, "stderr": "apt failed"})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)

        with pytest.raises(RuntimeError, match="Updating system package list failed"):
            update_system_package_lists(silent=True)


class TestGetUpgradablePackages:
    def test_parses_apt_list(self, monkeypatch) -> None:
        output = (
            "package1/stable 1.0 [upgradable from: 0.9]\n"
            "package2/testing 2.0 [upgradable from: 1.0]\n"
        )
        monkeypatch.setattr("utils.sys_utils.check_output", lambda *a, **k: output)
        assert get_upgradable_packages() == ["package1", "package2"]


class TestCheckPackageInstall:
    def test_detects_installed(self, monkeypatch) -> None:
        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            return type("R", (), {"stdout": "install ok installed"})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        assert check_package_install({"git"}) == []

    def test_detects_missing(self, monkeypatch) -> None:
        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            return type("R", (), {"stdout": "not-installed"})()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        assert check_package_install({"missing"}) == ["missing"]


class TestInstallSystemPackages:
    def test_runs_apt(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        install_system_packages(["git", "curl"])
        assert runs == [["sudo", "apt-get", "install", "-y", "git", "curl"]]


class TestUpgradeSystemPackages:
    def test_runs_apt(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        upgrade_system_packages(["git"])
        assert runs == [["sudo", "apt-get", "upgrade", "-y", "git"]]


class TestGetIpv4Addr:
    def test_returns_socket_address(self, monkeypatch) -> None:
        class FakeSocket:
            def __init__(self, *args):
                pass

            def settimeout(self, value: float) -> None:
                pass

            def connect(self, addr: tuple) -> None:
                pass

            def getsockname(self) -> tuple:
                return ("192.168.1.50", 54321)

            def close(self) -> None:
                pass

        monkeypatch.setattr("utils.sys_utils.socket.socket", FakeSocket)
        assert get_ipv4_addr() == "192.168.1.50"

    def test_falls_back_to_loopback(self, monkeypatch) -> None:
        class FakeSocket:
            def __init__(self, *args):
                pass

            def settimeout(self, value: float) -> None:
                pass

            def connect(self, addr: tuple) -> None:
                raise OSError("no route")

            def close(self) -> None:
                pass

        monkeypatch.setattr("utils.sys_utils.socket.socket", FakeSocket)
        assert get_ipv4_addr() == "127.0.0.1"


class TestDownloadFile:
    def test_without_progress(self, monkeypatch) -> None:
        calls: List[tuple] = []

        def fake_urlretrieve(url: str, target: Path, reporthook=None) -> None:
            calls.append((url, str(target), reporthook))

        monkeypatch.setattr(
            "utils.sys_utils.urllib.request.urlretrieve", fake_urlretrieve
        )
        download_file("http://x/file", Path("/target"), show_progress=False)
        assert calls == [("http://x/file", str(Path("/target")), None)]

    def test_with_progress(self, monkeypatch) -> None:
        calls: List[tuple] = []

        def fake_urlretrieve(url: str, target: Path, reporthook=None) -> None:
            calls.append((url, str(target), reporthook))
            if reporthook:
                reporthook(1, 1024, 2048)

        monkeypatch.setattr(
            "utils.sys_utils.urllib.request.urlretrieve", fake_urlretrieve
        )
        download_file("http://x/file", Path("/target"), show_progress=True)
        assert calls[0][2] is not None


class TestDownloadProgress:
    def test_writes_to_stdout(self, capsys) -> None:
        download_progress(1, 1024, 2048)
        captured = capsys.readouterr()
        assert "Downloading:" in captured.out
        assert "50.00%" in captured.out


class TestSetNginxPermissions:
    def test_no_change_when_executable(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.sys_utils.run",
            lambda cmd, **kwargs: (
                type("R", (), {"stdout": "drwxr-xr-x"})()
                if "ls" in cmd
                else pytest.fail("should not chmod")
            ),
        )
        set_nginx_permissions()

    def test_adds_execute(self, monkeypatch) -> None:
        commands: List[Any] = []

        def fake_run(cmd, **kwargs):
            commands.append(cmd)
            if isinstance(cmd, str):
                return type("R", (), {"stdout": "drwxr------"})()
            return None

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        monkeypatch.setattr("utils.sys_utils.Path.home", lambda: Path("/home/user"))
        set_nginx_permissions()
        assert ["chmod", "og+x", Path("/home/user")] in commands


class TestCmdSysctlService:
    def test_runs_systemctl(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        cmd_sysctl_service("klipper", "restart")
        assert runs == [["sudo", "systemctl", "restart", "klipper"]]


class TestCmdSysctlManage:
    def test_runs_systemctl(self, monkeypatch) -> None:
        runs: List[List[str]] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append(cmd)
            return None

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        cmd_sysctl_manage("daemon-reload")
        assert runs == [["sudo", "systemctl", "daemon-reload"]]


class TestUnitFileExists:
    def test_finds_matching_service(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.SYSTEMD", tmp_path)
        (tmp_path / "klipper.service").write_text("")
        (tmp_path / "klipper-1.service").write_text("")
        (tmp_path / "moonraker.service").write_text("")

        assert unit_file_exists("klipper", "service") is True
        assert unit_file_exists("moonraker", "service") is True
        assert unit_file_exists("klipper", "timer") is False

    def test_respects_exclude(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.SYSTEMD", tmp_path)
        (tmp_path / "klipper-mcu.service").write_text("")

        assert unit_file_exists("klipper", "service", exclude=["mcu"]) is False


class TestLogProcess:
    def test_prints_stdout(self, monkeypatch, capsys) -> None:
        lines = iter(["line1\n", "line2\n", ""])
        poll_results = iter([None, 0])

        class FakeStdout:
            def fileno(self) -> int:
                return 7

            def readline(self) -> str:
                return next(lines)

        class FakeProcess:
            stdout = FakeStdout()

            def poll(self):
                return next(poll_results)

        monkeypatch.setattr(
            "utils.sys_utils.select.select", lambda r, w, x: ([7], [], [])
        )
        log_process(FakeProcess())  # type: ignore[arg-type]

        captured = capsys.readouterr()
        assert "line1" in captured.out
        assert "line2" in captured.out


class TestCreateServiceFile:
    def test_writes_via_tee(self, monkeypatch) -> None:
        runs: List[tuple] = []

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            runs.append((cmd, kwargs.get("input")))
            return None

        monkeypatch.setattr("utils.sys_utils.SYSTEMD", Path("/etc/systemd/system"))
        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        create_service_file("klipper.service", "[Unit]\n")

        assert runs[0][0] == [
            "sudo",
            "tee",
            Path("/etc/systemd/system/klipper.service"),
        ]
        assert runs[0][1] == b"[Unit]\n"


class TestCreateEnvFile:
    def test_writes_file(self, tmp_path: Path) -> None:
        path = tmp_path / "env"
        create_env_file(path, "KEY=value\n")
        assert path.read_text() == "KEY=value\n"


class TestRemoveSystemService:
    def test_rejects_bad_name(self) -> None:
        with pytest.raises(ValueError):
            remove_system_service("klipper")

    def test_skips_missing_file(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.SYSTEMD", tmp_path)
        remove_system_service("klipper.service")

    def test_full_removal(self, monkeypatch) -> None:
        sysd = Path("/fake/systemd")
        service_file = sysd / "klipper.service"
        monkeypatch.setattr("utils.sys_utils.SYSTEMD", sysd)

        monkeypatch.setattr(
            "utils.sys_utils.Path.exists",
            lambda self: str(self) == str(service_file),
        )
        monkeypatch.setattr(
            "utils.sys_utils.Path.is_file",
            lambda self: str(self) == str(service_file),
        )

        service_calls: List[tuple] = []
        manage_calls: List[str] = []
        removed: List[Path] = []

        monkeypatch.setattr(
            "utils.sys_utils.cmd_sysctl_service",
            lambda name, action: service_calls.append((name, action)),
        )
        monkeypatch.setattr(
            "utils.sys_utils.cmd_sysctl_manage",
            lambda action: manage_calls.append(action),
        )
        monkeypatch.setattr(
            "utils.sys_utils.remove_with_sudo", lambda p: removed.append(p)
        )

        remove_system_service("klipper.service")

        assert service_calls == [
            ("klipper.service", "stop"),
            ("klipper.service", "disable"),
        ]
        assert removed == [service_file]
        assert manage_calls == ["daemon-reload", "reset-failed"]


class _FakeInstanceType:
    pass


_FakeInstanceType.__name__ = "Klipper"


class TestGetServiceFilePath:
    def test_builds_path(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.SYSTEMD", Path("/etc/systemd/system"))
        assert get_service_file_path(_FakeInstanceType, "") == Path(
            "/etc/systemd/system/klipper.service"
        )
        assert get_service_file_path(_FakeInstanceType, "1") == Path(
            "/etc/systemd/system/klipper-1.service"
        )


class TestGetDistroInfo:
    def test_parses_os_release(self, monkeypatch) -> None:
        content = """
ID="ubuntu"
ID_LIKE="debian"
VERSION_ID="22.04"
"""
        monkeypatch.setattr(
            "utils.sys_utils.check_output", lambda *a, **k: content.encode()
        )
        assert get_distro_info() == ("ubuntu", "22.04")

    def test_remaps_raspbian(self, monkeypatch) -> None:
        content = """
ID="raspbian"
ID_LIKE="debian"
VERSION_ID="11"
"""
        monkeypatch.setattr(
            "utils.sys_utils.check_output", lambda *a, **k: content.encode()
        )
        assert get_distro_info() == ("debian", "11")

    def test_raises_on_missing_id(self, monkeypatch) -> None:
        monkeypatch.setattr(
            "utils.sys_utils.check_output", lambda *a, **k: b'VERSION_ID="1"\n'
        )
        with pytest.raises(ValueError):
            get_distro_info()


class TestGetSystemTimezone:
    def test_from_etc_timezone(self, monkeypatch) -> None:
        def fake_open(path: str, mode: str = "r", *args, **kwargs):
            if path == "/etc/timezone":
                return StringIO("Europe/Berlin\n")
            return builtins.open(path, mode, *args, **kwargs)

        monkeypatch.setattr("builtins.open", fake_open)
        assert get_system_timezone() == "Europe/Berlin"

    def test_fallback_to_timedatectl(self, monkeypatch) -> None:
        def fake_open(path: str, mode: str = "r", *args, **kwargs):
            raise FileNotFoundError(path)

        monkeypatch.setattr("builtins.open", fake_open)

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            class Result:
                stdout = "Timezone=America/New_York\n"

            return Result()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        assert get_system_timezone() == "America/New_York"

    def test_fallback_to_readlink(self, monkeypatch) -> None:
        def fake_open(path: str, mode: str = "r", *args, **kwargs):
            raise FileNotFoundError(path)

        monkeypatch.setattr("builtins.open", fake_open)

        def fake_run(cmd: List[str], **kwargs: Any) -> Any:
            if cmd[:2] == ["timedatectl", "show"]:
                raise CalledProcessError(1, "timedatectl")

            class Result:
                stdout = "/usr/share/zoneinfo/Asia/Tokyo\n"

            return Result()

        monkeypatch.setattr("utils.sys_utils.run", fake_run)
        assert get_system_timezone() == "Asia/Tokyo"

    def test_defaults_to_utc(self, monkeypatch) -> None:
        def fake_open(path: str, mode: str = "r", *args, **kwargs):
            raise FileNotFoundError(path)

        monkeypatch.setattr("builtins.open", fake_open)
        monkeypatch.setattr(
            "utils.sys_utils.run",
            lambda *a, **k: (_ for _ in ()).throw(CalledProcessError(1, "timedatectl")),
        )
        assert get_system_timezone() == "UTC"


class TestGetCurrentUser:
    def test_posix_uses_pwd(self, monkeypatch) -> None:
        import sys
        import types

        fake_pwd = types.SimpleNamespace(getpwuid=lambda uid: ["alice", "x", uid])
        monkeypatch.setitem(sys.modules, "pwd", fake_pwd)
        monkeypatch.setattr("utils.sys_utils.os.name", "posix")
        monkeypatch.setattr("utils.sys_utils.os.getuid", lambda: 1000, raising=False)

        assert get_current_user() == "alice"

    def test_non_posix_uses_getpass(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.os.name", "nt")
        monkeypatch.setattr("getpass.getuser", lambda: "bob")

        assert get_current_user() == "bob"


class TestGetUserGroups:
    def test_posix_maps_gids_to_names(self, monkeypatch) -> None:
        import sys
        import types

        fake_grp = types.SimpleNamespace(
            getgrgid=lambda gid: types.SimpleNamespace(gr_name=f"g{gid}")
        )
        monkeypatch.setitem(sys.modules, "grp", fake_grp)
        monkeypatch.setattr("utils.sys_utils.os.name", "posix")
        monkeypatch.setattr(
            "utils.sys_utils.os.getgroups", lambda: [10, 20], raising=False
        )

        assert get_user_groups() == ["g10", "g20"]

    def test_non_posix_returns_empty(self, monkeypatch) -> None:
        monkeypatch.setattr("utils.sys_utils.os.name", "nt")

        assert get_user_groups() == []
