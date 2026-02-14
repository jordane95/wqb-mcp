"""MCP tool definitions for WorldQuant BRAIN platform."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "brain-platform-mcp",
    "A server for interacting with the WorldQuant BRAIN platform",
)

# Import tool modules to register @mcp.tool() decorators via side-effect
from . import (  # noqa: F401, E402
    auth_tools,
    simulation_tools,
    alpha_tools,
    correlation_tools,
    data_tools,
    community_tools,
    user_tools,
    forum_tools,
    operators_tools,
)
