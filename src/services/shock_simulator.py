"""
Orchestrator for the shock simulation pipeline.
Contains zero LLM calls — all computation is deterministic Python.
Per CLAUDE.md §5: LLMs are only responsible for interpretation narrative.
"""
import logging

from src.models.simulation import (
    DealFinancials,
    ScenarioMetrics,
    ShockScenario,
    ShockType,
    SimulationResult,
)
from src.services.sensitivity_analysis import build_tornado_bars
from src.services.shock_calculator import (
    apply_fx_shock,
    apply_interest_rate_shock,
    apply_market_downturn_shock,
    compute_base_case,
)

logger = logging.getLogger(__name__)

# ── Preset shock scenarios ────────────────────────────────────────────────────

PRESET_SCENARIOS: list[ShockScenario] = [
    ShockScenario(
        shock_type=ShockType.INTEREST_RATE,
        label="Rate +100bps",
        magnitude=0.01,
    ),
    ShockScenario(
        shock_type=ShockType.INTEREST_RATE,
        label="Rate +200bps",
        magnitude=0.02,
    ),
    ShockScenario(
        shock_type=ShockType.INTEREST_RATE,
        label="Rate +300bps",
        magnitude=0.03,
    ),
    ShockScenario(
        shock_type=ShockType.FX_CHANGE,
        label="FX -10%",
        magnitude=-0.10,
    ),
    ShockScenario(
        shock_type=ShockType.FX_CHANGE,
        label="FX -20%",
        magnitude=-0.20,
    ),
    ShockScenario(
        shock_type=ShockType.MARKET_DOWNTURN,
        label="Market -20%",
        magnitude=0.20,
    ),
    ShockScenario(
        shock_type=ShockType.MARKET_DOWNTURN,
        label="Market -40%",
        magnitude=0.40,
    ),
]


def _apply_scenario(f: DealFinancials, scenario: ShockScenario) -> ScenarioMetrics:
    if scenario.shock_type == ShockType.INTEREST_RATE:
        return apply_interest_rate_shock(f, scenario.magnitude)
    if scenario.shock_type == ShockType.FX_CHANGE:
        return apply_fx_shock(f, scenario.magnitude)
    if scenario.shock_type == ShockType.MARKET_DOWNTURN:
        return apply_market_downturn_shock(f, scenario.magnitude)
    raise ValueError(f"Unknown shock type: {scenario.shock_type}")


def run_simulation(
    financials: DealFinancials,
    scenarios: list[ShockScenario] | None = None,
) -> SimulationResult:
    """
    Run the full shock simulation.

    Parameters
    ----------
    financials : DealFinancials
        Base-case financial inputs.
    scenarios : list[ShockScenario] | None
        Shock scenarios to apply; defaults to PRESET_SCENARIOS.

    Returns
    -------
    SimulationResult
        Base case, all shocked scenarios, and tornado bars.
        Claude's interpretation narrative is added separately by the calling agent.
    """
    active_scenarios = scenarios or PRESET_SCENARIOS

    logger.info("Shock simulation starting for '%s'", financials.company_name)
    base = compute_base_case(financials)
    logger.info("Base case: IRR=%.1f%% MOIC=%.2fx", (base.irr or 0) * 100, base.moic)

    shocked: list[ScenarioMetrics] = []
    for scenario in active_scenarios:
        result = _apply_scenario(financials, scenario)
        shocked.append(result)
        logger.info(
            "Scenario [%s]: IRR=%.1f%% MOIC=%.2fx exit=$%.1fM",
            result.label, (result.irr or 0) * 100, result.moic, result.exit_value_usd_m,
        )

    tornado = build_tornado_bars(financials)
    logger.info("Tornado built — top driver: %s (swing=%.1f%%)", tornado[0].parameter, tornado[0].irr_swing * 100)

    return SimulationResult(
        company_name=financials.company_name,
        base_case=base,
        shocked_scenarios=shocked,
        tornado_bars=tornado,
    )
