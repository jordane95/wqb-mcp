"""Alpha MCP tools."""

from pathlib import Path
from typing import List, Literal, Optional

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
):
    """
    Get user's alphas with advanced filtering, pagination, and sorting.

    This tool retrieves a list of your alphas, allowing for detailed filtering based on stage,
    creation date, submission date, and visibility. It also supports pagination and custom sorting.

    Args:
        stage (str): The stage of the alphas to retrieve.
            - "IS": In-Sample (alphas that have not been submitted).
            - "OS": Out-of-Sample (alphas that have been submitted).
            Defaults to "IS".
        limit (int): The maximum number of alphas to return in a single request.
            For example, `limit=50` will return at most 50 alphas. Defaults to 30.
        offset (int): The number of alphas to skip from the beginning of the list.
            Used for pagination. For example, `limit=50, offset=50` will retrieve alphas 51-100.
            Defaults to 0.
        start_date (Optional[str]): The earliest creation date for the alphas to be included.
            Filters for alphas created on or after this date.
            Example format: "2023-01-01T00:00:00Z".
        end_date (Optional[str]): The latest creation date for the alphas to be included.
            Filters for alphas created before this date.
            Example format: "2023-12-31T23:59:59Z".
        submission_start_date (Optional[str]): The earliest submission date for the alphas.
            Only applies to "OS" alphas. Filters for alphas submitted on or after this date.
            Example format: "2024-01-01T00:00:00Z".
        submission_end_date (Optional[str]): The latest submission date for the alphas.
            Only applies to "OS" alphas. Filters for alphas submitted before this date.
            Example format: "2024-06-30T23:59:59Z".
        order (Optional[str]): The sorting order for the returned alphas.
            Prefix with a hyphen (-) for descending order.
            Examples: "name" (sort by name ascending), "-dateSubmitted" (sort by submission date descending).
        hidden (Optional[bool]): Filter alphas based on their visibility.
            - `True`: Only return hidden alphas.
            - `False`: Only return non-hidden alphas.
            If not provided, both hidden and non-hidden alphas are returned.

    Returns:
        Dict[str, Any]: A dictionary containing a list of alpha details under the 'results' key,
        along with pagination information. If an error occurs, it returns a dictionary with an 'error' key.
    """
    return str(await brain_client.get_user_alphas(
        stage=stage, limit=limit, offset=offset, start_date=start_date,
        end_date=end_date, submission_start_date=submission_start_date,
        submission_end_date=submission_end_date, order=order, hidden=hidden
    ))


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
    """Update alpha properties (name, color, tags, descriptions)."""
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
