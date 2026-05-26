"""Quick validation of end-to-end pipeline with the Samsung demo scenario."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.WARNING)

from dotenv import load_dotenv
load_dotenv()

from src.core.pipeline import ICPipeline
from src.models.deal import DealInput

deal = DealInput(
    company_name="Samsung Electronics",
    industry="AI Semiconductor",
    deal_stage="Growth Equity",
    investment_amount_usd_m=500.0,
    shock_scenario="Interest rates rise 0.5%",
)

print("Running pipeline for:", deal.company_name)
pipeline = ICPipeline.build()
result = pipeline.run(deal, progress_cb=lambda m: print(" >", m))

chair = result.state.get("chairman_output")
print()
print("=== DEMO SCENARIO RESULTS ===")
print(f"Company     : {result.deal.company_name}")
print(f"Industry    : {result.deal.industry}")
print(f"Shock       : {result.deal.shock_scenario}")
print(f"Base IRR    : {(result.simulation.base_case.irr or 0)*100:.1f}%")
print(f"Base MOIC   : {result.simulation.base_case.moic:.2f}x")
print(f"Decision    : {chair.final_decision.value if chair else 'N/A'}")
print(f"Vote tally  : {chair.vote_tally if chair else {}}")
print(f"Memo title  : {result.memo.header.company_name}")
print("=== PASSED ===")
