"""Pre-warm the static cache for datasets and datafields.

Usage:
    wqb-mcp-warmup              # warm all combos from platform settings
    wqb-mcp-warmup --force      # force refresh even if cache is valid
    python -m wqb_mcp.warmup    # same thing
"""

import asyncio
import sys
import time

from .client import brain_client


async def warmup(force: bool = False) -> None:
    """Fetch platform settings, then pre-warm datasets & datafields for each combo."""
    t0 = time.time()

    # 1. Platform settings (also discovers all combos)
    print("Fetching platform settings...", file=sys.stderr)
    settings = await brain_client.get_platform_setting_options(force_refresh=force)
    print(f"  {settings.total_combinations} combos found", file=sys.stderr)

    # 2. Iterate each combo: datasets + datafields
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
                print(f"    {ds.count} datasets", file=sys.stderr)

                # Fetch datafields for each dataset
                for dataset in ds.results:
                    try:
                        print(f"    datafields for {dataset.id}...", file=sys.stderr)
                        df = await brain_client.get_datafields(
                            instrument_type=instrument_type, region=region, delay=delay,
                            universe=universe, dataset_id=dataset.id, force_refresh=force,
                        )
                        print(f"      {df.count} datafields", file=sys.stderr)
                    except Exception as e:
                        print(f"      ERROR: {e}", file=sys.stderr)

            except Exception as e:
                print(f"    ERROR: {e}", file=sys.stderr)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s", file=sys.stderr)


def main():
    force = "--force" in sys.argv
    asyncio.run(warmup(force))


if __name__ == "__main__":
    main()
