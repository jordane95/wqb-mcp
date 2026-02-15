"""User MCP tools."""

from typing import Optional

from . import mcp
from ..client import brain_client


@mcp.tool()
async def get_user_profile(user_id: str = "self"):
    """
    Get user profile information.

    Args:
        user_id: User ID (default: "self" for current user)

    Returns:
        User profile data
    """
    return str(await brain_client.get_user_profile(user_id))


@mcp.tool()
async def get_messages(limit: Optional[int] = None, offset: int = 0):
    """
    Get messages for the current user with optional pagination.

    Args:
        limit: Maximum number of messages to return (e.g., 10 for top 10 messages)
        offset: Number of messages to skip (for pagination)

    Returns:
        Messages for the current user, optionally limited by count
    """
    return str(await brain_client.get_messages(limit, offset))


@mcp.tool()
async def get_user_activities(user_id: str, grouping: Optional[str] = None):
    """Get user activity diversity data."""
    return str(await brain_client.get_user_activities(user_id, grouping))


@mcp.tool()
async def get_pyramid_multipliers():
    """Get current pyramid multipliers showing BRAIN's encouragement levels."""
    return str(await brain_client.get_pyramid_multipliers())


@mcp.tool()
async def get_pyramid_alphas(start_date: Optional[str] = None,
                               end_date: Optional[str] = None):
    """Get user's current alpha distribution across pyramid categories."""
    return str(await brain_client.get_pyramid_alphas(start_date, end_date))


@mcp.tool()
async def value_factor_trendScore(start_date: str, end_date: str):
    """Compute and return the diversity score for REGULAR alphas in a submission-date window."""
    return str(await brain_client.value_factor_trendScore(start_date=start_date, end_date=end_date))


@mcp.tool()
async def get_daily_and_quarterly_payment(email: Optional[str] = None, password: Optional[str] = None):
    """
    Get daily and quarterly payment information from WorldQuant BRAIN platform.

    This function retrieves both base payments (daily alpha performance payments) and
    other payments (competition rewards, quarterly payments, referrals, etc.).

    Args:
        email: Your BRAIN platform email address (optional if stored in keyring)
        password: Your BRAIN platform password (optional if stored in keyring)

    Returns:
        Dictionary containing base payment and other payment data with summaries and detailed records
    """
    return str(await brain_client.get_daily_and_quarterly_payment(email=email, password=password))
