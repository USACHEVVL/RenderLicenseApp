from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from server.db.base_class import Base

class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    valid_until = Column(DateTime, nullable=True)

    # Отношения
    user = relationship("User", back_populates="licenses")
    machine = relationship("Machine", back_populates="license", uselist=False)  # Один к одному
