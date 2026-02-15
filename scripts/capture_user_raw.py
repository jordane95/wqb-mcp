"""Capture raw user endpoint responses for schema documentation.

Run in an authenticated environment:
    python3 scripts/capture_user_raw.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from wqb_mcp.client import brain_client


def _safe_json(response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"_non_json_body": (response.text or "")[:4000]}


def _record(method: str, url: str, response, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "request": {
            "method": method,
            "url": url,
            "params": params or {},
        },
        "response": {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "json_or_text": _safe_json(response),
        },
    }


async def main() -> None:
    await brain_client.ensure_authenticated()
    base = brain_client.base_url
    out: Dict[str, Any] = {"endpoints": {}, "derived": {}}

    # /users/self
    self_url = f"{base}/users/self"
    self_resp = brain_client.session.get(self_url)
    out["endpoints"]["users_self"] = _record("GET", self_url, self_resp)
    user_id = None
    if self_resp.status_code == 200:
        self_json = _safe_json(self_resp)
        if isinstance(self_json, dict):
            user_id = self_json.get("id")
    out["derived"]["user_id"] = user_id

    # /users/self/alphas
    alphas_url = f"{base}/users/self/alphas"
    alphas_params = {"stage": "OS", "limit": 20, "offset": 0}
    alphas_resp = brain_client.session.get(alphas_url, params=alphas_params)
    out["endpoints"]["users_self_alphas"] = _record("GET", alphas_url, alphas_resp, params=alphas_params)

    # /users/self/messages
    messages_url = f"{base}/users/self/messages"
    messages_params = {"limit": 10, "offset": 0}
    messages_resp = brain_client.session.get(messages_url, params=messages_params)
    out["endpoints"]["messages"] = _record("GET", messages_url, messages_resp, params=messages_params)

    # /users/{id}/activities
    activities_user = user_id or "self"
    activities_url = f"{base}/users/{activities_user}/activities"
    activities_params = {"grouping": "day"}
    activities_resp = brain_client.session.get(activities_url, params=activities_params)
    out["endpoints"]["activities"] = _record("GET", activities_url, activities_resp, params=activities_params)

    # /users/self/activities/pyramid-multipliers
    multipliers_url = f"{base}/users/self/activities/pyramid-multipliers"
    multipliers_resp = brain_client.session.get(multipliers_url)
    out["endpoints"]["pyramid_multipliers"] = _record("GET", multipliers_url, multipliers_resp)

    # /users/self/activities/pyramid-alphas
    pyramid_params = {}
    p1 = f"{base}/users/self/activities/pyramid-alphas"
    r1 = brain_client.session.get(p1, params=pyramid_params)
    out["endpoints"]["pyramid_alphas"] = _record("GET", p1, r1, params=pyramid_params)

    output = Path("assets/logs/user_raw_probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
