"""
Plotly chart builders for shock simulation output.
All functions receive typed data models and return go.Figure — no business logic here.
"""
import logging

import plotly.graph_objects as go

from src.models.simulation import ScenarioMetrics, SimulationResult, TornadoBar
from src.services.sensitivity_analysis import run_sensitivity_curve
from src.models.simulation import DealFinancials

logger = logging.getLogger(__name__)

_PALETTE = {
    "base": "#1f77b4",
    "positive": "#2ca02c",
    "negative": "#d62728",
    "neutral": "#7f7f7f",
    "accent": "#ff7f0e",
}


# ── Tornado chart ─────────────────────────────────────────────────────────────

def plot_tornado_chart(
    tornado_bars: list[TornadoBar],
    base_irr: float | None,
    title: str = "IRR Sensitivity — Tornado Chart",
) -> go.Figure:
    """
    Horizontal bar chart showing IRR swing for each parameter.
    Bars are sorted by |swing| descending (largest driver at top).
    """
    base = base_irr or 0.0
    params = [b.parameter for b in tornado_bars]
    low_deltas = [(b.low_irr or base) - base for b in tornado_bars]
    high_deltas = [(b.high_irr or base) - base for b in tornado_bars]
    low_labels = [f"{b.low_label}: {(b.low_irr or 0) * 100:.1f}%" for b in tornado_bars]
    high_labels = [f"{b.high_label}: {(b.high_irr or 0) * 100:.1f}%" for b in tornado_bars]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Downside",
        x=[d * 100 for d in low_deltas],
        y=params,
        orientation="h",
        marker_color=_PALETTE["negative"],
        text=low_labels,
        textposition="outside",
        hovertemplate="%{y}: %{x:.2f}pp vs base<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Upside",
        x=[d * 100 for d in high_deltas],
        y=params,
        orientation="h",
        marker_color=_PALETTE["positive"],
        text=high_labels,
        textposition="outside",
        hovertemplate="%{y}: +%{x:.2f}pp vs base<extra></extra>",
    ))
    fig.add_vline(x=0, line_width=2, line_color="black")

    fig.update_layout(
        title=title,
        xaxis_title="IRR Delta vs Base Case (pp)",
        yaxis_title="Parameter",
        barmode="overlay",
        template="plotly_white",
        height=max(300, 60 * len(params)),
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


# ── Scenario comparison ───────────────────────────────────────────────────────

def plot_scenario_comparison(
    base_case: ScenarioMetrics,
    shocked_scenarios: list[ScenarioMetrics],
    metric: str = "irr",
) -> go.Figure:
    """
    Grouped bar chart comparing base case vs all shock scenarios on IRR or MOIC.
    """
    all_scenarios = [base_case] + shocked_scenarios
    labels = [s.label for s in all_scenarios]

    if metric == "irr":
        values = [(s.irr or 0) * 100 for s in all_scenarios]
        y_title = "IRR (%)"
        title = "IRR — Base Case vs Shock Scenarios"
    else:
        values = [s.moic for s in all_scenarios]
        y_title = "MOIC (x)"
        title = "MOIC — Base Case vs Shock Scenarios"

    colors = [
        _PALETTE["base"] if i == 0 else (
            _PALETTE["positive"] if values[i] >= values[0]
            else _PALETTE["negative"]
        )
        for i in range(len(values))
    ]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        hovertemplate="%{x}: %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(
        y=values[0],
        line_dash="dash",
        line_color=_PALETTE["neutral"],
        annotation_text="Base",
        annotation_position="top right",
    )
    fig.update_layout(
        title=title,
        yaxis_title=y_title,
        xaxis_tickangle=-30,
        template="plotly_white",
        height=420,
    )
    return fig


# ── Waterfall chart ───────────────────────────────────────────────────────────

def plot_irr_waterfall(
    base_case: ScenarioMetrics,
    shock_scenario: ScenarioMetrics,
) -> go.Figure:
    """
    Waterfall breaking down IRR change from base to shock case.
    """
    base_irr = (base_case.irr or 0) * 100
    shock_irr = (shock_scenario.irr or 0) * 100
    delta = shock_irr - base_irr

    multiple_delta = (shock_scenario.exit_multiple - base_case.exit_multiple) / base_case.exit_multiple * base_irr
    growth_delta = (shock_scenario.effective_growth_rate - base_case.effective_growth_rate) / max(base_case.effective_growth_rate, 0.001) * base_irr * 0.5
    rate_delta = delta - multiple_delta - growth_delta  # residual

    fig = go.Figure(go.Waterfall(
        name="IRR Bridge",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=["Base IRR", "Multiple Δ", "Growth Δ", "Rate / Other Δ", f"Shock IRR\n({shock_scenario.label})"],
        y=[base_irr, multiple_delta, growth_delta, rate_delta, shock_irr],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": _PALETTE["negative"]}},
        increasing={"marker": {"color": _PALETTE["positive"]}},
        totals={"marker": {"color": _PALETTE["accent"]}},
        text=[f"{v:.1f}%" for v in [base_irr, multiple_delta, growth_delta, rate_delta, shock_irr]],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"IRR Bridge — Base to {shock_scenario.label}",
        yaxis_title="IRR (%)",
        template="plotly_white",
        height=420,
        showlegend=False,
    )
    return fig


# ── Sensitivity curves ────────────────────────────────────────────────────────

def plot_sensitivity_curves(
    financials: DealFinancials,
    fields: list[str] | None = None,
) -> go.Figure:
    """
    Line chart showing IRR as a function of each parameter (spider-style).
    """
    if fields is None:
        fields = ["revenue_growth_rate", "ev_revenue_multiple", "discount_rate"]

    field_labels = {
        "revenue_growth_rate": "Revenue Growth Rate",
        "ev_revenue_multiple": "Exit Multiple",
        "discount_rate": "Discount Rate (WACC)",
        "holding_period_years": "Holding Period",
    }

    fig = go.Figure()
    colors = [_PALETTE["base"], _PALETTE["positive"], _PALETTE["negative"], _PALETTE["accent"]]

    for field, color in zip(fields, colors):
        curve = run_sensitivity_curve(financials, field, n_points=25, delta_range=0.40)
        x_vals = [pt[0] for pt in curve]
        y_vals = [(pt[1] or 0) * 100 for pt in curve]
        label = field_labels.get(field, field)

        # Normalise x-axis to % change from base for comparability
        base_val = float(getattr(financials, field))
        x_pct = [(v - base_val) / base_val * 100 for v in x_vals]

        fig.add_trace(go.Scatter(
            x=x_pct, y=y_vals,
            mode="lines",
            name=label,
            line=dict(color=color, width=2),
            hovertemplate=f"{label}: %{{x:.1f}}% → IRR %{{y:.1f}}%<extra></extra>",
        ))

    fig.add_vline(x=0, line_dash="dot", line_color=_PALETTE["neutral"], annotation_text="Base")
    fig.update_layout(
        title="IRR Sensitivity Curves",
        xaxis_title="Parameter Change vs Base (%)",
        yaxis_title="IRR (%)",
        template="plotly_white",
        height=420,
        legend=dict(orientation="h", y=-0.20),
    )
    return fig
