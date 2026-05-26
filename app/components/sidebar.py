import streamlit as st


def render_sidebar() -> dict:
    """Render the sidebar and return user inputs as a plain dict."""
    with st.sidebar:
        st.image(
            "https://img.icons8.com/fluency/96/investment-portfolio.png",
            width=64,
        )
        st.title("IC Simulation")
        st.caption("AI Investment Committee")
        st.divider()

        st.subheader("Deal Information")

        company_name = st.text_input(
            "Company Name",
            placeholder="e.g. OpenAI, Stripe, Kakao",
            help="Name of the company being evaluated",
        )

        industry = st.selectbox(
            "Industry",
            options=[
                "",
                "AI / Machine Learning",
                "FinTech",
                "HealthTech",
                "SaaS / B2B Software",
                "Consumer Tech",
                "Deep Tech / Semiconductor",
                "Climate Tech",
                "E-Commerce",
                "Other",
            ],
            help="Primary industry sector of the deal",
        )

        deal_stage = st.selectbox(
            "Deal Stage",
            options=["", "Seed", "Series A", "Series B", "Series C+", "Growth", "Pre-IPO"],
        )

        investment_amount = st.number_input(
            "Investment Amount (USD M)",
            min_value=0.0,
            step=0.5,
            format="%.1f",
            help="Proposed investment amount in millions USD",
        )

        st.divider()
        st.subheader("Shock Scenario")

        shock_input = st.text_area(
            "Define Shock",
            placeholder=(
                "e.g. Interest rates rise 200bps,\n"
                "key competitor raises $500M,\n"
                "regulatory ban in EU market"
            ),
            height=100,
            help="Describe macro or sector shock to stress-test the investment thesis",
        )

        st.divider()

        run_button = st.button(
            "Run IC Simulation",
            type="primary",
            use_container_width=True,
            disabled=not (company_name and industry),
        )

        if not company_name or not industry:
            st.caption("Fill in Company Name and Industry to enable simulation.")

    return {
        "company_name": company_name,
        "industry": industry,
        "deal_stage": deal_stage,
        "investment_amount": investment_amount,
        "shock_input": shock_input,
        "run": run_button,
    }
