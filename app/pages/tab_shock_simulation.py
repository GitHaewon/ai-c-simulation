import streamlit as st


def render(inputs: dict, result=None) -> None:
    st.header("Shock Simulation")
    st.caption("Stress-test the investment thesis against macro and sector shocks.")

    if result is None:
        _empty_state()
        return

    sim = result.simulation
    base = sim.base_case

    st.markdown(f"**Active shock:** `{result.deal.shock_scenario or 'No shock defined'}`")
    st.divider()

    # ── Scenario comparison ───────────────────────────────────────────────────
    st.subheader("Scenario Comparison — IRR")
    from src.services.visualization import plot_scenario_comparison, plot_tornado_chart, plot_irr_waterfall
    fig_irr = plot_scenario_comparison(base, sim.shocked_scenarios, metric="irr")
    st.plotly_chart(fig_irr, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("MOIC Comparison")
        fig_moic = plot_scenario_comparison(base, sim.shocked_scenarios, metric="moic")
        st.plotly_chart(fig_moic, use_container_width=True)

    with col2:
        st.subheader("IRR Sensitivity Tornado")
        fig_tornado = plot_tornado_chart(sim.tornado_bars, base.irr)
        st.plotly_chart(fig_tornado, use_container_width=True)

    # ── Waterfall for worst shock ─────────────────────────────────────────────
    if sim.shocked_scenarios:
        worst = min(sim.shocked_scenarios, key=lambda s: s.irr or 0)
        st.subheader(f"IRR Bridge — Base → {worst.label}")
        fig_wf = plot_irr_waterfall(base, worst)
        st.plotly_chart(fig_wf, use_container_width=True)

    # ── Scenario table ────────────────────────────────────────────────────────
    st.subheader("Full Scenario Table")
    rows = [
        {
            "Scenario": s.label,
            "IRR": f"{(s.irr or 0)*100:.1f}%",
            "MOIC": f"{s.moic:.2f}x",
            "Exit Value ($M)": f"{s.exit_value_usd_m:.1f}",
            "Exit Multiple": f"{s.exit_multiple:.1f}x",
            "ΔIRR vs Base": f"{((s.irr or 0)-(base.irr or 0))*100:+.1f}pp",
        }
        for s in sim.shocked_scenarios
    ]
    st.dataframe(rows, use_container_width=True)


def _empty_state() -> None:
    st.info("Define a shock scenario in the sidebar and click **Run IC Simulation**.", icon="⚡")
    with st.expander("How does Shock Simulation work?"):
        st.markdown("""
        1. You describe a shock scenario in the sidebar.
        2. The **Shock Simulator** applies the shock to the base-case financial model.
        3. IRR / MOIC are recalculated deterministically — no LLM involved.
        4. A tornado chart shows which parameters drive the most IRR variance.

        **Supported shocks:** interest rate rise · FX change · market downturn
        """)
