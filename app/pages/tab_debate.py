import streamlit as st

_AGENTS = [
    ("data_collection_output", "데이터 수집",      "🔍", None),
    ("financial_output",       "재무 분석관",       "📊", "financial_analysis"),
    ("risk_output",            "리스크 심사역",     "🛡️", "risk"),
    ("bull_output",            "강세론 위원",       "🟢", "bull"),
    ("bear_output",            "약세론 위원",       "🔴", "bear"),
    ("chairman_output",        "투자위원장",        "👔", "chairman"),
]

_VOTE_BADGE = {
    "APPROVE":     "🟢 승인",
    "CONDITIONAL": "🟡 조건부 승인",
    "REJECT":      "🔴 반려",
}

_DECISION_BADGE = {
    "APPROVE":     "🟢 **승인 (APPROVE)**",
    "CONDITIONAL": "🟡 **조건부 승인 (CONDITIONAL)**",
    "REJECT":      "🔴 **반려 (REJECT)**",
}


def render(inputs: dict, result=None) -> None:
    st.header("AI 투자위원회 토론")
    st.caption("투자위원회 위원 에이전트 간 실시간 심의 현황입니다.")

    if result is None:
        _empty_state()
        return

    state = result.state
    company = result.deal.company_name

    # ── 위원회 현황 ───────────────────────────────────────────────────────────
    st.subheader("위원회 현황")
    cols = st.columns(len(_AGENTS))
    for col, (key, label, icon, _) in zip(cols, _AGENTS):
        output = state.get(key)
        with col:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                st.markdown(f"**{label}**")
                if output is None:
                    st.caption("대기 중")
                elif hasattr(output, "vote"):
                    st.caption(_VOTE_BADGE.get(output.vote.value, output.vote.value))
                else:
                    st.caption("✓ 완료")

    st.divider()

    # ── 심의 기록 ─────────────────────────────────────────────────────────────
    st.subheader(f"심의 기록 — {company}")

    # 데이터 수집
    dc = state.get("data_collection_output")
    if dc:
        with st.chat_message(name="데이터 수집", avatar="🔍"):
            st.markdown("**수집 핵심 사실:**")
            for fact in dc.key_facts:
                st.markdown(f"- {fact}")
            if dc.data_sources:
                st.caption("출처: " + " | ".join(dc.data_sources))

    # 분석 위원 (재무/리스크/강세/약세)
    for key, label, icon, _ in _AGENTS[1:-1]:
        output = state.get(key)
        if output is None:
            continue
        with st.chat_message(name=label, avatar=icon):
            vote_badge = _VOTE_BADGE.get(output.vote.value, output.vote.value)
            st.markdown(f"**투표: {vote_badge}**  (확신도: {output.confidence:.0%})")
            if output.findings:
                st.markdown("**핵심 발견:**")
                for f in output.findings:
                    st.markdown(f"- {f}")
            if output.concerns:
                st.markdown("**우려 사항:**")
                for c in output.concerns:
                    st.markdown(f"- ⚠ {c}")
            if output.vote_rationale:
                st.markdown(f"*{output.vote_rationale}*")

    # 투자위원장
    chair = state.get("chairman_output")
    if chair:
        with st.chat_message(name="투자위원장", avatar="👔"):
            st.markdown(f"### 최종 의사결정: {_DECISION_BADGE.get(chair.final_decision.value, chair.final_decision.value)}")
            if chair.resolution_rationale:
                st.markdown(chair.resolution_rationale)
            if chair.conditions:
                st.markdown("**승인 조건:**")
                for cond in chair.conditions:
                    st.markdown(f"- {cond}")

    st.divider()

    # ── 투표 집계표 ───────────────────────────────────────────────────────────
    st.subheader("투표 집계표")
    if chair and chair.vote_tally:
        _agent_name_map = {
            "financial_analysis": "재무 분석관",
            "risk":               "리스크 심사역",
            "bull":               "강세론 위원",
            "bear":               "약세론 위원",
        }
        rows = [
            {
                "위원":   _agent_name_map.get(agent, agent),
                "투표 결과": _VOTE_BADGE.get(vote, vote),
            }
            for agent, vote in chair.vote_tally.items()
        ]
        st.dataframe(rows, use_container_width=True)

        col1, col2 = st.columns(2)
        col1.metric(
            "최종 결정",
            _VOTE_BADGE.get(chair.final_decision.value, chair.final_decision.value),
        )
        col2.metric("정족수", "충족 ✓" if chair.quorum_met else "미충족 ✗")


def _empty_state() -> None:
    st.info(
        "사이드바에 딜 정보를 입력하고 **🚀 투자위원회 분석 시작** 버튼을 클릭하세요.",
        icon="🎙️",
    )
    st.subheader("투자위원회 구성원")
    cols = st.columns(len(_AGENTS))
    for col, (_, label, icon, _) in zip(cols, _AGENTS):
        with col:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                st.markdown(f"**{label}**")
                st.caption("대기 중 …")
