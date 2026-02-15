"""Forum MCP tools."""

from . import mcp
from ..forum import forum_scraper
from ..config import load_credentials

@mcp.tool()
async def get_glossary_terms(email: str = "", password: str = ""):
    """
    Get glossary terms from WorldQuant BRAIN forum.

    Note: This uses Playwright and is implemented in forum.py

    Args:
        email: Your BRAIN platform email address (optional if stored in keyring)
        password: Your BRAIN platform password (optional if stored in keyring)

    Returns:
        A list of glossary terms with definitions
    """
    stored_email, stored_password = load_credentials()
    email = email or stored_email
    password = password or stored_password
    if not email or not password:
        raise ValueError("Authentication credentials not provided or found in config.")

    return str(await forum_scraper.get_glossary_terms(email, password))


@mcp.tool()
async def search_forum_posts(search_query: str, email: str = "", password: str = "",
                             max_results: int = 50):
    """
    Search forum posts on WorldQuant BRAIN support site.

    Note: This uses Playwright and is implemented in forum.py

    Args:
        search_query: Search term or phrase
        email: Your BRAIN platform email address (optional if stored in keyring)
        password: Your BRAIN platform password (optional if stored in keyring)
        max_results: Maximum number of results to return (default: 50)

    Returns:
        Search results with analysis
    """
    stored_email, stored_password = load_credentials()
    email = email or stored_email
    password = password or stored_password
    if not email or not password:
        raise ValueError("Authentication credentials not provided or found in config.")

    return str(await forum_scraper.search_forum_posts(email, password, search_query, max_results))


@mcp.tool()
async def read_forum_post(article_id: str, email: str = "", password: str = "",
                          include_comments: bool = True):
    """
    Get a specific forum post by article ID.

    Note: This uses Playwright and is implemented in forum.py

    Args:
        article_id: The article ID to retrieve
        email: Your BRAIN platform email address (optional if stored in keyring)
        password: Your BRAIN platform password (optional if stored in keyring)

    Returns:
        Forum post content with comments
    """
    stored_email, stored_password = load_credentials()
    email = email or stored_email
    password = password or stored_password
    if not email or not password:
        raise ValueError("Authentication credentials not provided or found in config.")

    return str(await forum_scraper.read_full_forum_post(email, password, article_id, include_comments))
