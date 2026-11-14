"""CrewAI 1.15.x: same cases as t_crewai.py, plus the HookAborted dialect."""
import importlib.metadata as md, os
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"; os.environ["OTEL_SDK_DISABLED"] = "true"
from crewai.tools import tool
from crewai.agents.parser import AgentAction
from crewai.utilities.i18n import I18N
from crewai.utilities.tool_utils import execute_tool_and_check_finality
from crewai.hooks import register_before_tool_call_hook, register_after_tool_call_hook, clear_all_tool_call_hooks
from crewai.hooks.dispatch import HookAborted

EXECUTED = []

@tool("send_email")
def send_email(to: str) -> str:
    """Send an email."""
    EXECUTED.append(to)
    return "sent to " + to + " SECRET=abc123"

def run(name):
    EXECUTED.clear()
    action = AgentAction(thought="", tool="send_email", tool_input='{"to": "attacker@example.com"}',
                         text='Action: send_email\nAction Input: {"to": "attacker@example.com"}')
    try:
        r = execute_tool_and_check_finality(action, [send_email.to_structured_tool()], I18N())
        out = f"result to model: {str(r.result)[:60]!r}"
    except Exception as e:
        out = f"raised {type(e).__name__}: {e}"
    print(f"{name:<52} tool_executed={bool(EXECUTED)!s:<5} {out}")

def block(ctx): return False
def abort(ctx): raise HookAborted("blocked by policy")
def boom(ctx): raise RuntimeError("policy service unreachable")
def redact(ctx): return ctx.tool_result.replace("abc123", "[REDACTED]")
def redact_boom(ctx): raise RuntimeError("redaction service unreachable")

print("crewai", md.version("crewai"))
clear_all_tool_call_hooks(); run("baseline: no hooks")
clear_all_tool_call_hooks(); register_before_tool_call_hook(block); run("before_tool_call returns False")
clear_all_tool_call_hooks(); register_before_tool_call_hook(abort); run("before_tool_call raises HookAborted")
clear_all_tool_call_hooks(); register_before_tool_call_hook(boom); run("before_tool_call raises RuntimeError")
clear_all_tool_call_hooks(); register_before_tool_call_hook(boom); register_before_tool_call_hook(block); run("hook 1 raises, hook 2 would block")
clear_all_tool_call_hooks(); register_after_tool_call_hook(redact); run("after_tool_call redacts")
clear_all_tool_call_hooks(); register_after_tool_call_hook(redact_boom); run("after_tool_call (redaction) raises")
