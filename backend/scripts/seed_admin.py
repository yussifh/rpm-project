"""
One-off bootstrap script to create the FIRST admin account.

Why this is a script and not an API endpoint: a public "create the first
admin" endpoint would be a standing security hole — anyone who found it
before you did could create their own admin account. Instead, this script
is run once, out-of-band, by whoever controls deploy/DB access (which is
already a position of trust). Every admin account created AFTER this one
should go through POST /admin/users/admin (Module 4), which requires an
existing admin's auth token.

Usage:
    python -m scripts.seed_admin --email admin@example.com --password "..." --full-name "System Admin"

Or interactively (omits --password so it isn't left in shell history):
    python -m scripts.seed_admin --email admin@example.com --full-name "System Admin"
"""

import argparse
import getpass
import sys

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.admin import AdminProfile
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap the first admin account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password", required=False, help="Omit to be prompted securely instead.")
    parser.add_argument("--super-admin", action="store_true", default=True)
    args = parser.parse_args()

    password = args.password or getpass.getpass("Admin password: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        users = UserRepository(db)
        if users.get_by_email(args.email):
            print(f"A user with email '{args.email}' already exists. Aborting.", file=sys.stderr)
            sys.exit(1)

        user = User(
            email=args.email.lower(),
            hashed_password=hash_password(password),
            full_name=args.full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        user.admin_profile = AdminProfile(is_super_admin=args.super_admin)
        users.create(user)
        print(f"Admin account created: {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
