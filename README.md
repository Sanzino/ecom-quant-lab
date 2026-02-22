# Ecom Quant Lab

**Quantitative decision intelligence framework for e-commerce performance analysis**

A structured training lab for building data-driven decision-making skills in paid advertising and product economics. This project removes emotional decision-making from ad spend allocation through rigorous break-even analysis, margin sensitivity testing, and simulation-based scenario planning.

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

### Interactive Analysis Notebooks
Jupyter notebooks combining mathematical theory, implementation, and visualization:
- **01 — Break-Even Analysis**: Margin sensitivity, threshold calculations, cost-profitability visualization
- **02 — KPI Decision Engine**: Statistical confidence, decision zones, campaign lifecycle
- **03 — Campaign Simulator**: Monte Carlo methodology, log-normal distributions, strategy comparison

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
print(f"Net Profit: {analysis['net_profit']:.2f} NOK")   # 457.83 NOK
print(f"Margin: {analysis['margin_percent']:.1f}%")       # 57.3%
print(f"Break-Even ROAS: {analysis['breakeven_roas']:.2f}") # 1.74
```

### Campaign Evaluation
```python
from src.kpi_engine import KPIDecisionEngine

engine = KPIDecisionEngine(calc, min_conversions=10)
engine.get_decision_report(spend=5000, conversions=25, revenue=12000)
# → ✅ SCALE — CPA 56% below max with medium confidence
```

### Monte Carlo Simulation
```python
from src.simulator import CampaignSimulator

sim = CampaignSimulator(engine, n_simulations=1000, random_seed=42)
sim.get_prediction_report(daily_budget=500, expected_cpa=350, days=14)
# → 80.7% SCALE probability, +3,056 NOK expected profit
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
Run the campaign 1000× with randomized CPA to get probability distributions instead of single-point estimates.

---

## Project Structure
```
ecom-quant-lab/
├── src/
│   ├── __init__.py
│   ├── break_even.py       # Profitability calculation engine
│   ├── kpi_engine.py       # Scale/Hold/Kill decision logic
│   └── simulator.py        # Monte Carlo scenario modeling
├── notebooks/
│   ├── 01_break_even_analyse.ipynb
│   ├── 02_kpi_decision_engine.ipynb
│   └── 03_simulator.ipynb
├── tests/
│   ├── test_kpi_engine.py  # 34 tests
│   └── test_simulator.py   # 17 tests
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
- **pytest** — Testing (51 tests, all passing)

---

## License

MIT License

---

## Contact

GitHub: [@Sanzino](https://github.com/Sanzino)

---

**Built February 2026**
