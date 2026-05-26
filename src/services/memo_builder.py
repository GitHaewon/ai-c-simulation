"""
Assembles ICMemo from agent outputs and simulation results.
Contains zero LLM calls — all assembly is deterministic extraction.
Per CLAUDE.md §5: LLMs supply narrative text; this layer only structures it.
"""
import logging

from src.models.agent_output import AgentOutput, ChairmanOutput, DataCollectionOutput, Vote
from src.models.memo import (
    FinancialSection,
    ICMemo,
    MemoHeader,
    OverviewSection,
    RecommendationSection,
    RiskItem,
    RiskSection,
    ShockSection,
    ShockSummaryRow,
    ThesisSection,
)
from src.models.simulation import SimulationResult

logger = logging.getLogger(__name__)


def build_memo(
    company_name: str,
    industry: str,
    deal_stage: str = "",
    investment_amount_usd_m: float = 0.0,
    data_collection: DataCollectionOutput | None = None,
    financial_output: AgentOutput | None = None,
    risk_output: AgentOutput | None = None,
    bull_output: AgentOutput | None = None,
    bear_output: AgentOutput | None = None,
    chairman_output: ChairmanOutput | None = None,
    simulation: SimulationResult | None = None,
) -> ICMemo:
    """
    Assemble a complete ICMemo from typed agent outputs and simulation data.
    Missing outputs produce empty sections — no hard failures.
    """
    logger.info("Building IC memo for '%s'", company_name)

    memo = ICMemo(
        header=_build_header(company_name, industry, deal_stage, investment_amount_usd_m),
        overview=_build_overview(data_collection),
        financials=_build_financials(financial_output, simulation),
        thesis=_build_thesis(bull_output, bear_output),
        risks=_build_risks(risk_output),
        shock_summary=_build_shock_summary(simulation),
        recommendation=_build_recommendation(chairman_output),
    )
    logger.info("IC memo assembled — decision: %s", memo.recommendation.decision.value)
    return memo


# ── Section builders ──────────────────────────────────────────────────────────

def _build_header(
    company_name: str, industry: str, deal_stage: str, amount: float
) -> MemoHeader:
    return MemoHeader(
        company_name=company_name,
        industry=industry,
        deal_stage=deal_stage,
        investment_amount_usd_m=amount,
    )


def _build_overview(dc: DataCollectionOutput | None) -> OverviewSection:
    if dc is None:
        return OverviewSection()
    return OverviewSection(key_facts=dc.key_facts, data_sources=dc.data_sources)


def _build_financials(
    output: AgentOutput | None,
    sim: SimulationResult | None,
) -> FinancialSection:
    base_irr = None
    base_moic = 0.0
    exit_val = 0.0
    exit_mult = 0.0

    if sim:
        base_irr = (sim.base_case.irr or 0.0) * 100
        base_moic = sim.base_case.moic
        exit_val = sim.base_case.exit_value_usd_m
        exit_mult = sim.base_case.exit_multiple

    if output is None:
        return FinancialSection(
            base_irr_pct=base_irr, base_moic=base_moic,
            exit_value_usd_m=exit_val, exit_multiple=exit_mult,
        )
    return FinancialSection(
        base_irr_pct=base_irr,
        base_moic=base_moic,
        exit_value_usd_m=exit_val,
        exit_multiple=exit_mult,
        findings=output.findings,
        concerns=output.concerns,
        agent_confidence=output.confidence,
    )


def _build_thesis(
    bull: AgentOutput | None,
    bear: AgentOutput | None,
) -> ThesisSection:
    return ThesisSection(
        lead_thesis="",  # populated by Lead Partner agent in Phase 6
        bull_points=bull.findings if bull else [],
        bear_points=bear.findings if bear else [],
    )


def _build_risks(output: AgentOutput | None) -> RiskSection:
    if output is None:
        return RiskSection()
    risks = [
        RiskItem(
            label=f"Risk {i + 1}",
            description=concern,
            severity=_infer_severity(concern),
        )
        for i, concern in enumerate(output.concerns)
    ]
    return RiskSection(risks=risks, agent_confidence=output.confidence)


def _build_shock_summary(sim: SimulationResult | None) -> ShockSection:
    if sim is None:
        return ShockSection()

    base_irr = (sim.base_case.irr or 0.0) * 100
    rows = [
        ShockSummaryRow(
            label=s.label,
            irr_pct=(s.irr or 0.0) * 100 if s.irr is not None else None,
            moic=s.moic,
            delta_irr_pp=((s.irr or 0.0) - (sim.base_case.irr or 0.0)) * 100
            if s.irr is not None
            else None,
        )
        for s in sim.shocked_scenarios
    ]
    top = sim.tornado_bars[0] if sim.tornado_bars else None
    return ShockSection(
        base_irr_pct=round(base_irr, 2),
        base_moic=sim.base_case.moic,
        scenarios=rows,
        top_driver=top.parameter if top else "",
        top_driver_swing_pp=round(top.irr_swing * 100, 2) if top else 0.0,
    )


def _build_recommendation(output: ChairmanOutput | None) -> RecommendationSection:
    if output is None:
        return RecommendationSection(decision=Vote.CONDITIONAL, rationale="Pending committee deliberation.")
    return RecommendationSection(
        decision=output.final_decision,
        vote_tally=output.vote_tally,
        quorum_met=output.quorum_met,
        conditions=output.conditions,
        rationale=output.resolution_rationale,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_severity(concern_text: str) -> str:
    text = concern_text.lower()
    if any(w in text for w in ("critical", "severe", "ban", "fraud", "insolvency")):
        return "High"
    if any(w in text for w in ("regulatory", "concentration", "dependency", "burn")):
        return "High"
    if any(w in text for w in ("competitive", "margin", "uncertain", "unclear")):
        return "Medium"
    return "Low"
