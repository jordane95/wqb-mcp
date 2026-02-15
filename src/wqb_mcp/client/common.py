"""Shared client helpers."""

from typing import Any


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
