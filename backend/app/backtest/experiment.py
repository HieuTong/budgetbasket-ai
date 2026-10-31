"""Train the specials model on early weeks, then backtest every policy on later, unseen weeks."""
from __future__ import annotations

from .data import WeeklySeries
from .policies import AlwaysBuy, DecisionEnginePolicy, RollingLowHeuristic
from .simulator import run_backtest
from .specials_model import SpecialsModel, SpecialsModelPolicy, build_dataset
from .uncertainty import bootstrap_savings


def _pick_threshold(model, series, val_start, val_end, candidates=(0.4, 0.5, 0.6, 0.7)) -> float:
    """Choose the WAIT threshold on a validation slice of the TRAINING period, never the test period."""
    best, best_saving = 0.5, float("-inf")
    for th in candidates:
        rep = run_backtest_slice(series, [SpecialsModelPolicy(model, th)], val_start, val_end)
        saving = rep.always_buy_spend - next(iter(rep.results.values())).spend
        if saving > best_saving:
            best, best_saving = th, saving
    return best


def run_backtest_slice(series, policies, start, end):
    """Backtest only purchase needs in [start, end); policies still see all earlier history."""
    clipped = [WeeklySeries(s.product_id, s.name, s.category, s.dates[:end], s.prices[:end], s.source)
               for s in series]
    report = None
    # The simulator needs each model policy to know the product's category.
    for s in clipped:
        for p in policies:
            if isinstance(p, SpecialsModelPolicy):
                p.category = s.category.lower()
        partial = run_backtest([s], policies, warmup_weeks=start)
        report = partial if report is None else _merge(report, partial)
    return report


def _merge(a, b):
    a.oracle_spend += b.oracle_spend
    a.always_buy_spend += b.always_buy_spend
    a.needs += b.needs
    a.products += b.products
    a.always_by_product.update(b.always_by_product)
    a.oracle_by_product.update(b.oracle_by_product)
    for name, r in b.results.items():
        t = a.results[name]
        t.spend += r.spend; t.needs += r.needs; t.waits += r.waits
        t.backfires += r.backfires; t.weeks_waited += r.weeks_waited
        t.per_product.update(r.per_product)
        for cat, v in r.per_category.items():
            c = t.per_category.setdefault(cat, {"spend": 0.0, "needs": 0})
            c["spend"] += v["spend"]; c["needs"] += v["needs"]
    return a


def run_experiment(series: list[WeeklySeries], train_frac: float = 0.6, seed: int = 0) -> dict:
    weeks = min(len(s.prices) for s in series)
    split = int(weeks * train_frac)
    val_start = int(split * 0.7)

    # 1. Fit on the early part of training, tune the threshold on the later part of training.
    X_fit, y_fit = build_dataset(series, 0, val_start)
    tuning_model = SpecialsModel().fit(X_fit, y_fit)
    threshold = _pick_threshold(tuning_model, series, val_start, split)

    # 2. Refit on the whole training period, then evaluate once on the untouched test period.
    X_tr, y_tr = build_dataset(series, 0, split)
    model = SpecialsModel().fit(X_tr, y_tr)
    X_te, y_te = build_dataset(series, split, weeks)
    clf = model.evaluate(X_te, y_te)

    policies = [AlwaysBuy(), RollingLowHeuristic(), DecisionEnginePolicy(), SpecialsModelPolicy(model, threshold)]
    report = run_backtest_slice(series, policies, split, weeks)
    model_name = policies[-1].name
    return {
        "split_week": split, "test_weeks": weeks - split, "threshold": threshold,
        "classification": clf.__dict__, "coefficients": model.coefficients(),
        "report": report, "model_policy": model_name,
        "intervals": {
            p.name: bootstrap_savings(report, p.name, seed=seed) for p in policies[1:]
        },
        "model_vs_heuristic": bootstrap_savings(report, model_name, seed=seed, baseline="rolling_low_8w"),
    }
