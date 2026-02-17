# WorldQuant BRAIN MCP Server

Minimal MCP server for WorldQuant BRAIN platform integration with Claude Code.

## Features

- Complete BRAIN platform API integration (alphas, simulations, data)
- Forum access (glossary, search, posts)
- Biometric authentication support
- Browser automation for complex workflows
- Flexible credential management (env vars or system keyring)
- Token-efficient tool responses: markdown summaries for readability, with large tabular data persisted to local CSV files instead of returning full payloads.

## Setup

### 1. Install Package

```bash
pip install -e .

# Install Playwright browser
python -m playwright install chromium
```

### 2. Configure Credentials

The server checks credentials in this order:

1. **Environment variables** (`WQB_EMAIL`, `WQB_PASSWORD`)
2. **System keyring** (macOS Keychain / Windows Credential Locker)

Choose one of the following methods:

**Method 1: Environment variables via `claude mcp add` (recommended)**

This registers the server and configures credentials in one step:

```bash
claude mcp add wqb-mcp -e WQB_EMAIL=you@example.com -e WQB_PASSWORD=yourpass -- python -m wqb_mcp.server
```

**Method 2: System keyring**

```bash
wqb-mcp-setup
```

### 3. Register MCP Server

Only needed if using Method 2 (Method 1 already registers the server).

```bash
claude mcp add wqb-mcp -- python -m wqb_mcp.server
```

### 4. Verify & Restart

```bash
# Check server connects
claude mcp list

# Restart Claude Code
exit
claude
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
2. Make sure the `python` path in `claude mcp add` matches your system's Python executable
3. Run debug mode to see errors:
```bash
claude --debug
```

### Playwright errors

Reinstall browser:
```bash
python -m playwright install chromium
```
