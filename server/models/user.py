from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from server.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    referral_code = Column(String, unique=True, index=True)
    referred_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    referral_bonus_claimed = Column(Boolean, default=False, nullable=False)

    license = relationship(
        "License",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    referrer = relationship("User", remote_side=[id])
