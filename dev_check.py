"""Simple debug script to inspect users and licenses."""

from server.db.session import SessionLocal
from server.models.license import License
from server.models.user import User

with SessionLocal() as db:
    users = db.query(User).all()
    licenses = db.query(License).all()

    print(f"Users: {users}")
    print(f"Licenses: {licenses}")
