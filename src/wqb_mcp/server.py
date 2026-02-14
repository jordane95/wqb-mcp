"""Entry point for the WorldQuant BRAIN MCP Server."""

from .tools import mcp


def main():
    mcp.run()


if __name__ == "__main__":
    main()
