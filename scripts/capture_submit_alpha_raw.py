"""Capture raw submit-alpha endpoint responses for schema documentation.

Run in an authenticated environment:
    python3 scripts/capture_submit_alpha_raw.py
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

    # --- 1. Test specific IS alphas ---
    test_alpha_ids = ["Gr02KvoO", "xAwLG7kl", "d58MKdn2"]

    for alpha_id in test_alpha_ids:
        key = f"submit_{alpha_id}"
        print(f"\n--- Submitting {alpha_id} ---")
        submit_resp = brain_client.session.post(
            f"{brain_client.base_url}/alphas/{alpha_id}/submit"
        )
        result[key] = {
            "url": str(submit_resp.url),
            "method": "POST",
            "status_code": submit_resp.status_code,
            "headers": dict(submit_resp.headers),
            "body": _safe_json(submit_resp),
        }
        print(f"  status: {submit_resp.status_code}")

        # If 201 with Location, poll until checks resolve
        location = submit_resp.headers.get("Location", "")
        retry_after = submit_resp.headers.get("Retry-After", "")
        # API returns http:// Location but server requires https://
        if location.startswith("http://"):
            location = "https://" + location[len("http://"):]
        if submit_resp.status_code == 201 and location:
            polls: List[Dict[str, Any]] = []
            for i in range(15):
                wait = float(retry_after) if retry_after else 2.0
                time.sleep(max(wait, 1.0))
                poll_resp = brain_client.session.get(location)
                retry_after = poll_resp.headers.get("Retry-After")
                poll_record = {
                    "poll": i + 1,
                    "url": location,
                    "method": "GET",
                    "status_code": poll_resp.status_code,
                    "retry_after": retry_after,
                    "headers": dict(poll_resp.headers),
                    "body": _safe_json(poll_resp),
                }
                polls.append(poll_record)
                print(f"  poll {i + 1}: status={poll_resp.status_code} Retry-After={retry_after}")
                if retry_after in (None, "0", "0.0"):
                    break
            result[f"{key}_polls"] = polls

    # --- 3. Find an OS alpha and try re-submitting (capture error) ---
    os_resp = brain_client.session.get(
        f"{brain_client.base_url}/users/self/alphas",
        params={"stage": "OS", "limit": 1},
    )
    result["find_os_alpha"] = {
        "url": str(os_resp.url),
        "status_code": os_resp.status_code,
        "body": _safe_json(os_resp),
    }

    os_alpha_id = None
    os_body = result["find_os_alpha"]["body"]
    if isinstance(os_body, dict):
        results = os_body.get("results") or []
        if results and isinstance(results[0], dict):
            os_alpha_id = results[0].get("id")
    result["os_alpha_id"] = os_alpha_id

    if os_alpha_id:
        resubmit_resp = brain_client.session.post(
            f"{brain_client.base_url}/alphas/{os_alpha_id}/submit"
        )
        result["resubmit_os"] = {
            "url": str(resubmit_resp.url),
            "method": "POST",
            "status_code": resubmit_resp.status_code,
            "headers": dict(resubmit_resp.headers),
            "body": _safe_json(resubmit_resp),
        }
    else:
        result["resubmit_os"] = {"skipped": True, "reason": "no OS alpha found"}

    # --- 4. Try submitting a bogus alpha ID (capture 404) ---
    bogus_resp = brain_client.session.post(
        f"{brain_client.base_url}/alphas/BOGUS_ID_000/submit"
    )
    result["submit_bogus"] = {
        "url": str(bogus_resp.url),
        "method": "POST",
        "status_code": bogus_resp.status_code,
        "headers": dict(bogus_resp.headers),
        "body": _safe_json(bogus_resp),
    }

    out = Path("assets/logs/submit_alpha_raw_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved → {out}")


if __name__ == "__main__":
    asyncio.run(main())
