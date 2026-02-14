"""Entry point for the WorldQuant BRAIN MCP Server."""

import sys

from .config import load_credentials


def main():
    email, _ = load_credentials()
    if not email:
        print(
            "ERROR: No credentials found. Server cannot start.\n"
            "Configure credentials via one of:\n"
            "  1. Set WQB_EMAIL and WQB_PASSWORD environment variables\n"
            "  2. Run: wqb-mcp-setup (system keyring)",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(f"✓ Credentials loaded for {email}\n")

    from .tools import mcp
    mcp.run()


if __name__ == "__main__":
    main()
