from dataclasses import dataclass

from models.subject import Subject
from models.teacher import Teacher
from models.lesson_requirements import LessonRequirements
from models.room import Room
from models.grade import Grade


@dataclass
class SchedulerContext:
    requirements: dict[int, LessonRequirements]
    teachers: dict[int, Teacher]
    rooms: dict[int, Room]
    grades: dict[int, Grade]
    subjects: dict[int, Subject]

    @classmethod
    def load(cls, session) -> "SchedulerContext":
        return cls(
            requirements={requirement.id: requirement for requirement in session.query(LessonRequirements).all()},
            teachers={teacher.id: teacher for teacher in session.query(Teacher).all()},
            rooms={room.id: room for room in session.query(Room).all()},
            grades={grade.id: grade for grade in session.query(Grade).all()},
            subjects={subject.id: subject for subject in session.query(Subject).all()},
        )