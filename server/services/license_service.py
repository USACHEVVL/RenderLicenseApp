from sqlalchemy.orm import Session
from server.models.license import License
from server.models.user import User

def create_license(db: Session, license_key: str, machine_name: str, user: User):
    license = License(license_key=license_key, machine_name=machine_name, user_id=user.id)
    db.add(license)
    db.commit()
    db.refresh(license)
    return license

def get_license_by_key(db: Session, license_key: str):
    return db.query(License).filter(License.license_key == license_key).first()
