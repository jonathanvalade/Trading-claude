"""Chronological out-of-sample evaluation helper; no training or tuning automation."""
from datetime import datetime
from .portfolio_backtest import replay
from .backtest import validate_history

def split_sessions(bars, train_sessions, test_sessions, step_sessions=None):
    if train_sessions < 1 or test_sessions < 1:
        raise ValueError("Both windows must be positive")
    ordered = validate_history(bars)
    dates = sorted({bar.timestamp.date().isoformat() for bar in ordered})
    step = step_sessions or test_sessions
    if step < 1:
        raise ValueError("Step must be positive")
    for i in range(0, len(dates) - train_sessions - test_sessions + 1, step):
        train_days = set(dates[i:i + train_sessions])
        test_days = set(dates[i + train_sessions:i + train_sessions + test_sessions])
        yield {"train_dates": sorted(train_days), "test_dates": sorted(test_days),
               "train_bars": [b for b in ordered if b.timestamp.date().isoformat() in train_days],
               "test_bars": [b for b in ordered if b.timestamp.date().isoformat() in test_days]}

def evaluate_out_of_sample(bars, train_sessions, test_sessions, config=None, costs=None,
                           approvals=None, step_sessions=None):
    """Evaluate held-out windows only; user must choose strategy before each test window.

    No model training, parameter selection or AI inference occurs in this function.
    approvals must have been recorded causally, without access to future bars.
    """
    output = []
    for fold in split_sessions(bars, train_sessions, test_sessions, step_sessions):
        output.append({"train_dates": fold["train_dates"], "test_dates": fold["test_dates"],
                       "rules_only": replay(fold["test_bars"], config, costs)["metrics"],
                       "ai_gated": replay(fold["test_bars"], config, costs, approvals)["metrics"]
                       if approvals is not None else None})
    return output
