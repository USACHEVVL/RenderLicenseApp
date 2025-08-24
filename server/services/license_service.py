from sqlalchemy.orm import Session
from server.models.license import License
from server.models.user import User


def create_license(db: Session, license_key: str, user: User, valid_until=None):
    license = db.query(License).filter_by(user_id=user.id).first()
    if license:
        license.license_key = license_key
        if valid_until is not None:
            license.valid_until = valid_until
    else:
        license = License(license_key=license_key, user_id=user.id, valid_until=valid_until)
        db.add(license)
    db.commit()
    db.refresh(license)
    return license

def get_license_by_key(db: Session, license_key: str):
    return db.query(License).filter(License.license_key == license_key).first()
