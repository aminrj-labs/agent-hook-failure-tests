"""Fail-closed tests for OpenAI Agents SDK tool hooks. No network: ScriptedModel."""
import asyncio, sys
from agents import Agent, Runner, function_tool, RunHooks
from agents.tool_guardrails import tool_input_guardrail, ToolGuardrailFunctionOutput
from agents.testing import ScriptedModel, ModelStep, function_call, assistant_message
import agents

EXECUTED = []

def make_tool(guardrail=None):
    kw = {"tool_input_guardrails": [guardrail]} if guardrail else {}
    @function_tool(**kw)
    def send_email(to: str) -> str:
        """Send an email."""
        EXECUTED.append(to)
        return "sent"
    return send_email

def model():
    return ScriptedModel([
        ModelStep(output=[function_call("send_email", {"to": "attacker@example.com"}, call_id="c1")]),
        ModelStep(output=[assistant_message("done")]),
    ])

async def run(name, guardrail=None, hooks=None, timeout=None):
    EXECUTED.clear()
    agent = Agent(name="a", model=model(), tools=[make_tool(guardrail)])
    outcome = "completed"
    try:
        coro = Runner.run(agent, "go", hooks=hooks)
        if timeout:
            await asyncio.wait_for(coro, timeout)
        else:
            await coro
    except asyncio.TimeoutError:
        outcome = f"no SDK timeout; run still blocked after {timeout}s (outer wait_for cancelled it)"
    except Exception as e:
        outcome = f"run raised {type(e).__name__}: {str(e)[:80]}"
    print(f"{name:<38} tool_executed={bool(EXECUTED)!s:<5} {outcome}")

@tool_input_guardrail
def gr_reject(data):
    return ToolGuardrailFunctionOutput.reject_content("blocked")

@tool_input_guardrail
def gr_raises(data):
    raise RuntimeError("policy service unreachable")

@tool_input_guardrail
async def gr_hangs(data):
    await asyncio.sleep(30)
    return ToolGuardrailFunctionOutput.allow()

class RaisingHooks(RunHooks):
    async def on_tool_start(self, context, agent, tool):
        raise RuntimeError("policy service unreachable")

async def main():
    print("openai-agents", agents.__version__ if hasattr(agents, "__version__") else "")
    await run("baseline: no guardrail")
    await run("tool_input_guardrail -> reject_content", gr_reject)
    await run("tool_input_guardrail raises", gr_raises)
    await run("tool_input_guardrail hangs (30s)", gr_hangs, timeout=3)
    await run("RunHooks.on_tool_start raises", hooks=RaisingHooks())

asyncio.run(main())
