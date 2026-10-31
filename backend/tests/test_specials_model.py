import numpy as np
import pytest

from app.backtest.data import synthetic_specials
from app.backtest.experiment import run_experiment
from app.backtest.features import build_features, label
from app.backtest.policies import AlwaysBuy
from app.backtest.simulator import run_backtest
from app.backtest.specials_model import SpecialsModel, build_dataset
from app.backtest.uncertainty import bootstrap_savings


def test_features_ignore_the_future():
    prices = [10, 10, 7, 10, 10, 10, 7, 10, 10, 10, 10, 10, 10]
    changed = prices[:10] + [1, 1, 1]  # rewrite everything after week 9
    assert build_features(prices, 9, False) == build_features(changed, 9, False)


def test_label_looks_only_inside_the_horizon():
    prices = [10, 10, 10, 8, 10]
    assert label(prices, 1, 2) == 1      # week 3 is 20% cheaper, within 2 weeks
    assert label(prices, 0, 2) == 0      # weeks 1-2 are not cheaper
    assert label(prices, 3, 2) is None   # not enough future to know


def test_dataset_embargo_keeps_labels_out_of_the_test_period():
    series = synthetic_specials(5, weeks=40, seed=3)
    _, y_all = build_dataset(series, 0, 40)
    _, y_cut = build_dataset(series, 0, 20)
    # Pantry items look 4 weeks ahead, so no training example may start after week 15.
    assert len(y_cut) < len(y_all)
    for s in series:
        assert len(s.prices) == 40  # dataset building must not modify the series


def test_model_beats_guessing_on_held_out_weeks():
    series = synthetic_specials(30, weeks=80, seed=4)
    model = SpecialsModel().fit(*build_dataset(series, 0, 50))
    report = model.evaluate(*build_dataset(series, 50, 80))
    assert report.auc > 0.7
    assert report.brier < report.brier_baseline


def test_model_needs_both_outcomes():
    with pytest.raises(ValueError):
        SpecialsModel().fit(np.zeros((5, 7)), np.zeros(5, dtype=int))


def test_bootstrap_interval_contains_estimate_and_is_reproducible():
    series = synthetic_specials(12, weeks=40, seed=5)
    report = run_backtest(series, [AlwaysBuy()])
    a = bootstrap_savings(report, "always_buy", n=300, seed=1)
    b = bootstrap_savings(report, "always_buy", n=300, seed=1)
    assert a == b and a["low"] <= a["estimate"] <= a["high"]


def test_experiment_reports_every_policy_with_intervals():
    out = run_experiment(synthetic_specials(20, weeks=70, seed=6), seed=0)
    assert out["threshold"] in (0.4, 0.5, 0.6, 0.7)
    assert out["model_policy"] in out["intervals"]
    assert set(out["model_vs_heuristic"]) == {"estimate", "low", "high"}
