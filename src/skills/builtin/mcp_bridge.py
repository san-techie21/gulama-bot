"""
MCP (Model Context Protocol) bridge skill for Gulama.

Implements both MCP Server (expose Gulama skills to other agents) and
MCP Client (consume external MCP servers as tools).

This makes Gulama interoperable with Claude Desktop, Cursor, Windsurf,
and any other MCP-compatible AI tool.

MCP Protocol: https://modelcontextprotocol.io/
Transport: stdio (for local) and SSE (for remote)

Requires: pip install mcp
"""

from __future__ import annotations

from typing import Any

from src.security.policy_engine import ActionType
from src.skills.base import BaseSkill, SkillMetadata, SkillResult
from src.utils.logging import get_logger

logger = get_logger("mcp_bridge")


class MCPBridgeSkill(BaseSkill):
    """
    MCP Bridge — connect to external MCP servers and expose Gulama as one.

    Actions:
    - list_servers: List configured MCP servers
    - connect: Connect to an MCP server
    - call_tool: Call a tool on a connected MCP server
    - list_tools: List tools from a connected MCP server
    - read_resource: Read a resource from a connected MCP server
    """

    def __init__(self) -> None:
        self._connections: dict[str, Any] = {}  # server_name -> client session
        self._server_configs: dict[str, dict[str, Any]] = {}

    def get_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="mcp",
            description="Connect to external MCP servers and call their tools",
            version="1.0.0",
            author="gulama",
            required_actions=[ActionType.NETWORK_REQUEST, ActionType.SKILL_EXECUTE],
            is_builtin=True,
        )

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "mcp",
                "description": (
                    "MCP (Model Context Protocol) bridge. Connect to external AI tool servers. "
                    "Actions: list_servers, connect, list_tools, call_tool, read_resource"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "list_servers",
                                "connect",
                                "list_tools",
                                "call_tool",
                                "read_resource",
                            ],
                            "description": "MCP action to perform",
                        },
                        "server_name": {
                            "type": "string",
                            "description": "Name of the MCP server to interact with",
                        },
                        "command": {
                            "type": "string",
                            "description": "Command to launch MCP server (for connect with stdio transport)",
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Arguments for the server command",
                        },
                        "url": {
                            "type": "string",
                            "description": "SSE URL for remote MCP server (for connect with SSE transport)",
                        },
                        "tool_name": {
                            "type": "string",
                            "description": "Name of the tool to call (for call_tool action)",
                        },
                        "tool_args": {
                            "type": "object",
                            "description": "Arguments for the tool call (for call_tool action)",
                        },
                        "resource_uri": {
                            "type": "string",
                            "description": "URI of the resource to read (for read_resource action)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, **kwargs: Any) -> SkillResult:
        """Execute an MCP action."""
        action = kwargs.get("action", "list_servers")

        dispatch = {
            "list_servers": self._list_servers,
            "connect": self._connect,
            "list_tools": self._list_tools,
            "call_tool": self._call_tool,
            "read_resource": self._read_resource,
        }

        handler = dispatch.get(action)
        if not handler:
            return SkillResult(
                success=False,
                output="",
                error=f"Unknown MCP action: {action}",
            )

        try:
            return await handler(**{k: v for k, v in kwargs.items() if k != "action"})
        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="MCP SDK not installed. Run: pip install mcp",
            )
        except Exception as e:
            logger.error("mcp_error", action=action, error=str(e))
            return SkillResult(success=False, output="", error=f"MCP error: {str(e)[:300]}")

    async def _list_servers(self, **_: Any) -> SkillResult:
        """List configured and connected MCP servers."""
        if not self._connections and not self._server_configs:
            return SkillResult(
                success=True,
                output="No MCP servers configured. Use 'connect' to add one.",
            )

        lines = []
        for name, config in self._server_configs.items():
            connected = name in self._connections
            transport = config.get("transport", "stdio")
            status = "connected" if connected else "disconnected"
            lines.append(f"  {name} [{transport}] — {status}")

        for name in self._connections:
            if name not in self._server_configs:
                lines.append(f"  {name} [active] — connected")

        return SkillResult(success=True, output="MCP Servers:\n" + "\n".join(lines))

    async def _connect(
        self,
        server_name: str = "",
        command: str = "",
        args: list[str] | None = None,
        url: str = "",
        **_: Any,
    ) -> SkillResult:
        """Connect to an MCP server via stdio or SSE."""
        if not server_name:
            return SkillResult(success=False, output="", error="server_name is required")

        if server_name in self._connections:
            return SkillResult(success=True, output=f"Already connected to '{server_name}'")

        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError:
            return SkillResult(
                success=False,
                output="",
                error="MCP SDK not installed. Run: pip install mcp",
            )

        if url:
            # SSE transport
            try:
                from mcp.client.sse import sse_client

                sse_transport = sse_client(url)
                read_stream, write_stream = await sse_transport.__aenter__()
                session = ClientSession(read_stream, write_stream)
                await session.__aenter__()
                await session.initialize()

                self._connections[server_name] = {
                    "session": session,
                    "transport": sse_transport,
                    "type": "sse",
                }
                self._server_configs[server_name] = {"transport": "sse", "url": url}

                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools] if tools.tools else []

                return SkillResult(
                    success=True,
                    output=f"Connected to '{server_name}' via SSE. Tools: {', '.join(tool_names) or 'none'}",
                    metadata={"server": server_name, "tools": tool_names},
                )
            except Exception as e:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"SSE connection failed: {str(e)[:200]}",
                )

        elif command:
            # stdio transport
            try:
                server_params = StdioServerParameters(
                    command=command,
                    args=args or [],
                )

                stdio_transport = stdio_client(server_params)
                read_stream, write_stream = await stdio_transport.__aenter__()
                session = ClientSession(read_stream, write_stream)
                await session.__aenter__()
                await session.initialize()

                self._connections[server_name] = {
                    "session": session,
                    "transport": stdio_transport,
                    "type": "stdio",
                }
                self._server_configs[server_name] = {
                    "transport": "stdio",
                    "command": command,
                    "args": args or [],
                }

                tools = await session.list_tools()
                tool_names = [t.name for t in tools.tools] if tools.tools else []

                return SkillResult(
                    success=True,
                    output=f"Connected to '{server_name}' via stdio. Tools: {', '.join(tool_names) or 'none'}",
                    metadata={"server": server_name, "tools": tool_names},
                )
            except Exception as e:
                return SkillResult(
                    success=False,
                    output="",
                    error=f"Stdio connection failed: {str(e)[:200]}",
                )

        return SkillResult(
            success=False,
            output="",
            error="Either 'command' (for stdio) or 'url' (for SSE) is required",
        )

    async def _list_tools(self, server_name: str = "", **_: Any) -> SkillResult:
        """List tools available on a connected MCP server."""
        if not server_name:
            return SkillResult(success=False, output="", error="server_name is required")

        conn = self._connections.get(server_name)
        if not conn:
            return SkillResult(
                success=False,
                output="",
                error=f"Not connected to '{server_name}'. Connect first.",
            )

        session = conn["session"]
        tools = await session.list_tools()

        if not tools.tools:
            return SkillResult(success=True, output=f"No tools on '{server_name}'")

        lines = []
        for tool in tools.tools:
            desc = tool.description[:80] if tool.description else "No description"
            lines.append(f"  {tool.name}: {desc}")

        return SkillResult(
            success=True,
            output=f"Tools on '{server_name}':\n" + "\n".join(lines),
            metadata={"tool_count": len(tools.tools)},
        )

    async def _call_tool(
        self,
        server_name: str = "",
        tool_name: str = "",
        tool_args: dict[str, Any] | None = None,
        **_: Any,
    ) -> SkillResult:
        """Call a tool on a connected MCP server."""
        if not server_name:
            return SkillResult(success=False, output="", error="server_name is required")
        if not tool_name:
            return SkillResult(success=False, output="", error="tool_name is required")

        conn = self._connections.get(server_name)
        if not conn:
            return SkillResult(
                success=False,
                output="",
                error=f"Not connected to '{server_name}'",
            )

        session = conn["session"]
        result = await session.call_tool(tool_name, tool_args or {})

        # Extract text content from result
        output_parts = []
        for content_block in result.content:
            if hasattr(content_block, "text"):
                output_parts.append(content_block.text)
            elif hasattr(content_block, "data"):
                output_parts.append(f"[Binary data: {len(content_block.data)} bytes]")

        output = "\n".join(output_parts) if output_parts else "(No output)"

        return SkillResult(
            success=not result.isError if hasattr(result, "isError") else True,
            output=output,
            metadata={"server": server_name, "tool": tool_name},
        )

    async def _read_resource(
        self,
        server_name: str = "",
        resource_uri: str = "",
        **_: Any,
    ) -> SkillResult:
        """Read a resource from a connected MCP server."""
        if not server_name:
            return SkillResult(success=False, output="", error="server_name is required")
        if not resource_uri:
            return SkillResult(success=False, output="", error="resource_uri is required")

        conn = self._connections.get(server_name)
        if not conn:
            return SkillResult(
                success=False,
                output="",
                error=f"Not connected to '{server_name}'",
            )

        session = conn["session"]
        result = await session.read_resource(resource_uri)

        output_parts = []
        for content_block in result.contents:
            if hasattr(content_block, "text"):
                output_parts.append(content_block.text)

        output = "\n".join(output_parts) if output_parts else "(No content)"

        return SkillResult(
            success=True,
            output=output,
            metadata={"server": server_name, "uri": resource_uri},
        )

    async def cleanup(self) -> None:
        """Disconnect from all MCP servers."""
        for name, conn in self._connections.items():
            try:
                session = conn["session"]
                transport = conn["transport"]
                await session.__aexit__(None, None, None)
                await transport.__aexit__(None, None, None)
                logger.info("mcp_disconnected", server=name)
            except Exception as e:
                logger.warning("mcp_cleanup_error", server=name, error=str(e))
        self._connections.clear()
