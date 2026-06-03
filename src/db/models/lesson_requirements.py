from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from db.models.base import Base


class LessonRequirements(Base):
    __tablename__ = 'lesson_requirements'
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'))
    teacher_id = Column(Integer, ForeignKey('teachers.id'))
    grade_id = Column(Integer, ForeignKey('grades.id'))
    lessons_per_week = Column(Integer, default=1)

    subject = relationship('Subject', foreign_keys=[subject_id])
    teacher = relationship('Teacher', foreign_keys=[teacher_id])
    grade = relationship('Grade', foreign_keys=[grade_id])

