---
name: todo4-work
description: "Guidance for managing tasks in Todo4 effectively. Load whenever the user asks you to create, update, organize, review, plan, or triage their tasks — e.g. 'plan my week', 'what should I work on', 'triage my todo list', 'break this down', 'schedule a follow-up'. Use alongside the Todo4 MCP tools (create_task, list_tasks, update_task, notify_human)."
---

# Working with Todo4

Use this skill alongside the Todo4 MCP tools. If those tools are not available, run `todo4_status` — if not configured, trigger the onboarding skill.

## Core tools (from the Todo4 MCP server)

- `create_task` — create a task with title, description, due date, tags, priority, subtasks
- `list_tasks` — list tasks with filters (status, tag, due range, priority)
- `get_task` — fetch a single task by ID
- `update_task` — change status, due date, priority, tags, description
- `notify_human` — send a message to the user's Todo4 inbox when something needs their attention

## Principles

**One task = one outcome.** A task should name a finishable outcome, not a topic. Rewrite "Q2 report" as "Draft Q2 revenue summary for Monday's exec sync."

**Due dates are commitments, not wishes.** Only set a due date if missing it has a consequence. Otherwise leave it open.

**Notify the human sparingly.** Use `notify_human` for blockers, ambiguous input, or things the user explicitly asked you to flag. Routine progress belongs in task comments, not notifications.

## When to use each feature

| Feature | Use when | Don't use for |
|---------|----------|---------------|
| **Subtasks** | A single task needs 2–6 concrete steps and you want one rollup status | Long-running initiatives (use separate tasks + a tag) |
| **Tags** | Grouping across projects, clients, or themes (`#client-acme`, `#research`) | One-off context (put it in the description) |
| **Priority** | Distinguishing "today vs. this week vs. someday" | Labeling every task — only mark the top ~20% |
| **Recurrence** | Habits and reviews that repeat on a schedule (weekly review, monthly report) | Multi-step projects that happen to recur |
| **Reference URL** | Linking to the source of truth (ticket, doc, PR) | Screenshots or copy-paste of content |
| **Description** | Acceptance criteria, links, context the user needs to pick up the task cold | Task history — use comments for that |

## Common workflows

**"Plan my week"**
1. `list_tasks` with filter `dueBefore: next Sunday` and `status: open`.
2. Group by priority and due date. Surface overdue first, then due this week.
3. Ask the user which tasks to reschedule, delegate, or drop — one decision at a time.
4. Apply changes with `update_task`.

**"Triage my inbox"**
1. `list_tasks` with `status: needs_attention`.
2. For each, propose: close, snooze, break into subtasks, or hand back with a question via `notify_human`.
3. Never auto-close. Always confirm with the user first.

**"Break this down"**
1. Restate the user's goal as a single outcome.
2. Propose 3–6 subtasks, ordered by dependency.
3. Confirm, then create with `create_task` (subtasks in the same call if supported, else create parent then update).

**"Follow up on X"**
1. Create a task with a due date tied to the reason you're following up (e.g. "when the draft is supposed to land").
2. Put the "why" in the description so future-you has context.
3. Add a `reference_url` to the thing you're following up on.

## Anti-patterns

- Creating a task titled "Ask John about Y" with no due date — it will rot. Set a date.
- Dumping a long meeting transcript into the description — summarize the decisions and link to the transcript.
- Using `notify_human` as a progress log — users will mute you.
- Closing tasks the user didn't explicitly approve closing.

## When MCP isn't working

If `create_task`/`list_tasks` fail, call `todo4_status` first. If `"configured": false`, trigger the onboarding skill. If `"configured": true` but tools still fail, tell the user to run `/reload-mcp` or restart Hermes.
