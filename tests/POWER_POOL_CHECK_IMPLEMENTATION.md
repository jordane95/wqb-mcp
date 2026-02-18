# Power Pool Alpha Submission Check

## Overview

This implementation adds Power Pool-specific correlation rules to the `get_submission_check` MCP tool.

## Changes Made

### 1. Updated `correlation.py` (line 209-255)

Added `is_power_pool` parameter to `get_submission_check()` method:

```python
async def get_submission_check(self, alpha_id: str, is_power_pool: bool = False) -> SubmissionCheckResponse:
```

**Logic:**

- **If `is_power_pool=False` (default):** Checks prod + self correlation with threshold=0.7
- **If `is_power_pool=True`:**
  - Checks power-pool correlation with threshold=0.5
  - If PP correlation > 0.5, applies the 10% Sharpe rule:
    - Fetches the most correlated PP alpha's Sharpe
    - If current alpha's Sharpe >= 1.1 × correlated_alpha_sharpe, the check passes
    - Otherwise, the check fails

### 2. Updated `correlation_tools.py` (line 27-35)

Updated MCP tool signature to expose the `is_power_pool` parameter:

```python
@mcp.tool()
async def get_submission_check(alpha_id: str, is_power_pool: bool = False):
    """Comprehensive pre-submission check.

    Args:
        alpha_id: The ID of the alpha to check.
        is_power_pool: If True, applies Power Pool correlation rules (threshold=0.5, 10% Sharpe rule).
    """
    return str(await brain_client.get_submission_check(alpha_id, is_power_pool=is_power_pool))
```

## Usage

### Regular Alpha Check
```python
result = await brain_client.get_submission_check("QPrxWqE5", is_power_pool=False)
# Checks prod + self correlation with threshold=0.7
```

### Power Pool Alpha Check
```python
result = await brain_client.get_submission_check("QPrxWqE5", is_power_pool=True)
# Checks power-pool correlation with threshold=0.5
# Applies 10% Sharpe rule if correlation > 0.5
```

## Test Case

Alpha `QPrxWqE5` should be tested with both modes:
- Regular mode: checks against prod/self with 0.7 threshold
- Power Pool mode: checks against power-pool with 0.5 threshold, applies 10% Sharpe rule for alpha `1YV8jJaR`

## Files Modified

1. `/Users/lizehan/code/quant/wqb-mcp/src/wqb_mcp/client/correlation.py`
2. `/Users/lizehan/code/quant/wqb-mcp/src/wqb_mcp/tools/correlation_tools.py`

## Test Script

A test script is available at `/Users/lizehan/code/quant/wqb-mcp/tests/test_power_pool_check.py` for manual verification.
