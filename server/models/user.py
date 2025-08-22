from sqlalchemy import Column, Integer, BigInteger
from sqlalchemy.orm import relationship
from server.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)

    licenses = relationship(
        "License",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    machines = relationship(
        "Machine",
        back_populates="user",
        cascade="all, delete-orphan"
    )