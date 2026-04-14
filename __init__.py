"""Todo4 Hermes plugin — registration entry point."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from . import config, schemas, tools

logger = logging.getLogger(__name__)

_PLUGIN_DIR = Path(__file__).resolve().parent
_BUNDLED_SKILLS = _PLUGIN_DIR / "skills"


def register(ctx) -> None:
    """Wire tools and skill files into Hermes."""
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

    _install_skills()


def _install_skills() -> None:
    """Copy each bundled skill subdirectory's SKILL.md into ~/.hermes/skills/.

    Hermes discovers skills by rglob'ing for files literally named `SKILL.md`
    under ~/.hermes/skills/ (see hermes_cli/tools/skills_tool.py), so we must
    install one SKILL.md per skill directory with that exact casing.
    """
    if not _BUNDLED_SKILLS.exists():
        return
    hermes_skills = config.get_hermes_home() / "skills"
    try:
        hermes_skills.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("todo4: could not create skills dir %s: %s", hermes_skills, exc)
        return
    for src_dir in _BUNDLED_SKILLS.iterdir():
        if not src_dir.is_dir():
            continue
        src_skill = src_dir / "SKILL.md"
        if not src_skill.exists():
            continue
        dest_dir = hermes_skills / src_dir.name
        dest_skill = dest_dir / "SKILL.md"
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_skill, dest_skill)  # always overwrite
        except OSError as exc:
            logger.warning("todo4: could not install skill %s: %s", src_dir.name, exc)
