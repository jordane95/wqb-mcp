"""CLI tool to store BRAIN credentials in the system keyring."""

import getpass
import sys

from .config import SERVICE_NAME, load_credentials, save_credentials


def main():
    print("WorldQuant BRAIN MCP - Credential Setup")
    print("=" * 40)

    # Show current status
    email, _ = load_credentials()
    if email:
        print(f"Existing credentials found (email: {email})")
        choice = input("Overwrite? [y/N]: ").strip().lower()
        if choice != "y":
            print("Keeping existing credentials.")
            return

    # Prompt for credentials
    email = input("Email: ").strip()
    if not email:
        print("Email cannot be empty.", file=sys.stderr)
        sys.exit(1)

    password = getpass.getpass("Password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        sys.exit(1)

    if save_credentials(email, password):
        print(f"Credentials saved to system keyring (service: {SERVICE_NAME})")
    else:
        print("Failed to save credentials.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
