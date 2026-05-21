from sqlalchemy import Column, Integer, String

from .base import Base


class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)