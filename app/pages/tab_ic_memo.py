from pathlib import Path
import streamlit as st


def render(inputs: dict, result=None) -> None:
    st.header("IC Memo Draft")
    st.caption("Auto-generated Investment Committee memo from agent deliberation.")

    if result is None:
        _empty_state()
        return

    memo = result.memo
    h = memo.header

    st.success(f"IC Memo generated for **{h.company_name}** ({h.industry})")
    st.divider()

    # ── 1. Executive Summary ──────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("1. Investment Overview")
        for fact in memo.overview.key_facts:
            st.markdown(f"- {fact}")
        if memo.overview.data_sources:
            st.caption("Sources: " + " | ".join(memo.overview.data_sources))

    # ── 2. Financial Analysis ─────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("2. Financial Analysis")
        f = memo.financials
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Base IRR", f"{f.base_irr_pct:.1f}%" if f.base_irr_pct else "—")
        c2.metric("Base MOIC", f"{f.base_moic:.2f}x")
        c3.metric("Exit Value", f"${f.exit_value_usd_m:.1f}M")
        c4.metric("Exit Multiple", f"{f.exit_multiple:.1f}x Rev")
        for item in f.findings:
            st.markdown(f"▸ {item}")
        for item in f.concerns:
            st.markdown(f"⚠ {item}")

    # ── 3. Investment Thesis ──────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("3. Investment Thesis")
        col_bull, col_bear = st.columns(2)
        with col_bull:
            st.markdown("**🟢 Bull Case**")
            for p in memo.thesis.bull_points:
                st.markdown(f"- {p}")
        with col_bear:
            st.markdown("**🔴 Bear Case**")
            for p in memo.thesis.bear_points:
                st.markdown(f"- {p}")

    # ── 4. Key Risks ──────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("4. Key Risks")
        _SEV = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
        for risk in memo.risks.risks:
            st.markdown(f"{_SEV.get(risk.severity,'⚪')} **{risk.severity}** — {risk.description}")

    # ── 5. Shock Summary ──────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("5. Shock Simulation Summary")
        s = memo.shock_summary
        if s.top_driver:
            st.info(f"Top IRR driver: **{s.top_driver}** (±{s.top_driver_swing_pp:.1f}pp swing)")
        rows = [
            {"Scenario": r.label,
             "IRR": f"{r.irr_pct:.1f}%" if r.irr_pct is not None else "—",
             "MOIC": f"{r.moic:.2f}x",
             "ΔIRR": f"{r.delta_irr_pp:+.1f}pp" if r.delta_irr_pp is not None else "—"}
            for r in s.scenarios
        ]
        if rows:
            st.dataframe(rows, use_container_width=True)

    # ── 6. Final Recommendation ───────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("6. Final Recommendation")
        r = memo.recommendation
        _BADGE = {
            "APPROVE": "🟢 **APPROVE**",
            "CONDITIONAL": "🟡 **CONDITIONAL APPROVAL**",
            "REJECT": "🔴 **REJECT**",
        }
        st.markdown(f"### {_BADGE.get(r.decision.value, r.decision.value)}")
        if r.vote_tally:
            vote_cols = st.columns(len(r.vote_tally))
            for col, (agent, vote) in zip(vote_cols, r.vote_tally.items()):
                col.metric(agent.replace("_", " ").title(), vote)
        if r.conditions:
            st.markdown("**Conditions:**")
            for c in r.conditions:
                st.markdown(f"- {c}")
        if r.rationale:
            st.markdown("**Rationale:**")
            st.markdown(r.rationale)

    st.divider()
    _export_buttons(result)


def _export_buttons(result) -> None:
    from src.services.memo_exporter import export_json, export_markdown, export_pptx

    col1, col2, col3 = st.columns(3)

    with col1:
        md = export_markdown(result.memo)
        st.download_button("⬇ Download Markdown", md, "ic_memo.md", "text/markdown")

    with col2:
        json_str = export_json(result.memo)
        st.download_button("⬇ Download JSON", json_str, "ic_memo.json", "application/json")

    with col3:
        import io
        from pathlib import Path
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
            pptx_path = Path(tmp.name)
        export_pptx(result.memo, pptx_path)
        pptx_bytes = pptx_path.read_bytes()
        pptx_path.unlink(missing_ok=True)
        st.download_button("⬇ Download PPTX", pptx_bytes, "ic_memo.pptx",
                           "application/vnd.openxmlformats-officedocument.presentationml.presentation")


def _empty_state() -> None:
    st.info("Fill in the deal information in the sidebar and click **Run IC Simulation**.", icon="📋")
    with st.expander("What will this memo include?"):
        st.markdown("""
        - **Investment Overview** — key facts from data collection
        - **Financial Analysis** — IRR, MOIC, valuation metrics
        - **Investment Thesis** — bull and bear cases side-by-side
        - **Key Risks** — severity-tagged risk table
        - **Shock Summary** — scenario comparison table
        - **Final Recommendation** — committee vote + conditions + rationale
        """)
