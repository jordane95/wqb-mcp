"""Authentication MCP tools."""

import logging
from typing import Optional

from . import mcp
from ..client import brain_client
from ..config import load_credentials, save_credentials, delete_credentials

logger = logging.getLogger(__name__)


@mcp.tool()
async def authenticate(email: Optional[str] = None, password: Optional[str] = None):
    """
    Authenticate with WorldQuant BRAIN platform.

    This is the first step in any BRAIN workflow. You must authenticate before using any other tools.
    Credentials are stored securely in the system keyring after first successful login.

    Args:
        email: Your BRAIN platform email address (optional if stored in keyring)
        password: Your BRAIN platform password (optional if stored in keyring)

    Returns:
        Authentication result with user info and permissions
    """
    stored_email, stored_password = load_credentials()

    email = email or stored_email
    password = password or stored_password
    if not email or not password:
        raise ValueError("Authentication credentials not provided. Run 'python -m wqb_mcp.setup' to store credentials.")

    auth_result = await brain_client.authenticate(email, password)

    # Save to keyring on success
    if auth_result.status == "authenticated":
        save_credentials(email, password)

    return str(auth_result)


@mcp.tool()
async def manage_credentials(action: str = "status"):
    """
    Manage stored credentials.

    Args:
        action: "status" to check credential sources, "delete" to remove stored credentials from keyring

    Returns:
        Credential status or deletion result
    """
    if action == "status":
        email, _ = load_credentials()
        result = {
            "has_credentials": email is not None,
            "email": email,
            "is_authenticated": await brain_client.is_authenticated()
        }
        return str(result)

    elif action == "delete":
        success = delete_credentials()
        result = {
            "deleted": success,
            "message": "Credentials removed from keyring" if success else "Failed to delete credentials"
        }
        return str(result)

    raise ValueError(f"Invalid action '{action}'. Use 'status' or 'delete'.")
