"""Capture raw multi-simulation responses for schema documentation.

Run in an authenticated environment:
    python3 scripts/capture_multi_simulation_raw.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from wqb_mcp.client import brain_client


def _safe_json(response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"_non_json_body": (response.text or "")[:4000]}


def _record(method: str, url: str, response, params: Optional[Dict[str, Any]] = None, payload: Any = None) -> Dict[str, Any]:
    return {
        "request": {
            "method": method,
            "url": url,
            "params": params or {},
            "payload": payload,
        },
        "response": {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "json_or_text": _safe_json(response),
        },
    }


def _build_regular_item(expression: str) -> Dict[str, Any]:
    return {
        "type": "REGULAR",
        "settings": {
            "instrumentType": "EQUITY",
            "region": "USA",
            "universe": "TOP3000",
            "delay": 1,
            "decay": 0.0,
            "neutralization": "NONE",
            "truncation": 0.0,
            "pasteurization": "ON",
            "unitHandling": "VERIFY",
            "nanHandling": "OFF",
            "language": "FASTEXPR",
            "visualization": True,
            "testPeriod": "P0Y0M",
            "maxTrade": "OFF",
        },
        "regular": expression,
    }


async def _poll_until_done(url: str, max_polls: int) -> List[Dict[str, Any]]:
    polls: List[Dict[str, Any]] = []
    for _ in range(max_polls):
        response = brain_client.session.get(url)
        polls.append(_record("GET", url, response))
        retry_after = response.headers.get("Retry-After")
        if retry_after in (None, "0", "0.0"):
            break
        await asyncio.sleep(float(retry_after or 1))
    return polls


async def main() -> None:
    await brain_client.ensure_authenticated()
    base = brain_client.base_url
    out: Dict[str, Any] = {
        "request_meta": {
            "alpha_expressions": [
                "rank(close)",
                "rank(open)",
            ],
            "max_parent_polls": 20,
            "max_child_polls": 60,
        },
        "captures": {},
    }

    payload = [_build_regular_item(expr) for expr in out["request_meta"]["alpha_expressions"]]
    submit_url = f"{base}/simulations"
    submit_resp = brain_client.session.post(submit_url, json=payload)
    out["captures"]["submit"] = _record("POST", submit_url, submit_resp, payload=payload)

    location = submit_resp.headers.get("Location")
    out["derived"] = {"parent_location": location}
    if submit_resp.status_code != 201 or not location:
        output = Path("assets/logs/multi_simulation_raw_probe.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(output)
        return

    parent_polls = await _poll_until_done(location, max_polls=out["request_meta"]["max_parent_polls"])
    out["captures"]["parent_polls"] = parent_polls

    last_parent_body = parent_polls[-1]["response"]["json_or_text"] if parent_polls else {}
    children = []
    if isinstance(last_parent_body, dict):
        raw_children = last_parent_body.get("children")
        if isinstance(raw_children, list):
            children = [str(item) for item in raw_children]
    out["derived"]["children"] = children

    child_captures: List[Dict[str, Any]] = []
    for child in children:
        child_url = child if child.startswith("http") else f"{base}/simulations/{child}"
        polls = await _poll_until_done(child_url, max_polls=out["request_meta"]["max_child_polls"])
        child_entry: Dict[str, Any] = {"child": child, "child_url": child_url, "polls": polls}

        alpha_id = None
        if polls:
            last_body = polls[-1]["response"]["json_or_text"]
            if isinstance(last_body, dict):
                alpha_id = last_body.get("alpha")
        child_entry["alpha_id"] = alpha_id

        if alpha_id:
            alpha_url = f"{base}/alphas/{alpha_id}"
            alpha_resp = brain_client.session.get(alpha_url)
            child_entry["alpha_details"] = _record("GET", alpha_url, alpha_resp)

        child_captures.append(child_entry)

    out["captures"]["children"] = child_captures

    output = Path("assets/logs/multi_simulation_raw_probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
