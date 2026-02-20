"""Shared utilities across client and tools."""

from typing import Any, Dict, List
from pathlib import Path

import pandas as pd


def parse_json_or_error(response: Any, endpoint: str) -> Any:
    """Parse JSON payload or raise a detailed parsing error."""
    try:
        return response.json()
    except Exception as e:
        preview = (response.text or "")[:200]
        ct = response.headers.get("Content-Type")
        raise ValueError(
            f"Non-JSON response from {endpoint} | status={response.status_code} | "
            f"content-type={ct} | body={preview!r} | error={e}"
        ) from e


def save_csv(rows: List[Dict[str, Any]], path: Path) -> int:
    """Save rows to CSV and return column count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return 0

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return len(df.columns)


def dataframe_markdown_preview(
    rows: List[Dict[str, Any]],
    preferred_cols: List[str],
    max_rows: int = 5,
    fallback_cols: int = 3,
) -> str:
    """Render a markdown table preview from row dicts."""
    if not rows:
        return "(no rows)"
    df = pd.DataFrame(rows).head(max_rows)
    preview_cols = [col for col in preferred_cols if col in df.columns]
    if not preview_cols:
        preview_cols = df.columns.tolist()[:fallback_cols]
    return df[preview_cols].to_markdown(index=False)
