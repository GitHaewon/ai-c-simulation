import streamlit as st


def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown(
            "<div style='text-align:center;font-size:2rem;'>💼</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<h2 style='text-align:center;letter-spacing:-0.5px;'>IC 시뮬레이터</h2>",
            unsafe_allow_html=True,
        )
        st.caption("AI 투자위원회 분석 시스템")
        st.divider()

        st.subheader("딜 기본 정보")

        company_name = st.text_input(
            "기업명",
            placeholder="예) 삼성전자, OpenAI, 카카오",
            help="투자 검토 대상 기업명을 입력하세요.",
        )

        industry = st.selectbox(
            "산업 분야",
            options=[
                "",
                "AI / 머신러닝",
                "핀테크 (FinTech)",
                "헬스테크 (HealthTech)",
                "SaaS / B2B 소프트웨어",
                "소비자 테크",
                "딥테크 / 반도체",
                "클라이밋테크 (기후기술)",
                "이커머스",
                "AI 반도체",
                "기타",
            ],
            help="딜의 주요 산업 섹터를 선택하세요.",
        )

        deal_stage = st.selectbox(
            "투자 단계",
            options=["", "시드 (Seed)", "시리즈 A", "시리즈 B", "시리즈 C+", "성장 투자 (Growth)", "Pre-IPO"],
        )

        investment_amount = st.number_input(
            "투자금액 (USD 백만)",
            min_value=0.0,
            step=0.5,
            format="%.1f",
            help="제안 투자금액 (단위: 백만 달러)",
        )

        st.divider()
        st.subheader("거시경제 충격 시나리오")

        shock_input = st.text_area(
            "충격 시나리오 입력",
            placeholder=(
                "예) 금리 200bp 상승,\n"
                "핵심 경쟁사 $500M 조달,\n"
                "EU 시장 규제 강화"
            ),
            height=100,
            help="투자 논거를 스트레스 테스트할 거시경제 또는 섹터 충격을 입력하세요.",
        )

        st.divider()

        run_button = st.button(
            "🚀 투자위원회 분석 시작",
            type="primary",
            use_container_width=True,
            disabled=not (company_name and industry),
        )

        if not company_name or not industry:
            st.caption("기업명과 산업 분야를 입력하면 분석이 활성화됩니다.")

    return {
        "company_name": company_name,
        "industry": industry,
        "deal_stage": deal_stage,
        "investment_amount": investment_amount,
        "shock_input": shock_input,
        "run": run_button,
    }
