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

### Break-Even Engine
Core module for calculating fundamental profitability metrics:
- Net profit before advertising spend
- Profit margin percentage
- Maximum sustainable Cost Per Acquisition (CPA)
- Break-even Return On Ad Spend (ROAS)

The engine demonstrates that common industry benchmarks (such as "ROAS above 2.0 is good") are meaningless without context. A 2.0 ROAS can be highly profitable or a significant loss depending on product margin structure.

### Interactive Analysis Notebooks
Jupyter notebooks combining mathematical theory, implementation, and visualization:
- **Break-Even Analysis** - Comprehensive walkthrough of margin sensitivity and threshold calculations
- Full derivations of formulas with worked examples
- Visual demonstrations of cost-profitability relationships

### Planned Modules
- **KPI Decision Engine** - Automated campaign evaluation logic with statistical significance testing
- **Performance Simulator** - Monte Carlo scenario modeling for pre-deployment testing

---

## Installation

**Requirements:**
- Python 3.8 or higher
- pip package manager

**Setup:**
```bash

📝 SMART! La oss gjøre det mer profesjonelt!
🔥 Ny README - Ren og profesjonell:
markdown

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

### Break-Even Engine
Core module for calculating fundamental profitability metrics:
- Net profit before advertising spend
- Profit margin percentage
- Maximum sustainable Cost Per Acquisition (CPA)
- Break-even Return On Ad Spend (ROAS)

The engine demonstrates that common industry benchmarks (such as "ROAS above 2.0 is good") are meaningless without context. A 2.0 ROAS can be highly profitable or a significant loss depending on product margin structure.

### Interactive Analysis Notebooks
Jupyter notebooks combining mathematical theory, implementation, and visualization:
- **Break-Even Analysis** - Comprehensive walkthrough of margin sensitivity and threshold calculations
- Full derivations of formulas with worked examples
- Visual demonstrations of cost-profitability relationships

### Planned Modules
- **KPI Decision Engine** - Automated campaign evaluation logic with statistical significance testing
- **Performance Simulator** - Monte Carlo scenario modeling for pre-deployment testing

---

## Installation

**Requirements:**
- Python 3.8 or higher
- pip package manager

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

### As a Python Module
```python
from src.break_even import BreakEvenCalculator

calculator = BreakEvenCalculator(
    sale_price=799,
    product_cost=250,
    shipping_cost=65,
    payment_fee_percent=0.029,
    payment_fee_fixed=3
)

analysis = calculator.get_full_analysis()

print(f"Net Profit: {analysis['net_profit']:.2f} NOK")
print(f"Margin: {analysis['margin_percent']:.1f}%")
print(f"Break-Even ROAS: {analysis['breakeven_roas']:.2f}")
```

**Output:**
```
Net Profit: 457.83 NOK
Margin: 57.3%
Break-Even ROAS: 1.74
```

### Interactive Exploration
```bash
jupyter notebook notebooks/ecom_quant_lab.ipynb
```

The notebook provides step-by-step explanations of each concept with executable code cells and visualizations.

---

## Core Concepts

### Break-Even ROAS Calculation

The minimum ROAS required to avoid losses:
```
Break-Even ROAS = Sale Price / Maximum CPA
                = Sale Price / Net Profit
                = 1 / (Margin% / 100)
```

**Example:**
- Product with 57% margin: Break-even ROAS = 1.74
- Product with 30% margin: Break-even ROAS = 3.33

This demonstrates why industry-standard ROAS targets are unreliable without product-specific margin analysis.

### Margin Sensitivity Analysis

Small changes in cost structure create disproportionate effects on profitability thresholds:

**Example scenario:**
- Shipping cost increases by 20 NOK
- Margin decreases by 2.5 percentage points
- Break-even ROAS increases by 0.08

This relationship highlights why cost control is critical for sustainable ad-driven growth.

---

## Project Structure
```
ecom-quant-lab/
├── src/
│   ├── break_even.py          # Profitability calculation engine
│   ├── kpi_engine.py          # Decision logic (planned)
│   └── simulator.py           # Scenario modeling (planned)
├── notebooks/
│   └── ecom_quant_lab.ipynb   # Educational analysis notebook
├── tests/                     # Unit tests (planned)
├── data/                      # Sample datasets
├── requirements.txt           # Python dependencies
└── README.md
```

---

## Technical Stack

- **Python 3.14** - Primary language
- **NumPy** - Numerical operations
- **Pandas** - Data manipulation
- **Matplotlib** - Plotting and visualization
- **Seaborn** - Statistical graphics
- **Jupyter** - Interactive computing environment

---

## Development Roadmap

**Phase 1: Foundation** (Completed)
- Break-even calculation engine
- Pedagogical notebook with theory and examples
- Margin sensitivity visualization

**Phase 2: Decision Systems** (In Progress)
- KPI evaluation framework
- Statistical significance testing
- Automated Scale/Hold/Kill logic

**Phase 3: Simulation** (Planned)
- Monte Carlo scenario generator
- Risk analysis tools
- Multi-variable sensitivity testing

---

## Learning Objectives

This project is structured as a progressive learning experience:

**Week 1: Economic Fundamentals**
- Understanding true profitability vs. revenue
- Margin structure and sensitivity
- CPA and ROAS relationship derivation

**Week 2: Decision Framework**
- Statistical significance in performance data
- Threshold-based decision logic
- Risk management through simulation

The goal is to develop intuition for capital allocation in uncertain environments with limited sample sizes—a common challenge in early-stage ad campaigns.

---

## Methodology

All calculations use conservative assumptions:
- Payment processing fees based on standard Stripe pricing (2.9% + fixed fee)
- No assumption of economies of scale
- No customer lifetime value modeling (single-transaction analysis)

This approach provides worst-case scenario analysis. Any improvements in unit economics or repeat purchase behavior create upside margin of safety.

---

## Contributing

This is a personal educational project, but constructive feedback is welcome through GitHub issues.

---

## License

MIT License

---

## Contact

GitHub: [@Sanzino](https://github.com/Sanzino)

---

**Built February 2026**

