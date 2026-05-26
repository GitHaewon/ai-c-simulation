"""
Export ICMemo to JSON, Markdown, and PPTX.
No business logic — pure format conversion.
"""
import json
import logging
from pathlib import Path

from src.models.agent_output import Vote
from src.models.memo import ICMemo
from src.services.pptx_builder import export_pptx as _build_pptx

logger = logging.getLogger(__name__)

_VOTE_LABEL = {Vote.APPROVE: "✅ APPROVE", Vote.CONDITIONAL: "⚠️ CONDITIONAL", Vote.REJECT: "❌ REJECT"}
_SEVERITY_EMOJI = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}


# ── JSON ──────────────────────────────────────────────────────────────────────

def export_json(memo: ICMemo, output_path: Path | None = None) -> str:
    payload = json.dumps(json.loads(memo.model_dump_json()), indent=2, ensure_ascii=False)
    if output_path:
        output_path.write_text(payload, encoding="utf-8")
        logger.info("Memo exported to JSON: %s", output_path)
    return payload


# ── Markdown ──────────────────────────────────────────────────────────────────

def export_markdown(memo: ICMemo, output_path: Path | None = None) -> str:
    h = memo.header
    lines: list[str] = [
        f"# Investment Committee Memo — {h.company_name}",
        f"> **Industry:** {h.industry}  |  **Stage:** {h.deal_stage or 'N/A'}  "
        f"|  **Amount:** ${h.investment_amount_usd_m:.1f}M  |  **Date:** {h.prepared_date}",
        "",
    ]

    # 1. Investment Overview
    lines += ["---", "## 1. Investment Overview", ""]
    for fact in memo.overview.key_facts:
        lines.append(f"- {fact}")
    if memo.overview.data_sources:
        lines += ["", "**Sources:** " + " | ".join(memo.overview.data_sources)]
    lines.append("")

    # 2. Financial Analysis
    f = memo.financials
    lines += [
        "---", "## 2. Financial Analysis", "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Base IRR | {f.base_irr_pct:.1f}% |" if f.base_irr_pct else "| Base IRR | — |",
        f"| Base MOIC | {f.base_moic:.2f}x |",
        f"| Exit Value | ${f.exit_value_usd_m:.1f}M |",
        f"| Exit Multiple | {f.exit_multiple:.1f}x EV/Rev |",
        "",
    ]
    if f.findings:
        lines.append("**Findings:**")
        for item in f.findings:
            lines.append(f"- {item}")
    if f.concerns:
        lines += ["", "**Concerns:**"]
        for item in f.concerns:
            lines.append(f"- {item}")
    lines.append("")

    # 3. Investment Thesis
    t = memo.thesis
    lines += ["---", "## 3. Investment Thesis", ""]
    if t.lead_thesis:
        lines += [f"> {t.lead_thesis}", ""]
    if t.bull_points:
        lines += ["### Bull Case"]
        for p in t.bull_points:
            lines.append(f"- {p}")
        lines.append("")
    if t.bear_points:
        lines += ["### Bear Case"]
        for p in t.bear_points:
            lines.append(f"- {p}")
    lines.append("")

    # 4. Key Risks
    lines += ["---", "## 4. Key Risks", "",
              "| # | Risk | Severity |", "|---|------|----------|"]
    for i, risk in enumerate(memo.risks.risks, 1):
        emoji = _SEVERITY_EMOJI.get(risk.severity, "")
        lines.append(f"| {i} | {risk.description} | {emoji} {risk.severity} |")
    lines.append("")

    # 5. Shock Simulation Summary
    s = memo.shock_summary
    lines += ["---", "## 5. Shock Simulation Summary", ""]
    if s.base_irr_pct is not None:
        lines.append(f"**Base Case:** IRR {s.base_irr_pct:.1f}% | MOIC {s.base_moic:.2f}x")
        lines.append("")
    if s.top_driver:
        lines.append(f"**Top Sensitivity Driver:** {s.top_driver} (±{s.top_driver_swing_pp:.1f}pp IRR swing)")
        lines.append("")
    lines += ["| Scenario | IRR | MOIC | ΔIRR vs Base |",
              "|----------|-----|------|--------------|"]
    for row in s.scenarios:
        irr_str = f"{row.irr_pct:.1f}%" if row.irr_pct is not None else "—"
        delta_str = f"{row.delta_irr_pp:+.1f}pp" if row.delta_irr_pp is not None else "—"
        lines.append(f"| {row.label} | {irr_str} | {row.moic:.2f}x | {delta_str} |")
    lines.append("")

    # 6. Final Recommendation
    r = memo.recommendation
    lines += [
        "---", "## 6. Final Recommendation", "",
        f"### Decision: {_VOTE_LABEL[r.decision]}",
        "",
        f"**Quorum Met:** {'Yes' if r.quorum_met else 'No'}",
        "",
    ]
    if r.vote_tally:
        lines += ["**Vote Tally:**", ""]
        for agent, vote in r.vote_tally.items():
            lines.append(f"- {agent}: `{vote}`")
        lines.append("")
    if r.conditions:
        lines += ["**Conditions:**"]
        for cond in r.conditions:
            lines.append(f"- {cond}")
        lines.append("")
    if r.rationale:
        lines += ["**Rationale:**", "", r.rationale, ""]

    content = "\n".join(lines)
    if output_path:
        output_path.write_text(content, encoding="utf-8")
        logger.info("Memo exported to Markdown: %s", output_path)
    return content


# ── PPTX ──────────────────────────────────────────────────────────────────────

def export_pptx(memo: ICMemo, output_path: Path) -> Path:
    return _build_pptx(memo, output_path)
