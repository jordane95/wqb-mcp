import base64
import json
import os
from pathlib import Path

import requests
import tomllib


def load_creds():
    email = os.getenv("WQB_EMAIL")
    password = os.getenv("WQB_PASSWORD")
    if email and password:
        return email, password

    cfg_path = Path.home() / ".codex" / "config.toml"
    if cfg_path.exists():
        cfg = tomllib.loads(cfg_path.read_text())
        env = cfg.get("mcp_servers", {}).get("wqb-mcp", {}).get("env", {})
        email = env.get("WQB_EMAIL")
        password = env.get("WQB_PASSWORD")
        if email and password:
            return email, password

    raise RuntimeError(
        "Missing credentials: set WQB_EMAIL/WQB_PASSWORD or ~/.codex/config.toml mcp_servers.wqb-mcp.env"
    )


def try_json(resp):
    try:
        return resp.json()
    except Exception:
        return None


def capture_get(session, url, params=None):
    resp = session.get(url, params=params, timeout=30)
    return {
        "url": resp.url,
        "status_code": resp.status_code,
        "headers": {
            "Content-Type": resp.headers.get("Content-Type"),
            "Retry-After": resp.headers.get("Retry-After"),
            "Content-Length": resp.headers.get("Content-Length"),
        },
        "body_text_preview": (resp.text or "")[:4000],
        "body_json_preview": try_json(resp),
    }


def main():
    email, password = load_creds()
    session = requests.Session()

    auth = base64.b64encode(f"{email}:{password}".encode()).decode()
    login = session.post(
        "https://api.worldquantbrain.com/authentication",
        headers={"Authorization": f"Basic {auth}"},
        timeout=30,
    )

    out = {
        "login": {
            "status_code": login.status_code,
            "headers": {
                "Content-Type": login.headers.get("Content-Type"),
                "WWW-Authenticate": login.headers.get("WWW-Authenticate"),
                "Location": login.headers.get("Location"),
            },
            "body_json_preview": try_json(login),
            "body_text_preview": (login.text or "")[:1000],
        },
        "captures": {},
    }

    if login.status_code != 201:
        Path("alpha_raw_capture.log").write_text(json.dumps(out, indent=2, ensure_ascii=False))
        print("Login failed. Wrote alpha_raw_capture.log")
        return

    user_alphas = capture_get(
        session,
        "https://api.worldquantbrain.com/users/self/alphas",
        {"stage": "IS", "limit": 1},
    )
    out["captures"]["user_alphas"] = user_alphas

    alpha_id = None
    ua_json = user_alphas.get("body_json_preview")
    if isinstance(ua_json, dict):
        results = ua_json.get("results") or []
        if results and isinstance(results[0], dict):
            alpha_id = results[0].get("id")
    out["alpha_id"] = alpha_id

    if alpha_id:
        out["captures"]["alpha_details"] = capture_get(
            session, f"https://api.worldquantbrain.com/alphas/{alpha_id}"
        )
        out["captures"]["record_sets"] = capture_get(
            session, f"https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets"
        )
        out["captures"]["alpha_pnl"] = capture_get(
            session, f"https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/pnl"
        )
        out["captures"]["alpha_yearly_stats"] = capture_get(
            session, f"https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/yearly-stats"
        )
        out["captures"]["performance_comparison"] = capture_get(
            session, f"https://api.worldquantbrain.com/alphas/{alpha_id}/performance-comparison"
        )

        rs = out["captures"]["record_sets"].get("body_json_preview")
        if isinstance(rs, dict):
            recs = rs.get("records") or []
            if recs and isinstance(recs[0], list) and recs[0]:
                rs_name = recs[0][0]
                out["record_set_name_sample"] = rs_name
                out["captures"]["record_set_data"] = capture_get(
                    session,
                    f"https://api.worldquantbrain.com/alphas/{alpha_id}/recordsets/{rs_name}",
                )

    Path("alpha_raw_capture.log").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("Wrote alpha_raw_capture.log")


if __name__ == "__main__":
    main()
