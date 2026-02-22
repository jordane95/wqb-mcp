#!/usr/bin/env python3
"""Read wqb-mcp credentials from system keyring."""

from __future__ import annotations

import argparse
import json
import sys

import keyring


DEFAULT_SERVICE = "wqb-mcp"
EMAIL_KEY = "email"
PASSWORD_KEY = "password"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Get wqb-mcp credentials from system keyring."
    )
    parser.add_argument(
        "--service",
        default=DEFAULT_SERVICE,
        help=f"Keyring service name (default: {DEFAULT_SERVICE})",
    )
    parser.add_argument(
        "--show-password",
        action="store_true",
        help="Print the password in clear text (off by default).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for scripts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    email = keyring.get_password(args.service, EMAIL_KEY)
    password = keyring.get_password(args.service, PASSWORD_KEY)

    if not email and not password:
        print(
            f"No credentials found in keyring for service '{args.service}'.",
            file=sys.stderr,
        )
        return 1

    display_password = password if args.show_password else ("*" * 8 if password else None)

    if args.json:
        payload = {
            "service": args.service,
            "email": email,
            "password": display_password,
            "password_present": bool(password),
        }
        print(json.dumps(payload, ensure_ascii=True))
    else:
        print(f"service: {args.service}")
        print(f"email: {email or '<missing>'}")
        print(f"password: {display_password or '<missing>'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
