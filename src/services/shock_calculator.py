"""
All financial calculations are deterministic Python — zero LLM calls.
Per CLAUDE.md §5: LLMs must never compute numbers Python can compute.
"""
import logging

import numpy as np

from src.models.simulation import DealFinancials, ScenarioMetrics

logger = logging.getLogger(__name__)

# ── Calibration constants ─────────────────────────────────────────────────────

# Each 100bps rate rise compresses EV/Revenue multiple by this fraction.
RATE_TO_MULTIPLE_SENSITIVITY = 4.0

# Market downturn transmits to revenue growth at this fraction.
GROWTH_SHOCK_TRANSMISSION = 0.7

# Market downturn transmits to exit multiple compression at this fraction.
MULTIPLE_SHOCK_TRANSMISSION = 0.6


# ── Core financial functions ──────────────────────────────────────────────────

def calculate_irr(cash_flows: list[float]) -> float | None:
    """
    Newton-Raphson IRR on a cash flow series.
    Returns None when no solution converges (e.g., all-positive flows).
    """
    if not cash_flows or cash_flows[0] >= 0:
        return None

    rate = 0.10
    for _ in range(1000):
        npv = sum(cf / (1.0 + rate) ** t for t, cf in enumerate(cash_flows))
        dnpv = sum(
            -t * cf / (1.0 + rate) ** (t + 1)
            for t, cf in enumerate(cash_flows)
            if t > 0
        )
        if abs(dnpv) < 1e-14:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-9:
            return round(new_rate, 6)
        rate = new_rate
    return None


def calculate_moic(invested_capital: float, exit_value: float) -> float:
    return round(exit_value / invested_capital, 4)


def build_cash_flows(
    invested_capital: float,
    exit_value: float,
    holding_period_years: int,
) -> list[float]:
    """Standard VC cash flow: outflow at t=0, exit at t=N."""
    flows = [-invested_capital] + [0.0] * (holding_period_years - 1) + [exit_value]
    return flows


def compute_exit_revenue(
    base_revenue: float,
    growth_rate: float,
    years: int,
) -> float:
    return base_revenue * (1.0 + growth_rate) ** years


def compute_exit_value(exit_revenue: float, multiple: float, debt: float) -> float:
    return max(exit_revenue * multiple - debt, 0.0)


# ── Base-case builder ─────────────────────────────────────────────────────────

def compute_base_case(f: DealFinancials) -> ScenarioMetrics:
    exit_rev = compute_exit_revenue(f.revenue_usd_m, f.revenue_growth_rate, f.holding_period_years)
    exit_val = compute_exit_value(exit_rev, f.ev_revenue_multiple, f.debt_usd_m)
    flows = build_cash_flows(f.invested_capital_usd_m, exit_val, f.holding_period_years)
    return ScenarioMetrics(
        label="Base Case",
        irr=calculate_irr(flows),
        moic=calculate_moic(f.invested_capital_usd_m, exit_val),
        exit_value_usd_m=round(exit_val, 3),
        exit_revenue_usd_m=round(exit_rev, 3),
        exit_multiple=f.ev_revenue_multiple,
        effective_growth_rate=f.revenue_growth_rate,
        effective_discount_rate=f.discount_rate,
        cash_flows=flows,
    )


# ── Shock appliers ────────────────────────────────────────────────────────────

def apply_interest_rate_shock(f: DealFinancials, delta_rate: float) -> ScenarioMetrics:
    """
    delta_rate: positive = rate rise (e.g. 0.02 = +200bps).
    Effect: discount rate rises, exit multiple compresses.
    """
    new_discount_rate = f.discount_rate + delta_rate
    multiple_compression = RATE_TO_MULTIPLE_SENSITIVITY * delta_rate
    new_multiple = max(f.ev_revenue_multiple * (1.0 - multiple_compression), 0.5)

    exit_rev = compute_exit_revenue(f.revenue_usd_m, f.revenue_growth_rate, f.holding_period_years)
    exit_val = compute_exit_value(exit_rev, new_multiple, f.debt_usd_m)
    flows = build_cash_flows(f.invested_capital_usd_m, exit_val, f.holding_period_years)

    label = f"Rate +{int(delta_rate * 10000)}bps"
    logger.debug("Shock [%s]: multiple %.2f→%.2f, exit_val $%.1fM", label, f.ev_revenue_multiple, new_multiple, exit_val)
    return ScenarioMetrics(
        label=label,
        irr=calculate_irr(flows),
        moic=calculate_moic(f.invested_capital_usd_m, exit_val),
        exit_value_usd_m=round(exit_val, 3),
        exit_revenue_usd_m=round(exit_rev, 3),
        exit_multiple=round(new_multiple, 3),
        effective_growth_rate=f.revenue_growth_rate,
        effective_discount_rate=round(new_discount_rate, 4),
        cash_flows=flows,
    )


def apply_fx_shock(f: DealFinancials, fx_change: float) -> ScenarioMetrics:
    """
    fx_change: signed fraction (e.g. -0.10 = foreign currency weakens 10%).
    Effect: revenue shrinks proportional to foreign_revenue_pct.
    """
    revenue_impact = 1.0 + f.foreign_revenue_pct * fx_change
    adj_revenue = f.revenue_usd_m * revenue_impact

    exit_rev = compute_exit_revenue(adj_revenue, f.revenue_growth_rate, f.holding_period_years)
    exit_val = compute_exit_value(exit_rev, f.ev_revenue_multiple, f.debt_usd_m)
    flows = build_cash_flows(f.invested_capital_usd_m, exit_val, f.holding_period_years)

    direction = "+" if fx_change >= 0 else ""
    label = f"FX {direction}{fx_change * 100:.0f}%"
    logger.debug("Shock [%s]: adj_revenue $%.1fM, exit_val $%.1fM", label, adj_revenue, exit_val)
    return ScenarioMetrics(
        label=label,
        irr=calculate_irr(flows),
        moic=calculate_moic(f.invested_capital_usd_m, exit_val),
        exit_value_usd_m=round(exit_val, 3),
        exit_revenue_usd_m=round(exit_rev, 3),
        exit_multiple=f.ev_revenue_multiple,
        effective_growth_rate=f.revenue_growth_rate,
        effective_discount_rate=f.discount_rate,
        cash_flows=flows,
    )


def apply_market_downturn_shock(f: DealFinancials, downturn_severity: float) -> ScenarioMetrics:
    """
    downturn_severity: 0–1 (e.g. 0.30 = severe 30% market contraction).
    Effect: revenue growth and exit multiple both compress.
    """
    growth_adj = f.revenue_growth_rate * (1.0 - GROWTH_SHOCK_TRANSMISSION * downturn_severity)
    multiple_adj = f.ev_revenue_multiple * (1.0 - MULTIPLE_SHOCK_TRANSMISSION * downturn_severity)

    exit_rev = compute_exit_revenue(f.revenue_usd_m, growth_adj, f.holding_period_years)
    exit_val = compute_exit_value(exit_rev, multiple_adj, f.debt_usd_m)
    flows = build_cash_flows(f.invested_capital_usd_m, exit_val, f.holding_period_years)

    label = f"Market -{downturn_severity * 100:.0f}%"
    logger.debug("Shock [%s]: growth %.2f→%.2f, multiple %.2f→%.2f", label, f.revenue_growth_rate, growth_adj, f.ev_revenue_multiple, multiple_adj)
    return ScenarioMetrics(
        label=label,
        irr=calculate_irr(flows),
        moic=calculate_moic(f.invested_capital_usd_m, exit_val),
        exit_value_usd_m=round(exit_val, 3),
        exit_revenue_usd_m=round(exit_rev, 3),
        exit_multiple=round(multiple_adj, 3),
        effective_growth_rate=round(growth_adj, 4),
        effective_discount_rate=f.discount_rate,
        cash_flows=flows,
    )
