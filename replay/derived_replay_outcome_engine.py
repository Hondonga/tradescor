"""Replay adapter around the production paper fill/outcome modules."""
from paper_testing.derived_fill_engine import evaluate_paper_fill
from paper_testing.derived_outcome_resolver import resolve_paper_outcome
from paper_testing.derived_mfe_mae_tracker import track_mfe_mae

def evaluate_fill(setup,candles,entry_type="confirmation_close",slippage_points=0):return evaluate_paper_fill(setup,candles,entry_type,slippage_points)
def evaluate_outcome(setup,candles,fill_time,ambiguity_policy="mark_ambiguous",management=None):return resolve_paper_outcome(setup,candles,fill_time,ambiguity_policy,management)
def evaluate_excursion(setup,candles,fill_time,resolved_time=None):return track_mfe_mae(setup,candles,fill_time,resolved_time=resolved_time)

