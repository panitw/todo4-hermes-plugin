# todo4-hermes-plugin

Hermes Agent plugin that onboards [Todo4](https://todo4.io) from chat and ships skills to work with Todo4.

## What it does

- **Onboards Todo4 from chat** — email → OTP → agent connection, no browser or password required.
- **Configures the Todo4 MCP server** — writes the server entry into your Hermes YAML config and stores the agent token in `~/.hermes/.env`.
- **Ships two bundled skills** (installed to `~/.hermes/skills/`):
  - `todo4-onboard` — the interview flow the agent follows to create an account and connect.
  - `todo4-work` — an agent playbook for effective day-to-day task management.

See the [Hermes plugin guide](https://hermes-agent.nousresearch.com/docs/guides/build-a-hermes-plugin) for context on how plugins plug in.

## Install

```bash
hermes plugins install https://github.com/panitw/todo4-hermes-plugin
```

Then restart Hermes so the plugin is loaded:

```bash
hermes gateway restart
```

## Usage

### Onboarding

Hermes doesn't auto-match fuzzy phrases to skills reliably. Use one of these explicit prompts in chat:

1. **Run the skill by name** (recommended):

   > Run the todo4-onboard skill

2. **Call the tool directly** (fallback if the skill doesn't trigger):

   > Use `todo4_register` to sign me up — my email is you@example.com

Either way, the flow asks for your email, sends a one-time code, verifies it, and connects this Hermes instance as your Todo4 agent. After the flow completes, run `hermes gateway restart` (or `/reload-mcp`) to activate the Todo4 MCP tools.

### Diagnostics

Ask the agent:

> Call `todo4_status`

…which reports whether the agent token is present, the MCP entry is in `config.yaml`, and the Todo4 API is reachable.

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
