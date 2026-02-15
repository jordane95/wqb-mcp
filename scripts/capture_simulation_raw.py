"""Capture raw simulation endpoint responses for schema documentation.

Run in an authenticated environment:
    python3 scripts/capture_simulation_raw.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict

from wqb_mcp.client import brain_client
from wqb_mcp.client.simulation import SimulationData, SimulationSettings


def _safe_json(response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"_non_json_body": (response.text or "")[:2000]}


async def main() -> None:
    await brain_client.ensure_authenticated()

    settings = SimulationSettings(
        instrumentType="EQUITY",
        region="USA",
        universe="TOP3000",
        delay=1,
        decay=0.0,
        neutralization="NONE",
        truncation=0.0,
        pasteurization="ON",
        unitHandling="VERIFY",
        nanHandling="OFF",
        language="FASTEXPR",
        visualization=False,
        testPeriod="P0Y0M",
    )
    sim = SimulationData(type="REGULAR", settings=settings, regular="rank(close)")

    settings_dict = sim.settings.model_dump()
    settings_dict.pop("selectionHandling", None)
    settings_dict.pop("selectionLimit", None)
    settings_dict.pop("componentActivation", None)
    payload = {"type": sim.type, "settings": settings_dict, "regular": sim.regular}

    post_resp = brain_client.session.post(f"{brain_client.base_url}/simulations", json=payload)
    location = post_resp.headers.get("Location", "")

    result: Dict[str, Any] = {
        "request": {
            "url": f"{brain_client.base_url}/simulations",
            "method": "POST",
            "payload": payload,
        },
        "post_response": {
            "status_code": post_resp.status_code,
            "headers": dict(post_resp.headers),
            "json_or_text": _safe_json(post_resp),
            "location": location,
        },
    }

    if location and post_resp.status_code < 400:
        status_resp = brain_client.session.get(location)
        result["status_response"] = {
            "url": location,
            "method": "GET",
            "status_code": status_resp.status_code,
            "headers": dict(status_resp.headers),
            "json_or_text": _safe_json(status_resp),
        }

    out = Path("assets/logs/simulation_raw_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    asyncio.run(main())
