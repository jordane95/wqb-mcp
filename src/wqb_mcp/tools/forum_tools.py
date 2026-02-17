"""Forum MCP tools."""

from pathlib import Path
from typing import Optional

from . import mcp
from ..forum import forum_scraper
from ..config import load_credentials
from ..utils import expand_nested_data, save_flat_csv


@mcp.tool()
async def get_glossary_terms(email: str = "", password: str = "",
                             output_path: Optional[str] = None):
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
    response = await forum_scraper.get_glossary_terms(email, password)
    rows = [t.model_dump() for t in response.terms]
    target = Path(output_path) if output_path else Path("assets") / "forum" / "glossary.csv"
    col_count = save_flat_csv(rows, target)
    return (
        "Saved glossary CSV\n"
        f"- path: `{target}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- columns: `{col_count}`\n"
        f"- preview:\n```text\n{response}\n```"
    )


@mcp.tool()
async def search_forum_posts(search_query: str, email: str = "", password: str = "",
                             max_results: int = 50, output_path: Optional[str] = None):
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

    response = await forum_scraper.search_forum_posts(email, password, search_query, max_results)
    rows = expand_nested_data([r.model_dump() for r in response.results], preserve_original=True)
    safe_query = search_query.replace(" ", "_").lower()[:50]
    target = (
        Path(output_path)
        if output_path
        else Path("assets") / "forum" / f"search_{safe_query}.csv"
    )
    col_count = save_flat_csv(rows, target)
    return (
        "Saved forum search CSV\n"
        f"- path: `{target}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- columns: `{col_count}`\n"
        f"- total_found: `{response.total_found}`\n"
        f"- preview:\n```text\n{response}\n```"
    )


@mcp.tool()
async def read_forum_post(article_id: str, email: str = "", password: str = "",
                          include_comments: bool = True, output_path: Optional[str] = None):
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

    response = await forum_scraper.read_full_forum_post(email, password, article_id, include_comments)

    # Save full post + comments to CSV
    post = response.post
    rows = [{"type": "post", "author": post.author, "date": post.details.date,
             "title": post.title, "body": post.body, "votes": post.details.votes}]
    for c in response.comments:
        rows.append({"type": "comment", "author": c.author, "date": c.date,
                      "title": "", "body": c.body, "votes": ""})
    target = Path(output_path) if output_path else Path("assets") / "forum" / f"post_{article_id}.csv"
    col_count = save_flat_csv(rows, target)
    return (
        "Saved forum post CSV\n"
        f"- path: `{target}`\n"
        f"- rows: `{len(rows)}`\n"
        f"- columns: `{col_count}`\n"
        f"- total_comments: `{response.total_comments}`\n"
        f"- preview:\n```text\n{response}\n```"
    )
