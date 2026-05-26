import tempfile
from pathlib import Path

import streamlit as st

_SEVERITY_BADGE = {
    "High":   ("🔴", "고위험"),
    "Medium": ("🟡", "중위험"),
    "Low":    ("🟢", "저위험"),
}

_DECISION_BADGE = {
    "APPROVE":     "🟢 **승인 (APPROVE)**",
    "CONDITIONAL": "🟡 **조건부 승인 (CONDITIONAL)**",
    "REJECT":      "🔴 **반려 (REJECT)**",
}


def render(inputs: dict, result=None) -> None:
    st.header("투자 검토 보고서")
    st.caption("AI 투자위원회 심의 결과를 기반으로 자동 생성된 투자 검토 보고서입니다.")

    if result is None:
        _empty_state()
        return

    memo = result.memo
    h = memo.header

    st.success(f"**{h.company_name}** ({h.industry}) 투자 검토 보고서 생성 완료")
    st.divider()

    # ── 1. 투자 개요 ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("1. 투자 개요")
        for fact in memo.overview.key_facts:
            st.markdown(f"- {fact}")
        if memo.overview.data_sources:
            st.caption("참고 자료: " + " | ".join(memo.overview.data_sources))

    # ── 2. 재무 분석 ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("2. 재무 분석")
        f = memo.financials
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("기준 IRR",   f"{f.base_irr_pct:.1f}%" if f.base_irr_pct is not None else "—")
        c2.metric("기준 MOIC",  f"{f.base_moic:.2f}x")
        c3.metric("엑싯 가치",  f"${f.exit_value_usd_m:.1f}M")
        c4.metric("엑싯 배수",  f"{f.exit_multiple:.1f}x Rev")
        if f.findings:
            st.markdown("**주요 발견:**")
            for item in f.findings:
                st.markdown(f"▸ {item}")
        if f.concerns:
            st.markdown("**우려 사항:**")
            for item in f.concerns:
                st.markdown(f"⚠ {item}")

    # ── 3. 투자 논거 ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("3. 투자 논거")
        if memo.thesis.lead_thesis:
            st.info(memo.thesis.lead_thesis)
        col_bull, col_bear = st.columns(2)
        with col_bull:
            st.markdown("**🟢 매력 요인 (Bull Case)**")
            for p in memo.thesis.bull_points:
                st.markdown(f"- {p}")
        with col_bear:
            st.markdown("**🔴 우려 사항 (Bear Case)**")
            for p in memo.thesis.bear_points:
                st.markdown(f"- {p}")

    # ── 4. 주요 리스크 ────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("4. 주요 리스크")
        for risk in memo.risks.risks:
            emoji, label = _SEVERITY_BADGE.get(risk.severity, ("⚪", risk.severity))
            st.markdown(f"{emoji} **{label}** — {risk.description}")

    # ── 5. 충격 시나리오 요약 ─────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("5. 충격 시나리오 요약")
        s = memo.shock_summary
        if s.top_driver:
            st.info(f"최대 IRR 영향 변수: **{s.top_driver}** (±{s.top_driver_swing_pp:.1f}pp 변동)")
        rows = [
            {
                "시나리오":         r.label,
                "IRR":              f"{r.irr_pct:.1f}%" if r.irr_pct is not None else "—",
                "MOIC":             f"{r.moic:.2f}x",
                "기본 대비 IRR 변화": f"{r.delta_irr_pp:+.1f}pp" if r.delta_irr_pp is not None else "—",
            }
            for r in s.scenarios
        ]
        if rows:
            st.dataframe(rows, use_container_width=True)

    # ── 6. 최종 투자 의사결정 ─────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("6. 최종 투자 의사결정")
        r = memo.recommendation
        st.markdown(f"### {_DECISION_BADGE.get(r.decision.value, r.decision.value)}")

        if r.vote_tally:
            st.markdown("**위원별 투표 현황**")
            vote_cols = st.columns(len(r.vote_tally))
            _vote_label = {"APPROVE": "승인", "CONDITIONAL": "조건부", "REJECT": "반려"}
            for col, (agent, vote) in zip(vote_cols, r.vote_tally.items()):
                col.metric(
                    agent.replace("_", " ").replace("financial analysis", "재무분석")
                         .replace("risk", "리스크").replace("bull", "강세론자")
                         .replace("bear", "약세론자").title(),
                    _vote_label.get(vote, vote),
                )

        if r.conditions:
            st.markdown("**승인 조건:**")
            for c in r.conditions:
                st.markdown(f"- {c}")
        if r.rationale:
            st.markdown("**검토 의견:**")
            st.markdown(r.rationale)

    st.divider()
    _export_buttons(result)


def _export_buttons(result) -> None:
    from src.services.memo_exporter import export_json, export_markdown, export_pptx

    st.markdown("**보고서 다운로드**")
    col1, col2, col3 = st.columns(3)

    with col1:
        md = export_markdown(result.memo)
        st.download_button(
            "📥 Markdown 다운로드",
            md.encode("utf-8"),
            "ic_memo.md",
            "text/markdown",
            use_container_width=True,
        )

    with col2:
        json_str = export_json(result.memo)
        st.download_button(
            "📥 JSON 다운로드",
            json_str.encode("utf-8"),
            "ic_memo.json",
            "application/json",
            use_container_width=True,
        )

    with col3:
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
            pptx_path = Path(tmp.name)
        export_pptx(result.memo, pptx_path)
        pptx_bytes = pptx_path.read_bytes()
        pptx_path.unlink(missing_ok=True)
        st.download_button(
            "📥 PPTX 다운로드",
            pptx_bytes,
            "ic_memo.pptx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            use_container_width=True,
        )


def _empty_state() -> None:
    st.info(
        "사이드바에 딜 정보를 입력하고 **🚀 투자위원회 분석 시작** 버튼을 클릭하세요.",
        icon="📋",
    )
    with st.expander("보고서에 포함되는 내용"):
        st.markdown("""
        - **투자 개요** — 데이터 수집 에이전트가 확인한 핵심 사실
        - **재무 분석** — IRR, MOIC, 밸류에이션 지표
        - **투자 논거** — 강세/약세 시나리오 비교
        - **주요 리스크** — 심각도 등급별 리스크 목록
        - **충격 시나리오 요약** — 거시경제 스트레스 테스트 결과
        - **최종 의사결정** — 위원회 투표 결과 및 조건·검토 의견
        """)
