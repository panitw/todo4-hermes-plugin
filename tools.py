"""Todo4 Hermes plugin — tool handlers.

Contract:
- Every handler returns a JSON string (never a dict, never raises).
- Secrets (OTP codes, tokens, MCP config contents) are never logged or echoed.
- The access_token from verify_otp is ephemeral — it's only returned so the
  skill can immediately hand it to connect. It is never persisted here.
"""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml

import config

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _s(v: Any) -> str:
    """Coerce to string and strip. Tolerates non-string inputs from the LLM."""
    if v is None:
        return ""
    return str(v).strip()


def _err(code: str, message: str, **extra: Any) -> str:
    payload = {"ok": False, "error": code, "message": message}
    payload.update(extra)
    return json.dumps(payload)


def _ok(**fields: Any) -> str:
    return json.dumps({"ok": True, **fields})


def _post(path: str, body: Dict[str, Any], token: Optional[str] = None) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.post(
        f"{config.get_api_url()}{path}",
        json=body,
        headers=headers,
        timeout=_DEFAULT_TIMEOUT,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tool: register — send OTP to email
# ─────────────────────────────────────────────────────────────────────────────
def register(args: Dict[str, Any], **kwargs: Any) -> str:
    email = _s(args.get("email"))
    if not email:
        return _err("missing_email", "Email is required.")
    if not _EMAIL_RE.match(email):
        return _err("invalid_email", "That doesn't look like a valid email.")
    try:
        resp = _post("/auth/register-passwordless", {"email": email})
    except requests.RequestException as exc:
        return _err("network", f"Could not reach Todo4: {exc}")

    if resp.status_code in (200, 201):
        return _ok(message="Verification code sent.")
    if resp.status_code == 429:
        retry_after = _extract_retry_after(resp)
        return _err("rate_limited", "Too many requests. Please wait and try again.",
                    retryAfterSeconds=retry_after)
    if resp.status_code == 400:
        return _err("invalid_email", "That email was rejected by Todo4.")
    return _err("server", f"Unexpected response ({resp.status_code}).")


# ─────────────────────────────────────────────────────────────────────────────
# Tool: verify_otp — exchange email+code for an access token (from cookie)
# ─────────────────────────────────────────────────────────────────────────────
def verify_otp(args: Dict[str, Any], **kwargs: Any) -> str:
    email = _s(args.get("email"))
    code = _s(args.get("code"))
    if not email or not code:
        return _err("missing_args", "Email and code are required.")
    try:
        resp = _post("/auth/verify-otp", {"email": email, "code": code})
    except requests.RequestException as exc:
        return _err("network", f"Could not reach Todo4: {exc}")

    if resp.status_code == 200:
        access_token = _extract_access_token(resp)
        if not access_token:
            return _err("parse_error", "Verification succeeded but access_token was missing.")
        return _ok(accessToken=access_token)
    if resp.status_code == 400:
        return _err("invalid_code", "That code didn't work. Double-check and try again.")
    if resp.status_code == 429:
        return _err("rate_limited", "Too many verification attempts. Please wait.",
                    retryAfterSeconds=_extract_retry_after(resp))
    return _err("server", f"Unexpected response ({resp.status_code}).")


# ─────────────────────────────────────────────────────────────────────────────
# Tool: connect — register this agent, write MCP config + .env
# ─────────────────────────────────────────────────────────────────────────────
def connect(args: Dict[str, Any], **kwargs: Any) -> str:
    access_token = _s(args.get("accessToken"))
    agent_name = _s(args.get("agentName")) or "Hermes"
    if not access_token:
        return _err("missing_args", "accessToken is required.")
    body = {"agentName": agent_name, "agentPlatform": config.AGENT_PLATFORM}
    try:
        resp = _post("/auth/agent-connect", body, token=access_token)
    except requests.RequestException as exc:
        return _err("network", f"Could not reach Todo4: {exc}")

    if resp.status_code == 401:
        return _err("unauthorized", "Access token was rejected. Restart the onboarding.")
    if resp.status_code == 422:
        return _err("quota_exceeded",
                    "This account has reached its agent limit. Manage agents at todo4.io.")
    if resp.status_code == 429:
        return _err("rate_limited", "Too many connect attempts. Please wait.",
                    retryAfterSeconds=_extract_retry_after(resp))
    if resp.status_code not in (200, 201):
        return _err("server", f"Unexpected response ({resp.status_code}).")

    try:
        body = resp.json()
    except ValueError:
        return _err("parse_error", "Response was not valid JSON.")
    if not isinstance(body, dict):
        return _err("parse_error", "Response JSON was not an object.")
    data = body.get("data") if isinstance(body.get("data"), dict) else {}

    agent_token = data.get("agentAccessToken")
    snippet = data.get("mcpConfigSnippet")
    snippet = snippet if isinstance(snippet, dict) else {}
    servers = snippet.get("mcpServers")
    servers = servers if isinstance(servers, dict) else {}
    todo4_entry = servers.get(config.SERVER_NAME)
    if not agent_token or not isinstance(todo4_entry, dict):
        return _err("parse_error", "Missing agentAccessToken or mcpConfigSnippet in response.")

    # Rewrite Authorization header to reference the env var, not the raw token.
    existing_headers = todo4_entry.get("headers")
    headers = dict(existing_headers) if isinstance(existing_headers, dict) else {}
    headers["Authorization"] = f"Bearer ${{{config.ENV_TOKEN_KEY}}}"
    yaml_entry = {k: v for k, v in todo4_entry.items() if k != "headers"}
    yaml_entry["headers"] = headers

    try:
        _merge_yaml_config(yaml_entry)
        _write_env_token(agent_token)
    except _ConfigRootError as exc:
        return _err("config_conflict", str(exc))
    except (OSError, yaml.YAMLError, UnicodeDecodeError) as exc:
        return _err("io_error", f"Could not write Hermes config: {exc}")

    return _ok(
        message=f"Connected as '{agent_name}'. Restart Hermes or run /reload-mcp.",
        reloadHint="/reload-mcp",
        webLoginUrl=data.get("webLoginUrl") or None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tool: status — probe local config + remote reachability
# ─────────────────────────────────────────────────────────────────────────────
def status(args: Dict[str, Any], **kwargs: Any) -> str:
    env_file = config.get_env_file()
    config_path = config.get_config_path()

    token_present = _env_has_token(env_file)
    config_has_entry = False
    config_valid = True
    if config_path.exists():
        try:
            loaded = yaml.safe_load(config_path.read_text()) or {}
            if isinstance(loaded, dict):
                servers = loaded.get("mcp_servers")
                if isinstance(servers, dict):
                    config_has_entry = bool(servers.get(config.SERVER_NAME))
            else:
                config_valid = False
        except (yaml.YAMLError, OSError, UnicodeDecodeError):
            config_valid = False

    api_reachable = False
    api_error: Optional[str] = None
    try:
        r = requests.get(f"{config.get_api_url()}/health", timeout=5)
        api_reachable = r.ok
    except requests.RequestException as exc:
        api_error = str(exc)

    return _ok(
        configured=token_present and config_has_entry and config_valid,
        tokenPresent=token_present,
        mcpEntryPresent=config_has_entry,
        configValid=config_valid,
        apiReachable=api_reachable,
        apiError=api_error,
        configPath=str(config_path),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────────────
class _ConfigRootError(Exception):
    """Raised when the existing Hermes config is not a YAML mapping."""


def _extract_access_token(resp: requests.Response) -> Optional[str]:
    """Prefer requests' parsed cookie jar; fall back to the raw Set-Cookie header."""
    token = resp.cookies.get("access_token")
    if token:
        return token
    raw = resp.headers.get("Set-Cookie")
    if not raw:
        return None
    jar = SimpleCookie()
    try:
        jar.load(raw)
    except Exception:
        return None
    morsel = jar.get("access_token")
    return morsel.value if morsel else None


def _extract_retry_after(resp: requests.Response) -> Optional[int]:
    header = resp.headers.get("Retry-After")
    if header and header.isdigit():
        return int(header)
    try:
        details = (resp.json().get("error") or {}).get("details") or {}
        val = details.get("retryAfterSeconds")
        return int(val) if val is not None else None
    except (ValueError, AttributeError):
        return None


def _merge_yaml_config(todo4_entry: Dict[str, Any]) -> None:
    path = config.get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, Any] = {}
    if path.exists():
        loaded = yaml.safe_load(path.read_text()) or {}
        if loaded and not isinstance(loaded, dict):
            raise _ConfigRootError(
                f"Existing Hermes config at {path} is not a YAML mapping; refusing to overwrite."
            )
        if isinstance(loaded, dict):
            existing = loaded
    servers = existing.get("mcp_servers")
    if not isinstance(servers, dict):
        servers = {}
    servers[config.SERVER_NAME] = todo4_entry
    existing["mcp_servers"] = servers
    _atomic_write(path, yaml.safe_dump(existing, sort_keys=False), mode=0o644)


def _write_env_token(token: str) -> None:
    path = config.get_env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = config.ENV_TOKEN_KEY
    lines: list[str] = []
    if path.exists():
        for line in path.read_text().splitlines():
            stripped = line.lstrip()
            if stripped.startswith(f"{key}=") or stripped.startswith(f"export {key}="):
                continue
            lines.append(line)
    lines.append(f"{key}={token}")
    _atomic_write(path, "\n".join(lines) + "\n", mode=0o600)


def _env_has_token(env_file: Path) -> bool:
    if not env_file.exists():
        return False
    key = config.ENV_TOKEN_KEY
    try:
        text = env_file.read_text()
    except (OSError, UnicodeDecodeError):
        return False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(f"export {key}="):
            stripped = stripped[len("export "):]
        if stripped.startswith(f"{key}="):
            _, _, value = stripped.partition("=")
            return bool(value.strip().strip('"').strip("'"))
    return False


def _atomic_write(path: Path, content: str, mode: int = 0o644) -> None:
    """Write content to path atomically (temp file + rename), chmod after write."""
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
