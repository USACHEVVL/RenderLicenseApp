from server.db.session import SessionLocal
from server.models.user import User
from server.models.license import License

db = SessionLocal()
users = db.query(User).all()
licenses = db.query(License).all()

print(f"Users: {users}")
print(f"Licenses: {licenses}")

db.close()
