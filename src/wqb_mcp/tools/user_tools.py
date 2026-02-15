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
async def get_documentations():
    """
    Get available documentations and learning materials.

    Returns:
        List of documentations
    """
    return str(await brain_client.get_documentations())


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
async def get_documentation_page(page_id: str):
    """Retrieve detailed content of a specific documentation page/article."""
    return str(await brain_client.get_documentation_page(page_id))


@mcp.tool()
async def get_daily_and_quarterly_payment(email: str = "", password: str = ""):
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
    from ..config import load_credentials

    stored_email, stored_password = load_credentials()
    email = email or stored_email
    password = password or stored_password
    if not email or not password:
        raise ValueError("Authentication credentials not provided or found in config.")

    await brain_client.authenticate(email, password)

    # Get base payments
    try:
        base_response = brain_client.session.get(f"{brain_client.base_url}/users/self/activities/base-payment")
        base_response.raise_for_status()
        base_payments = base_response.json()
    except:
        base_payments = "no data"

    try:
        # Get other payments
        other_response = brain_client.session.get(f"{brain_client.base_url}/users/self/activities/other-payment")
        other_response.raise_for_status()
        other_payments = other_response.json()
    except:
        other_payments = "no data"
    result = {
        "base_payments": base_payments,
        "other_payments": other_payments
    }
    return str(result)
