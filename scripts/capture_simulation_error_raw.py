"""Capture raw simulation error responses for invalid settings/expressions.

Run in an authenticated environment:
    python3 scripts/capture_simulation_error_raw.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from wqb_mcp.client import brain_client


def _safe_json(response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"_non_json_body": (response.text or "")[:4000]}


def _make_payload(region: str, regular: str) -> Dict[str, Any]:
    return {
        "type": "REGULAR",
        "settings": {
            "instrumentType": "EQUITY",
            "region": region,
            "universe": "TOP3000",
            "delay": 1,
            "decay": 0.0,
            "neutralization": "NONE",
            "truncation": 0.0,
            "pasteurization": "ON",
            "unitHandling": "VERIFY",
            "nanHandling": "OFF",
            "language": "FASTEXPR",
            "visualization": False,
            "testPeriod": "P0Y0M",
            "maxTrade": "OFF",
        },
        "regular": regular,
    }


def _make_base_settings() -> Dict[str, Any]:
    return {
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
        "visualization": False,
        "testPeriod": "P0Y0M",
        "maxTrade": "OFF",
    }


async def _capture_case(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = brain_client.session.post(f"{brain_client.base_url}/simulations", json=payload)
    out: Dict[str, Any] = {
        "case": name,
        "request": {
            "url": f"{brain_client.base_url}/simulations",
            "method": "POST",
            "payload": payload,
        },
        "post_response": {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "json_or_text": _safe_json(response),
            "location": response.headers.get("Location", ""),
        },
    }

    location = response.headers.get("Location", "")
    if location and response.status_code < 400:
        # Poll a few times to catch expression/validation errors surfaced asynchronously.
        polls = []
        for _ in range(3):
            status_resp = brain_client.session.get(location)
            polls.append(
                {
                    "status_code": status_resp.status_code,
                    "headers": dict(status_resp.headers),
                    "json_or_text": _safe_json(status_resp),
                }
            )
            retry_after = status_resp.headers.get("Retry-After")
            if retry_after in (None, "0", "0.0"):
                break
            await asyncio.sleep(float(retry_after))
        out["status_polls"] = polls

    return out


async def main() -> None:
    await brain_client.ensure_authenticated()

    invalid_instrument = _make_base_settings()
    invalid_instrument["instrumentType"] = "CRYPTO"

    invalid_delay = _make_base_settings()
    invalid_delay["delay"] = 2

    invalid_universe = _make_base_settings()
    invalid_universe["universe"] = "TOP999999"

    missing_required_settings = _make_base_settings()
    missing_required_settings.pop("region", None)

    cases = [
        ("invalid_region", _make_payload(region="XXX", regular="rank(close)")),
        ("invalid_expression", _make_payload(region="USA", regular="rank(close")),
        ("unknown_datafield", _make_payload(region="USA", regular="rank(this_field_does_not_exist_abc123)")),
        ("bad_type_expression", _make_payload(region="USA", regular="ts_mean(close, \"abc\")")),
        (
            "invalid_instrument_type",
            {"type": "REGULAR", "settings": invalid_instrument, "regular": "rank(close)"},
        ),
        (
            "invalid_delay",
            {"type": "REGULAR", "settings": invalid_delay, "regular": "rank(close)"},
        ),
        (
            "invalid_universe",
            {"type": "REGULAR", "settings": invalid_universe, "regular": "rank(close)"},
        ),
        (
            "missing_settings_field",
            {"type": "REGULAR", "settings": missing_required_settings, "regular": "rank(close)"},
        ),
        (
            "wrong_settings_type",
            {"type": "REGULAR", "settings": "not-an-object", "regular": "rank(close)"},
        ),
        (
            "missing_regular_expr",
            {"type": "REGULAR", "settings": _make_base_settings()},
        ),
    ]
    results = []
    for name, payload in cases:
        results.append(await _capture_case(name, payload))

    out = Path("assets/logs/simulation_error_raw_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cases": results}, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    asyncio.run(main())
