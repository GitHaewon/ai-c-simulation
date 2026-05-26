"""
Sensitivity analysis for tornado chart generation.
All deterministic — no LLM calls.
"""
import logging
from copy import deepcopy

from src.models.simulation import DealFinancials, TornadoBar
from src.services.shock_calculator import (
    build_cash_flows,
    calculate_irr,
    calculate_moic,
    compute_exit_revenue,
    compute_exit_value,
)

logger = logging.getLogger(__name__)

# ── Parameter ranges for tornado analysis ─────────────────────────────────────

TORNADO_PARAMS: list[dict] = [
    {
        "name": "Revenue Growth Rate",
        "field": "revenue_growth_rate",
        "low_delta": -0.10,   # -10pp absolute
        "high_delta": +0.10,
        "fmt": lambda v: f"{v * 100:+.0f}pp",
    },
    {
        "name": "Exit EV/Revenue Multiple",
        "field": "ev_revenue_multiple",
        "low_delta": -2.0,    # -2x absolute
        "high_delta": +2.0,
        "fmt": lambda v: f"{v:+.1f}x",
    },
    {
        "name": "Discount Rate (WACC)",
        "field": "discount_rate",
        "low_delta": -0.02,   # -200bps
        "high_delta": +0.02,
        "fmt": lambda v: f"{v * 100:+.0f}bps",
    },
    {
        "name": "Holding Period",
        "field": "holding_period_years",
        "low_delta": -1,
        "high_delta": +2,
        "fmt": lambda v: f"{v:+d}yr",
    },
    {
        "name": "EBITDA Margin",
        "field": "ebitda_margin",
        "low_delta": -0.10,
        "high_delta": +0.10,
        "fmt": lambda v: f"{v * 100:+.0f}pp",
    },
]


def _irr_for_financials(f: DealFinancials) -> float | None:
    exit_rev = compute_exit_revenue(f.revenue_usd_m, f.revenue_growth_rate, f.holding_period_years)
    exit_val = compute_exit_value(exit_rev, f.ev_revenue_multiple, f.debt_usd_m)
    flows = build_cash_flows(f.invested_capital_usd_m, exit_val, f.holding_period_years)
    return calculate_irr(flows)


def _perturb(f: DealFinancials, field: str, delta: float | int) -> DealFinancials:
    data = f.model_dump()
    data[field] = max(data[field] + delta, 0.001)  # floor to prevent negatives
    return DealFinancials(**data)


def build_tornado_bars(f: DealFinancials) -> list[TornadoBar]:
    """
    For each parameter, compute IRR at low and high perturbation.
    Returns bars sorted descending by |IRR swing| — ready for tornado chart.
    """
    bars: list[TornadoBar] = []

    for param in TORNADO_PARAMS:
        f_low = _perturb(f, param["field"], param["low_delta"])
        f_high = _perturb(f, param["field"], param["high_delta"])

        low_irr = _irr_for_financials(f_low)
        high_irr = _irr_for_financials(f_high)

        swing = abs((high_irr or 0) - (low_irr or 0))

        bars.append(
            TornadoBar(
                parameter=param["name"],
                low_irr=low_irr,
                high_irr=high_irr,
                low_label=param["fmt"](param["low_delta"]),
                high_label=param["fmt"](param["high_delta"]),
                irr_swing=round(swing, 4),
            )
        )
        logger.debug(
            "Tornado [%s]: low_irr=%.2f%% high_irr=%.2f%% swing=%.2f%%",
            param["name"],
            (low_irr or 0) * 100, (high_irr or 0) * 100, swing * 100,
        )

    bars.sort(key=lambda b: b.irr_swing, reverse=True)
    return bars


def run_sensitivity_curve(
    f: DealFinancials,
    field: str,
    n_points: int = 20,
    delta_range: float = 0.5,
) -> list[tuple[float, float | None, float]]:
    """
    Vary `field` from (base - delta_range) to (base + delta_range) in n_points steps.
    Returns [(param_value, irr, moic), ...].
    """
    base_val: float = float(getattr(f, field))
    low = base_val * (1.0 - delta_range)
    high = base_val * (1.0 + delta_range)
    values = [low + (high - low) * i / (n_points - 1) for i in range(n_points)]

    results: list[tuple[float, float | None, float]] = []
    for val in values:
        f_perturbed = _perturb(f, field, val - base_val)
        exit_rev = compute_exit_revenue(
            f_perturbed.revenue_usd_m,
            f_perturbed.revenue_growth_rate,
            f_perturbed.holding_period_years,
        )
        exit_val = compute_exit_value(exit_rev, f_perturbed.ev_revenue_multiple, f_perturbed.debt_usd_m)
        flows = build_cash_flows(f_perturbed.invested_capital_usd_m, exit_val, f_perturbed.holding_period_years)
        irr = calculate_irr(flows)
        moic = calculate_moic(f_perturbed.invested_capital_usd_m, exit_val)
        results.append((round(val, 4), irr, moic))

    return results
