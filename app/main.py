import logging

import streamlit as st

from app.components.sidebar import render_sidebar
from app.pages.tab_debate import render as render_debate
from app.pages.tab_ic_memo import render as render_ic_memo
from app.pages.tab_shock_simulation import render as render_shock

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AI IC Simulation",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("💼 AI Investment Committee Simulation")
st.markdown(
    "Simulate a full IC process — multi-agent debate, shock stress-testing, "
    "and automatic IC memo generation."
)
st.divider()

inputs = render_sidebar()

# ── Run pipeline ──────────────────────────────────────────────────────────────

if inputs["run"]:
    from src.core.pipeline import ICPipeline
    from src.models.deal import DealInput

    deal = DealInput(
        company_name=inputs["company_name"],
        industry=inputs["industry"],
        deal_stage=inputs.get("deal_stage", ""),
        investment_amount_usd_m=float(inputs.get("investment_amount", 0) or 0),
        shock_scenario=inputs.get("shock_input", ""),
    )

    log_lines: list[str] = []

    with st.status("Running IC Simulation …", expanded=True) as status:
        def _cb(msg: str) -> None:
            log_lines.append(msg)
            status.write(msg)

        try:
            pipeline = ICPipeline.build()
            result = pipeline.run(deal, progress_cb=_cb)
            st.session_state["pipeline_result"] = result
            status.update(label="IC Simulation complete ✓", state="complete")
        except Exception as exc:
            logger.error("Pipeline failed: %s", exc)
            st.session_state.pop("pipeline_result", None)
            status.update(label=f"Pipeline failed: {exc}", state="error")
            st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────

result = st.session_state.get("pipeline_result")

tab_memo, tab_shock, tab_debate = st.tabs(
    ["📋 IC Memo Draft", "⚡ Shock Simulation", "🎙️ AI IC Debate"]
)
with tab_memo:
    render_ic_memo(inputs, result)
with tab_shock:
    render_shock(inputs, result)
with tab_debate:
    render_debate(inputs, result)
