"""Correlation MCP tools."""

from typing import Literal

from . import mcp
from ..client import brain_client
from ..client.correlation import CorrelationType


@mcp.tool()
async def check_correlation(
    alpha_id: str,
    correlation_type: str = "both",
    threshold: float = 0.7,
    mode: Literal["remote", "local"] = "remote",
    years: int = 4,
    force_refresh: bool = False,
):
    """Check alpha correlation against production alphas, self alphas, or both.

    Args:
        alpha_id: The ID of the alpha to check.
        correlation_type: Which correlations to check. Valid values: "prod", "self", "power-pool", "both" (prod+self), "all" (prod+self+power-pool).
        threshold: Correlation threshold (default 0.7). Alpha passes if max correlation is below this.
        mode: "remote" (BRAIN API correlation endpoint) or "local" (PnL-based local computation).
        years: Trailing years of returns used only when mode="local".
        force_refresh: Re-download all OS alpha details and PnL data (mode="local" only).
    """
    if correlation_type == "both":
        check_types = [CorrelationType.PROD, CorrelationType.SELF]
    elif correlation_type == "all":
        check_types = [CorrelationType.PROD, CorrelationType.SELF, CorrelationType.POWER_POOL]
    else:
        check_types = [CorrelationType(correlation_type)]

    if mode == "local":
        result = await brain_client.check_local_correlation(
            alpha_id=alpha_id,
            check_types=check_types,
            threshold=threshold,
            years=years,
            force_refresh=force_refresh,
        )
    else:
        result = await brain_client.check_correlation(alpha_id, check_types, threshold)

    return str(result)


# Deprecated: replaced by check_alpha in alpha_tools.py
# @mcp.tool()
async def get_submission_check(alpha_id: str, is_power_pool: bool = False):
    """Comprehensive pre-submission check.

    Args:
        alpha_id: The ID of the alpha to check.
        is_power_pool: If True, applies Power Pool correlation rules (threshold=0.5, 10% Sharpe rule).
    """
    return str(await brain_client.get_submission_check(alpha_id, is_power_pool=is_power_pool))
