# WorldQuant BRAIN MCP Server

Minimal MCP server for WorldQuant BRAIN platform integration with Claude Code.

## Features

- Complete BRAIN platform API integration (alphas, simulations, data)
- Forum access (glossary, search, posts)
- Biometric authentication support
- Browser automation for complex workflows
- Flexible credential management (env vars or system keyring)

## Setup

### 1. Install Package

```bash
pip install -e .

# Install Playwright browser
python3 -m playwright install chromium
```

### 2. Configure Credentials

The server checks credentials in this order:

1. **Environment variables** (`WQB_EMAIL`, `WQB_PASSWORD`)
2. **System keyring** (macOS Keychain / Windows Credential Locker)

Choose one of the following methods:

**Method 1: Environment variables via `claude mcp add` (recommended)**

This registers the server and configures credentials in one step:

```bash
claude mcp add wqb-mcp -e WQB_EMAIL=you@example.com -e WQB_PASSWORD=yourpass -- python3 -m wqb_mcp.server
```

**Method 2: System keyring**

```bash
wqb-mcp-setup
```

### 3. Register MCP Server

Only needed if using Method 2 (Method 1 already registers the server).

> **Note:** Use `python3` (not `python`) to ensure the correct interpreter is used when Claude Code spawns the process. Shell aliases don't work in non-interactive subprocesses.

```bash
claude mcp add wqb-mcp -- python3 -m wqb_mcp.server
```

### 4. Verify & Restart

```bash
# Check server connects
claude mcp list

# Restart Claude Code
exit
claude
```

## Package Structure

```
wqb-mcp/
├── src/
│   └── wqb_mcp/
│       ├── __init__.py
│       ├── server.py              # Entry point (auto-prompts setup on first run)
│       ├── setup.py               # CLI credential setup
│       ├── models.py              # Pydantic models
│       ├── config.py              # Credential management (env vars + keyring)
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

1. Check credentials are configured (see step 2 above)
2. Make sure you used `python3` not `python` in `claude mcp add`
3. Run debug mode to see errors:
```bash
claude --debug
```

### Playwright errors

Reinstall browser:
```bash
python3 -m playwright install chromium
```
