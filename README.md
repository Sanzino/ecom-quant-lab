# Ecom Quant Lab

**Quantitative decision intelligence framework for e-commerce performance analysis**

A structured training lab for building data-driven decision-making skills in paid advertising and product economics. This project removes emotional decision-making from ad spend allocation through rigorous break-even analysis, margin sensitivity testing, simulation-based scenario planning, and competitive price intelligence.

---

## Purpose

This project is designed as a skill-building framework for understanding e-commerce unit economics and ad performance analysis. It focuses on quantitative reasoning and structured decision-making rather than automation or shortcuts.

**What this is:**
- A framework for analytical thinking in e-commerce
- A tool for understanding profitability fundamentals
- A portfolio demonstration of quantitative reasoning
- A training environment for capital allocation discipline

**What this is not:**
- An automation tool or bot
- A marketing system
- Financial advice software

---

## Features

### Break-Even Engine (`src/break_even.py`)
Core module for calculating fundamental profitability metrics:
- Net profit before advertising spend
- Profit margin percentage
- Maximum sustainable Cost Per Acquisition (CPA)
- Break-even Return On Ad Spend (ROAS)
- Organic sales break-even analysis (fixed monthly costs vs. units sold)

The engine demonstrates that common industry benchmarks (such as "ROAS above 2.0 is good") are meaningless without context. A 2.0 ROAS can be highly profitable or a significant loss depending on product margin structure.

### KPI Decision Engine (`src/kpi_engine.py`)
Automated campaign evaluation with statistical confidence gating:
- Two-layer decision logic: confidence gate → performance gate
- Three confidence levels (LOW/MEDIUM/HIGH) based on sample size
- Scale/Hold/Kill decisions with configurable buffer thresholds
- CPA ratio normalization for product-agnostic evaluation

### Campaign Simulator (`src/simulator.py`)
Monte Carlo simulation for pre-deployment scenario planning:
- Log-normal CPA sampling with configurable variability
- 1000+ simulation runs per prediction
- Probability distribution of Scale/Hold/Kill outcomes
- Profit confidence intervals (p10, mean, p90)

### Competitor Scanner (`src/competitor_scanner.py`)
Automated competitive price intelligence for Norwegian e-commerce:
- Scrapes finn.no/shop and Google Shopping Norway (requests + BeautifulSoup)
- 6 rotating user-agents with 3-retry logic and graceful failure on blocking
- Norwegian price parser: handles `1.299,-`, `349,00`, `NOK 799` formats
- Append-only CSV logging to `data/competitor_data.csv` for historical tracking
- Pricing position analysis: how many competitors are cheaper vs. more expensive
- Margin sensitivity at competitor average price

### Interactive Analysis Notebooks
Jupyter notebooks combining mathematical theory, implementation, and visualization:
- **01 — Break-Even Analysis**: Margin sensitivity, threshold calculations, cost-profitability visualization, organic sales curve
- **02 — KPI Decision Engine**: Statistical confidence, decision zones, campaign lifecycle
- **03 — Campaign Simulator**: Monte Carlo methodology, log-normal distributions, strategy comparison
- **04 — Competitor Analysis**: Price landscape, historical price tracking, margin sensitivity curves

---

## Installation

**Requirements:**
- Python 3.8+
- pip

**Setup:**
```bash
git clone https://github.com/Sanzino/ecom-quant-lab.git
cd ecom-quant-lab

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

## Usage

### Break-Even Analysis
```python
from src.break_even import BreakEvenCalculator

calc = BreakEvenCalculator(
    sale_price=799,
    product_cost=250,
    shipping_cost=65,
    payment_fee_percent=0.029,
    payment_fee_fixed=3
)

analysis = calc.get_full_analysis()
print(f"Net Profit: {analysis['net_profit']:.2f} NOK")     # 457.83 NOK
print(f"Margin: {analysis['margin_percent']:.1f}%")         # 57.3%
print(f"Break-Even ROAS: {analysis['breakeven_roas']:.2f}") # 1.74

# Organic sales — how many units to cover fixed monthly costs?
result = calc.calculate_organic_profit(units_sold=3)
print(f"Profitable: {result['profitable']}")          # True
print(f"Break-even units: {result['break_even_units']}") # 2.57
```

### Campaign Evaluation
```python
from src.kpi_engine import KPIDecisionEngine

engine = KPIDecisionEngine(calc, min_conversions=10)
engine.get_decision_report(spend=5000, conversions=25, revenue=12000)
# → SCALE — CPA 56% below max with medium confidence
```

### Monte Carlo Simulation
```python
from src.simulator import CampaignSimulator

sim = CampaignSimulator(engine, n_simulations=1000, random_seed=42)
sim.get_prediction_report(daily_budget=500, expected_cpa=350, days=14)
# → 80.7% SCALE probability, +3,056 NOK expected profit
```

### Competitor Price Scanning
```python
from src.competitor_scanner import CompetitorScanner

scanner = CompetitorScanner(
    keyword    = "juicer bærbar",
    our_price  = 349,
    our_margin = 0.684,
)

results = scanner.scan()           # scrapes finn.no + Google Shopping
summary = scanner.get_summary()    # aggregated positioning report

print(f"Competitors found: {summary['competitor_count']}")
print(f"Cheapest:          {summary['min_price']} NOK")
print(f"Avg competitor:    {summary['avg_price']} NOK")
print(f"Cheaper than us:   {summary['cheaper_than_us']}")
print(f"We are cheapest:   {summary['we_are_cheapest']}")
print(f"Margin at avg:     {summary['margin_at_avg_price']}%")
```

### Interactive Exploration
```bash
jupyter notebook notebooks/
```

---

## Core Concepts

### Break-Even ROAS
```
Break-Even ROAS = Sale Price / Max CPA = 1 / (Margin% / 100)
```
- 57% margin → BE-ROAS 1.74 (easy to hit)
- 30% margin → BE-ROAS 3.33 (much harder)

### Two-Layer Decision Logic
```
Layer 1 — Confidence gate:
  LOW confidence (<10 sales)  → always HOLD

Layer 2 — Performance gate:
  CPA ratio > 1.2 (kill_threshold)  → KILL
  CPA ratio < 0.9 (scale_threshold) → SCALE
  Everything else                    → HOLD
```

### Monte Carlo Prediction
Run the campaign 1000× with randomized CPA to get probability distributions instead of single-point estimates. Uses log-normal distribution — always positive, right-skewed, realistic for CPA variance.

### Competitor Positioning
```
price_difference = our_price - competitor_price
  → positive: competitor is cheaper than us
  → negative: we are cheaper than competitor

margin_at_avg_price = (avg_competitor_price - our_costs) / avg_competitor_price
  → answers: "what is our margin if we match the market?"
```

---

## Testing

```bash
pytest tests/ -v
```

| Test file | Tests | Coverage |
|---|---|---|
| `test_break_even.py` | 16 | Net profit, margin, organic profit |
| `test_kpi_engine.py` | 37 | Confidence, CPA/ROAS, decision logic |
| `test_simulator.py` | 14 | Sampling, reproducibility, probabilities |
| `test_competitor_scanner.py` | 44 | HTTP mocking, CSV append, positioning |
| **Total** | **111** | **All passing** |

---

## Project Structure
```
ecom-quant-lab/
├── src/
│   ├── __init__.py
│   ├── break_even.py           # Profitability calculation engine
│   ├── kpi_engine.py           # Scale/Hold/Kill decision logic
│   ├── simulator.py            # Monte Carlo scenario modeling
│   └── competitor_scanner.py  # Competitive price intelligence
├── notebooks/
│   ├── 01_break_even_analyse.ipynb
│   ├── 02_kpi_decision_engine.ipynb
│   ├── 03_simulator.ipynb
│   └── 04_competitor_analysis.ipynb
├── tests/
│   ├── test_break_even.py         # 16 tests
│   ├── test_kpi_engine.py         # 37 tests
│   ├── test_simulator.py          # 14 tests
│   └── test_competitor_scanner.py # 44 tests
├── data/
│   └── competitor_data.csv        # Auto-created, append-only price history
├── requirements.txt
└── README.md
```

---

## Technical Stack

- **Python 3.14**
- **NumPy** — Numerical operations & Monte Carlo sampling
- **Pandas** — Data manipulation
- **Matplotlib / Seaborn** — Visualization
- **Jupyter** — Interactive notebooks
- **requests + BeautifulSoup4** — Web scraping
- **pytest** — Testing (111 tests, all passing)

---

## License

MIT License

---

## Contact

GitHub: [@Sanzino](https://github.com/Sanzino)

---

**Built February 2026**
