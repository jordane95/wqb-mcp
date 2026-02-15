"""Operators MCP tools."""

from . import mcp
from ..client import brain_client


@mcp.tool()
async def get_operators():
    """
    Get available operators for alpha creation.

    Returns:
        Dictionary containing operators list and count
    """
    return str(await brain_client.get_operators())


@mcp.tool()
async def run_selection(
    selection: str,
    instrument_type: str = "EQUITY",
    region: str = "USA",
    delay: int = 1,
    selection_limit: int = 1000,
    selection_handling: str = "POSITIVE",
):
    """
    Run a selection query to filter instruments.

    Args:
        selection: Selection criteria
        instrument_type: Type of instruments
        region: Geographic region
        delay: Delay setting
        selection_limit: Maximum number of results
        selection_handling: How to handle selection results

    Returns:
        Selection results
    """
    return str(await brain_client.run_selection(
        selection, instrument_type, region, delay, selection_limit, selection_handling
    ))


@mcp.tool()
async def get_platform_setting_options():
    """Discover valid simulation setting options (instrument types, regions, delays, universes, neutralization).

    Use this when a simulation request might contain an invalid/mismatched setting. If an AI or user supplies
    incorrect parameters (e.g., wrong region for an instrument type), call this tool to retrieve the authoritative
    option sets and correct the inputs before proceeding.

    Returns:
        A structured list of valid combinations and choice lists to validate or fix simulation settings.
    """
    return str(await brain_client.get_platform_setting_options())
