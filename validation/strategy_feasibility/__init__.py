"""Reusable strategy-feasibility harness.

Every directional strategy hypothesis must pass this gate before it is allowed
anywhere near the main engine. The harness answers, on causally generated
setups with matched controls, symmetric geometry, realistic costs and grouped
uncertainty:

  1. Does the setup outperform random direction?
  2. Does direction add value after holding geometry constant?
  3. Is the result stable across symbols?
  4. Is it stable across independent periods?
  5. Does it survive costs?
  6. Is the effect concentrated in one event cluster?
  7. Does the confidence interval exclude zero?
  8. Has the development data already been consumed?

Its single most positive verdict is ELIGIBLE_FOR_FORMAL_WALK_FORWARD.
It never returns "production ready".
"""
from .experiment_spec import ExperimentSpec
from .event_matcher import Event, normalize_events
from .feasibility_service import run_feasibility
from .feasibility_report import Outcome

__all__ = ["ExperimentSpec", "Event", "normalize_events", "run_feasibility", "Outcome"]
