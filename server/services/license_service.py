from sqlalchemy.orm import Session
from server.models.license import License
from server.models.user import User


def create_license(db: Session, license_key: str, user: User, next_charge_at=None):
    license = db.query(License).filter_by(user_id=user.id).first()
    if license:
        license.license_key = license_key
        if next_charge_at is not None:
            license.next_charge_at = next_charge_at
            license.valid_until = next_charge_at
            license.is_active = True
    else:
        license = License(
            license_key=license_key,
            user_id=user.id,
            next_charge_at=next_charge_at,
            valid_until=next_charge_at,
            is_active=True,
        )
        db.add(license)
    db.commit()
    db.refresh(license)
    return license

def get_license_by_key(db: Session, license_key: str):
    return db.query(License).filter(License.license_key == license_key).first()
