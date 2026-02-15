import base64
import json
import os
from pathlib import Path

import requests
import tomllib

BASE_URL = "https://api.worldquantbrain.com"
OUT_FILE = Path("assets/alpha_region_details_raw.json")
REGION_IDS = {
    "USA": "9qPmO8P1",
    "GLB": "kqk3X0bL",
    "EUR": "LLbrYQ3v",
    "ASI": "npkQGW33",
    "CHN": "2rqWVl3Y",
    "AMR": "9qPm58Aq",
    "IND": "88kYW2Pm",
}


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


def fetch_alpha(session: requests.Session, alpha_id: str) -> dict:
    resp = session.get(f"{BASE_URL}/alphas/{alpha_id}", timeout=30)
    out = {
        "alpha_id": alpha_id,
        "status_code": resp.status_code,
        "url": resp.url,
        "content_type": resp.headers.get("Content-Type"),
    }
    try:
        out["json"] = resp.json()
    except Exception:
        out["text_preview"] = (resp.text or "")[:2000]
    return out


def main() -> None:
    email, password = load_creds()
    session = requests.Session()

    login = auth(session, email, password)
    result = {
        "login": {
            "status_code": login.status_code,
            "content_type": login.headers.get("Content-Type"),
            "location": login.headers.get("Location"),
        },
        "region_ids": REGION_IDS,
        "alpha_details_by_region": {},
    }

    if login.status_code != 201:
        result["login"]["body_preview"] = (login.text or "")[:1000]
        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        Path(OUT_FILE).write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(f"Login failed. Wrote {OUT_FILE}")
        return

    for region, alpha_id in REGION_IDS.items():
        result["alpha_details_by_region"][region] = fetch_alpha(session, alpha_id)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    Path(OUT_FILE).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT_FILE}")


if __name__ == "__main__":
    main()
