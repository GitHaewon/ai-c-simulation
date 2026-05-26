"""Quick validation of Korean visualization functions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.simulation import ScenarioMetrics, TornadoBar
from src.services.visualization import (
    plot_tornado_chart, plot_scenario_comparison, plot_irr_waterfall,
)

base = ScenarioMetrics(
    label="기본", irr=0.25, moic=3.0,
    exit_value_usd_m=300, exit_revenue_usd_m=30,
    exit_multiple=10, effective_growth_rate=0.3,
    effective_discount_rate=0.12, cash_flows=[-100, 0, 0, 0, 0, 300],
)
shocked = ScenarioMetrics(
    label="금리 +200bp", irr=0.20, moic=2.5,
    exit_value_usd_m=250, exit_revenue_usd_m=30,
    exit_multiple=8, effective_growth_rate=0.3,
    effective_discount_rate=0.14, cash_flows=[-100, 0, 0, 0, 0, 250],
)
bars = [TornadoBar(
    parameter="매출 성장률",
    low_irr=0.18, high_irr=0.32,
    low_label="-20%", high_label="+20%",
    irr_swing=0.14,
)]

fig1 = plot_tornado_chart(bars, 0.25)
fig2 = plot_scenario_comparison(base, [shocked], "irr")
fig3 = plot_irr_waterfall(base, shocked)

print("차트 생성 OK")
print("토네이도 제목:", fig1.layout.title.text)
print("시나리오 제목:", fig2.layout.title.text)
print("브리지 제목  :", fig3.layout.title.text)
print("ALL PASSED")
