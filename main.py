from src.constraints.registry import ConstraintRegistry
from src.constraints.constraints import PenalizeWindows, NoDoubleBooking

registry = (
    ConstraintRegistry()
    .register(PenalizeWindows(penalty=50))
    .register(NoDoubleBooking(penalty=1000))
)