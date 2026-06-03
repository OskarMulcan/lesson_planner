from sqlalchemy import Column, Integer, ForeignKey

from .base import Base

class TeacherSubject(Base):
    __tablename__ = 'teacher_subject'
    subject_id = Column(Integer, ForeignKey('subjects.id'), primary_key=True)
    teacher_id = Column(Integer, ForeignKey('teachers.id'), primary_key=True)