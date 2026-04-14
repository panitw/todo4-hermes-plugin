"""Path + env resolvers for the Todo4 Hermes plugin."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_API_URL = "https://todo4.io/api/v1"
ENV_TOKEN_KEY = "TODO4_AGENT_TOKEN"
ENV_API_URL_KEY = "TODO4_API_URL"
SERVER_NAME = "todo4"
AGENT_PLATFORM = "hermes"


def get_api_url() -> str:
    return os.environ.get(ENV_API_URL_KEY, DEFAULT_API_URL).rstrip("/")


def get_hermes_home() -> Path:
    override = os.environ.get("HERMES_HOME")
    if override:
        return Path(override)
    return Path.home() / ".hermes"


def get_config_path() -> Path:
    override = os.environ.get("HERMES_CONFIG")
    if override:
        return Path(override)
    return get_hermes_home() / "config.yaml"


def get_env_file() -> Path:
    return get_hermes_home() / ".env"


def get_skills_dir() -> Path:
    return get_hermes_home() / "skills" / "todo4"
