# todo4-hermes-plugin

Hermes Agent plugin that onboards [Todo4](https://todo4.io) from chat and ships skills to work with Todo4.

## What it does

- **Onboards Todo4 from chat** — email → OTP → agent connection, no browser or password required.
- **Configures the Todo4 MCP server** — writes the server entry into your Hermes YAML config and stores the agent token in `~/.hermes/.env`.
- **Ships two bundled skills**:
  - `onboard.md` — the interview flow the agent follows when you say "set me up with Todo4".
  - `work-with-todo4.md` — an agent playbook for effective day-to-day task management.
- **`hermes todo4 doctor` CLI** — diagnose the Todo4 connection from the terminal.

See the [Hermes plugin guide](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin) for context on how plugins plug in.

## Install

```bash
hermes plugins install https://github.com/panitw/todo4-hermes-plugin
```

When prompted for environment variables, **skip them** — the onboarding flow will populate `TODO4_AGENT_TOKEN` in `~/.hermes/.env` automatically, and `TODO4_API_URL` defaults to `https://todo4.io/api/v1`.

Restart Hermes (or run `/reload-mcp` after onboarding) for the new tools and skills to activate.

## Usage

In chat, say any of:

- "Set me up with Todo4"
- "Connect Todo4"
- "I want to use Todo4"

The `onboard` skill walks you through one question at a time and finishes by writing the MCP config. Run `/reload-mcp` (or restart Hermes) to activate the Todo4 MCP tools.

From the terminal:

```bash
hermes todo4 doctor
```

## Requirements

- Python ≥ 3.9
- `requests`, `PyYAML` (installed automatically by pip)

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `TODO4_API_URL` | `https://todo4.io/api/v1` | Todo4 API base. Override for staging. |
| `HERMES_HOME` | `~/.hermes` | Hermes config root. Override for isolated testing. |
| `HERMES_CONFIG` | `$HERMES_HOME/config.yaml` | Full path to the Hermes YAML config. |
| `TODO4_AGENT_TOKEN` | *(set by plugin)* | Agent bearer token, stored in `$HERMES_HOME/.env`. |

## Security

| What the plugin does | With |
|---|---|
| Calls `POST /auth/register-passwordless` | User email only |
| Calls `POST /auth/verify-otp` | Email + 6-digit code |
| Calls `POST /auth/agent-connect` | Access-token JWT (ephemeral, 1-hour expiry) |
| Writes MCP config to `$HERMES_HOME/config.yaml` | Deep-merge, preserves other MCP servers |
| Writes agent token to `$HERMES_HOME/.env` | As `TODO4_AGENT_TOKEN=...` |

The Hermes YAML config stores the authorization header as `Bearer ${TODO4_AGENT_TOKEN}` — the raw agent token lives only in `.env`.

Tool handlers never raise, never log secrets, and never return tokens inside the MCP config blob.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
