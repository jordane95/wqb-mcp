# WorldQuant BRAIN MCP Server

Minimal MCP server for WorldQuant BRAIN platform integration with Claude Code.

## Features

- Complete BRAIN platform API integration (alphas, simulations, data)
- Forum access (glossary, search, posts)
- Biometric authentication support
- Browser automation for complex workflows

## Setup

### 1. Install Package

```bash
# Install in editable mode (for development)
pip install -e .

# Or install normally
pip install .

# Install Playwright browser
python -m playwright install chromium
```

### 2. Register MCP Server

```bash
# Use the installed package module
claude mcp add brain-mcp -- python -m wqb_mcp.server
```

**Alternative**: Install from Git (coming soon)
```bash
pip install git+https://github.com/jordane95/wqb-mcp.git
claude mcp add brain-mcp -- python -m wqb_mcp.server
```

### 3. Configure Credentials

Store credentials securely in your system keyring:

```bash
python -m wqb_mcp.setup
```

This prompts for email and password directly in the terminal (password is masked). Credentials are stored in macOS Keychain / Windows Credential Locker — no plaintext files.

### 4. Restart Claude Code

```bash
# Exit current session
exit

# Start new session
claude
```

## Package Structure

```
wqb-mcp/
├── src/
│   └── wqb_mcp/
│       ├── __init__.py
│       ├── server.py              # Entry point
│       ├── models.py              # Pydantic models
│       ├── config.py              # Credential management (keyring + .env)
│       ├── forum.py               # Forum scraper (Playwright)
│       ├── client/
│       │   ├── __init__.py        # BrainApiClient (composed from mixins)
│       │   ├── auth.py            # Authentication
│       │   ├── simulation.py      # Simulations
│       │   ├── alpha.py           # Alpha management
│       │   ├── correlation.py     # Correlation checks
│       │   ├── data.py            # Datasets & datafields
│       │   ├── diversity.py       # Diversity scoring
│       │   ├── community.py       # Events, competitions
│       │   ├── user.py            # Profile, messages, pyramids
│       │   ├── operators.py       # Operators & selection
│       │   └── platform_config.py # Platform settings
│       └── tools/
│           ├── __init__.py        # FastMCP instance
│           ├── auth_tools.py
│           ├── simulation_tools.py
│           ├── alpha_tools.py
│           ├── correlation_tools.py
│           ├── data_tools.py
│           ├── community_tools.py
│           ├── user_tools.py
│           ├── forum_tools.py
│           └── operators_tools.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Usage

Once configured, the MCP server provides tools for:

- **Alphas**: Create, simulate, submit
- **Data**: Fetch market data, fundamentals
- **Simulations**: Run backtests, analyze results
- **Forum**: Search docs, get glossary terms
- **Account**: Manage profile, settings

## Troubleshooting

### MCP shows "failed" status

Run debug mode to see errors:
```bash
claude --debug
```

### Playwright errors

Reinstall browser:
```bash
python -m playwright install chromium
```
