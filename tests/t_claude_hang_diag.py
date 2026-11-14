import asyncio, time, pathlib, sys
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, UserMessage, AssistantMessage, ResultMessage
CWD = pathlib.Path(__file__).parent / "cwd"; MARK = CWD / "marker.txt"
async def hangs(i, t, c):
    await asyncio.sleep(120); return {}
async def main(on_failure):
    if MARK.exists(): MARK.unlink()
    kw = {"on_failure": on_failure} if on_failure else {}
    opts = ClaudeAgentOptions(model="claude-haiku-4-5", cwd=str(CWD), allowed_tools=["Bash"], permission_mode="bypassPermissions",
        hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[hangs], timeout=5, **kw)]}, max_turns=2, setting_sources=[])
    t0 = time.time()
    try:
        async for m in query(prompt=f"Run exactly this Bash command and nothing else: touch {MARK}", options=opts):
            if isinstance(m, UserMessage) and isinstance(m.content, list):
                for b in m.content:
                    if getattr(b, "content", None) is not None: print(f"  t+{time.time()-t0:.0f}s tool_result:", str(b.content)[:160])
            if isinstance(m, ResultMessage): print(f"  t+{time.time()-t0:.0f}s result subtype={m.subtype}")
    except Exception as e: print("  raised", type(e).__name__, str(e)[:100])
    print(f"on_failure={on_failure} executed={MARK.exists()}")
asyncio.run(main(sys.argv[1] if len(sys.argv)>1 else None))
