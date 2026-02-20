"""
Local TTL-based cache for static BRAIN platform data.

Cache layout::

    ~/.wqb_mcp/cache/
    ├── cache_index.json
    ├── data/
    │   └── {instrument_type}/{region}/{universe}/D{delay}/
    │       ├── .meta.json
    │       ├── datasets.csv
    │       ├── datafields.csv
    │       └── dataset/
    │           └── {dataset_id}/
    │               ├── .meta.json
    │               └── datafields.csv
    ├── operators/
    │   ├── .meta.json
    │   └── operators.csv
    ├── platform_settings/
    │   ├── .meta.json
    │   └── platform_settings.json
    ├── documentations/
    │   ├── .meta.json
    │   ├── index.json
    │   └── pages/{page_id}.json
    ├── glossary/
    │   ├── .meta.json
    │   └── glossary.json
    └── pyramid_multipliers/
        ├── .meta.json
        └── pyramid_multipliers.csv
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd


_DEFAULT_ROOT = Path.home() / ".wqb_mcp" / "cache"
_INDEX_VERSION = 1


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _log(message: str, level: str = "INFO") -> None:
    try:
        print(f"[{level}] [StaticCache] {message}", file=sys.stderr)
    except Exception:
        pass


class StaticCache:
    """TTL-based local cache for static BRAIN platform data."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else _DEFAULT_ROOT
        self._index: Optional[Dict[str, Any]] = None  # lazy-loaded

    # -- atomic write helpers ------------------------------------------------

    @staticmethod
    def _atomic_write_text(path: Path, content: str) -> None:
        """Write text atomically via tempfile + os.replace."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    # -- index operations ----------------------------------------------------

    @property
    def _index_path(self) -> Path:
        return self.root / "cache_index.json"

    def _load_index(self) -> Dict[str, Any]:
        """Load central index from disk, or create empty."""
        if self._index is not None:
            return self._index
        try:
            with open(self._index_path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") == _INDEX_VERSION:
                self._index = data
                return self._index
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        self._index = {"version": _INDEX_VERSION, "entries": {}}
        return self._index

    def _save_index(self) -> None:
        idx = self._load_index()
        self._atomic_write_text(self._index_path, json.dumps(idx, indent=2, default=str))

    # -- .meta.json helpers --------------------------------------------------

    def _meta_path(self, file_subpath: str) -> Path:
        """Return the .meta.json path for the folder containing file_subpath."""
        return self.root / Path(file_subpath).parent / ".meta.json"

    def _load_meta(self, file_subpath: str) -> Dict[str, Any]:
        meta_path = self._meta_path(file_subpath)
        try:
            with open(meta_path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_meta(self, file_subpath: str, meta: Dict[str, Any]) -> None:
        meta_path = self._meta_path(file_subpath)
        self._atomic_write_text(meta_path, json.dumps(meta, indent=2, default=str))

    def _meta_key(self, file_subpath: str) -> str:
        """Relative filename within its parent folder, used as key in .meta.json."""
        return Path(file_subpath).name

    # -- validity check ------------------------------------------------------

    def _is_entry_valid(self, entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is still within its TTL."""
        try:
            cached_at = datetime.fromisoformat(entry["cached_at"])
            ttl_days = entry["ttl_days"]
            return _now() < cached_at + timedelta(days=ttl_days)
        except (KeyError, ValueError, TypeError):
            return False

    # -- public API ----------------------------------------------------------

    def is_valid(self, cache_key: str) -> bool:
        """Check if entry exists in index and is not expired."""
        idx = self._load_index()
        entry = idx["entries"].get(cache_key)
        if entry is None:
            return False
        return self._is_entry_valid(entry)

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Return index entry if valid, else None."""
        idx = self._load_index()
        entry = idx["entries"].get(cache_key)
        if entry is None or not self._is_entry_valid(entry):
            return None
        file_path = self.root / entry["path"]
        if not file_path.exists():
            return None
        return entry

    # -- DataFrame-based read/write (tabular data) --------------------------

    @staticmethod
    def _parse_cell(value: Any) -> Any:
        """Try to parse a CSV cell as JSON (for nested dicts/lists).

        Empty strings are converted to None (CSV stores None as '').
        """
        if not isinstance(value, str):
            return value
        if value == "":
            return None
        s = value.strip()
        if s and s[0] in ('{', '[', '"'):
            try:
                return json.loads(s)
            except (json.JSONDecodeError, ValueError):
                pass
        return value

    def read_table(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Read cached CSV as list of dicts if valid, else None.

        Nested dicts/lists stored as JSON strings in CSV cells are parsed back automatically.
        """
        entry = self.get(cache_key)
        if entry is None:
            return None
        file_path = self.root / entry["path"]
        try:
            df = pd.read_csv(file_path, keep_default_na=False)
            rows = df.to_dict(orient="records")
            # Parse JSON-encoded cells back into dicts/lists
            rows = [
                {k: self._parse_cell(v) for k, v in row.items()}
                for row in rows
            ]
            _log(f"cache HIT  {cache_key} ({len(rows)} rows)")
            return rows
        except Exception as exc:
            _log(f"cache read error {cache_key}: {exc}", "WARN")
            return None

    def write_table(
        self,
        cache_key: str,
        rows: List[Dict[str, Any]],
        ttl_days: int,
        file_subpath: str,
    ) -> None:
        """Write list of dicts as CSV. Nested dicts/lists are JSON-encoded in cells."""
        if not rows:
            return
        # JSON-encode any nested values so CSV cells are parseable on read
        csv_rows = [
            {k: json.dumps(v, default=str) if isinstance(v, (dict, list)) else v
             for k, v in row.items()}
            for row in rows
        ]
        df = pd.DataFrame(csv_rows)
        csv_path = self.root / file_subpath
        self._atomic_write_text(csv_path, df.to_csv(index=False))

        self._update_index_and_meta(cache_key, file_subpath, ttl_days, record_count=len(df))
        _log(f"cache WRITE {cache_key} ({len(df)} rows -> {file_subpath})")

    # -- JSON read/write (non-tabular data) ---------------------------------

    def read_dict(self, cache_key: str) -> Optional[Any]:
        """Read cached JSON if valid, else None."""
        entry = self.get(cache_key)
        if entry is None:
            return None
        file_path = self.root / entry["path"]
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            _log(f"cache HIT  {cache_key}")
            return data
        except Exception as exc:
            _log(f"cache read error {cache_key}: {exc}", "WARN")
            return None

    def write_dict(
        self,
        cache_key: str,
        data: Any,
        ttl_days: int,
        file_subpath: str,
    ) -> None:
        """Write JSON data, update .meta.json and cache_index.json."""
        file_path = self.root / file_subpath
        self._atomic_write_text(file_path, json.dumps(data, indent=2, default=str))
        self._update_index_and_meta(cache_key, file_subpath, ttl_days)
        _log(f"cache WRITE {cache_key} -> {file_subpath}")

    # -- index/meta update helper -------------------------------------------

    def _update_index_and_meta(
        self, cache_key: str, file_subpath: str, ttl_days: int, record_count: Optional[int] = None,
    ) -> None:
        now_iso = _now_iso()
        entry_data: Dict[str, Any] = {
            "cached_at": now_iso,
            "ttl_days": ttl_days,
            "path": file_subpath,
        }
        meta_entry: Dict[str, Any] = {
            "cached_at": now_iso,
            "ttl_days": ttl_days,
        }
        if record_count is not None:
            entry_data["record_count"] = record_count
            meta_entry["record_count"] = record_count

        idx = self._load_index()
        idx["entries"][cache_key] = entry_data
        self._save_index()

        meta = self._load_meta(file_subpath)
        meta[self._meta_key(file_subpath)] = meta_entry
        self._save_meta(file_subpath, meta)

    def invalidate(self, cache_key: str) -> None:
        """Remove a single cache entry."""
        idx = self._load_index()
        entry = idx["entries"].pop(cache_key, None)
        if entry:
            self._save_index()
            file_path = self.root / entry["path"]
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass
            _log(f"cache INVALIDATE {cache_key}")

    def invalidate_all(self) -> None:
        """Remove all cache entries and files."""
        self._index = {"version": _INDEX_VERSION, "entries": {}}
        self._save_index()
        # Remove all data directories but keep cache_index.json
        for child in self.root.iterdir():
            if child.name == "cache_index.json":
                continue
            if child.is_dir():
                import shutil
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass
        _log("cache INVALIDATE ALL")
