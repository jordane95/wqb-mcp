"""Capture a live submit-alpha flow for a specific alpha.

Usage:
    python3 scripts/capture_submit_alpha_live.py
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

    alpha_id = "1YV8jJaR"
    result: Dict[str, Any] = {"alpha_id": alpha_id}

    # POST submit
    submit_resp = brain_client.session.post(
        f"{brain_client.base_url}/alphas/{alpha_id}/submit"
    )
    result["post"] = {
        "status_code": submit_resp.status_code,
        "headers": dict(submit_resp.headers),
        "body": _safe_json(submit_resp),
    }
    print(f"POST status: {submit_resp.status_code}")

    # Poll if 201
    if submit_resp.status_code == 201:
        poll_url = f"{brain_client.base_url}/alphas/{alpha_id}/submit"
        retry_after = submit_resp.headers.get("Retry-After", "1")
        polls: List[Dict[str, Any]] = []
        for i in range(30):
            wait = float(retry_after) if retry_after else 1.0
            time.sleep(max(wait, 1.0))
            poll_resp = brain_client.session.get(poll_url)
            retry_after = poll_resp.headers.get("Retry-After")
            poll_record = {
                "poll": i + 1,
                "status_code": poll_resp.status_code,
                "retry_after": retry_after,
                "body": _safe_json(poll_resp),
            }
            polls.append(poll_record)
            print(f"  poll {i + 1}: status={poll_resp.status_code} Retry-After={retry_after}")
            if retry_after in (None, "0", "0.0"):
                break
        result["polls"] = polls

    out = Path("assets/logs/submit_alpha_live_1YV8jJaR.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved → {out}")


if __name__ == "__main__":
    asyncio.run(main())
