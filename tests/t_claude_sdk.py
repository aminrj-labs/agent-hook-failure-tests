"""Fail-closed tests for Claude Agent SDK PreToolUse hooks. Live model (Haiku), Bash tool, bypassPermissions."""
import asyncio, os, sys, importlib.metadata as md, pathlib
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, AssistantMessage, ResultMessage

CWD = pathlib.Path(__file__).parent / "cwd"
MARK = CWD / "marker.txt"

async def raises(input_data, tool_use_id, context):
    raise RuntimeError("policy service unreachable")

async def hangs(input_data, tool_use_id, context):
    await asyncio.sleep(120)
    return {}

async def denies(input_data, tool_use_id, context):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": "blocked by policy"}}

async def run(name, hook=None, **mkw):
    if MARK.exists(): MARK.unlink()
    hooks = {"PreToolUse": [HookMatcher(matcher="Bash", hooks=[hook], **mkw)]} if hook else None
    opts = ClaudeAgentOptions(model="claude-haiku-4-5", cwd=str(CWD), allowed_tools=["Bash"],
                              permission_mode="bypassPermissions", hooks=hooks, max_turns=3,
                              setting_sources=[])
    err = ""
    try:
        async for m in query(prompt=f"Run exactly this Bash command and nothing else: touch {MARK}", options=opts):
            pass
    except Exception as e:
        err = f" (run raised {type(e).__name__}: {str(e)[:80]})"
    print(f"{name:<48} tool_executed={MARK.exists()!s:<5}{err}", flush=True)

async def main():
    print("claude-agent-sdk", md.version("claude-agent-sdk"))
    await run("baseline: no hook")
    await run("PreToolUse returns deny", denies)
    await run("PreToolUse raises, on_failure unset", raises)
    await run("PreToolUse raises, on_failure='block'", raises, on_failure="block")
    await run("PreToolUse hangs, timeout=5, on_failure unset", hangs, timeout=5)
    await run("PreToolUse hangs, timeout=5, on_failure='block'", hangs, timeout=5, on_failure="block")

asyncio.run(main())
