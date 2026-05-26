import streamlit as st


def render(inputs: dict) -> None:
    """Shock Simulation tab — UI skeleton only, no service calls."""
    st.header("Shock Simulation")
    st.caption(
        "Stress-test the investment thesis against macro and sector shocks "
        "before the committee finalises its vote."
    )

    if not inputs.get("run"):
        _render_empty_state()
        return

    _render_simulation_skeleton(inputs)


def _render_empty_state() -> None:
    st.info(
        "Define a shock scenario in the sidebar and click **Run IC Simulation**.",
        icon="⚡",
    )

    with st.expander("How does Shock Simulation work?", expanded=False):
        st.markdown(
            """
            1. You describe a macro or sector shock in the sidebar.
            2. The **Shock Simulator** applies the shock parameters to the base-case financial model.
            3. Each IC agent re-evaluates their position under the shock scenario.
            4. Revised votes and an updated memo section are produced.

            **Example shocks:**
            - *Interest rates rise 200bps* → discount rate impact on valuation
            - *Key competitor raises $500M* → market share and pricing pressure
            - *Regulatory ban in EU* → addressable market reduction
            """
        )


def _render_simulation_skeleton(inputs: dict) -> None:
    shock = inputs.get("shock_input") or "No shock defined"
    company = inputs["company_name"]

    st.markdown(f"**Active shock:** `{shock}`")
    st.divider()

    # ── Scenario comparison ───────────────────────────────────────────────────
    st.subheader("Scenario Comparison")
    col_base, col_shock = st.columns(2)

    with col_base:
        with st.container(border=True):
            st.markdown("#### Base Case")
            st.metric("IRR", "—")
            st.metric("MOIC", "—")
            st.metric("EV / Revenue", "—")
            st.caption("*Placeholder — base-case financials*")

    with col_shock:
        with st.container(border=True):
            st.markdown("#### Shock Case")
            st.metric("IRR", "—", delta="—")
            st.metric("MOIC", "—", delta="—")
            st.metric("EV / Revenue", "—", delta="—")
            st.caption("*Placeholder — shock-adjusted financials*")

    # ── Waterfall chart placeholder ───────────────────────────────────────────
    st.subheader("IRR Bridge — Base vs Shock")
    st.markdown(
        "*Placeholder — Plotly waterfall chart will render here "
        "once the Shock Simulator service is connected.*"
    )
    st.bar_chart({"Base": [0], "Shock": [0]})  # empty chart to show layout

    # ── Agent re-votes under shock ────────────────────────────────────────────
    st.subheader(f"Agent Re-Votes Under Shock — {company}")
    with st.container(border=True):
        cols = st.columns(5)
        agents = ["Lead Partner", "Financial Analyst", "Legal", "Risk Officer", "Portfolio Mgr"]
        for col, agent in zip(cols, agents):
            col.metric(agent, "—", delta="—")
        st.caption("*Placeholder — revised votes from Shock Simulator will appear here.*")

    # ── Shock narrative ───────────────────────────────────────────────────────
    st.subheader("Shock Impact Narrative")
    with st.container(border=True):
        st.markdown("*Placeholder — Risk Officer shock narrative will appear here.*")
