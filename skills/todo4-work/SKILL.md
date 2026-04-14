---
name: todo4-work
description: "How to work with a user's Todo4 tasks. Load this whenever the user mentions Todo4, their task list, their todo list, or asks you to create/list/update/organize/plan/triage tasks (e.g. 'create a task', 'what's on my list', 'plan my week', 'triage my inbox', 'follow up on X', 'break this down'). The Todo4 MCP server is the ONLY way to access Todo4 data — this skill tells you which MCP tools to call and when."
---

# Working with Todo4

## CRITICAL: Todo4 lives behind MCP tools — nothing else

When the user asks anything about their Todo4 tasks, you **must** use the Todo4 MCP tools listed below. Do **NOT**:

- Call `curl`, `wget`, `urllib`, `requests`, or any other HTTP client against `https://todo4.io` — the API requires an agent bearer token that lives in `~/.hermes/.env` and the endpoints expect specific envelopes. Trying to hand-craft HTTP calls will waste turns and fail.
- Use `browser_navigate`, `browser_click`, or the Playwright skill — Todo4's web UI is for humans, not for scraping.
- Shell out to `terminal`, `ls`, `grep`, `cat ~/.hermes/...` to "find" Todo4 — the tools are already loaded into your toolset; you don't need to discover them from the filesystem.
- Run `execute_code` to reinvent what the MCP tools already do.

If the Todo4 MCP tools don't seem available to you, call the `todo4_status` plugin tool and report its output to the user — don't improvise another path.

## The MCP tools you have

The Todo4 MCP server is connected as `todo4`. The tools exposed to you have **no prefix** — call them by their bare name (e.g. `list_tasks`, not `todo4:list_tasks` or `todo4.list_tasks`). The `todo4:` notation only appears in `hermes tools enable/disable` CLI syntax, not in tool-call invocations.

| Tool | Purpose |
|---|---|
| `get_platform_info` | Discover capabilities, connected agents, and available features. Call this first if you're unsure what's possible. |
| `list_tasks` | List tasks with filters (status, tag, due date range, priority, assignee). |
| `get_task` | Fetch a single task by ID — includes subtasks, comments, history. |
| `create_task` | Create a task with title, description, due date, tags, priority, subtasks. |
| `update_task` | Change status, due date, priority, tags, description on an existing task. |
| `notify_human` | Send a message to the user's Todo4 inbox. Use for blockers, ambiguous input, or things the user explicitly asked you to flag. |
| `open_website` | Generate a one-time login URL so the user can open Todo4 in the browser already signed in. |

If you see 11+ MCP tools under `todo4` but the table above only lists 7, the extra tools handle subtasks, comments, and notifications — use them when the user's request needs them (e.g. `add_comment`, `add_subtask` — call `get_platform_info` or just try the tool to see its schema).

## Principles

**One task = one outcome.** A task names a finishable outcome, not a topic. Rewrite "Q2 report" as "Draft Q2 revenue summary for Monday's exec sync."

**Due dates are commitments, not wishes.** Only set a due date if missing it has a consequence.

**Notify sparingly.** `notify_human` is for things the user needs to see now. Routine progress belongs in task comments (or no update at all).

**Confirm before destructive changes.** Never close, delete, or reassign a task without explicit user approval.

## When to use each feature

| Feature | Use when | Don't use for |
|---|---|---|
| **Subtasks** | A single task needs 2–6 concrete steps with one rollup status | Long-running initiatives (use separate tasks + a shared tag) |
| **Tags** | Grouping across projects, clients, or themes (`#client-acme`, `#research`) | One-off context (put it in the description) |
| **Priority** | Distinguishing "today vs. this week vs. someday" | Labeling every task — only mark the top ~20% |
| **Recurrence** | Habits and reviews that repeat on a schedule | Multi-step projects that happen to recur |
| **Reference URL** | Linking to the source of truth (ticket, doc, PR) | Screenshots or copy-paste of content |
| **Description** | Acceptance criteria, links, context the user needs to pick up the task cold | Task history — use comments for that |

## Common workflows

**"Show me my tasks" / "Get task list"**
→ Call `list_tasks` (no filters for a full list, or `status: open` for active only). Present a short summary, not a dump.

**"Plan my week"**
1. `list_tasks` with `dueBefore: <next Sunday>` and `status: open`.
2. Group by priority and due date. Surface overdue first, then due this week.
3. Ask the user which to reschedule, delegate, or drop — one decision at a time.
4. Apply changes with `update_task`.

**"Triage my inbox"**
1. `list_tasks` with `status: needs_attention`.
2. For each, propose: close, snooze, break into subtasks, or hand back via `notify_human`.
3. Never auto-close. Confirm with the user first.

**"Break this down"**
1. Restate the goal as a single outcome.
2. Propose 3–6 subtasks ordered by dependency.
3. Confirm, then create with `create_task` (subtasks inline if supported, else parent + follow-ups).

**"Follow up on X"**
1. Create a task with a due date tied to the reason you're following up.
2. Put the "why" in the description.
3. Add the source `reference_url`.

## Anti-patterns

- Task titled "Ask John about Y" with no due date — it will rot. Set a date.
- Dumping a long meeting transcript into a description — summarize decisions, link the transcript.
- Using `notify_human` as a progress log — users will mute you.
- Closing tasks without explicit user approval.

## If something goes wrong

1. MCP tool returns an auth error → the agent token expired or the MCP config is stale. Ask the user to run `hermes gateway restart`, then try again. If still failing, call `todo4_status` (plugin tool) to diagnose.
2. You can't find `list_tasks` / `create_task` in your toolset → the Todo4 MCP server isn't connected. Call `todo4_status` (the plugin tool, with prefix); if `configured: false`, trigger the `todo4-onboard` skill.
3. You're tempted to reach for `curl`, `execute_code`, `browser_navigate`, or `terminal` → go back to the table above. Every Todo4 operation has a dedicated MCP tool.
