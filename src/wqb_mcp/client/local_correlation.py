"""
Local correlation mixin — client-side correlation using fetched PnL data.

Counterpart of ``correlation.py`` which queries BRAIN's server-side
``/correlations/`` endpoints.  This mixin fetches daily returns via the
sibling mixin methods (``get_record_set_data``, ``get_user_alphas``),
caches results locally as per-alpha parquet + JSON files, and computes
Pearson correlation with numpy/pandas.

Cache layout::

    ~/.wqb_mcp/alpha_cache/
    ├── index.json
    └── alphas/
        ├── <alpha_id>/
        │   └── daily-pnl.parquet   # daily returns from BRAIN's "daily-pnl" recordset
        └── ...

index.json schema::

    {
        "version": 1,
        "updated_at": "2024-01-01T00:00:00+00:00",
        "alphas": {
            "<alpha_id>": {
                "name": "...",
                "instrument_type": "EQUITY",
                "region": "USA",
                "universe": "TOP3000",
                "is_power_pool": false,
                "sharpe": 1.23,
                "returns": 0.05,
                "turnover": 0.10,
                "fitness": 0.80,
                "margin": 0.01
            },
            ...
        }
    }

Key entry point: ``check_local_correlation`` — drop-in replacement for
``CorrelationMixin.check_correlation`` that returns the same
``CorrelationCheckResponse`` model.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .alpha import AlphaDetailsResponse
from .correlation import (
    CorrelationCheckResponse,
    CorrelationCheckResult,
    CorrelationData,
    CorrelationSchema,
    CorrelationSchemaName,
    CorrelationType,
    SchemaProperty,
    SelfCorrelationRecord,
)

_DEFAULT_DATA_DIR = Path.home() / ".wqb_mcp" / "alpha_cache"
_INDEX_VERSION = 1

_CORR_TYPE_TO_TAG = {
    CorrelationType.SELF: "SelfCorr",
    CorrelationType.POWER_POOL: "PPAC",
}


@dataclasses.dataclass
class AlphaIndexEntry:
    """Schema for a single alpha entry in the cache index."""
    name: Optional[str] = None
    instrument_type: Optional[str] = None
    region: str = ""
    universe: Optional[str] = None
    is_power_pool: bool = False
    sharpe: Optional[float] = None
    returns: Optional[float] = None
    turnover: Optional[float] = None
    fitness: Optional[float] = None
    margin: Optional[float] = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# AlphaCache — per-alpha parquet + JSON cache backed by a directory on disk
# ---------------------------------------------------------------------------

class AlphaCache:
    """Per-alpha parquet + JSON cache backed by a directory on disk."""

    def __init__(self, data_path: Optional[Path] = None):
        self.path = Path(data_path) if data_path else _DEFAULT_DATA_DIR
        self.path.mkdir(parents=True, exist_ok=True)
        self._index: Optional[Dict] = None  # lazy-loaded, in-memory cache
        self._all_returns: Optional[pd.DataFrame] = None

    # -- atomic write helpers -----------------------------------------------

    @staticmethod
    def _write_json(path: Path, obj: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(obj, f, indent=2, default=str)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    @staticmethod
    def _write_parquet(path: Path, df: pd.DataFrame) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".parquet.tmp")
        os.close(fd)
        try:
            df.to_parquet(tmp)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- index operations ---------------------------------------------------

    def load_index(self) -> Optional[Dict]:
        try:
            with open(self.path / "index.json") as f:
                index = json.load(f)
            if index.get("version") == _INDEX_VERSION:
                self._index = index
                return index
            return None
        except FileNotFoundError:
            return None

    def save_index(self) -> None:
        if self._index is None:
            return
        self._index["updated_at"] = _now_iso()
        self._write_json(self.path / "index.json", self._index)

    @property
    def index(self) -> Dict:
        """Lazy-load index from disk, or create an empty one."""
        if self._index is not None:
            return self._index
        loaded = self.load_index()
        if loaded is not None:
            return loaded
        self._index = {"version": _INDEX_VERSION, "updated_at": _now_iso(), "alphas": {}}
        return self._index

    def register_alpha(self, alpha_id: str, entry: AlphaIndexEntry) -> None:
        """Add or update an alpha entry in the in-memory index."""
        self.index["alphas"][alpha_id] = dataclasses.asdict(entry)

    # -- per-alpha I/O ------------------------------------------------------

    def _alpha_dir(self, alpha_id: str) -> Path:
        return self.path / "alphas" / alpha_id

    def _read_parquet(self, alpha_id: str, name: str) -> Optional[pd.DataFrame]:
        parquet_path = self._alpha_dir(alpha_id) / f"{name}.parquet"
        if not parquet_path.exists():
            return None
        return pd.read_parquet(parquet_path)

    def save_alpha(
        self,
        alpha_id: str,
        daily_returns: pd.DataFrame,
    ) -> None:
        """Persist one alpha's daily-pnl parquet."""
        alpha_path = self._alpha_dir(alpha_id)
        self._write_parquet(alpha_path / "daily-pnl.parquet", daily_returns)

    def load_daily_returns(self, alpha_ids: List[str]) -> pd.DataFrame:
        """Load daily-pnl parquet files for *alpha_ids* into a single wide DataFrame."""
        frames: List[pd.DataFrame] = []
        for alpha_id in alpha_ids:
            frame = self._read_parquet(alpha_id, "daily-pnl")
            if frame is None:
                continue
            if alpha_id not in frame.columns:
                if len(frame.columns) == 1:
                    frame.columns = [alpha_id]
                else:
                    continue
            else:
                frame = frame[[alpha_id]]
            frames.append(frame)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, axis=1).sort_index()

    # -- derived views ------------------------------------------------------

    @property
    def all_returns(self) -> pd.DataFrame:
        """Lazy-load all cached daily returns into a single wide DataFrame."""
        if self._all_returns is not None:
            return self._all_returns
        all_ids = list(self.index.get("alphas", {}).keys())
        self._all_returns = self.load_daily_returns(all_ids) if all_ids else pd.DataFrame()
        return self._all_returns

    def _group_alpha_ids_by_region(self, tag: str, region: Optional[str] = None) -> Dict[str, List[str]]:
        """Derive ``{region: [alpha_ids]}`` from the index.

        tag="PPAC" -> power pool alphas, "SelfCorr" -> non-power-pool.
        If *region* is given, only that region is included.
        """
        by_region: Dict[str, List[str]] = defaultdict(list)
        for alpha_id, raw in self.index.get("alphas", {}).items():
            alpha_region = raw.get("region", "")
            if not alpha_region:
                continue
            is_pp = raw.get("is_power_pool", False)
            if tag == "PPAC" and not is_pp:
                continue
            if tag == "SelfCorr" and is_pp:
                continue
            if region and alpha_region != region:
                continue
            by_region[alpha_region].append(alpha_id)
        return dict(by_region)

    def fetch_correlation(
        self,
        alpha_id: str,
        candidate_returns: pd.DataFrame,
        region: str,
        corr_type: CorrelationType,
        years: int = 4,
    ) -> CorrelationData:
        """Local equivalent of ``CorrelationMixin._fetch_correlation``.

        Computes Pearson correlation of a candidate alpha against the cached
        baseline set and returns ``CorrelationData`` matching the remote API
        schema.  No threshold logic — the caller decides pass/fail.
        """
        if corr_type == CorrelationType.PROD:
            raise ValueError("PROD correlation is not supported locally.")

        tag = _CORR_TYPE_TO_TAG[corr_type]
        alpha_ids_by_region = self._group_alpha_ids_by_region(tag, region=region)
        cached_returns = self.all_returns

        if cached_returns.empty or candidate_returns.empty or not region:
            return CorrelationData()

        baseline_alpha_ids = [
            col for col in alpha_ids_by_region.get(region, [])
            if col in cached_returns.columns
        ]
        if not baseline_alpha_ids:
            return CorrelationData()

        candidate_trimmed = _trim_returns(candidate_returns, years=years)
        baseline_trimmed = _trim_returns(cached_returns[baseline_alpha_ids], years=years)
        common_dates = candidate_trimmed.index.intersection(baseline_trimmed.index)
        if len(common_dates) < 30:
            return CorrelationData()

        candidate_series = candidate_trimmed.loc[common_dates, alpha_id]
        baseline_block = baseline_trimmed.loc[common_dates, baseline_alpha_ids]

        correlations = baseline_block.corrwith(candidate_series)
        correlations = correlations.replace([np.inf, -np.inf], np.nan).dropna()
        correlations = correlations.sort_values(ascending=False)
        if correlations.empty:
            return CorrelationData()

        props = [
            SchemaProperty(name=n, title=n, type="STRING")
            for n in SelfCorrelationRecord.model_fields
        ]
        schema = CorrelationSchema(
            name=CorrelationSchemaName.SELF,
            title="Self Correlation",
            properties=props,
        )

        alphas_index = self.index.get("alphas", {})
        records = []
        for partner_id, corr_value in correlations.items():
            raw = alphas_index.get(partner_id, {})
            records.append([
                str(partner_id),
                raw.get("name"),
                raw.get("instrument_type"),
                raw.get("region") or None,
                raw.get("universe"),
                round(float(corr_value), 4),
                raw.get("sharpe"),
                raw.get("returns"),
                raw.get("turnover"),
                raw.get("fitness"),
                raw.get("margin"),
            ])

        return CorrelationData(
            schema=schema,
            max=round(float(correlations.iloc[0]), 4),
            min=round(float(correlations.iloc[-1]), 4),
            records=records,
        )


# ---------------------------------------------------------------------------
# Pure-compute helpers (no I/O, no self)
# ---------------------------------------------------------------------------

def _trim_returns(returns: pd.DataFrame, years: int = 4) -> pd.DataFrame:
    """Keep only the last *years* of daily returns.

    Cutoff snapped to Jan 1 of the nearest year boundary to match BRAIN's
    year-aligned lookback window.
    """
    if returns.empty:
        return returns
    index = pd.to_datetime(returns.index)
    last = index.max()
    anchor_year = last.year + 1 if last.month >= 7 else last.year
    cutoff = pd.Timestamp(f"{anchor_year - years}-01-01")
    return returns[index >= cutoff]


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------

class LocalCorrelationMixin:
    """Client-side correlation using locally-fetched & cached daily returns.

    Primary entry point: ``check_local_correlation``.
    """

    # -- fetch helpers ------------------------------------------------------

    async def _fetch_daily_returns(self, alpha_id: str) -> pd.DataFrame:
        """Fetch daily returns for one alpha from BRAIN's ``daily-pnl`` recordset.

        Returns a single-column DataFrame indexed by Date.
        """
        recordset = await self.get_record_set_data(alpha_id, "daily-pnl")
        frame = pd.DataFrame(recordset.rows_as_dicts())
        frame = frame.rename(columns={"date": "Date", "pnl": alpha_id})
        return frame[["Date", alpha_id]].set_index("Date")

    async def _fetch_all_os_alphas(self) -> List[AlphaDetailsResponse]:
        """Paginate ``get_user_alphas(stage="OS")`` to completion."""
        fetched: List[AlphaDetailsResponse] = []
        offset = 0
        total: Optional[int] = None
        limit = 100
        while total is None or len(fetched) < total:
            resp = await self.get_user_alphas(
                stage="OS", limit=limit, offset=offset, order="-dateSubmitted",
            )
            if total is None:
                total = resp.count
            fetched.extend(resp.results)
            if len(resp.results) < limit:
                break
            offset += limit
        return fetched[:total]

    # -- baseline sync ------------------------------------------------------

    async def _sync_baseline(self, cache: AlphaCache) -> Dict:
        """Ensure OS baseline cache is up-to-date. Returns the live index dict."""
        loaded = cache.load_index()
        cached_ids = set(loaded["alphas"]) if loaded else set()

        if not loaded:
            self.log("No cache found, downloading full OS alpha data...", "INFO")
        else:
            self.log(f"Loaded cached OS baseline: {len(cached_ids)} alphas", "INFO")

        os_alphas = await self._fetch_all_os_alphas()
        current_ids = {a.id for a in os_alphas}

        # Remove stale entries (no longer OS)
        stale_ids = cached_ids - current_ids
        if stale_ids:
            for stale_id in stale_ids:
                cache.index["alphas"].pop(stale_id, None)
                alpha_dir = cache._alpha_dir(stale_id)
                if alpha_dir.exists():
                    shutil.rmtree(alpha_dir, ignore_errors=True)
            self.log(f"Removed {len(stale_ids)} stale alphas from cache", "INFO")

        # Download new alphas
        new_alphas = [a for a in os_alphas if a.id not in cached_ids]
        if not new_alphas and not stale_ids:
            if loaded is None:
                self.log("No OS alpha data available", "WARNING")
            return cache.index

        synced = 0
        for alpha in new_alphas:
            try:
                settings = alpha.settings
                is_stats = alpha.is_
                entry = AlphaIndexEntry(
                    name=alpha.name,
                    instrument_type=settings.instrumentType,
                    region=settings.region,
                    universe=settings.universe,
                    is_power_pool=alpha.is_power_pool,
                    sharpe=is_stats.sharpe,
                    returns=is_stats.returns,
                    turnover=is_stats.turnover,
                    fitness=is_stats.fitness,
                    margin=is_stats.margin,
                )
                daily_returns = await self._fetch_daily_returns(alpha.id)
                cache.save_alpha(
                    alpha.id, daily_returns,
                )
                cache.register_alpha(alpha.id, entry)
                synced += 1
            except Exception as e:
                self.log(f"Failed to sync alpha {alpha.id}: {e}", "WARNING")

        if synced > 0 or stale_ids:
            cache.save_index()
        self.log(
            f"Synced {synced}/{len(new_alphas)} new, removed {len(stale_ids)} stale, "
            f"total: {len(cache.index['alphas'])}",
            "INFO",
        )
        return cache.index

    # -- public API ---------------------------------------------------------

    @staticmethod
    def _to_check_result(
        corr_data: CorrelationData, threshold: float,
    ) -> CorrelationCheckResult:
        """Convert a ``CorrelationData`` into a pass/fail check result."""
        if corr_data.max is None:
            return CorrelationCheckResult(passes_check=True)
        passes_check = corr_data.max < threshold
        count = None
        top_correlations = None
        if corr_data.is_self_type and corr_data.parsed_records:
            count = len(corr_data.parsed_records)
            top_correlations = corr_data.parsed_records[:3]
        return CorrelationCheckResult(
            max_correlation=corr_data.max,
            passes_check=passes_check,
            count=count,
            top_correlations=top_correlations,
        )

    def _build_check_response(
        self,
        alpha_id: str,
        cache: AlphaCache,
        candidate_returns: pd.DataFrame,
        region: str,
        check_types: List[CorrelationType],
        threshold: float,
        years: int,
    ) -> CorrelationCheckResponse:
        """Build a full check response for one alpha across all check_types."""
        checks: Dict[CorrelationType, CorrelationCheckResult] = {}
        all_passed = True
        for check_type in check_types:
            corr_data = cache.fetch_correlation(
                alpha_id, candidate_returns, region, check_type, years=years,
            )
            result = self._to_check_result(corr_data, threshold)
            checks[check_type] = result
            if not result.passes_check:
                all_passed = False
        return CorrelationCheckResponse(
            alpha_id=alpha_id,
            threshold=threshold,
            check_types=check_types,
            checks=checks,
            all_passed=all_passed,
        )

    async def check_local_correlation(
        self,
        alpha_id: str,
        check_types: Optional[List[CorrelationType]] = None,
        threshold: float = 0.7,
        years: int = 4,
    ) -> CorrelationCheckResponse:
        """Local equivalent of ``CorrelationMixin.check_correlation``.

        Fetches the target alpha's daily returns, syncs the OS baseline
        cache, and computes Pearson correlation locally.

        Supports SELF and POWER_POOL only. Raises ValueError for PROD.
        """
        await self.ensure_authenticated()
        if check_types is None:
            check_types = [CorrelationType.SELF]

        if CorrelationType.PROD in check_types:
            raise ValueError(
                "PROD correlation is not supported locally. "
                "Use mode='remote' for PROD checks."
            )

        cache = AlphaCache()
        await self._sync_baseline(cache)

        candidate_returns, alpha_detail = await asyncio.gather(
            self._fetch_daily_returns(alpha_id),
            self.get_alpha_details(alpha_id),
        )
        region = alpha_detail.settings.region

        return self._build_check_response(
            alpha_id, cache, candidate_returns, region,
            check_types, threshold, years,
        )

    async def batch_check_local_correlation(
        self,
        alpha_ids: List[str],
        check_types: Optional[List[CorrelationType]] = None,
        threshold: float = 0.7,
        years: int = 4,
    ) -> Dict[str, Any]:
        """Batch local correlation check for multiple alphas.

        For each alpha, computes baseline correlation (same as
        ``check_local_correlation``).  Additionally computes a pairwise
        correlation matrix between the candidate alphas.

        Returns a dict with:
            - ``intra_correlation``: pd.DataFrame —
              pairwise correlation matrix between candidates.
            - ``inter_correlation``: Dict[str, CorrelationCheckResponse] —
              each candidate vs the cached baseline alphas.
        """
        await self.ensure_authenticated()
        if check_types is None:
            check_types = [CorrelationType.SELF]
        if CorrelationType.PROD in check_types:
            raise ValueError(
                "PROD correlation is not supported locally. "
                "Use mode='remote' for PROD checks."
            )

        cache = AlphaCache()
        await self._sync_baseline(cache)

        # Fetch returns and regions for all candidates in parallel
        returns_tasks = [self._fetch_daily_returns(aid) for aid in alpha_ids]
        detail_tasks = [self.get_alpha_details(aid) for aid in alpha_ids]
        all_returns, all_details = await asyncio.gather(
            asyncio.gather(*returns_tasks),
            asyncio.gather(*detail_tasks),
        )
        candidate_returns_list = list(all_returns)
        regions: Dict[str, str] = {
            aid: detail.settings.region
            for aid, detail in zip(alpha_ids, all_details)
        }

        # Merge into a single DataFrame
        candidate_returns = pd.concat(candidate_returns_list, axis=1)

        # Inter-correlation: each candidate vs baseline alphas
        inter_correlation: Dict[str, CorrelationCheckResponse] = {}
        for alpha_id in alpha_ids:
            inter_correlation[alpha_id] = self._build_check_response(
                alpha_id, cache, candidate_returns[[alpha_id]],
                regions[alpha_id], check_types, threshold, years,
            )

        # Intra-correlation: pairwise between candidates
        trimmed = _trim_returns(candidate_returns, years=years)
        intra_correlation = trimmed.corr()

        return {
            "intra_correlation": intra_correlation,
            "inter_correlation": inter_correlation,
        }
