"""Data MCP tools."""

from pathlib import Path
from typing import Optional
from . import mcp
from ..client import brain_client
from ..utils import expand_nested_data, save_flat_csv


@mcp.tool()
async def get_datasets(
    instrument_type: str = "EQUITY",
    region: str = "USA",
    delay: int = 1,
    universe: str = "TOP3000",
    theme: str = "false",
    search: Optional[str] = None,
    output_path: Optional[str] = None,
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
        Markdown summary with saved CSV path
    """
    response = await brain_client.get_datasets(instrument_type, region, delay, universe, theme, search)
    rows = expand_nested_data(response.model_dump().get("results", []), preserve_original=True)
    target = (
        Path(output_path)
        if output_path
        else Path("assets") / "data" / f"datasets_{region.lower()}_{universe.lower()}.csv"
    )
    col_count = save_flat_csv(rows, target)
    return (
        "Saved datasets CSV\n"
        f"- path: `{target}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- columns: `{col_count}`\n"
        f"- total_count: `{response.count}`\n"
        f"- preview:\n```text\n{response}\n```"
    )


@mcp.tool()
async def get_datafields(
    instrument_type: str = "EQUITY",
    region: str = "USA",
    delay: int = 1,
    universe: str = "TOP3000",
    theme: str = "false",
    dataset_id: Optional[str] = None,
    data_type: str = "ALL",
    search: Optional[str] = None,
    output_path: Optional[str] = None,
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
        Markdown summary with saved CSV path
    """
    response = await brain_client.get_datafields(
        instrument_type, region, delay, universe, theme, dataset_id, data_type, search
    )
    rows = expand_nested_data(response.model_dump().get("results", []), preserve_original=True)
    target = (
        Path(output_path)
        if output_path
        else Path("assets") / "data" / f"datafields_{region.lower()}_{universe.lower()}_{data_type.lower()}.csv"
    )
    col_count = save_flat_csv(rows, target)
    return (
        "Saved datafields CSV\n"
        f"- path: `{target}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- columns: `{col_count}`\n"
        f"- total_count: `{response.count}`\n"
        f"- preview:\n```text\n{response}\n```"
    )
