"""Performance and benchmark analytics for backtest results."""

from __future__ import annotations

from math import sqrt

from quant_trader.backtest.models import EquitySnapshot


def compute_returns(curve: list[EquitySnapshot]) -> list[float]:
    """Compute period-over-period returns from equity curve."""

    if len(curve) < 2:
        return []
    returns: list[float] = []
    for prev, curr in zip(curve[:-1], curve[1:], strict=False):
        if prev.equity == 0:
            returns.append(0.0)
        else:
            returns.append((curr.equity / prev.equity) - 1.0)
    return returns


def summarize_performance(
    curve: list[EquitySnapshot],
    benchmark_curve: list[tuple[object, float]],
) -> dict[str, float | str]:
    """Generate a compact backtest performance report."""

    if not curve:
        return {"status": "empty"}

    total_return = (curve[-1].equity / curve[0].equity) - 1.0 if curve[0].equity else 0.0
    max_drawdown = max((point.drawdown for point in curve), default=0.0)

    rets = compute_returns(curve)
    mean_ret = sum(rets) / len(rets) if rets else 0.0
    vol = (sum((r - mean_ret) ** 2 for r in rets) / max(len(rets), 1)) ** 0.5
    sharpe_like = (mean_ret / vol * sqrt(252)) if vol > 0 else 0.0

    benchmark_return = 0.0
    if len(benchmark_curve) >= 2 and benchmark_curve[0][1] != 0:
        benchmark_return = (benchmark_curve[-1][1] / benchmark_curve[0][1]) - 1.0

    return {
        "status": "ok",
        "start_equity": curve[0].equity,
        "end_equity": curve[-1].equity,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "mean_period_return": mean_ret,
        "volatility": vol,
        "sharpe_like": sharpe_like,
        "benchmark_return": benchmark_return,
        "excess_return": total_return - benchmark_return,
    }
