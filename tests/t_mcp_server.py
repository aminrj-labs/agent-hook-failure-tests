"""Fail-closed tests for MCP Python SDK server-side tools/call interception. In-memory client."""
import anyio, importlib.metadata as md
from mcp.client.client import Client
from mcp.server.mcpserver import MCPServer
from mcp.server.extension import Extension

EXECUTED = []

class Raises(Extension):
    identifier = "com.example/policy"
    async def intercept_tool_call(self, params, ctx, call_next):
        raise RuntimeError("policy service unreachable")

class Hangs(Extension):
    identifier = "com.example/policy-hang"
    async def intercept_tool_call(self, params, ctx, call_next):
        await anyio.sleep(30)
        return await call_next(ctx)

async def mw_raises(ctx, call_next):
    if ctx.method == "tools/call":
        raise RuntimeError("policy service unreachable")
    return await call_next(ctx)

def server(**kw):
    s = MCPServer("t", **kw)
    @s.tool()
    def send_email(to: str) -> str:
        """Send an email."""
        EXECUTED.append(to); return "sent"
    return s

async def run(name, **kw):
    EXECUTED.clear(); out = ""
    try:
        with anyio.fail_after(5):
            async with Client(server(**kw)) as c:
                r = await c.call_tool("send_email", {"to": "attacker@example.com"})
                out = f"isError={getattr(r, 'isError', getattr(r, 'is_error', None))} {str(r.content)[:70]}"
    except TimeoutError:
        out = "no SDK timeout; still blocked after 5s"
    except Exception as e:
        out = f"client got {type(e).__name__}: {str(e)[:70]}"
    print(f"{name:<40} tool_executed={bool(EXECUTED)!s:<5} {out}")

async def main():
    print("mcp", md.version("mcp"))
    await run("baseline")
    await run("Extension.intercept_tool_call raises", extensions=[Raises()])
    await run("Extension.intercept_tool_call hangs", extensions=[Hangs()])
    await run("ServerMiddleware raises on tools/call", middleware=[mw_raises])

anyio.run(main)
