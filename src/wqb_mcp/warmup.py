"""Pre-warm the static cache for datasets and datafields.

Usage:
    wqb-mcp-warmup              # warm all combos from platform settings
    wqb-mcp-warmup --force      # force refresh even if cache is valid
    wqb-mcp-warmup --stats      # show cached dataset/datafield counts
    wqb-mcp-warmup --rebuild    # generate category-based derived cache view
    python -m wqb_mcp.warmup    # same thing
"""

import asyncio
import json
import shutil
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

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


def _count_csv_rows(path: Path) -> int:
    """Return number of data rows in a CSV (total lines minus header)."""
    try:
        with open(path, "rb") as f:
            n = sum(1 for _ in f)
        return max(n - 1, 0)
    except OSError:
        return 0


def cache_stats() -> None:
    """Print per-combo dataset/datafield counts from the local cache."""
    data_root = Path.home() / ".wqb_mcp" / "cache" / "data"
    if not data_root.exists():
        print("No cache found.", file=sys.stderr)
        return

    combo_rows: list[tuple[str, int, int]] = []  # (label, ds_count, df_count)

    # Walk: data/{instrument_type}/{region}/{universe}/D{delay}/
    for inst_dir in sorted(data_root.iterdir()):
        if not inst_dir.is_dir():
            continue
        instrument_type = inst_dir.name
        for region_dir in sorted(inst_dir.iterdir()):
            if not region_dir.is_dir():
                continue
            region = region_dir.name
            for universe_dir in sorted(region_dir.iterdir()):
                if not universe_dir.is_dir():
                    continue
                universe = universe_dir.name
                for delay_dir in sorted(universe_dir.iterdir()):
                    if not delay_dir.is_dir() or not delay_dir.name.startswith("D"):
                        continue
                    delay_tag = delay_dir.name  # e.g. "D1"

                    ds_csv = delay_dir / "datasets.csv"
                    ds_count = _count_csv_rows(ds_csv)

                    df_count = 0
                    ds_subdir = delay_dir / "dataset"
                    if ds_subdir.is_dir():
                        for ds_id_dir in ds_subdir.iterdir():
                            df_csv = ds_id_dir / "datafields.csv"
                            if df_csv.exists():
                                df_count += _count_csv_rows(df_csv)

                    label = f"{instrument_type}/{region}/{universe}/{delay_tag}"
                    combo_rows.append((label, ds_count, df_count))

    if not combo_rows:
        print("Cache is empty.", file=sys.stderr)
        return

    max_label = max(len(r[0]) for r in combo_rows)

    print("\nCache Statistics\n")
    for label, ds, df in combo_rows:
        print(f"{label:<{max_label}}  datasets={ds:<6} datafields={df}")

    total_ds = sum(r[1] for r in combo_rows)
    total_df = sum(r[2] for r in combo_rows)

    print(f"\nTotal ({len(combo_rows)} combos):  datasets={total_ds:<6} datafields={total_df}")


def _parse_json_name(raw):
    """Extract 'name' from a JSON-encoded cell like '{"id":"x","name":"Foo"}'."""
    if isinstance(raw, dict):
        return raw.get("name", str(raw))
    if not isinstance(raw, str):
        return str(raw) if raw is not None else ""
    try:
        return json.loads(raw).get("name", raw)
    except (json.JSONDecodeError, TypeError, AttributeError):
        return raw


def _parse_json_id(raw):
    """Extract 'id' from a JSON-encoded cell."""
    if isinstance(raw, dict):
        return raw.get("id", "")
    if not isinstance(raw, str):
        return ""
    try:
        return json.loads(raw).get("id", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return ""


def _build_availability_col(df):
    """Vectorized: build 'REGION/UNIVERSE/D{delay}' combo string per row."""
    return df["region"].astype(str) + "/" + df["universe"].astype(str) + "/D" + df["delay"].astype(str)


def _agg_availability(series):
    """Aggregate combo strings: sort unique, pipe-join."""
    return "|".join(sorted(series.unique()))


def rebuild_category_cache() -> None:
    """Generate a category-based derived cache view under data_by_category/."""
    import pandas as pd

    data_root = Path.home() / ".wqb_mcp" / "cache" / "data"
    out_root = Path.home() / ".wqb_mcp" / "cache" / "data_by_category"
    if not data_root.exists():
        print("No cache found.", file=sys.stderr)
        return

    # --- 1. Load all cached CSVs ---
    ds_frames = []
    df_frames = []

    for ds_csv in sorted(data_root.glob("*/*/*/*/datasets.csv")):
        try:
            ds_frames.append(pd.read_csv(ds_csv, keep_default_na=False))
        except Exception:
            pass

    for df_csv in sorted(data_root.glob("*/*/*/*/dataset/*/datafields.csv")):
        try:
            df_frames.append(pd.read_csv(df_csv, keep_default_na=False))
        except Exception:
            pass

    if not ds_frames and not df_frames:
        print("Cache is empty.", file=sys.stderr)
        return

    # --- 2. Parse datasets ---
    ds_all = pd.concat(ds_frames, ignore_index=True) if ds_frames else pd.DataFrame()
    if not ds_all.empty:
        ds_all["category_id"] = ds_all["category"].apply(_parse_json_id)
        ds_all["category_name"] = ds_all["category"].apply(_parse_json_name)
        ds_all["subcategory_id"] = ds_all["subcategory"].apply(_parse_json_id)
        ds_all["subcategory_name"] = ds_all["subcategory"].apply(_parse_json_name)
        ds_all["_combo"] = _build_availability_col(ds_all)

    # --- 3. Parse datafields ---
    df_all = pd.concat(df_frames, ignore_index=True) if df_frames else pd.DataFrame()
    if not df_all.empty:
        df_all["dataset_id"] = df_all["dataset"].apply(_parse_json_id)
        df_all["dataset_name"] = df_all["dataset"].apply(_parse_json_name)
        df_all["category_id"] = df_all["category"].apply(_parse_json_id)
        df_all["subcategory_id"] = df_all["subcategory"].apply(_parse_json_id)
        df_all["_combo"] = _build_availability_col(df_all)

    # --- 4. Build per-dataset datafield availability ---
    #  {dataset_id: DataFrame with columns [id, description, type, availability]}
    ds_field_map: dict[str, pd.DataFrame] = {}
    if not df_all.empty:
        df_dedup = df_all.drop_duplicates(subset=["id", "_combo"])
        df_avail = df_dedup.groupby("id")["_combo"].apply(_agg_availability).rename("availability")
        df_meta = df_all.drop_duplicates(subset=["id"]).set_index("id")[
            ["description", "type", "dataset_id"]
        ]
        df_merged = df_meta.join(df_avail).reset_index()
        for dsid, grp in df_merged.groupby("dataset_id"):
            ds_field_map[dsid] = grp[["id", "description", "type", "availability"]].sort_values("id")

    # --- 5. Build per-dataset availability from datasets ---
    #  {dataset_id: {"name", "description", "availability", "subcategory_id", "category_id"}}
    ds_info: dict[str, dict] = {}
    if not ds_all.empty:
        ds_dedup = ds_all.drop_duplicates(subset=["id", "_combo"])
        ds_avail = ds_dedup.groupby("id")["_combo"].apply(_agg_availability).rename("availability")
        ds_meta = ds_all.drop_duplicates(subset=["id"]).set_index("id")[
            ["name", "description", "category_id", "category_name",
             "subcategory_id", "subcategory_name"]
        ]
        ds_joined = ds_meta.join(ds_avail).reset_index()
        for _, row in ds_joined.iterrows():
            field_count = len(ds_field_map.get(row["id"], []))
            ds_info[row["id"]] = {
                "name": row["name"],
                "description": row["description"],
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "subcategory_id": row["subcategory_id"],
                "subcategory_name": row["subcategory_name"],
                "availability": row["availability"],
                "datafield_count": field_count,
            }

    # --- 6. Build hierarchy: category -> subcategory -> dataset ---
    # {cat_id: {name, datasets: {subcat_id: {name, dataset_ids: [...]}}}}
    hierarchy: dict[str, dict] = {}
    for dsid, info in sorted(ds_info.items()):
        cat_id = info["category_id"]
        cat_name = info["category_name"]
        sub_id = info["subcategory_id"]
        sub_name = info["subcategory_name"]

        if cat_id not in hierarchy:
            hierarchy[cat_id] = {"name": cat_name, "subcategories": {}}
        cat = hierarchy[cat_id]
        if sub_id not in cat["subcategories"]:
            cat["subcategories"][sub_id] = {"name": sub_name, "dataset_ids": []}
        cat["subcategories"][sub_id]["dataset_ids"].append(dsid)

    # --- 7. Write output ---
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)

    top_categories = []
    total_ds_count = 0
    total_df_count = 0

    for cat_id in sorted(hierarchy):
        cat = hierarchy[cat_id]
        cat_dir = out_root / cat_id
        cat_dir.mkdir()

        cat_ds_count = 0
        cat_df_count = 0
        cat_availability: set[str] = set()
        cat_ds_rows = []
        subcat_summaries = []

        for sub_id in sorted(cat["subcategories"]):
            sub = cat["subcategories"][sub_id]
            sub_dir = cat_dir / sub_id
            sub_dir.mkdir()

            sub_ds_count = 0
            sub_df_count = 0
            sub_availability: set[str] = set()
            sub_ds_rows = []

            for dsid in sorted(sub["dataset_ids"]):
                info = ds_info[dsid]
                avail_str = info["availability"]
                avail_set = set(avail_str.split("|")) if avail_str else set()
                fc = info["datafield_count"]

                sub_ds_count += 1
                sub_df_count += fc
                sub_availability.update(avail_set)

                row = {
                    "id": dsid,
                    "name": info["name"],
                    "subcategory": sub["name"],
                    "datafield_count": fc,
                    "availability": avail_str,
                }
                sub_ds_rows.append(row)
                cat_ds_rows.append(row)

                # --- dataset-level dir ---
                ds_dir = sub_dir / dsid
                ds_dir.mkdir()
                _write_json(ds_dir / ".meta.json", {
                    "id": dsid,
                    "name": info["name"],
                    "description": info["description"],
                    "datafield_count": fc,
                    "availability": sorted(avail_set),
                })
                if dsid in ds_field_map:
                    ds_field_map[dsid].to_csv(ds_dir / "datafields.csv", index=False)

            # --- subcategory-level ---
            sub_avail_sorted = sorted(sub_availability)
            _write_json(sub_dir / ".meta.json", {
                "id": sub_id,
                "name": sub["name"],
                "dataset_count": sub_ds_count,
                "datafield_count": sub_df_count,
                "availability": sub_avail_sorted,
            })
            if sub_ds_rows:
                pd.DataFrame(sub_ds_rows).to_csv(sub_dir / "datasets.csv", index=False)

            cat_ds_count += sub_ds_count
            cat_df_count += sub_df_count
            cat_availability.update(sub_availability)
            subcat_summaries.append({
                "id": sub_id, "name": sub["name"], "dataset_count": sub_ds_count,
            })

        # --- category-level ---
        cat_avail_sorted = sorted(cat_availability)
        _write_json(cat_dir / ".meta.json", {
            "id": cat_id,
            "name": cat["name"],
            "dataset_count": cat_ds_count,
            "datafield_count": cat_df_count,
            "availability": cat_avail_sorted,
            "subcategories": subcat_summaries,
        })
        if cat_ds_rows:
            pd.DataFrame(cat_ds_rows).to_csv(cat_dir / "datasets.csv", index=False)

        top_categories.append({
            "id": cat_id, "name": cat["name"],
            "dataset_count": cat_ds_count, "datafield_count": cat_df_count,
        })
        total_ds_count += cat_ds_count
        total_df_count += cat_df_count

    # --- top-level meta ---
    _write_json(out_root / ".meta.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "category_count": len(hierarchy),
        "dataset_count": total_ds_count,
        "datafield_count": total_df_count,
        "categories": top_categories,
    })

    print(f"Rebuilt {out_root}", file=sys.stderr)
    print(f"  {len(hierarchy)} categories, {total_ds_count} datasets, {total_df_count} datafields",
          file=sys.stderr)


def _write_json(path: Path, data: dict) -> None:
    """Write a dict as pretty-printed JSON."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    if "--stats" in sys.argv:
        cache_stats()
        return
    if "--rebuild" in sys.argv:
        rebuild_category_cache()
        return
    force = "--force" in sys.argv
    asyncio.run(warmup(force))


if __name__ == "__main__":
    main()
