"""
Entry point: streamlit run app.py
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv()

import logging
import streamlit as st

from app.components.sidebar import render_sidebar
from app.pages.tab_debate import render as render_debate
from app.pages.tab_ic_memo import render as render_ic_memo
from app.pages.tab_shock_simulation import render as render_shock

st.set_page_config(
    page_title="AI 투자위원회 시뮬레이터",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 상단 헤더 ─────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='letter-spacing:-0.5px;'>💼 AI 투자위원회 시뮬레이션 시스템</h1>",
    unsafe_allow_html=True,
)
st.caption(
    "멀티 에이전트 AI가 실제 투자위원회 심의 프로세스를 시뮬레이션하고, "
    "투자 검토 보고서(IC Memo)를 자동으로 생성합니다."
)
st.divider()

inputs = render_sidebar()

# ── 파이프라인 실행 ────────────────────────────────────────────────────────────
if inputs["run"]:
    from src.core.pipeline import ICPipeline
    from src.models.deal import DealInput

    deal = DealInput(
        company_name=inputs["company_name"],
        industry=inputs["industry"],
        deal_stage=inputs.get("deal_stage", ""),
        investment_amount_usd_m=float(inputs.get("investment_amount") or 0),
        shock_scenario=inputs.get("shock_input", ""),
    )

    with st.status("투자위원회 시뮬레이션 실행 중 …", expanded=True) as status:
        try:
            pipeline = ICPipeline.build()
            result = pipeline.run(
                deal,
                progress_cb=lambda m: status.write(m),
            )
            st.session_state["pipeline_result"] = result
            status.update(label="✅ 시뮬레이션 완료", state="complete")
        except Exception as exc:
            logging.getLogger(__name__).error("Pipeline failed: %s", exc, exc_info=True)
            st.session_state.pop("pipeline_result", None)
            status.update(label=f"❌ 오류 발생: {exc}", state="error")
            st.stop()

# ── 탭 레이아웃 ───────────────────────────────────────────────────────────────
result = st.session_state.get("pipeline_result")

tab_memo, tab_shock, tab_debate = st.tabs([
    "📋 투자 검토 보고서",
    "⚡ 충격 시나리오 분석",
    "🎙️ AI 투자위원회 토론",
])
with tab_memo:
    render_ic_memo(inputs, result)
with tab_shock:
    render_shock(inputs, result)
with tab_debate:
    render_debate(inputs, result)
