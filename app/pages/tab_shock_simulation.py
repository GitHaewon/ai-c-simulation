import streamlit as st


def render(inputs: dict, result=None) -> None:
    st.header("충격 시나리오 분석")
    st.caption("거시경제 및 섹터 충격에 대한 투자 논거 스트레스 테스트 결과입니다.")

    if result is None:
        _empty_state()
        return

    sim = result.simulation
    base = sim.base_case

    shock_text = result.deal.shock_scenario or "충격 시나리오 미설정"
    st.markdown(f"**적용 충격 시나리오:** `{shock_text}`")
    st.divider()

    from src.services.visualization import (
        plot_scenario_comparison,
        plot_tornado_chart,
        plot_irr_waterfall,
    )

    # ── IRR 시나리오 비교 ──────────────────────────────────────────────────────
    st.subheader("시나리오 비교 — IRR")
    fig_irr = plot_scenario_comparison(base, sim.shocked_scenarios, metric="irr")
    st.plotly_chart(fig_irr, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("MOIC 비교")
        fig_moic = plot_scenario_comparison(base, sim.shocked_scenarios, metric="moic")
        st.plotly_chart(fig_moic, use_container_width=True)

    with col2:
        st.subheader("IRR 민감도 분석 (토네이도 차트)")
        fig_tornado = plot_tornado_chart(sim.tornado_bars, base.irr)
        st.plotly_chart(fig_tornado, use_container_width=True)

    # ── 최악 시나리오 IRR 브리지 ───────────────────────────────────────────────
    if sim.shocked_scenarios:
        worst = min(sim.shocked_scenarios, key=lambda s: s.irr or 0)
        st.subheader(f"IRR 브리지 — 기본 → {worst.label}")
        fig_wf = plot_irr_waterfall(base, worst)
        st.plotly_chart(fig_wf, use_container_width=True)

    # ── 전체 시나리오 비교표 ───────────────────────────────────────────────────
    st.subheader("전체 시나리오 비교표")
    rows = [
        {
            "시나리오":              s.label,
            "IRR":                   f"{(s.irr or 0)*100:.1f}%",
            "MOIC":                  f"{s.moic:.2f}x",
            "엑싯 가치 ($M)":        f"{s.exit_value_usd_m:.1f}",
            "엑싯 배수":             f"{s.exit_multiple:.1f}x",
            "기본 대비 IRR 변화":    f"{((s.irr or 0)-(base.irr or 0))*100:+.1f}pp",
        }
        for s in sim.shocked_scenarios
    ]
    st.dataframe(rows, use_container_width=True)


def _empty_state() -> None:
    st.info(
        "사이드바에 충격 시나리오를 입력하고 **🚀 투자위원회 분석 시작** 버튼을 클릭하세요.",
        icon="⚡",
    )
    with st.expander("충격 시나리오 분석 방식"):
        st.markdown("""
        1. 사이드바에 충격 시나리오를 자유 형식으로 입력합니다.
        2. **충격 시뮬레이터**가 기본 재무 모델에 충격을 적용합니다.
        3. IRR / MOIC를 결정론적(deterministic)으로 재계산합니다 — LLM 개입 없음.
        4. 토네이도 차트로 IRR 변동에 가장 큰 영향을 미치는 변수를 확인합니다.

        **지원 충격 유형:** 금리 상승 · 환율 변동 · 시장 하락
        """)
