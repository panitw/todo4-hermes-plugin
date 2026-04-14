---
name: todo4-onboard
description: "Sign up for Todo4 and connect this agent via MCP. Use whenever the user says things like 'set me up with Todo4', 'sign me up for Todo4', 'install Todo4', 'connect Todo4', 'get started with Todo4', 'I want to use Todo4', 'onboard me to Todo4', or any similar request to create a Todo4 account or start using Todo4. Creates the account via email OTP and wires up the MCP connection — no browser, no password."
---

# Todo4 Onboarding Skill (Hermes)

This is a fixed 4-step procedure. Follow it exactly, in order, one step at a time. Do not improvise, summarize, or skip steps.

## Language

Reply in the user's language. Detect it from their messages — if they write in Thai, reply in Thai; Japanese, reply in Japanese; and so on. Default to English only if the language is unclear.

The SAY lines in each step are reference wording in English. Translate them into the user's language while preserving the meaning, the information requested, and any placeholders (e.g., `<email>`, `<WEB_LOGIN_URL>`). Do NOT translate: tool output, URLs, or tokens.

## When to run this skill

Run this whole procedure, starting at STEP 1, whenever the user asks to sign up for, install, connect, onboard, or start using Todo4.

## DO NOT

- DO NOT explain what Todo4 is, list features, or ask "are you sure?" — just start STEP 1.
- DO NOT ask for more than one piece of information per message.
- DO NOT skip or combine steps.
- DO NOT continue past a failed step until the error is resolved.
- DO NOT echo the verification code, any token, or raw tool output back to the user.

---

## STEP 1 — Ask for email

SAY (verbatim):

> I'll set you up with Todo4. I just need your email so I can send a verification code. What email should I use?

WAIT for the user's reply. Store the reply as `<email>` and go to STEP 2.

---

## STEP 2 — Send verification code

CALL the tool `todo4_register` with `{"email": "<email>"}`.

Read the tool's JSON result:

- `"ok": true` → SAY (verbatim):
  > I've sent a 6-digit verification code to **<email>**. Please paste it here when it arrives.

  WAIT for the code and go to STEP 3.
- `"ok": false` and `"error": "invalid_email"` → SAY: "That email was rejected. Could you try another one?" Go back to STEP 1.
- `"ok": false` and `"error": "rate_limited"` → SAY: "We've hit a rate limit. Please wait a moment and try again." STOP.
- `"ok": false` and `"error": "network"` → SAY: "I couldn't reach the Todo4 server. Please check your connection and try again." STOP.
- any other error → SAY: "Something went wrong talking to Todo4. Try again in a moment." STOP.

---

## STEP 3 — Verify the code

Extract the 6 digits from the user's reply as `<code>`.

CALL `todo4_verify_otp` with `{"email": "<email>", "code": "<code>"}` **exactly once**. OTP codes are single-use; calling twice will fail the second time.

Read the result:

- `"ok": true` → store `accessToken` from the result in memory as `<access_token>`. SAY: "Email verified. Connecting myself as your agent…" and go to STEP 4.
- `"ok": false` and `"error": "invalid_code"` → SAY: "That code didn't work. Please double-check and try again." WAIT for a new code and repeat STEP 3. After 3 failures, SAY: "Let me send you a new code." and go back to STEP 2.
- `"ok": false` and `"error": "rate_limited"` → SAY: "Too many attempts. Please wait and try again." STOP.
- `"ok": false` and `"error": "network"` → SAY: "I couldn't reach the Todo4 server. Please check your connection." STOP.

Never echo `<access_token>` or the full tool output.

---

## STEP 4 — Connect this agent

CALL `todo4_connect` with `{"accessToken": "<access_token>", "agentName": "Hermes"}`.

Read the result:

- `"ok": true` → the plugin has written the MCP config and stored the agent token. Send the following as **three separate messages** — one per bullet, flushed individually.

  1. SAY (verbatim):
     > Done — I'm connected to your Todo4 account. Run `/reload-mcp` (or restart Hermes) to activate the Todo4 MCP tools.
  2. If `webLoginUrl` in the result is non-empty, SAY (substitute the URL literally — no code block):
     > Open your tasks in the browser — you'll be signed in automatically (link is single-use, valid for 5 minutes):
     > <webLoginUrl>

     If `webLoginUrl` is empty or null, skip this message entirely.
  3. SAY (verbatim):
     > After `/reload-mcp`, try: "Create a task to review the Q2 report by Friday."

  Then WAIT. When the user requests a task, use the Todo4 MCP tools (`create_task`, etc.) — not `todo4_register`/`verify`/`connect`.
- `"ok": false` and `"error": "unauthorized"` → SAY: "The verification session expired. Let me start over." Go back to STEP 1.
- `"ok": false` and `"error": "quota_exceeded"` → SAY: "Your account has reached the maximum number of connected agents. Manage them at todo4.io." STOP.
- `"ok": false` and `"error": "network"` → SAY: "I couldn't reach the Todo4 server. Please check your connection." STOP.
- any other error → SAY: "Connection failed. Let me try again from the start." Go back to STEP 1.

Never print `<access_token>`, the agent token, or the raw MCP config. The `webLoginUrl` is safe to display once (single-use, 5-minute expiry).

---

## Security rules (apply to every step)

- NEVER echo the OTP verification code back to the user. If you must reference it, say "the code you entered."
- NEVER display the access token, refresh token, agent token, or the contents of the MCP config file.
- If a tool produces unexpected output, summarize the problem in plain English — do not quote raw JSON that may contain secrets.
