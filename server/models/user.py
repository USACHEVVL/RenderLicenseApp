from sqlalchemy import Column, Integer, BigInteger, String
from sqlalchemy.orm import relationship
from server.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)

    licenses = relationship(
        "License",
        back_populates="user",
        cascade="all, delete-orphan"
    )
