import streamlit as st

_AGENTS = [
    ("data_collection_output", "Data Collection",   "🔍", None),
    ("financial_output",       "Financial Analyst",  "📊", "financial_analysis"),
    ("risk_output",            "Risk Officer",       "🛡️", "risk"),
    ("bull_output",            "Bull Advocate",      "🟢", "bull"),
    ("bear_output",            "Bear Advocate",      "🔴", "bear"),
    ("chairman_output",        "Chairman",           "👔", "chairman"),
]

_VOTE_BADGE = {
    "APPROVE":     "🟢 APPROVE",
    "CONDITIONAL": "🟡 CONDITIONAL",
    "REJECT":      "🔴 REJECT",
}


def render(inputs: dict, result=None) -> None:
    st.header("AI Investment Committee Debate")
    st.caption("Live deliberation between IC member agents.")

    if result is None:
        _empty_state()
        return

    state = result.state
    company = result.deal.company_name

    # ── Agent status row ──────────────────────────────────────────────────────
    st.subheader("Committee Status")
    cols = st.columns(len(_AGENTS))
    for col, (key, label, icon, _) in zip(cols, _AGENTS):
        output = state.get(key)
        with col:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                st.markdown(f"**{label}**")
                if output is None:
                    st.caption("—")
                elif hasattr(output, "vote"):
                    st.caption(_VOTE_BADGE.get(output.vote.value, output.vote.value))
                else:
                    st.caption("✓ Done")

    st.divider()

    # ── Transcript ────────────────────────────────────────────────────────────
    st.subheader(f"Deliberation Transcript — {company}")

    # Data Collection
    dc = state.get("data_collection_output")
    if dc:
        with st.chat_message(name="Data Collection", avatar="🔍"):
            st.markdown("**Key Facts Collected:**")
            for fact in dc.key_facts:
                st.markdown(f"- {fact}")
            if dc.data_sources:
                st.caption("Sources: " + " | ".join(dc.data_sources))

    # Parallel agents
    for key, label, icon, _ in _AGENTS[1:-1]:
        output = state.get(key)
        if output is None:
            continue
        with st.chat_message(name=label, avatar=icon):
            vote_badge = _VOTE_BADGE.get(output.vote.value, output.vote.value)
            st.markdown(f"**Vote: {vote_badge}**  (confidence: {output.confidence:.0%})")
            if output.findings:
                st.markdown("**Findings:**")
                for f in output.findings:
                    st.markdown(f"- {f}")
            if output.concerns:
                st.markdown("**Concerns:**")
                for c in output.concerns:
                    st.markdown(f"- ⚠ {c}")
            if output.vote_rationale:
                st.markdown(f"*{output.vote_rationale}*")

    # Chairman
    chair = state.get("chairman_output")
    if chair:
        with st.chat_message(name="Chairman", avatar="👔"):
            decision_badge = _VOTE_BADGE.get(chair.final_decision.value, chair.final_decision.value)
            st.markdown(f"### Final Decision: {decision_badge}")
            if chair.resolution_rationale:
                st.markdown(chair.resolution_rationale)
            if chair.conditions:
                st.markdown("**Conditions:**")
                for cond in chair.conditions:
                    st.markdown(f"- {cond}")

    st.divider()

    # ── Vote summary table ────────────────────────────────────────────────────
    st.subheader("Vote Summary")
    if chair and chair.vote_tally:
        rows = [
            {"Agent": agent.replace("_", " ").title(), "Vote": vote}
            for agent, vote in chair.vote_tally.items()
        ]
        st.dataframe(rows, use_container_width=True)

        col1, col2 = st.columns(2)
        col1.metric("Final Decision", chair.final_decision.value)
        col2.metric("Quorum", "Met ✓" if chair.quorum_met else "Not Met ✗")


def _empty_state() -> None:
    st.info("Enter deal details in the sidebar and click **Run IC Simulation**.", icon="🎙️")
    st.subheader("Committee Members")
    cols = st.columns(len(_AGENTS))
    for col, (_, label, icon, _) in zip(cols, _AGENTS):
        with col:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                st.markdown(f"**{label}**")
                st.caption("Waiting …")
