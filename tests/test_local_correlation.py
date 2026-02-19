#!/usr/bin/env python3
"""Test script for local correlation computation.

Compares results from the server-side ``check_correlation`` with the
local ``check_local_correlation`` to verify they produce consistent
results.
"""

import asyncio
import sys

from wqb_mcp.client import brain_client
from wqb_mcp.client.correlation import CorrelationType


# Use a known alpha ID — change this to one of your own if needed
DEFAULT_ALPHA_ID = "QPrxWqE5"


async def test_local_correlation(alpha_id: str):
    """Run local correlation and compare with server-side results."""

    # --- Authenticate (uses env vars WQB_EMAIL/WQB_PASSWORD or keyring) ---
    try:
        await brain_client.ensure_authenticated()
    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Set WQB_EMAIL and WQB_PASSWORD env vars, or store in keyring.")
        return

    # =================================================================
    # Test 1: Self correlation (local vs server)
    # =================================================================
    print("=" * 80)
    print("Test 1: Self correlation — SERVER")
    print("=" * 80)
    try:
        server_result = await brain_client.check_correlation(
            alpha_id,
            check_types=[CorrelationType.SELF],
            threshold=0.7,
        )
        print(server_result)
    except Exception as e:
        print(f"Server self-correlation failed: {e}")
        server_result = None
    print()

    print("=" * 80)
    print("Test 1: Self correlation — LOCAL")
    print("=" * 80)
    local_result = await brain_client.check_local_correlation(
        alpha_id,
        check_types=[CorrelationType.SELF],
        threshold=0.7,
    )
    print(local_result)
    print()

    # Compare
    if server_result:
        s_check = server_result.checks.get(CorrelationType.SELF)
        l_check = local_result.checks.get(CorrelationType.SELF)
        s_max = s_check.max_correlation if s_check else None
        l_max = l_check.max_correlation if l_check else None
        print(f"  Server max self-corr: {s_max}")
        print(f"  Local  max self-corr: {l_max}")
        if s_max is not None and l_max is not None:
            diff = abs(s_max - l_max)
            print(f"  Difference: {diff:.4f}")
            print(f"  Close enough (<0.05): {'YES' if diff < 0.05 else 'NO'}")
    print()

    # =================================================================
    # Test 2: Power Pool correlation (local)
    # =================================================================
    print("=" * 80)
    print("Test 2: Power Pool correlation — LOCAL")
    print("=" * 80)
    pp_result = await brain_client.check_local_correlation(
        alpha_id,
        check_types=[CorrelationType.POWER_POOL],
        threshold=0.5,
    )
    print(pp_result)
    pp_check = pp_result.checks.get(CorrelationType.POWER_POOL)
    if pp_check:
        print(f"\n  Max PP correlation: {pp_check.max_correlation}")
        print(f"  Passes (< 0.5): {pp_check.passes_check}")
        if pp_check.top_correlations:
            top = pp_check.top_correlations[0]
            print(f"  Most correlated: {top.id} ({top.correlation})")
    print()

    # =================================================================
    # Test 3: Both self + PP (local)
    # =================================================================
    print("=" * 80)
    print("Test 3: Self + Power Pool — LOCAL")
    print("=" * 80)
    both_result = await brain_client.check_local_correlation(
        alpha_id,
        check_types=[CorrelationType.SELF, CorrelationType.POWER_POOL],
        threshold=0.7,
    )
    print(both_result)
    print()

    # =================================================================
    # Test 4: PROD (should raise ValueError)
    # =================================================================
    print("=" * 80)
    print("Test 4: PROD correlation — LOCAL (expect ValueError)")
    print("=" * 80)
    try:
        await brain_client.check_local_correlation(
            alpha_id,
            check_types=[CorrelationType.PROD],
            threshold=0.7,
        )
        print("  ERROR: should have raised ValueError")
    except ValueError as e:
        print(f"  Correctly raised ValueError: {e}")
    print()

    # =================================================================
    # Test 5: Batch correlation
    # =================================================================
    print("=" * 80)
    print("Test 5: Batch local correlation")
    print("=" * 80)
    # Get a few alpha IDs from cache to test batch
    from wqb_mcp.client.local_correlation import AlphaCache
    cache = AlphaCache()
    cache.load_index()
    all_ids = list(cache.index.get("alphas", {}).keys())
    batch_ids = [alpha_id] + all_ids[:2]  # test alpha + 2 cached alphas
    batch_ids = list(dict.fromkeys(batch_ids))  # deduplicate, preserve order
    print(f"  Testing batch with {len(batch_ids)} alphas: {batch_ids}")
    print()

    batch_result = await brain_client.batch_check_local_correlation(
        batch_ids,
        check_types=[CorrelationType.SELF],
        threshold=0.7,
    )

    print("  --- Inter-correlation (each vs baseline) ---")
    for aid, check_resp in batch_result["inter_correlation"].items():
        print(f"  {aid}: {check_resp}")
    print()

    print("  --- Intra-correlation (pairwise between candidates) ---")
    print(batch_result["intra_correlation"].to_string())
    print()

    # =================================================================
    # Summary
    # =================================================================
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Alpha: {alpha_id}")
    print(f"Self corr (local):  {local_result.all_passed}")
    print(f"PP corr (local):    {pp_result.all_passed}")
    print(f"Both (local):       {both_result.all_passed}")
    print(f"PROD (local):       ValueError (correct)")
    print(f"Batch:              {len(batch_result['inter_correlation'])} alphas checked")


if __name__ == "__main__":
    aid = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ALPHA_ID
    asyncio.run(test_local_correlation(aid))
