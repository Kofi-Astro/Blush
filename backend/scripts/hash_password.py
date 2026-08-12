"""Generates a bcrypt hash for ADMIN_PASSWORD_HASH in .env.

Usage: python scripts/hash_password.py
"""

import getpass

import bcrypt

if __name__ == "__main__":
    password = getpass.getpass("Choose an admin password: ")
    confirm = getpass.getpass("Confirm: ")
    if password != confirm:
        raise SystemExit("Passwords didn't match.")

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    print("\nADMIN_PASSWORD_HASH=" + hashed)
