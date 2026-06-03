from sqlalchemy import Column, Integer, String

from .base import Base


class Grade(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    
