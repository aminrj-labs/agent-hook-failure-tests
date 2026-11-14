import os
os.environ["CREWAI_DISABLE_TELEMETRY"]="true"; os.environ["OTEL_SDK_DISABLED"]="true"
import crewai.hooks as H
print("HookAborted exported from crewai.hooks:", hasattr(H, "HookAborted"))
from crewai.hooks import before_tool_call
from crewai.hooks.dispatch import HookAborted
from crewai.tools import tool
from crewai.agents.parser import AgentAction
from crewai.utilities.i18n import I18N
from crewai.utilities.tool_utils import execute_tool_and_check_finality
EX=[]
@tool("send_email")
def send_email(to: str) -> str:
    """Send an email."""
    EX.append(to); return "sent"
def check(ctx): raise RuntimeError("policy service unreachable")
@before_tool_call
def policy(ctx):
    try:
        allowed = check(ctx)
    except Exception as e:
        raise HookAborted(f"policy check failed: {e}")
    if not allowed:
        raise HookAborted("denied by policy")
a=AgentAction(thought="",tool="send_email",tool_input='{"to":"x"}',text='Action: send_email\nAction Input: {"to": "x"}')
r=execute_tool_and_check_finality(a,[send_email.to_structured_tool()],I18N())
print("fix snippet: tool_executed=", bool(EX), "result:", r.result)
