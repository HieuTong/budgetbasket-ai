from datetime import date, timedelta

import pytest

from app.backtest.data import WeeklySeries, load_csv, synthetic_specials
from app.backtest.policies import AlwaysBuy, DecisionEnginePolicy, RollingLowHeuristic
from app.backtest.simulator import max_wait_for, run_backtest


def series(prices, category="pantry", pid="p1"):
    start = date(2025, 1, 6)
    return WeeklySeries(pid, pid, category, [start + timedelta(weeks=i) for i in range(len(prices))],
                        list(prices), "synthetic")


class AlwaysWait:
    name = "always_wait"

    def decide(self, dates, prices):
        return "WAIT"


class NoPeeking:
    """Fails the test if the simulator ever shows a policy a price from the future."""
    name = "no_peeking"

    def __init__(self, full):
        self.full = full

    def decide(self, dates, prices):
        assert prices == self.full[:len(prices)]
        assert dates[-1] == date(2025, 1, 6) + timedelta(weeks=len(prices) - 1)
        return "WAIT" if len(prices) % 2 else "BUY"


def test_policies_never_see_future_prices():
    prices = [5, 5, 5, 5, 4, 6, 3, 5, 5, 2, 5, 5]
    report = run_backtest([series(prices)], [NoPeeking(prices)], warmup_weeks=2, need_every_weeks=1)
    assert report.needs == 10


def test_oracle_is_a_lower_bound_and_always_buy_saves_nothing():
    data = synthetic_specials(n_products=10, weeks=40, seed=1)
    report = run_backtest(data, [AlwaysBuy(), RollingLowHeuristic(), AlwaysWait()])
    for r in report.results.values():
        assert r.spend >= report.oracle_spend - 1e-6
    rows = {r["policy"]: r for r in report.summary_rows()}
    assert rows["always_buy"]["savings_vs_always_buy_pct"] == 0.0


def test_waiting_is_forced_to_buy_at_the_deadline():
    # Pantry item: may wait 4 weeks. Price falls at week 3, rises at week 5.
    prices = [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 6, 12, 12, 12]
    report = run_backtest([series(prices)], [AlwaysWait()], warmup_weeks=8, need_every_weeks=100)
    r = report.results["always_wait"]
    assert r.weeks_waited == 4 and r.spend == 12  # waited past the special: a backfire
    assert r.backfires == 1
    assert report.oracle_spend == 6


def test_perishables_get_a_shorter_window():
    assert max_wait_for("produce") == 1 and max_wait_for("pantry") == 4


def test_rolling_low_waits_through_a_spike():
    prices = [5] * 8 + [8, 5, 5, 5]
    report = run_backtest([series(prices)], [RollingLowHeuristic()], warmup_weeks=8, need_every_weeks=100)
    assert report.results["rolling_low_8w"].spend == 5


def test_decision_engine_policy_runs_on_short_history():
    data = synthetic_specials(n_products=3, weeks=20, seed=2)
    report = run_backtest(data, [DecisionEnginePolicy()])
    assert report.results["decision_engine"].needs == report.needs


def test_csv_loader_aggregates_weekly_and_fills_gaps(tmp_path):
    f = tmp_path / "prices.csv"
    lines = ["product_id,name,category,date,price"]
    start = date(2025, 1, 6)
    for w in range(20):
        if w == 5:
            continue  # missing week gets the previous price
        lines.append(f"milk,Milk 2L,dairy,{start + timedelta(weeks=w)},{3.0 + (0.5 if w == 3 else 0)}")
        lines.append(f"milk,Milk 2L,dairy,{start + timedelta(weeks=w, days=2)},3.0")
    f.write_text("\n".join(lines))
    [s] = load_csv(f)
    assert len(s.prices) == 20 and s.category == "dairy"
    assert s.prices[3] == pytest.approx(3.25) and s.prices[5] == s.prices[4]
