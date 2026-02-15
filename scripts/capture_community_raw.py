"""Capture raw community endpoint responses for schema documentation.

Run in an authenticated environment:
    python3 scripts/capture_community_raw.py
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


def _pick_first_tutorial_page_id(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    tutorials = body.get("results")
    if not isinstance(tutorials, list):
        return None
    for tutorial in tutorials:
        if not isinstance(tutorial, dict):
            continue
        pages = tutorial.get("pages")
        if not isinstance(pages, list):
            continue
        for page in pages:
            if isinstance(page, dict) and page.get("id"):
                return str(page["id"])
    return None


async def main() -> None:
    await brain_client.ensure_authenticated()
    base = brain_client.base_url
    out: Dict[str, Any] = {"endpoints": {}}

    # /users/self
    self_url = f"{base}/users/self"
    self_resp = brain_client.session.get(self_url)
    out["endpoints"]["users_self"] = _record("GET", self_url, self_resp)
    user_id = None
    if self_resp.status_code == 200:
        user_id = _safe_json(self_resp).get("id")

    # /events
    events_url = f"{base}/events"
    events_resp = brain_client.session.get(events_url)
    out["endpoints"]["events"] = _record("GET", events_url, events_resp)

    # /tutorials
    tutorials_url = f"{base}/tutorials"
    tutorials_resp = brain_client.session.get(tutorials_url)
    out["endpoints"]["tutorials"] = _record("GET", tutorials_url, tutorials_resp)
    tutorial_page_id = None
    if tutorials_resp.status_code == 200:
        tutorial_page_id = _pick_first_tutorial_page_id(_safe_json(tutorials_resp))
    out.setdefault("derived", {})["sample_tutorial_page_id"] = tutorial_page_id

    # /tutorial-pages/{page_id}
    if tutorial_page_id:
        tutorial_page_url = f"{base}/tutorial-pages/{tutorial_page_id}"
        tutorial_page_resp = brain_client.session.get(tutorial_page_url)
        out["endpoints"]["tutorial_page"] = _record("GET", tutorial_page_url, tutorial_page_resp)

    # /consultant/boards/leader (with user id when available)
    leader_url = f"{base}/consultant/boards/leader"
    leader_params = {"user": user_id} if user_id else {}
    leader_resp = brain_client.session.get(leader_url, params=leader_params)
    out["endpoints"]["leaderboard"] = _record("GET", leader_url, leader_resp, params=leader_params)

    # /users/{id}/competitions
    competitions_user = user_id or "self"
    user_comp_url = f"{base}/users/{competitions_user}/competitions"
    user_comp_resp = brain_client.session.get(user_comp_url)
    out["endpoints"]["user_competitions"] = _record("GET", user_comp_url, user_comp_resp)

    competition_id = None
    if user_comp_resp.status_code == 200:
        body = _safe_json(user_comp_resp)
        results = body.get("results") if isinstance(body, dict) else None
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, dict):
                competition_id = first.get("id")
        elif isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, dict):
                competition_id = first.get("id")

    # /competitions/{id} and /competitions/{id}/agreement (if any competition found)
    if competition_id:
        comp_detail_url = f"{base}/competitions/{competition_id}"
        comp_detail_resp = brain_client.session.get(comp_detail_url)
        out["endpoints"]["competition_details"] = _record("GET", comp_detail_url, comp_detail_resp)

        comp_agreement_url = f"{base}/competitions/{competition_id}/agreement"
        comp_agreement_resp = brain_client.session.get(comp_agreement_url)
        out["endpoints"]["competition_agreement"] = _record("GET", comp_agreement_url, comp_agreement_resp)
        out.setdefault("derived", {})["sample_competition_id"] = competition_id
    else:
        out.setdefault("derived", {})["sample_competition_id"] = None

    output = Path("assets/logs/community_raw_probe.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
