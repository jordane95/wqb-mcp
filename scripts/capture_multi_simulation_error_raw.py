"""Capture raw multi-simulation error responses for invalid settings.

Run in an authenticated environment:
    python3 scripts/capture_multi_simulation_error_raw.py
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


def _record(method: str, url: str, response, payload: Any = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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


def _base_item(expr: str, settings_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    settings = {
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
    }
    if settings_override:
        settings.update(settings_override)
    return {
        "type": "REGULAR",
        "settings": settings,
        "regular": expr,
    }


async def _poll_until_done(url: str, max_polls: int = 30) -> list[Dict[str, Any]]:
    polls: list[Dict[str, Any]] = []
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
    url = f"{brain_client.base_url}/simulations"

    cases = {
        "invalid_region": [
            _base_item("rank(close)", {"region": "XXX"}),
            _base_item("rank(open)", {"region": "XXX"}),
        ],
        "invalid_delay": [
            _base_item("rank(close)", {"delay": 2}),
            _base_item("rank(open)", {"delay": 2}),
        ],
        "invalid_universe": [
            _base_item("rank(close)", {"universe": "TOP999999"}),
            _base_item("rank(open)", {"universe": "TOP999999"}),
        ],
        "invalid_instrument_type": [
            _base_item("rank(close)", {"instrumentType": "CRYPTO"}),
            _base_item("rank(open)", {"instrumentType": "CRYPTO"}),
        ],
        "missing_region_field": [
            {
                "type": "REGULAR",
                "settings": {
                    "instrumentType": "EQUITY",
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
                "regular": "rank(close)",
            },
            {
                "type": "REGULAR",
                "settings": {
                    "instrumentType": "EQUITY",
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
                "regular": "rank(open)",
            },
        ],
    }

    out: Dict[str, Any] = {"endpoint": url, "cases": {}}
    for case_name, payload in cases.items():
        response = brain_client.session.post(url, json=payload)
        out["cases"][case_name] = _record("POST", url, response, payload=payload)

    mixed_payload = [
        _base_item("rank(close)"),
        _base_item("this_field_does_not_exist_abc123"),
    ]
    mixed_submit = brain_client.session.post(url, json=mixed_payload)
    mixed: Dict[str, Any] = {
        "submit": _record("POST", url, mixed_submit, payload=mixed_payload),
        "parent_polls": [],
        "children": [],
    }

    parent_location = mixed_submit.headers.get("Location")
    if mixed_submit.status_code == 201 and parent_location:
        mixed["parent_polls"] = await _poll_until_done(parent_location, max_polls=30)
        parent_last = mixed["parent_polls"][-1]["response"]["json_or_text"] if mixed["parent_polls"] else {}
        child_ids = parent_last.get("children", []) if isinstance(parent_last, dict) else []
        for child_id in child_ids:
            child_url = child_id if str(child_id).startswith("http") else f"{brain_client.base_url}/simulations/{child_id}"
            child_polls = await _poll_until_done(child_url, max_polls=30)
            mixed["children"].append(
                {
                    "child_id": child_id,
                    "child_url": child_url,
                    "polls": child_polls,
                }
            )

    out["mixed_expression_case"] = mixed

    output = Path("assets/logs/multi_simulation_error_raw_probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
