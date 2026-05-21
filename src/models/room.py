from sqlalchemy import Integer, Column, String

from .base import Base


class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
