import streamlit as st

_AGENT_META: list[dict] = [
    {"id": "lead_partner",      "label": "Lead Partner",      "icon": "👔", "color": "#1f77b4"},
    {"id": "financial_analyst", "label": "Financial Analyst", "icon": "📊", "color": "#2ca02c"},
    {"id": "legal_compliance",  "label": "Legal & Compliance","icon": "⚖️", "color": "#9467bd"},
    {"id": "risk_officer",      "label": "Risk Officer",      "icon": "🛡️", "color": "#d62728"},
    {"id": "portfolio_manager", "label": "Portfolio Manager", "icon": "📁", "color": "#ff7f0e"},
]


def render(inputs: dict) -> None:
    """AI Investment Committee Debate tab — UI skeleton only, no agent calls."""
    st.header("AI Investment Committee Debate")
    st.caption(
        "Live deliberation between IC member agents. "
        "Each agent reviews the deal from its own perspective before voting."
    )

    if not inputs.get("run"):
        _render_empty_state()
        return

    _render_debate_skeleton(inputs)


def _render_empty_state() -> None:
    st.info(
        "Enter deal details in the sidebar and click **Run IC Simulation** to start the debate.",
        icon="🎙️",
    )

    st.subheader("Committee Members")
    cols = st.columns(len(_AGENT_META))
    for col, agent in zip(cols, _AGENT_META):
        with col:
            with st.container(border=True):
                st.markdown(f"### {agent['icon']}")
                st.markdown(f"**{agent['label']}**")
                st.caption("Waiting …")


def _render_debate_skeleton(inputs: dict) -> None:
    company = inputs["company_name"]
    industry = inputs["industry"]

    # ── Agent status cards ────────────────────────────────────────────────────
    st.subheader("Committee Status")
    cols = st.columns(len(_AGENT_META))
    for col, agent in zip(cols, _AGENT_META):
        with col:
            with st.container(border=True):
                st.markdown(f"### {agent['icon']}")
                st.markdown(f"**{agent['label']}**")
                st.caption("Analysing …")
                st.progress(0, text="Pending")

    st.divider()

    # ── Debate transcript ─────────────────────────────────────────────────────
    st.subheader(f"Deliberation Transcript — {company} ({industry})")

    for agent in _AGENT_META:
        with st.chat_message(name=agent["label"], avatar=agent["icon"]):
            st.markdown(
                f"*Placeholder — {agent['label']} deliberation output will stream here.*"
            )

    st.divider()

    # ── Vote summary ──────────────────────────────────────────────────────────
    st.subheader("Vote Summary")
    with st.container(border=True):
        vote_cols = st.columns([2, 1, 1, 1])
        vote_cols[0].markdown("**Agent**")
        vote_cols[1].markdown("**Vote**")
        vote_cols[2].markdown("**Confidence**")
        vote_cols[3].markdown("**Key Concern**")

        for agent in _AGENT_META:
            c0, c1, c2, c3 = st.columns([2, 1, 1, 1])
            c0.markdown(f"{agent['icon']} {agent['label']}")
            c1.markdown("`—`")
            c2.markdown("—")
            c3.markdown("*pending*")

    st.divider()

    # ── Final resolution ──────────────────────────────────────────────────────
    st.subheader("Final Resolution")
    with st.container(border=True):
        res_col1, res_col2 = st.columns([1, 2])
        with res_col1:
            st.metric("Committee Decision", "PENDING")
            st.metric("Votes to Approve", "— / 5")
        with res_col2:
            st.markdown("**Resolution Rationale**")
            st.markdown("*Placeholder — voting engine resolution will appear here.*")
