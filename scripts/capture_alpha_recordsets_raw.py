import base64
import json
import os
from pathlib import Path

import requests
import tomllib

BASE_URL = "https://api.worldquantbrain.com"
OUT_DIR = Path("assets")
ALPHA_ID = "kqk3X0bL"


def load_creds() -> tuple[str, str]:
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

    raise RuntimeError("Missing credentials in env or ~/.codex/config.toml")


def auth(session: requests.Session, email: str, password: str) -> requests.Response:
    token = base64.b64encode(f"{email}:{password}".encode()).decode()
    return session.post(
        f"{BASE_URL}/authentication",
        headers={"Authorization": f"Basic {token}"},
        timeout=30,
    )


def fetch_json(session: requests.Session, url: str) -> dict:
    resp = session.get(url, timeout=30)
    data = {
        "url": url,
        "status_code": resp.status_code,
        "content_type": resp.headers.get("Content-Type"),
    }
    try:
        data["json"] = resp.json()
    except Exception:
        data["text_preview"] = (resp.text or "")[:3000]
    return data


def main() -> None:
    email, password = load_creds()
    session = requests.Session()

    login = auth(session, email, password)
    out = {
        "alpha_id": ALPHA_ID,
        "login": {
            "status_code": login.status_code,
            "content_type": login.headers.get("Content-Type"),
        },
        "record_sets": {},
        "record_set_data": {},
    }

    if login.status_code != 201:
        out["login"]["body_preview"] = (login.text or "")[:1000]
    else:
        out["record_sets"] = fetch_json(session, f"{BASE_URL}/alphas/{ALPHA_ID}/recordsets")
        rs_json = out["record_sets"].get("json")
        items = rs_json.get("results", []) if isinstance(rs_json, dict) else []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            out["record_set_data"][name] = fetch_json(
                session, f"{BASE_URL}/alphas/{ALPHA_ID}/recordsets/{name}"
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / f"alpha_recordsets_raw_{ALPHA_ID}.json"
    out_file.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
