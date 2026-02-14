"""Credential management for the WorldQuant BRAIN MCP Server."""

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SERVICE_NAME = "wqb-mcp"


def load_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load credentials from environment variables or system keyring.

    Priority order:
    1. Environment variables (WQB_EMAIL, WQB_PASSWORD)
    2. System keyring

    Returns:
        (email, password) or (None, None) if not found
    """
    email = os.environ.get("WQB_EMAIL")
    password = os.environ.get("WQB_PASSWORD")
    if email and password:
        logger.info("Loaded credentials from environment variables")
        return email, password

    # Fall back to keyring
    try:
        import keyring
        email = keyring.get_password(SERVICE_NAME, "email")
        password = keyring.get_password(SERVICE_NAME, "password")
        if email and password:
            logger.info("Loaded credentials from keyring")
            return email, password
    except Exception as e:
        logger.warning(f"Could not read from keyring: {e}")

    return None, None


def save_credentials(email: str, password: str) -> bool:
    """Save credentials to system keyring.

    Returns:
        True if saved successfully, False otherwise
    """
    try:
        import keyring
        keyring.set_password(SERVICE_NAME, "email", email)
        keyring.set_password(SERVICE_NAME, "password", password)
        logger.info("Credentials saved to keyring")
        return True
    except Exception as e:
        logger.warning(f"Could not save to keyring: {e}")
        return False


def delete_credentials() -> bool:
    """Delete credentials from system keyring.

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        import keyring
        keyring.delete_password(SERVICE_NAME, "email")
        keyring.delete_password(SERVICE_NAME, "password")
        logger.info("Credentials deleted from keyring")
        return True
    except Exception as e:
        logger.warning(f"Could not delete from keyring: {e}")
        return False
