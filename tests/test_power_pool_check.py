#!/usr/bin/env python3
"""Test script for Power Pool alpha submission check."""

import asyncio
from wqb_mcp.client import brain_client


async def test_power_pool_check():
    """Test the Power Pool submission check with alpha QPrxWqE5."""

    # Authenticate (will use stored credentials from keyring)
    try:
        await brain_client.authenticate(None, None)
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Please ensure credentials are stored in keyring or provide them.")
        return

    alpha_id = "QPrxWqE5"

    print("=" * 80)
    print("Test 1: Regular submission check (is_power_pool=False)")
    print("=" * 80)
    result_regular = await brain_client.get_submission_check(alpha_id, is_power_pool=False)
    print(result_regular)
    print()

    print("=" * 80)
    print("Test 2: Power Pool submission check (is_power_pool=True)")
    print("=" * 80)
    result_pp = await brain_client.get_submission_check(alpha_id, is_power_pool=True)
    print(result_pp)
    print()

    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Regular check passed: {result_regular.all_passed}")
    print(f"Power Pool check passed: {result_pp.all_passed}")

    # Check correlation details
    if result_pp.correlation_checks.checks:
        from wqb_mcp.client.correlation import CorrelationType
        pp_check = result_pp.correlation_checks.checks.get(CorrelationType.POWER_POOL)
        if pp_check:
            print(f"\nPower Pool correlation details:")
            print(f"  Max correlation: {pp_check.max_correlation}")
            print(f"  Passes check: {pp_check.passes_check}")
            if pp_check.top_correlations:
                print(f"  Most correlated alpha: {pp_check.top_correlations[0].alpha_id}")
                print(f"  Correlation value: {pp_check.top_correlations[0].correlation}")


if __name__ == "__main__":
    asyncio.run(test_power_pool_check())
