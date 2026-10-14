"""Local administrator bootstrap. Passwords only arrive through a hidden prompt."""
import argparse
from getpass import getpass

from sqlalchemy.exc import IntegrityError

from backend.db import session_scope
from backend.models.auth import AuthEvent, User
from backend.models.auth_contracts import CreateUser
from backend.services.auth import hash_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-admin")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass("Temporary password (6–128 characters): ")
    if password != getpass("Confirm temporary password: "):
        parser.error("Passwords do not match")
    try:
        data = CreateUser(email=args.email, display_name=args.name, roles=["admin"], temporary_password=password)
        encoded = hash_password(data.temporary_password)
        with session_scope() as session:
            user = User(email=data.email, display_name=data.display_name, roles=data.roles, password_hash=encoded)
            session.add(user)
            session.flush()
            session.add(AuthEvent(event="ADMIN_BOOTSTRAPPED", target_id=user.id, outcome="success"))
        print("Administrator created. Sign in and change the temporary password.")
    except IntegrityError:
        parser.error("Email already exists")
    except ValueError:
        parser.error("Invalid email, name or password (password must have 6–128 characters)")


if __name__ == "__main__":
    main()
