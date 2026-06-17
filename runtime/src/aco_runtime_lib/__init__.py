"""ACO AI runtime library.

This is the production code path for the workflow engine. The
`apps/runtime` sidecar is a thin HTTP shell around it.

See `docs/ARCHITECTURE.md` §4 and `docs/WORKFLOW_SPEC.md` §4.
"""

from aco_runtime_lib.event_bus import EventBus, WfEvent
from aco_runtime_lib.workflow import State, StateMachine, Transition

__version__ = "0.1.0"

__all__ = [
    "EventBus",
    "State",
    "StateMachine",
    "Transition",
    "WfEvent",
    "__version__",
]
