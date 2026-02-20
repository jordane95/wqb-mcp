"""Community MCP tools."""

from typing import Optional

from . import mcp
from ..client import brain_client


@mcp.tool()
async def get_events():
    """
    Get available events and competitions.

    Returns:
        Available events and competitions
    """
    return str(await brain_client.get_events())


@mcp.tool()
async def get_leaderboard(user_id: Optional[str] = None):
    """
    Get leaderboard data.

    Args:
        user_id: Optional user ID to filter results

    Returns:
        Leaderboard data
    """
    return str(await brain_client.get_leaderboard(user_id))


@mcp.tool()
async def get_user_competitions(user_id: Optional[str] = None):
    """Get list of competitions that the user is participating in."""
    return str(await brain_client.get_user_competitions(user_id))


@mcp.tool()
async def get_competition_details(competition_id: str):
    """Get detailed information about a specific competition."""
    return str(await brain_client.get_competition_details(competition_id))


@mcp.tool()
async def get_competition_agreement(competition_id: str):
    """Get the rules, terms, and agreement for a specific competition."""
    return str(await brain_client.get_competition_agreement(competition_id))


@mcp.tool()
async def get_documentations(force_refresh: bool = False):
    """Get available documentations and learning materials."""
    return str(await brain_client.get_documentations(force_refresh=force_refresh))


@mcp.tool()
async def get_documentation_page(page_id: str, force_refresh: bool = False):
    """Retrieve detailed content of a specific documentation page/article."""
    return str(await brain_client.get_documentation_page(page_id, force_refresh=force_refresh))
