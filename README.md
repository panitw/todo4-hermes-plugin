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

Run these commands in order:

```bash
# 1. Clone the plugin into ~/.hermes/plugins/todo4/
hermes plugins install https://github.com/panitw/todo4-hermes-plugin

# 2. Trigger plugin discovery so register() runs and bundled skills land in
#    ~/.hermes/skills/todo4-onboard/ and ~/.hermes/skills/todo4-work/
hermes plugins list

# 3. Restart the gateway so it picks up the new toolset
hermes gateway restart
```

> **Why step 2 matters:** `hermes gateway restart` alone does **not** invoke a plugin's `register()` function. Plugin load happens during CLI commands that go through plugin discovery (like `hermes plugins list`). Without step 2, the bundled `todo4-onboard` and `todo4-work` skills won't appear in `~/.hermes/skills/`.

### Verify

```bash
hermes plugins list | grep todo4     # enabled, v0.1.0, source=git
hermes skills list  | grep todo4     # todo4-onboard + todo4-work, source=local
hermes tools list   | grep todo4     # ✓ enabled  todo4  🔌 Todo4
```

### Updating

```bash
hermes plugins uninstall todo4
hermes plugins install https://github.com/panitw/todo4-hermes-plugin
hermes plugins list
hermes gateway restart
```

(Hermes does not currently pull plugin updates in place when the version in `plugin.yaml` hasn't bumped, so uninstall + reinstall is the reliable path.)

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
python3 -m venv .venv
.venv/bin/pip install pytest responses requests PyYAML
cd /tmp && /path/to/hermes-plugin/.venv/bin/pytest /path/to/hermes-plugin/tests/
```

> Tests need to run from a cwd **outside** the plugin root. The plugin's `__init__.py` uses package-relative imports (`from . import config, tools`), which match how Hermes loads it at runtime but confuse pytest's test-collection walker when invoked from inside the plugin directory.

## License

MIT — see [LICENSE](LICENSE).
