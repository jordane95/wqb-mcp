"""Capture raw correlation endpoint responses for schema documentation.

Hits /alphas/{id}/correlations/{type} for prod, self, and power-pool,
plus error cases (bogus alpha ID, IS-only alpha).

Run in an authenticated environment:
    python3 scripts/capture_correlation_raw.py
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from wqb_mcp.client import brain_client

# Known alpha IDs for testing
OS_ALPHA_ID = "QPrxWqE5"       # An OS (submitted) alpha
IS_ALPHA_ID = "Gr02KvoO"       # An IS (unsubmitted) alpha
BOGUS_ALPHA_ID = "BOGUS_ID_000"


def _safe_json(response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"_non_json_body": (response.text or "")[:2000]}


def _capture_endpoint(alpha_id: str, corr_type: str, max_polls: int = 15) -> Dict[str, Any]:
    """Hit a single correlation endpoint with polling until data is ready."""
    url = f"{brain_client.base_url}/alphas/{alpha_id}/correlations/{corr_type}"
    print(f"  GET {url}")

    polls: List[Dict[str, Any]] = []
    final_body: Any = None
    final_status: int = 0
    final_headers: Dict[str, str] = {}

    for i in range(max_polls):
        resp = brain_client.session.get(url)
        final_status = resp.status_code
        final_headers = dict(resp.headers)
        retry_after = resp.headers.get("Retry-After")
        body = _safe_json(resp)

        poll_record = {
            "poll": i + 1,
            "status_code": resp.status_code,
            "retry_after": retry_after,
            "content_length": resp.headers.get("Content-Length"),
            "has_body": bool(resp.text.strip()),
        }
        polls.append(poll_record)
        print(f"    poll {i + 1}: status={resp.status_code} Retry-After={retry_after} body={bool(resp.text.strip())}")

        if resp.text.strip():
            final_body = body
            break

        if resp.status_code >= 400:
            final_body = body
            break

        wait = float(retry_after) if retry_after else 1.0
        time.sleep(max(wait, 0.5))
    else:
        final_body = {"_timeout": f"No data after {max_polls} polls"}

    return {
        "url": url,
        "method": "GET",
        "status_code": final_status,
        "headers": final_headers,
        "body": final_body,
        "polls": polls,
    }


async def main() -> None:
    await brain_client.ensure_authenticated()

    result: Dict[str, Any] = {}

    # --- 1. OS alpha: all three correlation types ---
    result["os_alpha_id"] = OS_ALPHA_ID
    for corr_type in ("prod", "self", "power-pool"):
        key = f"os_{corr_type.replace('-', '_')}"
        print(f"\n--- {corr_type} correlation for OS alpha {OS_ALPHA_ID} ---")
        result[key] = _capture_endpoint(OS_ALPHA_ID, corr_type)

    # --- 2. IS alpha: all three correlation types ---
    result["is_alpha_id"] = IS_ALPHA_ID
    for corr_type in ("prod", "self", "power-pool"):
        key = f"is_{corr_type.replace('-', '_')}"
        print(f"\n--- {corr_type} correlation for IS alpha {IS_ALPHA_ID} ---")
        result[key] = _capture_endpoint(IS_ALPHA_ID, corr_type)

    # --- 3. Bogus alpha ID (expect error) ---
    print(f"\n--- Bogus alpha ID {BOGUS_ALPHA_ID} ---")
    result["bogus_self"] = _capture_endpoint(BOGUS_ALPHA_ID, "self")

    # --- Save ---
    out = Path("assets/logs/correlation_raw_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    asyncio.run(main())
