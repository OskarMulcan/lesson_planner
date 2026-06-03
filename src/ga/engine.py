from dataclasses import dataclass
from collections import defaultdict

from db.models.subject import Subject
from db.models.teacher import Teacher
from db.models import LessonRequirements
from db.models.room import Room
from db.models.grade import Grade
from db.models.teacher_subject import TeacherSubject


@dataclass
class SchedulerContext:
    requirements: dict[int, LessonRequirements]
    teachers: dict[int, Teacher]
    rooms: dict[int, Room]
    grades: dict[int, Grade]
    subjects: dict[int, Subject]
    teacher_subjects: dict[int, list[TeacherSubject]]

    @classmethod
    def load(cls, session) -> "SchedulerContext":
        ts_map = defaultdict(list)
        for ts in session.query(TeacherSubject).all():
            ts_map[ts.subject_id].append(ts)
        return cls(
            requirements={requirement.id: requirement for requirement in session.query(LessonRequirements).all()},
            teachers={teacher.id: teacher for teacher in session.query(Teacher).all()},
            rooms={room.id: room for room in session.query(Room).all()},
            grades={grade.id: grade for grade in session.query(Grade).all()},
            subjects={subject.id: subject for subject in session.query(Subject).all()},
            teacher_subjects = dict(ts_map)
        )

    class GeneticEngine:
        def __init__(
                self,
                context: SchedulerContext,
                registry: ConstraintRegistry,
                population_size: int,
                tournament_size: int,
                mutation_rate: float,
                repair_every_n: int,
                max_generations: int,
                fitness_threshold: float,
                elite_size: int = 1,
        ):
            self._context = context
            self._registry = registry
            self._population = Population(context, registry)
            self._repair = RepairsOperator(context)
            self._population_size = population_size
            self._tournament_size = tournament_size
            self._mutation_rate = mutation_rate
            self._repair_every_n = repair_every_n
            self._max_generations = max_generations
            self._fitness_threshold = fitness_threshold
            self._elite_size = elite_size

        def run(self) -> Schedule:
            self._population.populate(self._population_size)
            self._population.set_population_fitness()

            for schedule in self._population.schedules:
                self._repair.repair(schedule)
            self._population.set_population_fitness()

            for generation in range(self._max_generations):
                best = min(self._population.schedules, key=lambda s: s.fitness)
                print(f"Generation {generation}, best fitness: {best.fitness}")

                if best.fitness <= self._fitness_threshold:
                    break

                elites = sorted(self._population.schedules, key = lambda schedule: schedule.fitness)[:self._elite_size]

                new_population = list(elites)
                while len(new_population) < self._population_size:
                    parent_a = self._population.tournament_selection(self._tournament_size)
                    parent_b = self._population.tournament_selection(self._tournament_size)
                    child = self._population.crossover(parent_a, parent_b)
                    self._population.mutate(child, self._mutation_rate)
                    new_population.append(child)

                self._population.schedules = new_population
                self._population.set_population_fitness()

                if generation % self._repair_every_n == 0:
                    for schedule in self._population.schedules:
                        self._repair.repair(schedule)
                    self._population.set_population_fitness()

            return min(self._population.schedules, key=lambda s: s.fitness)