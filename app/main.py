import streamlit as st

from app.components.sidebar import render_sidebar
from app.pages.tab_debate import render as render_debate
from app.pages.tab_ic_memo import render as render_ic_memo
from app.pages.tab_shock_simulation import render as render_shock

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI IC Simulation",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Header ────────────────────────────────────────────────────────────────────

st.title("💼 AI Investment Committee Simulation")
st.markdown(
    "Simulate a full Investment Committee process — multi-agent deliberation, "
    "shock stress-testing, and automatic IC memo generation."
)
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────

inputs = render_sidebar()

# ── Main tabs ─────────────────────────────────────────────────────────────────

tab_memo, tab_shock, tab_debate = st.tabs(
    ["📋 IC Memo Draft", "⚡ Shock Simulation", "🎙️ AI Investment Committee Debate"]
)

with tab_memo:
    render_ic_memo(inputs)

with tab_shock:
    render_shock(inputs)

with tab_debate:
    render_debate(inputs)
