from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from server.db.base_class import Base

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    subscription_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)
    next_charge_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="license")
