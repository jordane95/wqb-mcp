"""Operators MCP tools."""

from pathlib import Path
from typing import Optional

from . import mcp
from ..client import brain_client
from ..utils import save_csv


@mcp.tool()
async def get_operators(output_path: Optional[str] = None, force_refresh: bool = False):
    """
    Get available operators for alpha creation.

    Returns:
        Dictionary containing operators list and count
    """
    response = await brain_client.get_operators(force_refresh=force_refresh)
    rows = [op.model_dump(mode="json", exclude_none=True) for op in response.operators]
    target = Path(output_path) if output_path else Path("assets") / "operators" / "operators.csv"
    col_count = save_csv(rows, target)
    return (
        f"{response}\n"
        f"- csv_path: `{target}`\n"
        f"- csv_rows: `{len(rows)}`\n"
        f"- csv_columns: `{col_count}`"
    )


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
