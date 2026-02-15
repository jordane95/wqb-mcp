"""Capture raw platform config endpoint responses for schema documentation.

Run in an authenticated environment:
    python3 scripts/capture_platform_config_raw.py
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
    out: Dict[str, Any] = {"endpoints": {}}

    url = f"{base}/simulations"
    response = brain_client.session.options(url)
    out["endpoints"]["simulations_options"] = _record("OPTIONS", url, response)

    output = Path("assets/logs/platform_config_raw_probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
