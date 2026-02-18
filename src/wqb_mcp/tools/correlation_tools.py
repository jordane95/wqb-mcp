"""Correlation MCP tools."""

from . import mcp
from ..client import brain_client
from ..client.correlation import CorrelationType


@mcp.tool()
async def check_correlation(alpha_id: str, correlation_type: str = "both", threshold: float = 0.7):
    """Check alpha correlation against production alphas, self alphas, or both.

    Args:
        alpha_id: The ID of the alpha to check.
        correlation_type: Which correlations to check. Valid values: "prod", "self", "power-pool", "both" (prod+self), "all" (prod+self+power-pool).
        threshold: Correlation threshold (default 0.7). Alpha passes if max correlation is below this.
    """
    if correlation_type == "both":
        check_types = [CorrelationType.PROD, CorrelationType.SELF]
    elif correlation_type == "all":
        check_types = [CorrelationType.PROD, CorrelationType.SELF, CorrelationType.POWER_POOL]
    else:
        check_types = [CorrelationType(correlation_type)]
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
