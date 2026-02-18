"""Alpha MCP tools."""

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from . import mcp
from ..client import brain_client


@mcp.tool()
async def get_alpha_details(alpha_id: str):
    """
    Get detailed information about an alpha.

    Args:
        alpha_id: The ID of the alpha to retrieve

    Returns:
        Detailed alpha information
    """
    return str(await brain_client.get_alpha_details(alpha_id))


@mcp.tool()
async def get_user_alphas(
    stage: str = "IS",
    limit: int = 30,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    submission_start_date: Optional[str] = None,
    submission_end_date: Optional[str] = None,
    order: Optional[str] = None,
    hidden: Optional[bool] = None,
    sharpe_min: Optional[float] = None,
    sharpe_max: Optional[float] = None,
    fitness_min: Optional[float] = None,
    fitness_max: Optional[float] = None,
    tag: Optional[str] = None,
    extra_filters: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
):
    """
    Get user's alphas with advanced filtering, pagination, and sorting.

    This tool retrieves a list of your alphas, allowing for detailed filtering based on stage,
    creation date, and visibility. It also supports pagination and custom sorting.

    Common named params are provided for convenience. For any other platform-supported filter,
    use extra_filters with the raw API query parameter names (discoverable via browser dev-tools).

    Args:
        stage (str): "IS" (In-Sample/unsubmitted) or "OS" (Out-of-Sample/submitted). Defaults to "IS".
        limit (int): Max alphas to return. Defaults to 30.
        offset (int): Number of alphas to skip (pagination). Defaults to 0.
        start_date (Optional[str]): Earliest creation date. Example: "2023-01-01T00:00:00Z".
        end_date (Optional[str]): Latest creation date. Example: "2023-12-31T23:59:59Z".
        submission_start_date (Optional[str]): Earliest submission date (OS only).
        submission_end_date (Optional[str]): Latest submission date (OS only).
        order (Optional[str]): Sort order. Prefix with "-" for descending.
            Examples: "-is.sharpe", "-is.fitness", "dateCreated".
        hidden (Optional[bool]): True=only hidden, False=only visible, None=both.
        sharpe_min (Optional[float]): Minimum IS Sharpe ratio (is.sharpe>).
        sharpe_max (Optional[float]): Maximum IS Sharpe ratio (is.sharpe<). Useful for finding
            reverse signals, e.g. sharpe_max=-4 to find strong negative alphas to flip.
        fitness_min (Optional[float]): Minimum IS fitness (is.fitness>).
        fitness_max (Optional[float]): Maximum IS fitness (is.fitness<). Useful for reverse signals.
        tag (Optional[str]): Filter by a single tag name.
        extra_filters (Optional[Dict[str, Any]]): Arbitrary additional query parameters
            for any platform-supported filter not covered by named params.
            Examples:
              {"is.turnover>": 0.01, "is.turnover<": 0.5}  - turnover range
              {"is.longCount>": 9, "is.shortCount>": 9}  - min instrument counts
              {"settings.decay>": 5}  - min decay (integer)
              {"settings.neutralization": "SUBINDUSTRY"}  - specific neutralization
              {"status": "UNSUBMITTED"}  - filter by status
        output_path (Optional[str]): Custom CSV output path. Defaults to assets/alphas/user_alphas_{stage}.csv.

    Returns:
        Alpha list summary (top 3) with CSV path for full results.
    """
    resp = await brain_client.get_user_alphas(
        stage=stage, limit=limit, offset=offset, start_date=start_date,
        end_date=end_date, submission_start_date=submission_start_date,
        submission_end_date=submission_end_date, order=order, hidden=hidden,
        sharpe_min=sharpe_min, sharpe_max=sharpe_max,
        fitness_min=fitness_min, fitness_max=fitness_max,
        tag=tag, extra_filters=extra_filters,
    )
    if output_path:
        csv_path = Path(output_path)
    else:
        parts = [stage.lower()]
        if sharpe_min is not None:
            parts.append(f"sh{sharpe_min}")
        if sharpe_max is not None:
            parts.append(f"shx{sharpe_max}")
        if fitness_min is not None:
            parts.append(f"ft{fitness_min}")
        if fitness_max is not None:
            parts.append(f"ftx{fitness_max}")
        if tag:
            parts.append(f"t_{tag}")
        if order:
            parts.append(order.replace("-", "d_").replace(".", "_"))
        if extra_filters:
            for k, v in sorted(extra_filters.items()):
                parts.append(f"{k.replace('.', '_').replace('>', 'gt').replace('<', 'lt')}_{v}")
        slug = "_".join(str(p) for p in parts)
        # sanitize for filesystem
        slug = slug.replace("/", "_").replace(" ", "_")[:120]
        csv_path = Path("assets") / "alphas" / f"user_alphas_{slug}.csv"
    saved = resp.save_csv(csv_path)
    return f"{resp.summary()}\n\nFull results saved to: {saved}"


@mcp.tool()
async def submit_alpha(alpha_id: str):
    """
    Submit an alpha for production.

    Use this when your alpha is ready for production deployment.

    Args:
        alpha_id: The ID of the alpha to submit

    Returns:
        Submission result
    """
    return str(await brain_client.submit_alpha(alpha_id))


@mcp.tool()
async def check_alpha(alpha_id: str):
    """Check if an alpha is ready for submission using the platform's native check endpoint.

    Runs server-side checks (Sharpe, turnover, correlation, pyramid, themes, etc.)
    and polls until results are available. This is the same check the platform UI runs.

    Args:
        alpha_id: The ID of the alpha to check.
    """
    return str(await brain_client.check_alpha(alpha_id))


@mcp.tool()
async def set_alpha_properties(alpha_id: str, name: Optional[str] = None,
                               color: Optional[str] = None, tags: Optional[List[str]] = None,
                               selection_desc: Optional[str] = None, combo_desc: Optional[str] = None,
                               regular_desc: Optional[str] = None):
    """Update alpha properties (name, color, tags, descriptions).

    For Power Pool eligibility, regular_desc must follow this format:
        Idea: <your idea>
        Rationale for data used: <why this data>
        Rationale for operators used: <why these operators>

    The full description should be at least 100 characters total to pass POWER_POOL_DESCRIPTION_LENGTH check.
    """
    return str(await brain_client.set_alpha_properties(alpha_id, name, color, tags, selection_desc, combo_desc, regular_desc))


@mcp.tool()
async def get_record_set_data(
    alpha_id: str,
    record_set_name: Literal["pnl", "sharpe", "turnover", "daily-pnl", "yearly-stats"],
    output_path: Optional[str] = None,
):
    """Fetch a record set, save it locally as CSV, and return markdown summary."""
    data = await brain_client.get_record_set_data(alpha_id, record_set_name)
    if output_path:
        target = Path(output_path)
    else:
        safe_name = record_set_name.replace("-", "_")
        target = Path("assets") / "recordsets" / f"{alpha_id}_{safe_name}.csv"

    saved = data.save_csv(target)
    headers = [p.name for p in data.schema_.properties]
    headers_text = ", ".join(headers) if headers else "(no schema properties)"
    return (
        f"Saved recordset CSV\n"
        f"- alpha_id: `{alpha_id}`\n"
        f"- record_set: `{record_set_name}`\n"
        f"- path: `{saved}`\n"
        f"- rows: `{len(data.records)}`\n"
        f"- columns: `{len(data.schema_.properties)}`\n"
        f"- headers: `{headers_text}`"
    )


@mcp.tool()
async def performance_comparison(alpha_id: str, team_id: Optional[str] = None,
                                 competition: Optional[str] = None):
    """Get performance comparison data for an alpha."""
    return str(await brain_client.performance_comparison(alpha_id, team_id, competition))
