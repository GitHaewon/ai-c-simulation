import streamlit as st


def render(inputs: dict) -> None:
    """IC Memo Draft tab — UI skeleton only, no agent calls."""
    st.header("IC Memo Draft")
    st.caption("Auto-generated Investment Committee memo based on agent deliberation.")

    if not inputs.get("run"):
        _render_empty_state()
        return

    _render_memo_skeleton(inputs)


def _render_empty_state() -> None:
    st.info(
        "Fill in the deal information in the sidebar and click **Run IC Simulation** to generate the memo.",
        icon="📋",
    )

    with st.expander("What will this memo include?", expanded=False):
        st.markdown(
            """
            - **Executive Summary** — one-paragraph investment recommendation
            - **Investment Thesis** — lead partner's core argument
            - **Financial Analysis** — valuation, return scenarios (IRR / MOIC)
            - **Risk Assessment** — downside scenarios and mitigants
            - **Legal & Compliance Review** — regulatory flags and deal structure
            - **Portfolio Fit** — diversification and follow-on capacity
            - **Committee Vote** — individual votes and final resolution
            """
        )


def _render_memo_skeleton(inputs: dict) -> None:
    company = inputs["company_name"]
    industry = inputs["industry"]

    st.success(f"Generating IC memo for **{company}** ({industry}) …")
    st.divider()

    # ── Executive Summary ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("1. Executive Summary")
        with st.spinner("Lead Partner analysing …"):
            st.markdown(
                f"""
                > *Placeholder — Lead Partner agent output will appear here.*
                >
                > Company: **{company}** | Industry: **{industry}**
                > | Stage: {inputs.get("deal_stage") or "N/A"}
                > | Amount: ${inputs.get("investment_amount", 0):.1f}M
                """
            )

    # ── Investment Thesis ─────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("2. Investment Thesis")
        st.markdown("*Placeholder — Lead Partner thesis output will appear here.*")

    # ── Financial Analysis ────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("3. Financial Analysis")
        col1, col2, col3 = st.columns(3)
        col1.metric("IRR (Base)", "—")
        col2.metric("MOIC (Base)", "—")
        col3.metric("Payback Period", "—")
        st.markdown("*Placeholder — Financial Analyst agent output will appear here.*")

    # ── Risk Assessment ───────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("4. Risk Assessment")
        st.markdown("*Placeholder — Risk Officer agent output will appear here.*")

    # ── Legal & Compliance ────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("5. Legal & Compliance Review")
        st.markdown("*Placeholder — Legal & Compliance agent output will appear here.*")

    # ── Portfolio Fit ─────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("6. Portfolio Fit")
        st.markdown("*Placeholder — Portfolio Manager agent output will appear here.*")

    # ── Committee Vote ────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("7. Committee Vote")
        vote_cols = st.columns(5)
        agents = ["Lead Partner", "Financial Analyst", "Legal", "Risk Officer", "Portfolio Mgr"]
        for col, agent in zip(vote_cols, agents):
            col.metric(agent, "—")
        st.markdown("*Placeholder — Voting engine output will appear here.*")

    st.divider()
    st.button("Export Memo as PPTX", icon="📥", disabled=True)
