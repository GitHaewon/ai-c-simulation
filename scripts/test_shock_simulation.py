"""
Smoke-test for the Shock Simulation engine.

Run from project root:
    python scripts/test_shock_simulation.py
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.simulation import DealFinancials, ShockScenario, ShockType
from src.services.shock_simulator import run_simulation
from src.services.visualization import (
    plot_irr_waterfall,
    plot_scenario_comparison,
    plot_sensitivity_curves,
    plot_tornado_chart,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


SAMPLE_DEAL = DealFinancials(
    company_name="Acme AI",
    invested_capital_usd_m=30.0,
    revenue_usd_m=12.0,
    revenue_growth_rate=0.60,        # 60% CAGR
    ebitda_margin=0.15,
    ev_revenue_multiple=10.0,
    holding_period_years=5,
    discount_rate=0.12,
    debt_usd_m=0.0,
    foreign_revenue_pct=0.40,        # 40% revenue in foreign currency
)


def test_base_and_presets() -> None:
    result = run_simulation(SAMPLE_DEAL)

    base = result.base_case
    print("\n── Base Case ─────────────────────────────────────────")
    print(f"  IRR  : {(base.irr or 0) * 100:.1f}%")
    print(f"  MOIC : {base.moic:.2f}x")
    print(f"  Exit : ${base.exit_value_usd_m:.1f}M  (revenue ${base.exit_revenue_usd_m:.1f}M × {base.exit_multiple:.1f}x)")

    print("\n── Shock Scenarios ───────────────────────────────────")
    for s in result.shocked_scenarios:
        delta = ((s.irr or 0) - (base.irr or 0)) * 100
        print(
            f"  {s.label:<22} IRR={( s.irr or 0)*100:5.1f}%  "
            f"MOIC={s.moic:.2f}x  Δ={delta:+.1f}pp"
        )

    print("\n── Tornado (top 3 drivers) ───────────────────────────")
    for bar in result.tornado_bars[:3]:
        print(
            f"  {bar.parameter:<30} swing={bar.irr_swing * 100:.1f}pp  "
            f"[{bar.low_label} → {bar.high_label}]"
        )

    assert base.irr is not None, "Base IRR must be computable"
    assert base.moic > 1.0, "Base MOIC must be > 1x"
    assert len(result.tornado_bars) > 0
    print("\ntest_base_and_presets PASSED")


def test_custom_shock() -> None:
    custom = [
        ShockScenario(shock_type=ShockType.INTEREST_RATE, label="Severe Rate Shock", magnitude=0.05),
        ShockScenario(shock_type=ShockType.FX_CHANGE, label="FX -30%", magnitude=-0.30),
        ShockScenario(shock_type=ShockType.MARKET_DOWNTURN, label="Severe Downturn", magnitude=0.60),
    ]
    result = run_simulation(SAMPLE_DEAL, scenarios=custom)
    assert len(result.shocked_scenarios) == 3
    print("test_custom_shock PASSED")


def test_charts_build() -> None:
    result = run_simulation(SAMPLE_DEAL)

    fig1 = plot_tornado_chart(result.tornado_bars, result.base_case.irr)
    assert fig1 is not None

    fig2 = plot_scenario_comparison(result.base_case, result.shocked_scenarios, metric="irr")
    assert fig2 is not None

    fig3 = plot_scenario_comparison(result.base_case, result.shocked_scenarios, metric="moic")
    assert fig3 is not None

    fig4 = plot_irr_waterfall(result.base_case, result.shocked_scenarios[1])  # rate +200bps
    assert fig4 is not None

    fig5 = plot_sensitivity_curves(SAMPLE_DEAL)
    assert fig5 is not None

    print("test_charts_build PASSED (5 figures created)")


if __name__ == "__main__":
    test_base_and_presets()
    test_custom_shock()
    test_charts_build()
