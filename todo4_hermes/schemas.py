"""LLM-facing tool schemas. The description drives when the LLM picks each tool."""

REGISTER = {
    "name": "todo4_register",
    "description": (
        "Start Todo4 onboarding by sending a one-time verification code to the "
        "user's email. Call this when the user asks to sign up for, install, "
        "connect, or get started with Todo4. Always call todo4_verify_otp next."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The user's email address.",
            },
        },
        "required": ["email"],
    },
}

VERIFY_OTP = {
    "name": "todo4_verify_otp",
    "description": (
        "Verify the 6-digit code the user received by email. On success, returns "
        "an ephemeral accessToken — immediately pass it to todo4_connect. Do not "
        "log, echo, or persist the token."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "Email used in todo4_register."},
            "code": {"type": "string", "description": "6-digit verification code."},
        },
        "required": ["email", "code"],
    },
}

CONNECT = {
    "name": "todo4_connect",
    "description": (
        "Register this Hermes instance as a Todo4 agent and wire up MCP. Writes "
        "the MCP server entry into the Hermes YAML config and stores the agent "
        "token in ~/.hermes/.env. Call after todo4_verify_otp succeeds, passing "
        "the returned accessToken. The user must run /reload-mcp after."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "accessToken": {
                "type": "string",
                "description": "Access token returned by todo4_verify_otp.",
            },
            "agentName": {
                "type": "string",
                "description": "Display name for this agent (e.g. 'Hermes'). Defaults to 'Hermes'.",
            },
        },
        "required": ["accessToken"],
    },
}

STATUS = {
    "name": "todo4_status",
    "description": (
        "Check whether Todo4 is configured for this Hermes install: whether the "
        "agent token is present, the MCP server entry exists, and the Todo4 API "
        "is reachable. Use this to self-diagnose before attempting MCP calls or "
        "re-running onboarding."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}
