from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from server.db.base_class import Base

class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Отношения
    license = relationship("License", back_populates="machine")
    user = relationship("User", back_populates="machines")
