"""
Plotly chart builders for shock simulation output.
All functions receive typed data models and return go.Figure — no business logic here.
"""
import logging

import plotly.graph_objects as go

from src.models.simulation import DealFinancials, ScenarioMetrics, SimulationResult, TornadoBar
from src.services.sensitivity_analysis import run_sensitivity_curve

logger = logging.getLogger(__name__)

# ── Design tokens ─────────────────────────────────────────────────────────────
_C = {
    "base":     "#4C9BE8",   # 파란색 — 기본 시나리오
    "positive": "#00C853",   # 초록색 — 상승
    "negative": "#FF1744",   # 빨간색 — 하락
    "neutral":  "#8B949E",   # 회색
    "accent":   "#C9A84C",   # 골드 — 강조
    "bg":       "rgba(0,0,0,0)",           # 투명 배경 (Streamlit 테마 따름)
    "panel":    "rgba(22, 27, 34, 0.6)",   # 차트 패널
    "grid":     "rgba(139,148,158,0.15)",  # 그리드 라인
    "text":     "#E6EDF3",
}

_KR_FONT = "Malgun Gothic, Apple SD Gothic Neo, Noto Sans KR, Nanum Gothic, sans-serif"


def _dark_layout(**kwargs) -> dict:
    """Bloomberg-style dark layout defaults."""
    base = dict(
        paper_bgcolor=_C["bg"],
        plot_bgcolor=_C["panel"],
        font=dict(family=_KR_FONT, size=12, color=_C["text"]),
        xaxis=dict(
            gridcolor=_C["grid"],
            zerolinecolor=_C["grid"],
            linecolor=_C["neutral"],
            tickfont=dict(color=_C["text"]),
            title_font=dict(color=_C["neutral"]),
        ),
        yaxis=dict(
            gridcolor=_C["grid"],
            zerolinecolor=_C["grid"],
            linecolor=_C["neutral"],
            tickfont=dict(color=_C["text"]),
            title_font=dict(color=_C["neutral"]),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=_C["grid"],
            font=dict(color=_C["text"]),
        ),
        margin=dict(l=60, r=30, t=60, b=60),
    )
    base.update(kwargs)
    return base


# ── Tornado chart ─────────────────────────────────────────────────────────────

def plot_tornado_chart(
    tornado_bars: list[TornadoBar],
    base_irr: float | None,
    title: str = "IRR 민감도 분석 — 토네이도 차트",
) -> go.Figure:
    base = base_irr or 0.0
    params = [b.parameter for b in tornado_bars]
    low_deltas  = [(b.low_irr  or base) - base for b in tornado_bars]
    high_deltas = [(b.high_irr or base) - base for b in tornado_bars]
    low_labels  = [f"{b.low_label}: {(b.low_irr  or 0)*100:.1f}%" for b in tornado_bars]
    high_labels = [f"{b.high_label}: {(b.high_irr or 0)*100:.1f}%" for b in tornado_bars]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="하락 시나리오",
        x=[d * 100 for d in low_deltas],
        y=params,
        orientation="h",
        marker_color=_C["negative"],
        text=low_labels,
        textposition="outside",
        textfont=dict(color=_C["text"], size=10),
        hovertemplate="%{y}: %{x:.2f}pp vs 기본<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="상승 시나리오",
        x=[d * 100 for d in high_deltas],
        y=params,
        orientation="h",
        marker_color=_C["positive"],
        text=high_labels,
        textposition="outside",
        textfont=dict(color=_C["text"], size=10),
        hovertemplate="%{y}: +%{x:.2f}pp vs 기본<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=1.5, line_color=_C["neutral"])

    fig.update_layout(
        **_dark_layout(
            title=dict(text=title, font=dict(size=14, color=_C["accent"])),
            xaxis_title="기본 대비 IRR 변화 (pp)",
            yaxis_title="변수",
            barmode="overlay",
            height=max(300, 60 * len(params)),
            legend=dict(orientation="h", y=-0.18, font=dict(color=_C["text"])),
        )
    )
    return fig


# ── Scenario comparison ───────────────────────────────────────────────────────

def plot_scenario_comparison(
    base_case: ScenarioMetrics,
    shocked_scenarios: list[ScenarioMetrics],
    metric: str = "irr",
) -> go.Figure:
    all_scenarios = [base_case] + shocked_scenarios
    labels = [s.label for s in all_scenarios]

    if metric == "irr":
        values  = [(s.irr or 0) * 100 for s in all_scenarios]
        y_title = "IRR (%)"
        title   = "IRR — 기본 대비 충격 시나리오"
    else:
        values  = [s.moic for s in all_scenarios]
        y_title = "MOIC (x)"
        title   = "MOIC — 기본 대비 충격 시나리오"

    colors = [
        _C["accent"] if i == 0
        else (_C["positive"] if values[i] >= values[0] else _C["negative"])
        for i in range(len(values))
    ]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        textfont=dict(color=_C["text"]),
        hovertemplate="%{x}: %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(
        y=values[0],
        line_dash="dash",
        line_color=_C["neutral"],
        annotation_text="기본",
        annotation_font_color=_C["neutral"],
        annotation_position="top right",
    )
    fig.update_layout(
        **_dark_layout(
            title=dict(text=title, font=dict(size=14, color=_C["accent"])),
            yaxis_title=y_title,
            xaxis_tickangle=-30,
            height=400,
        )
    )
    return fig


# ── Waterfall chart ───────────────────────────────────────────────────────────

def plot_irr_waterfall(
    base_case: ScenarioMetrics,
    shock_scenario: ScenarioMetrics,
) -> go.Figure:
    base_irr  = (base_case.irr  or 0) * 100
    shock_irr = (shock_scenario.irr or 0) * 100
    delta = shock_irr - base_irr

    multiple_delta = (
        (shock_scenario.exit_multiple - base_case.exit_multiple)
        / base_case.exit_multiple * base_irr
    )
    growth_delta = (
        (shock_scenario.effective_growth_rate - base_case.effective_growth_rate)
        / max(base_case.effective_growth_rate, 0.001) * base_irr * 0.5
    )
    rate_delta = delta - multiple_delta - growth_delta

    fig = go.Figure(go.Waterfall(
        name="IRR 브리지",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=[
            "기본 IRR",
            "배수 변화",
            "성장률 변화",
            "금리 / 기타",
            f"충격 후 IRR\n({shock_scenario.label})",
        ],
        y=[base_irr, multiple_delta, growth_delta, rate_delta, shock_irr],
        connector={"line": {"color": _C["neutral"]}},
        decreasing={"marker": {"color": _C["negative"]}},
        increasing={"marker": {"color": _C["positive"]}},
        totals={"marker":    {"color": _C["accent"]}},
        text=[f"{v:.1f}%" for v in [base_irr, multiple_delta, growth_delta, rate_delta, shock_irr]],
        textposition="outside",
        textfont=dict(color=_C["text"]),
    ))
    fig.update_layout(
        **_dark_layout(
            title=dict(
                text=f"IRR 브리지 — 기본 → {shock_scenario.label}",
                font=dict(size=14, color=_C["accent"]),
            ),
            yaxis_title="IRR (%)",
            height=420,
            showlegend=False,
        )
    )
    return fig


# ── Sensitivity curves ────────────────────────────────────────────────────────

def plot_sensitivity_curves(
    financials: DealFinancials,
    fields: list[str] | None = None,
) -> go.Figure:
    if fields is None:
        fields = ["revenue_growth_rate", "ev_revenue_multiple", "discount_rate"]

    _field_labels = {
        "revenue_growth_rate": "매출 성장률",
        "ev_revenue_multiple": "엑싯 배수",
        "discount_rate":       "할인율 (WACC)",
        "holding_period_years": "보유 기간",
    }

    fig = go.Figure()
    colors = [_C["base"], _C["positive"], _C["negative"], _C["accent"]]

    for field, color in zip(fields, colors):
        curve  = run_sensitivity_curve(financials, field, n_points=25, delta_range=0.40)
        x_vals = [pt[0] for pt in curve]
        y_vals = [(pt[1] or 0) * 100 for pt in curve]
        label  = _field_labels.get(field, field)

        base_val = float(getattr(financials, field))
        x_pct    = [(v - base_val) / base_val * 100 for v in x_vals]

        fig.add_trace(go.Scatter(
            x=x_pct, y=y_vals,
            mode="lines",
            name=label,
            line=dict(color=color, width=2),
            hovertemplate=f"{label}: %{{x:.1f}}% → IRR %{{y:.1f}}%<extra></extra>",
        ))

    fig.add_vline(
        x=0,
        line_dash="dot",
        line_color=_C["neutral"],
        annotation_text="기본",
        annotation_font_color=_C["neutral"],
    )
    fig.update_layout(
        **_dark_layout(
            title=dict(text="IRR 민감도 곡선", font=dict(size=14, color=_C["accent"])),
            xaxis_title="기본 대비 파라미터 변화 (%)",
            yaxis_title="IRR (%)",
            height=420,
            legend=dict(orientation="h", y=-0.22, font=dict(color=_C["text"])),
        )
    )
    return fig
