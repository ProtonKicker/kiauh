# ======================================================================= #
#  Copyright (C) 2020 - 2026 Dominik Willner <th33xitus@gmail.com>        #
#                                                                         #
#  This file is part of KIAUH - Klipper Installation And Update Helper    #
#  https://github.com/dw-0/kiauh                                          #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import argparse
import sys
from typing import Callable, Dict, List, Tuple

from components.klipper.services.klipper_setup_service import KlipperSetupService
from components.moonraker.services.moonraker_setup_service import MoonrakerSetupService
from components.webui_client.services.web_client_config_setup_service import (
    WebClientConfigSetupService,
)
from components.webui_client.services.web_client_setup_service import (
    WebClientSetupService,
)

# A dispatcher receives the parsed argparse namespace and the parser (so it can
# raise ``parser.error`` for invalid input) and returns the CLI exit code.
Dispatcher = Callable[[argparse.Namespace, argparse.ArgumentParser], int]


def _add_klipper_install(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("klipper", help="Install Klipper")
    p.add_argument(
        "--count", type=int, default=None, help="Number of instances to install"
    )
    p.add_argument(
        "--name", action="append", default=[], help="Custom instance name(s)"
    )
    p.add_argument(
        "--create-example-cfg", action="store_true", help="Create example printer.cfg"
    )
    p.add_argument(
        "--match-moonraker",
        action="store_true",
        help="Match Klipper instance count to existing Moonraker instances",
    )


def _add_moonraker_install(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("moonraker", help="Install Moonraker")
    p.add_argument(
        "--klipper-suffix",
        action="append",
        default=[],
        help="Klipper suffix to set up Moonraker for (can be repeated)",
    )
    p.add_argument(
        "--create-example-cfg",
        action="store_true",
        help="Create example moonraker.conf",
    )


def _add_web_client_install(sub: argparse._SubParsersAction) -> None:
    for name in ("mainsail", "fluidd"):
        p = sub.add_parser(name, help=f"Install {name.capitalize()}")
        p.add_argument("--port", type=int, default=None, help="Listen port")
        p.add_argument(
            "--install-config",
            action="store_true",
            help="Install the recommended client config",
        )
        p.add_argument(
            "--continue-without-moonraker",
            action="store_true",
            help="Allow installation even if Moonraker is not installed",
        )

    sub.add_parser("mainsail-config", help="Install the Mainsail client config")
    sub.add_parser("fluidd-config", help="Install the Fluidd client config")


def _add_klipper_remove(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("klipper", help="Remove Klipper")
    p.add_argument("--service", action="store_true", help="Remove Klipper services")
    p.add_argument("--dir", action="store_true", help="Remove Klipper local repository")
    p.add_argument(
        "--env", action="store_true", help="Remove Klipper Python environment"
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Remove every installed Klipper instance (destructive)",
    )
    p.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Klipper instance suffix to remove (repeatable)",
    )


def _add_moonraker_remove(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("moonraker", help="Remove Moonraker")
    p.add_argument("--service", action="store_true", help="Remove Moonraker services")
    p.add_argument(
        "--dir", action="store_true", help="Remove Moonraker local repository"
    )
    p.add_argument(
        "--env", action="store_true", help="Remove Moonraker Python environment"
    )
    p.add_argument(
        "--polkit", action="store_true", help="Remove Moonraker policykit rules"
    )
    p.add_argument(
        "--all",
        action="store_true",
        help="Remove every installed Moonraker instance (destructive)",
    )
    p.add_argument(
        "--instance",
        action="append",
        default=[],
        help="Moonraker instance suffix to remove (repeatable)",
    )


def _add_web_client_remove(sub: argparse._SubParsersAction) -> None:
    for name in ("mainsail", "fluidd"):
        p = sub.add_parser(name, help=f"Remove {name.capitalize()}")
        p.add_argument("--client", action="store_true", help="Remove the web client")
        p.add_argument("--config", action="store_true", help="Remove the client config")
        p.add_argument("--no-backup", action="store_true", help="Skip config backup")


def _add_klipper_update(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("klipper", help="Update Klipper")
    p.add_argument("--backup", action="store_true", help="Backup before updating")


def _add_moonraker_update(sub: argparse._SubParsersAction) -> None:
    sub.add_parser("moonraker", help="Update Moonraker")


def _add_web_client_update(sub: argparse._SubParsersAction) -> None:
    for name in ("mainsail", "fluidd"):
        sub.add_parser(name, help=f"Update {name.capitalize()}")
    sub.add_parser("mainsail-config", help="Update the Mainsail client config")
    sub.add_parser("fluidd-config", help="Update the Fluidd client config")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kiauh")
    subparsers = parser.add_subparsers(dest="command")

    install = subparsers.add_parser("install", help="Install a component")
    install_sub = install.add_subparsers(dest="component", required=True)
    _add_klipper_install(install_sub)
    _add_moonraker_install(install_sub)
    _add_web_client_install(install_sub)

    remove = subparsers.add_parser("remove", help="Remove a component")
    remove_sub = remove.add_subparsers(dest="component", required=True)
    _add_klipper_remove(remove_sub)
    _add_moonraker_remove(remove_sub)
    _add_web_client_remove(remove_sub)

    update = subparsers.add_parser("update", help="Update a component")
    update_sub = update.add_subparsers(dest="component", required=True)
    _add_klipper_update(update_sub)
    _add_moonraker_update(update_sub)
    _add_web_client_update(update_sub)

    return parser


# --------------------------------------------------------------------------- #
# Command handlers: one callable per (command, component) pair.               #
# Adding a new component is a matter of registering a handler here instead of #
# extending the previous long if/elif chain.                                  #
# --------------------------------------------------------------------------- #
def _install_klipper(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.count is not None and args.name and args.count != len(args.name):
        parser.error("--count must match the number of --name values")

    service = KlipperSetupService()
    custom_names = {i: name for i, name in enumerate(args.name)} if args.name else None
    result = service.install(
        count=args.count,
        custom_names=custom_names,
        create_example_cfg=args.create_example_cfg,
        match_moonraker=args.match_moonraker,
        interactive=False,
    )
    return 0 if result else 1


def _remove_klipper(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not (args.service or args.dir or args.env):
        parser.error(
            "specify at least one of --service, --dir, --env for 'remove klipper'"
        )
    if args.service and not (args.all or args.instance):
        # refuse to silently wipe every Klipper instance.
        parser.error(
            "removing Klipper services is destructive; pass --all or "
            "--instance <suffix> (repeatable) to select what to remove"
        )
    service = KlipperSetupService()
    result = service.remove(
        remove_service=args.service,
        remove_dir=args.dir,
        remove_env=args.env,
        remove_all=args.all,
        instance_suffixes=args.instance or None,
        interactive=False,
    )
    return 0 if result else 1


def _update_klipper(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    service = KlipperSetupService()
    if args.backup:
        service.settings.kiauh.backup_before_update = True
    result = service.update(interactive=False)
    return 0 if result else 1


def _install_moonraker(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> int:
    service = MoonrakerSetupService()
    result = service.install(
        klipper_suffixes=args.klipper_suffix or None,
        create_example_cfg=args.create_example_cfg,
        interactive=False,
    )
    return 0 if result else 1


def _remove_moonraker(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not (args.service or args.dir or args.env or args.polkit):
        parser.error(
            "specify at least one of --service, --dir, --env, --polkit "
            "for 'remove moonraker'"
        )
    if args.service and not (args.all or args.instance):
        # refuse to silently wipe every Moonraker instance.
        parser.error(
            "removing Moonraker services is destructive; pass --all or "
            "--instance <suffix> (repeatable) to select what to remove"
        )
    service = MoonrakerSetupService()
    result = service.remove(
        remove_service=args.service,
        remove_dir=args.dir,
        remove_env=args.env,
        remove_polkit=args.polkit,
        remove_all=args.all,
        instance_suffixes=args.instance or None,
        interactive=False,
    )
    return 0 if result else 1


def _update_moonraker(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    service = MoonrakerSetupService()
    result = service.update(interactive=False)
    return 0 if result else 1


def _install_web_client(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> int:
    service = WebClientSetupService(args.component)
    result = service.install(
        port=args.port,
        install_client_cfg=args.install_config,
        continue_without_moonraker=args.continue_without_moonraker,
        interactive=False,
    )
    return 0 if result else 1


def _install_web_client_config(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> int:
    client_name = args.component.replace("-config", "")
    result = WebClientConfigSetupService(client_name).install(interactive=False)
    return 0 if result else 1


def _remove_web_client(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> int:
    if not (args.client or args.config):
        parser.error(
            f"specify at least one of --client, --config for 'remove {args.component}'"
        )
    service = WebClientSetupService(args.component)
    result = service.remove(
        remove_client=args.client,
        remove_client_cfg=args.config,
        backup_config=not args.no_backup,
        interactive=False,
    )
    return 0 if result else 1


def _update_web_client(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> int:
    result = WebClientSetupService(args.component).update()
    return 0 if result else 1


def _update_web_client_config(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> int:
    client_name = args.component.replace("-config", "")
    result = WebClientConfigSetupService(client_name).update(interactive=False)
    return 0 if result else 1


# Dispatch registry: (command, component) -> handler. Keeping this as a module
# constant (not a closure) keeps ``run_cli`` trivial and lets tests assert which
# combinations are actually supported.
DISPATCH: Dict[Tuple[str, str], Dispatcher] = {
    ("install", "klipper"): _install_klipper,
    ("remove", "klipper"): _remove_klipper,
    ("update", "klipper"): _update_klipper,
    ("install", "moonraker"): _install_moonraker,
    ("remove", "moonraker"): _remove_moonraker,
    ("update", "moonraker"): _update_moonraker,
    ("install", "mainsail"): _install_web_client,
    ("install", "fluidd"): _install_web_client,
    ("remove", "mainsail"): _remove_web_client,
    ("remove", "fluidd"): _remove_web_client,
    ("update", "mainsail"): _update_web_client,
    ("update", "fluidd"): _update_web_client,
    ("install", "mainsail-config"): _install_web_client_config,
    ("install", "fluidd-config"): _install_web_client_config,
    ("update", "mainsail-config"): _update_web_client_config,
    ("update", "fluidd-config"): _update_web_client_config,
}


def run_cli(argv: List[str] | None = None) -> int:
    """Run a headless CLI command.

    Returns 0 on success, -1 if no command was provided (-> fall back to TUI),
    and a positive exit code when a command reports failure.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        return -1

    handler = DISPATCH.get((args.command, args.component))
    if handler is None:
        parser.error(f"Unsupported command: {args.command} {args.component}")
    return handler(args, parser)


def main() -> None:
    sys.exit(run_cli())
