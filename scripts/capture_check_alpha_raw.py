"""Capture raw GET /alphas/{id}/check endpoint responses for schema documentation.

The /check endpoint uses a polling pattern:
- 200 with Retry-After header → checks still running
- 200 without Retry-After → checks complete, body has results
- 403 → checks resolved with failures

Run in an authenticated environment:
    python3 scripts/capture_check_alpha_raw.py
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List

from wqb_mcp.client import brain_client


def _safe_json(response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"_non_json_body": (response.text or "")[:2000]}


async def main() -> None:
    await brain_client.ensure_authenticated()

    result: Dict[str, Any] = {}

    # --- 1. Test IS alphas (should have checks to run) ---
    test_alpha_ids = ["MPlE0kbL", "QPrxWqE5"]

    for alpha_id in test_alpha_ids:
        key = f"check_{alpha_id}"
        print(f"\n--- Checking {alpha_id} ---")

        polls: List[Dict[str, Any]] = []
        for i in range(20):
            resp = brain_client.session.get(
                f"{brain_client.base_url}/alphas/{alpha_id}/check"
            )
            retry_after = resp.headers.get("Retry-After")
            poll_record = {
                "poll": i + 1,
                "url": str(resp.url),
                "method": "GET",
                "status_code": resp.status_code,
                "retry_after": retry_after,
                "headers": dict(resp.headers),
                "body": _safe_json(resp),
            }
            polls.append(poll_record)
            print(f"  poll {i + 1}: status={resp.status_code} Retry-After={retry_after} body_len={len(resp.text)}")

            done = retry_after in (None, "0", "0.0")
            if done or resp.status_code in (403, 404):
                break

            wait = float(retry_after) if retry_after else 1.0
            time.sleep(max(wait, 1.0))

        result[key] = polls

    # --- 2. Try checking a bogus alpha ID (capture 404) ---
    bogus_resp = brain_client.session.get(
        f"{brain_client.base_url}/alphas/BOGUS_ID_000/check"
    )
    result["check_bogus"] = {
        "url": str(bogus_resp.url),
        "method": "GET",
        "status_code": bogus_resp.status_code,
        "headers": dict(bogus_resp.headers),
        "body": _safe_json(bogus_resp),
    }
    print(f"\n--- Bogus ID: status={bogus_resp.status_code} ---")

    # --- 3. Try checking an OS alpha ---
    os_resp = brain_client.session.get(
        f"{brain_client.base_url}/users/self/alphas",
        params={"stage": "OS", "limit": 1},
    )
    os_body = os_resp.json() if os_resp.status_code == 200 else {}
    os_results = os_body.get("results") or []
    os_alpha_id = os_results[0]["id"] if os_results else None

    if os_alpha_id:
        print(f"\n--- Checking OS alpha {os_alpha_id} ---")
        os_check_resp = brain_client.session.get(
            f"{brain_client.base_url}/alphas/{os_alpha_id}/check"
        )
        result["check_os_alpha"] = {
            "alpha_id": os_alpha_id,
            "url": str(os_check_resp.url),
            "method": "GET",
            "status_code": os_check_resp.status_code,
            "retry_after": os_check_resp.headers.get("Retry-After"),
            "headers": dict(os_check_resp.headers),
            "body": _safe_json(os_check_resp),
        }
        print(f"  status={os_check_resp.status_code}")
    else:
        result["check_os_alpha"] = {"skipped": True, "reason": "no OS alpha found"}

    out = Path("assets/logs/check_alpha_raw_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved → {out}")


if __name__ == "__main__":
    asyncio.run(main())
