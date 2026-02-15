"""Data MCP tools."""

from typing import Any, Dict, List, Optional

from . import mcp
from ..client import brain_client


@mcp.tool()
async def get_datasets(
    instrument_type: str = "EQUITY",
    region: str = "USA",
    delay: int = 1,
    universe: str = "TOP3000",
    theme: str = "ALL",
    search: Optional[str] = None,
):
    """
    Get available datasets for research.

    Use this to discover what data is available for your alpha research.

    Args:
        instrument_type: Type of instruments (e.g., "EQUITY")
        region: Market region (e.g., "USA")
        delay: Data delay (0 or 1)
        universe: Universe of stocks (e.g., "TOP3000")
        theme: Theme filter

    Returns:
        Available datasets
    """
    return str(await brain_client.get_datasets(instrument_type, region, delay, universe, theme, search))


@mcp.tool()
async def get_datafields(
    instrument_type: str = "EQUITY",
    region: str = "USA",
    delay: int = 1,
    universe: str = "TOP3000",
    theme: str = "false",
    dataset_id: Optional[str] = None,
    data_type: str = "",
    search: Optional[str] = None,
):
    """
    Get available data fields for alpha construction.

    Use this to find specific data fields you can use in your alpha formulas.

    Args:
        instrument_type: Type of instruments (e.g., "EQUITY")
        region: Market region (e.g., "USA")
        delay: Data delay (0 or 1)
        universe: Universe of stocks (e.g., "TOP3000")
        theme: Theme filter
        dataset_id: Specific dataset ID to filter by
        data_type: Type of data (e.g., "MATRIX",'VECTOR','GROUP')
        search: Search term to filter fields

    Returns:
        Available data fields
    """
    return str(await brain_client.get_datafields(instrument_type, region, delay, universe, theme, dataset_id, data_type, search))


@mcp.tool()
async def expand_nested_data(data: List[Dict[str, Any]], preserve_original: bool = True):
    """Flatten complex nested data structures into tabular format."""
    return str(await brain_client.expand_nested_data(data, preserve_original))
