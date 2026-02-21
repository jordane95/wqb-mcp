"""Pre-warm the static cache for datasets and datafields.

Usage:
    wqb-mcp-warmup              # warm all combos from platform settings
    wqb-mcp-warmup --force      # force refresh even if cache is valid
    python -m wqb_mcp.warmup    # same thing
"""

import asyncio
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from .client import brain_client
from .client.data import DataMixin

_MAX_WORKERS = 8


def _datafields_cache_key(instrument_type: str, region: str, universe: str,
                          delay: int, dataset_id: str) -> str:
    prefix = DataMixin._data_cache_key_prefix(instrument_type, region, universe, delay)
    safe_id = dataset_id.replace(" ", "_")
    return f"{prefix}:datafields:{safe_id}"


def _fetch_datafields_sync(instrument_type, region, delay, universe, dataset_id, force):
    """Run get_datafields in a new event loop (for thread pool)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(brain_client.get_datafields(
            instrument_type=instrument_type, region=region, delay=delay,
            universe=universe, dataset_id=dataset_id, force_refresh=force,
        ))
    finally:
        loop.close()


async def warmup(force: bool = False) -> None:
    """Fetch platform settings, then pre-warm datasets & datafields for each combo."""
    t0 = time.time()
    errors = 0

    # 1. Platform settings
    print("Fetching platform settings...", file=sys.stderr)
    settings = await brain_client.get_platform_setting_options(force_refresh=force)
    print(f"  {settings.total_combinations} combos found", file=sys.stderr)

    # 2. Collect all (combo, dataset) pairs that need fetching
    pending = []  # list of (label, instrument_type, region, universe, delay, dataset_id)
    combo_stats = {}  # label -> {total, cached, pending}
    cache = brain_client._static_cache

    for combo in settings.instrument_options:
        instrument_type = combo.instrumentType
        region = combo.region
        delay = combo.delay
        for universe in combo.universe:
            label = f"{instrument_type}/{region}/{universe}/D{delay}"
            print(f"\n[{label}]", file=sys.stderr)

            try:
                print(f"  datasets...", file=sys.stderr)
                ds = await brain_client.get_datasets(
                    instrument_type=instrument_type, region=region, delay=delay,
                    universe=universe, force_refresh=force,
                )
                total_ds = ds.count
                cached = 0
                for dataset in ds.results:
                    key = _datafields_cache_key(instrument_type, region, universe, delay, dataset.id)
                    if force or not cache.is_valid(key):
                        pending.append((label, instrument_type, region, universe, delay, dataset.id))
                    else:
                        cached += 1
                combo_pending = total_ds - cached
                combo_stats[label] = {"total": total_ds, "cached": cached, "pending": combo_pending, "fetched": 0, "errors": defaultdict(list)}
                print(f"    {total_ds} datasets ({cached} cached, {combo_pending} to fetch)", file=sys.stderr)

            except Exception as e:
                print(f"    ERROR: {e}", file=sys.stderr)
                errs = defaultdict(list)
                errs[type(e).__name__].append(("datasets", str(e)))
                combo_stats[label] = {"total": 0, "cached": 0, "pending": 0, "fetched": 0, "errors": errs}
                errors += 1

    total = len(pending)
    total_cached = sum(s["cached"] for s in combo_stats.values())
    print(f"\n--- Pre-fetch ---", file=sys.stderr)
    for label, s in combo_stats.items():
        print(f"  {label}: {s['total']} total, {s['cached']} cached, {s['pending']} to fetch", file=sys.stderr)
    print(f"\n{total} datafield sets to fetch ({total_cached} already cached)", file=sys.stderr)

    if not pending:
        elapsed = time.time() - t0
        print(f"Done in {elapsed:.1f}s  (all cached, errors={errors})", file=sys.stderr)
        return

    # 3. Fetch with thread pool + progress bar
    brain_client.log_level = "WARN"  # suppress noisy auth/info logs during parallel fetch
    pbar = tqdm(total=len(pending), desc="datafields", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        future_to_item = {
            pool.submit(
                _fetch_datafields_sync,
                instrument_type, region, delay, universe, dataset_id, force,
            ): (label, dataset_id)
            for label, instrument_type, region, universe, delay, dataset_id in pending
        }

        for future in as_completed(future_to_item):
            label, dataset_id = future_to_item[future]
            try:
                future.result()
                combo_stats[label]["fetched"] += 1
            except Exception as e:
                tqdm.write(f"  ERROR {dataset_id}: {type(e).__name__}: {e}", file=sys.stderr)
                combo_stats[label]["errors"][type(e).__name__].append((dataset_id, str(e)))
                errors += 1
            pbar.update(1)

    pbar.close()
    brain_client.log_level = "INFO"  # restore

    # 4. Summary per combo
    print("\n--- Summary ---", file=sys.stderr)
    for label, s in combo_stats.items():
        err_count = sum(len(ids) for ids in s["errors"].values())
        status = "✓" if err_count == 0 and s["pending"] == s["fetched"] else "✗"
        print(f"  {status} {label}: {s['total']} total, {s['cached']} cached, {s['fetched']} fetched, {err_count} errors", file=sys.stderr)
        for err_type, entries in s["errors"].items():
            ids = [eid for eid, _ in entries]
            print(f"      {err_type} ({len(entries)}): {', '.join(ids)}", file=sys.stderr)
            for eid, msg in entries[:5]:
                print(f"        - {eid}: {msg}", file=sys.stderr)
            if len(entries) > 5:
                print(f"        ... and {len(entries) - 5} more", file=sys.stderr)

    elapsed = time.time() - t0
    fetched = sum(s["fetched"] for s in combo_stats.values())
    print(f"\nDone in {elapsed:.1f}s  (fetched={fetched}, errors={errors})", file=sys.stderr)


def main():
    force = "--force" in sys.argv
    asyncio.run(warmup(force))


if __name__ == "__main__":
    main()
