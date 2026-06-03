from sqlalchemy import Column, Integer, String

from .base import Base


class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)