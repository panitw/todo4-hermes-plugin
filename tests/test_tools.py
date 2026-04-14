"""Unit tests covering the I/O & Edge-Case Matrix from the spec."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest
import responses
import yaml

from todo4_hermes import config, tools


API = config.DEFAULT_API_URL


@pytest.fixture(autouse=True)
def isolated_hermes_home(tmp_path, monkeypatch):
    """Point HERMES_HOME to an isolated temp dir for every test."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_CONFIG", raising=False)
    monkeypatch.delenv(config.ENV_API_URL_KEY, raising=False)
    yield tmp_path


# ─── register ────────────────────────────────────────────────────────────────
@responses.activate
def test_register_happy():
    responses.post(f"{API}/auth/register-passwordless", status=201, json={})
    result = json.loads(tools.register({"email": "a@b.co"}))
    assert result["ok"] is True


def test_register_invalid_email():
    result = json.loads(tools.register({"email": "not-an-email"}))
    assert result == {"ok": False, "error": "invalid_email", "message": mock.ANY}


def test_register_missing_email():
    result = json.loads(tools.register({}))
    assert result["error"] == "missing_email"


@responses.activate
def test_register_rate_limited():
    responses.post(
        f"{API}/auth/register-passwordless",
        status=429,
        json={"error": {"details": {"retryAfterSeconds": 1800}}},
    )
    result = json.loads(tools.register({"email": "a@b.co"}))
    assert result["error"] == "rate_limited"
    assert result["retryAfterSeconds"] == 1800


@responses.activate
def test_register_validation_error():
    responses.post(f"{API}/auth/register-passwordless", status=400, json={})
    result = json.loads(tools.register({"email": "a@b.co"}))
    assert result["error"] == "invalid_email"


@responses.activate
def test_register_network_error():
    import requests as _requests
    responses.post(
        f"{API}/auth/register-passwordless",
        body=_requests.exceptions.ConnectionError("boom"),
    )
    result = json.loads(tools.register({"email": "a@b.co"}))
    assert result["error"] == "network"


# ─── verify_otp ──────────────────────────────────────────────────────────────
@responses.activate
def test_verify_happy():
    responses.post(
        f"{API}/auth/verify-otp",
        status=200,
        json={"data": {}},
        headers={"Set-Cookie": "access_token=JWT_VALUE; Path=/; HttpOnly"},
    )
    result = json.loads(tools.verify_otp({"email": "a@b.co", "code": "123456"}))
    assert result["ok"] is True
    assert result["accessToken"] == "JWT_VALUE"


@responses.activate
def test_verify_wrong_code():
    responses.post(f"{API}/auth/verify-otp", status=400, json={})
    result = json.loads(tools.verify_otp({"email": "a@b.co", "code": "000000"}))
    assert result["error"] == "invalid_code"


@responses.activate
def test_verify_rate_limited():
    responses.post(f"{API}/auth/verify-otp", status=429, json={})
    result = json.loads(tools.verify_otp({"email": "a@b.co", "code": "123456"}))
    assert result["error"] == "rate_limited"


def test_verify_missing_args():
    assert json.loads(tools.verify_otp({"email": "a@b.co"}))["error"] == "missing_args"
    assert json.loads(tools.verify_otp({"code": "1"}))["error"] == "missing_args"


# ─── connect ─────────────────────────────────────────────────────────────────
def _connect_response_body(token="secret-agent-123", url="https://todo4.io/mcp",
                           web_login="https://todo4.io/login/abc"):
    return {
        "data": {
            "agentAccessToken": token,
            "mcpConfigSnippet": {
                "mcpServers": {
                    "todo4": {
                        "url": url,
                        "headers": {"Authorization": f"Bearer {token}"},
                    }
                }
            },
            "webLoginUrl": web_login,
        }
    }


@responses.activate
def test_connect_happy_writes_yaml_and_env(isolated_hermes_home):
    responses.post(f"{API}/auth/agent-connect", status=200, json=_connect_response_body())

    result = json.loads(tools.connect({"accessToken": "JWT", "agentName": "Hermes"}))
    assert result["ok"] is True
    assert result["webLoginUrl"] == "https://todo4.io/login/abc"
    assert result["reloadHint"] == "/reload-mcp"

    config_path = isolated_hermes_home / "config.yaml"
    env_path = isolated_hermes_home / ".env"
    assert config_path.exists() and env_path.exists()

    yaml_doc = yaml.safe_load(config_path.read_text())
    todo4 = yaml_doc["mcp_servers"]["todo4"]
    assert todo4["url"] == "https://todo4.io/mcp"
    # The Authorization header must reference the env var, NOT embed the raw token.
    assert todo4["headers"]["Authorization"] == "Bearer ${TODO4_AGENT_TOKEN}"
    assert "secret-agent-123" not in config_path.read_text()

    env_lines = env_path.read_text().splitlines()
    assert env_lines.count("TODO4_AGENT_TOKEN=secret-agent-123") == 1


@responses.activate
def test_connect_merge_preserves_other_servers(isolated_hermes_home):
    # Seed an existing config with a github MCP server.
    config_path = isolated_hermes_home / "config.yaml"
    config_path.write_text(yaml.safe_dump({
        "mcp_servers": {
            "github": {"url": "https://gh/mcp", "headers": {"Authorization": "Bearer gh"}},
        },
        "other_setting": {"keep": "me"},
    }))
    responses.post(f"{API}/auth/agent-connect", status=200, json=_connect_response_body())

    result = json.loads(tools.connect({"accessToken": "JWT"}))
    assert result["ok"] is True

    merged = yaml.safe_load(config_path.read_text())
    assert set(merged["mcp_servers"].keys()) == {"github", "todo4"}
    assert merged["mcp_servers"]["github"]["url"] == "https://gh/mcp"
    assert merged["other_setting"] == {"keep": "me"}


@responses.activate
def test_connect_env_replaces_existing_token(isolated_hermes_home):
    env = isolated_hermes_home / ".env"
    env.write_text("FOO=bar\nTODO4_AGENT_TOKEN=OLD\nBAZ=qux\n")
    responses.post(f"{API}/auth/agent-connect", status=200,
                   json=_connect_response_body(token="new-agent-token"))

    json.loads(tools.connect({"accessToken": "JWT"}))
    lines = env.read_text().splitlines()
    assert "FOO=bar" in lines
    assert "BAZ=qux" in lines
    assert lines.count("TODO4_AGENT_TOKEN=new-agent-token") == 1
    assert "TODO4_AGENT_TOKEN=OLD" not in lines


@responses.activate
def test_connect_unauthorized():
    responses.post(f"{API}/auth/agent-connect", status=401, json={})
    result = json.loads(tools.connect({"accessToken": "bad"}))
    assert result["error"] == "unauthorized"


@responses.activate
def test_connect_quota():
    responses.post(f"{API}/auth/agent-connect", status=422, json={})
    result = json.loads(tools.connect({"accessToken": "JWT"}))
    assert result["error"] == "quota_exceeded"


@responses.activate
def test_connect_network_error():
    import requests as _requests
    responses.post(f"{API}/auth/agent-connect",
                   body=_requests.exceptions.ConnectionError("down"))
    result = json.loads(tools.connect({"accessToken": "JWT"}))
    assert result["error"] == "network"


def test_connect_missing_token():
    assert json.loads(tools.connect({}))["error"] == "missing_args"


# ─── status ──────────────────────────────────────────────────────────────────
@responses.activate
def test_status_configured(isolated_hermes_home):
    (isolated_hermes_home / ".env").write_text("TODO4_AGENT_TOKEN=x\n")
    (isolated_hermes_home / "config.yaml").write_text(yaml.safe_dump({
        "mcp_servers": {"todo4": {"url": "https://todo4.io/mcp"}}
    }))
    responses.get(f"{API}/health", status=200)

    result = json.loads(tools.status({}))
    assert result["configured"] is True
    assert result["tokenPresent"] is True
    assert result["mcpEntryPresent"] is True
    assert result["apiReachable"] is True


@responses.activate
def test_status_not_configured(isolated_hermes_home):
    responses.get(f"{API}/health", status=200)
    result = json.loads(tools.status({}))
    assert result["configured"] is False
    assert result["tokenPresent"] is False
    assert result["mcpEntryPresent"] is False


# ─── patch regression tests ──────────────────────────────────────────────────
@responses.activate
def test_register_accepts_200_as_success():
    responses.post(f"{API}/auth/register-passwordless", status=200, json={})
    assert json.loads(tools.register({"email": "a@b.co"}))["ok"] is True


def test_non_string_inputs_do_not_raise():
    # Handlers must coerce odd types rather than raise.
    assert json.loads(tools.register({"email": 12345}))["error"] == "invalid_email"
    assert json.loads(tools.verify_otp({"email": None, "code": 1}))["error"] == "missing_args"
    assert json.loads(tools.connect({"accessToken": None}))["error"] == "missing_args"


@responses.activate
def test_connect_rejects_non_dict_yaml_root(isolated_hermes_home):
    config_path = isolated_hermes_home / "config.yaml"
    config_path.write_text("- i_am_a_list\n- not_a_mapping\n")
    responses.post(f"{API}/auth/agent-connect", status=200, json=_connect_response_body())
    result = json.loads(tools.connect({"accessToken": "JWT"}))
    assert result["ok"] is False
    assert result["error"] == "config_conflict"
    # Original file preserved.
    assert config_path.read_text().startswith("- i_am_a_list")


@responses.activate
def test_connect_malformed_existing_yaml_returns_error(isolated_hermes_home):
    config_path = isolated_hermes_home / "config.yaml"
    config_path.write_text(":not valid yaml:\n  - [\n")
    responses.post(f"{API}/auth/agent-connect", status=200, json=_connect_response_body())
    result = json.loads(tools.connect({"accessToken": "JWT"}))
    assert result["ok"] is False
    assert result["error"] == "io_error"


def test_env_token_detection_tolerates_export_prefix_and_whitespace(isolated_hermes_home):
    env = isolated_hermes_home / ".env"
    env.write_text("  export TODO4_AGENT_TOKEN=abc\n")
    assert tools._env_has_token(env) is True


@responses.activate
def test_connect_writes_env_with_0600_permissions(isolated_hermes_home):
    responses.post(f"{API}/auth/agent-connect", status=200, json=_connect_response_body())
    json.loads(tools.connect({"accessToken": "JWT"}))
    env = isolated_hermes_home / ".env"
    assert oct(env.stat().st_mode & 0o777) == "0o600"


def test_status_reports_invalid_yaml(isolated_hermes_home):
    (isolated_hermes_home / "config.yaml").write_text(":bad:\n  ]\n")
    result = json.loads(tools.status({}))
    assert result["configValid"] is False
    assert result["configured"] is False


def test_status_api_unreachable(isolated_hermes_home, monkeypatch):
    # No responses registered — requests will fail connection.
    def boom(*_args, **_kwargs):
        raise __import__("requests").exceptions.ConnectionError("no route")
    monkeypatch.setattr("requests.get", boom)
    result = json.loads(tools.status({}))
    assert result["apiReachable"] is False
    assert result["apiError"] is not None
