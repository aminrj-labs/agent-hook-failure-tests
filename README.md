# agent-hook-failure-tests

What happens to a tool call when the security hook in front of it fails?

[OWASP Securing Agentic Applications V2](https://genai.owasp.org/resource/securing-agentic-applications-v2/) (November 2026), section 3.3.7, says that when a hook can't reach a decision ("an error, a timeout, or an unreachable enforcement service") the action "must fail closed", because "a hook that fails open can be bypassed by anyone able to make it fail." The guide lists 18 hook points. It doesn't say which frameworks meet that rule.

These tests check the pre-tool hook (`toolCallRequest` in the guide's terms) in five Python agent frameworks. Each test puts one tool that records whether it ran behind a hook that (a) denies, (b) raises, (c) hangs. The question each time: did the tool run?

Write-up: [When a Pre-Tool Hook Crashes, CrewAI and the Claude Agent SDK Run the Tool Anyway](https://aminrj.com/posts/agent-hooks-fail-open/) (4 December 2026).

## Results (14 November 2026)

| Framework and hook | Hook raises | Hook hangs |
|---|---|---|
| CrewAI 1.15.41, `before_tool_call` | **tool runs** (stated design) | not tested |
| CrewAI 1.15.41, `after_tool_call` redaction | **unredacted result to model** | n/a |
| Claude Agent SDK 0.2.182, `PreToolUse` (default) | **tool runs** | blocked at timeout |
| Claude Agent SDK 0.2.182, `PreToolUse`, `on_failure="block"` | blocked | blocked at timeout |
| LangChain 1.5.0, middleware `wrap_tool_call` | blocked | blocked, no timeout |
| LangChain 1.5.0, callback `on_tool_start` (default) | **tool runs** | not tested |
| LangChain 1.5.0, callback with `raise_error = True` | blocked | not tested |
| OpenAI Agents SDK 0.24.0, `tool_input_guardrail` | blocked | blocked, no timeout |
| OpenAI Agents SDK 0.24.0, `RunHooks.on_tool_start` | blocked | not tested |
| MCP Python SDK 2.3.0 (server), `intercept_tool_call` / `ServerMiddleware` | blocked | blocked, no timeout |

Full output: [`results/2026-11-14.md`](results/2026-11-14.md). "Blocked, no timeout" means the run waited on the hook indefinitely: fail closed, but the agent stalls with the policy service.

## Tests

| File | Framework | Model |
|---|---|---|
| `tests/t_openai_agents.py` | openai-agents | `agents.testing.ScriptedModel`, no network |
| `tests/t_langchain.py` | langchain / langgraph / langchain-core | fake chat model, no network |
| `tests/t_crewai_latest.py` | crewai 1.15.41 | none: drives `execute_tool_and_check_finality` directly |
| `tests/t_crewai_fix.py` | crewai 1.15.41 | checks the fail-closed workaround (raise `HookAborted`) |
| `tests/t_crewai_1_6_1.py` | crewai 1.6.1 | older behaviour: one raising hook also skipped later hooks |
| `tests/t_mcp_server.py` | mcp (Python SDK, server side) | none: in-memory client |
| `tests/t_claude_sdk.py`, `tests/t_claude_hang_diag.py` | claude-agent-sdk | live `claude-haiku-4-5`, Bash pre-allowed, `bypassPermissions` |

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
python3 -m venv .crew && .crew/bin/pip install -r requirements-crewai.txt   # separate: a shared install resolves crewai to 1.6.1
mkdir -p tests/cwd
for t in t_openai_agents t_langchain t_mcp_server; do .venv/bin/python -I tests/$t.py; done
.crew/bin/python -I tests/t_crewai_latest.py && .crew/bin/python -I tests/t_crewai_fix.py
.venv/bin/python -I tests/t_claude_sdk.py   # needs Claude Code authentication; makes a few Haiku calls
```

The Claude Agent SDK test runs a real `touch` command through Bash inside `tests/cwd/`. Everything else is offline.

## Limits

- One hook point of the guide's 18, plus the post-tool hook for CrewAI.
- Python packages only. TypeScript SDKs and Claude Code's `settings.json` command hooks are not covered.
- The Claude Agent SDK "tool runs" result is under `bypassPermissions` with Bash pre-allowed. A failed hook counts as "no decision", so a stricter permission mode may prompt instead.
- Versions move. Re-run before relying on these results.

Corrections and results for other frameworks are welcome as issues or pull requests.

## License

MIT
