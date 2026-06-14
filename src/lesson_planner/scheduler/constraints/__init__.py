from .base import Constraint, ConstraintResult, CompositeConstraint
from .constraints import (
    NoDoubleBookingConstraint,
    TeacherAvailabilityConstraint,
    LessonFrequencyConstraint,
    PenalizeClassWindowsConstraint,
    PenalizeTeacherWindowsConstraint,
)

REGISTRY = CompositeConstraint(
    "master_registry",
    NoDoubleBookingConstraint(),
    TeacherAvailabilityConstraint(),
    LessonFrequencyConstraint(),
    PenalizeClassWindowsConstraint(),
    PenalizeTeacherWindowsConstraint(),
)

__all__ = [
    "Constraint",
    "ConstraintResult",
    "CompositeConstraint",
    "NoDoubleBookingConstraint",
    "TeacherAvailabilityConstraint",
    "LessonFrequencyConstraint",
    "PenalizeClassWindowsConstraint",
    "PenalizeTeacherWindowsConstraint",
    "REGISTRY"
]