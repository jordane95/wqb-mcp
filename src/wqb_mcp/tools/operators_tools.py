"""Operators MCP tools."""

from pathlib import Path
from typing import Optional

from . import mcp
from ..client import brain_client
from ..utils import expand_nested_data, save_flat_csv


@mcp.tool()
async def get_operators(output_path: Optional[str] = None):
    """
    Get available operators for alpha creation.

    Returns:
        Dictionary containing operators list and count
    """
    response = await brain_client.get_operators()
    rows = expand_nested_data(
        [op.model_dump(mode="json", exclude_none=True) for op in response.operators],
        preserve_original=True,
    )
    target = Path(output_path) if output_path else Path("assets") / "operators" / "operators.csv"
    col_count = save_flat_csv(rows, target)
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


@mcp.tool()
async def get_platform_setting_options():
    """Discover valid simulation setting options (instrument types, regions, delays, universes, neutralization).

    Use this when a simulation request might contain an invalid/mismatched setting. If an AI or user supplies
    incorrect parameters (e.g., wrong region for an instrument type), call this tool to retrieve the authoritative
    option sets and correct the inputs before proceeding.

    Returns:
        A structured list of valid combinations and choice lists to validate or fix simulation settings.
    """
    response = await brain_client.get_platform_setting_options()

    # Build flat rows for CSV: one row per combination with full lists
    rows = []
    for combo in response.instrument_options:
        rows.append({
            "instrument_type": combo.instrument_type,
            "region": combo.region,
            "delay": combo.delay,
            "universes": "|".join(combo.universe),
            "neutralizations": "|".join(combo.neutralization),
            "universe_count": len(combo.universe),
            "neutralization_count": len(combo.neutralization),
        })

    target = Path("assets") / "data" / "platform_setting_options.csv"
    col_count = save_flat_csv(rows, target)

    return (
        f"{response}\n\n"
        f"Full results saved to CSV:\n"
        f"- csv_path: `{target}`\n"
        f"- csv_rows: `{len(rows)}`\n"
        f"- csv_columns: `{col_count}`"
    )
