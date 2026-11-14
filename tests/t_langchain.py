"""Fail-closed tests for LangChain 1.x create_agent (LangGraph runtime). No network: fake model."""
import asyncio, importlib.metadata as md
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.tools import tool

EXECUTED = []

@tool
def send_email(to: str) -> str:
    """Send an email."""
    EXECUTED.append(to)
    return "sent"

class Fake(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kw):
        return self

def model():
    return Fake(responses=[
        AIMessage(content="", tool_calls=[{"name": "send_email", "args": {"to": "attacker@example.com"}, "id": "c1"}]),
        AIMessage(content="done"),
    ])

class Raises(AgentMiddleware):
    def wrap_tool_call(self, request, handler):
        raise RuntimeError("policy service unreachable")

class Hangs(AgentMiddleware):
    async def awrap_tool_call(self, request, handler):
        await asyncio.sleep(30)
        return await handler(request)

class Blocks(AgentMiddleware):
    def wrap_tool_call(self, request, handler):
        from langchain_core.messages import ToolMessage
        return ToolMessage(content="blocked by policy", tool_call_id=request.tool_call["id"])

class CbRaises(BaseCallbackHandler):
    def on_tool_start(self, *a, **k):
        raise RuntimeError("policy service unreachable")

class CbRaisesStrict(CbRaises):
    raise_error = True

def run(name, middleware=(), callbacks=None):
    EXECUTED.clear()
    agent = create_agent(model(), tools=[send_email], middleware=list(middleware))
    out = "completed"
    try:
        r = agent.invoke({"messages": [{"role": "user", "content": "go"}]}, config={"callbacks": callbacks or []})
        tm = [m for m in r["messages"] if m.type == "tool"]
        if tm: out += f"; tool message to model: {tm[0].content[:70]!r}"
    except Exception as e:
        out = f"run raised {type(e).__name__}: {str(e)[:70]}"
    print(f"{name:<44} tool_executed={bool(EXECUTED)!s:<5} {out}")

async def run_async_hang():
    EXECUTED.clear()
    agent = create_agent(model(), tools=[send_email], middleware=[Hangs()])
    try:
        await asyncio.wait_for(agent.ainvoke({"messages": [{"role": "user", "content": "go"}]}), 3)
        out = "completed"
    except asyncio.TimeoutError:
        out = "no framework timeout; still blocked after 3s"
    print(f"{'middleware awrap_tool_call hangs (30s)':<44} tool_executed={bool(EXECUTED)!s:<5} {out}")

print("langchain", md.version("langchain"), "langgraph", md.version("langgraph"), "langchain-core", md.version("langchain-core"))
run("baseline: no middleware")
run("middleware wrap_tool_call returns block", [Blocks()])
run("middleware wrap_tool_call raises", [Raises()])
asyncio.run(run_async_hang())
run("callback on_tool_start raises (default)", callbacks=[CbRaises()])
run("callback on_tool_start raises (raise_error)", callbacks=[CbRaisesStrict()])
