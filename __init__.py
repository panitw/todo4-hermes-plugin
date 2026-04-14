"""Todo4 Hermes plugin — registration entry point."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from . import config, schemas, tools

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).resolve().parent
_BUNDLED_SKILLS = _PLUGIN_DIR / "skills"


def register(ctx) -> None:
    """Wire tools + CLI + skill files into Hermes."""
    ctx.register_tool(
        name="todo4_register",
        toolset="todo4",
        schema=schemas.REGISTER,
        handler=tools.register,
    )
    ctx.register_tool(
        name="todo4_verify_otp",
        toolset="todo4",
        schema=schemas.VERIFY_OTP,
        handler=tools.verify_otp,
    )
    ctx.register_tool(
        name="todo4_connect",
        toolset="todo4",
        schema=schemas.CONNECT,
        handler=tools.connect,
    )
    ctx.register_tool(
        name="todo4_status",
        toolset="todo4",
        schema=schemas.STATUS,
        handler=tools.status,
    )

    if hasattr(ctx, "register_cli_command"):
        ctx.register_cli_command(
            name="todo4",
            help="Manage the Todo4 connection",
            setup_fn=_setup_cli,
            handler_fn=_cli_handler,
        )

    _install_skills()


def _install_skills() -> None:
    dest_dir = config.get_skills_dir()
    if not _BUNDLED_SKILLS.exists():
        return
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("todo4: could not create skills dir %s: %s", dest_dir, exc)
        return
    for src in _BUNDLED_SKILLS.glob("*.md"):
        dest = dest_dir / src.name
        try:
            shutil.copy2(src, dest)  # always overwrite so plugin updates propagate
        except OSError as exc:
            logger.warning("todo4: could not install skill %s: %s", src.name, exc)


def _setup_cli(subparser) -> None:
    subs = subparser.add_subparsers(dest="todo4_command")
    subs.add_parser("doctor", help="Diagnose the Todo4 connection")
    subs.add_parser("status", help="Alias for doctor")


def _cli_handler(args) -> None:
    sub = getattr(args, "todo4_command", None)
    if sub in ("doctor", "status"):
        result = json.loads(tools.status({}))
        _print_doctor(result)
    else:
        print("Usage: hermes todo4 <doctor|status>")


def _print_doctor(report: dict) -> None:
    configured = report.get("configured")
    mark = "[OK]" if configured else "[  ]"
    print(f"{mark} Todo4 configured: {configured}")
    print(f"     Token in .env:       {report.get('tokenPresent')}")
    print(f"     MCP entry in config: {report.get('mcpEntryPresent')}")
    print(f"     Config is valid:     {report.get('configValid')}")
    print(f"     Config path:         {report.get('configPath')}")
    print(f"     API reachable:       {report.get('apiReachable')}")
    if report.get("apiError"):
        print(f"     API error:           {report['apiError']}")
    if not configured:
        print("\nRun the onboarding skill in chat: 'Run the todo4-onboard skill'.")
