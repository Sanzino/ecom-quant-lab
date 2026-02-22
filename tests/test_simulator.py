"""
Tests for CampaignSimulator.

Run with:
    pytest tests/test_simulator.py -v
"""

import sys
import pytest
import numpy as np

sys.path.insert(0, 'src')

from break_even import BreakEvenCalculator
from kpi_engine import KPIDecisionEngine
from simulator import CampaignSimulator


# ------------------------------------------------------------------ #
#  Fixtures                                                           #
# ------------------------------------------------------------------ #

@pytest.fixture
def calc():
    return BreakEvenCalculator(799, 250, 65, 0.029, 3)

@pytest.fixture
def engine(calc):
    return KPIDecisionEngine(calc, min_conversions=10)

@pytest.fixture
def sim(engine):
    return CampaignSimulator(engine, n_simulations=1000, random_seed=42)


# ------------------------------------------------------------------ #
#  TestInit                                                           #
# ------------------------------------------------------------------ #

class TestInit:

    def test_engine_is_stored(self, sim, engine):
        assert sim.engine is engine

    def test_n_simulations_is_stored(self, sim):
        assert sim.n_simulations == 1000

    def test_custom_n_simulations(self, engine):
        sim = CampaignSimulator(engine, n_simulations=500)
        assert sim.n_simulations == 500


# ------------------------------------------------------------------ #
#  TestSampleCPA                                                      #
# ------------------------------------------------------------------ #

class TestSampleCPA:

    def test_returns_correct_number_of_samples(self, sim):
        cpas = sim._sample_cpa(350)
        assert len(cpas) == 1000

    def test_mean_is_close_to_expected(self, sim):
        # Med 1000 samples skal snitt være nær expected (±10%)
        cpas = sim._sample_cpa(350)
        assert cpas.mean() == pytest.approx(350, rel=0.10)

    def test_all_values_are_positive(self, sim):
        cpas = sim._sample_cpa(350)
        assert (cpas > 0).all()

    def test_higher_cv_gives_more_spread(self, engine):
        sim1 = CampaignSimulator(engine, random_seed=42)
        sim2 = CampaignSimulator(engine, random_seed=42)
        low_spread  = sim1._sample_cpa(350, cpa_cv=0.1).std()
        high_spread = sim2._sample_cpa(350, cpa_cv=0.5).std()
        assert high_spread > low_spread


# ------------------------------------------------------------------ #
#  TestPredict                                                        #
# ------------------------------------------------------------------ #

class TestPredict:

    def test_returns_required_keys(self, sim):
        result = sim.predict(500, 350, 14)
        for key in ['total_budget', 'expected_conversions', 'days',
                    'scale_probability', 'hold_probability', 'kill_probability',
                    'profit_mean', 'profit_p10', 'profit_p90',
                    'simulated_cpas', 'simulated_profits', 'decisions']:
            assert key in result

    def test_total_budget_is_correct(self, sim):
        result = sim.predict(500, 350, 14)
        assert result['total_budget'] == 7000

    def test_probabilities_sum_to_100(self, sim):
        result = sim.predict(500, 350, 14)
        total = (result['scale_probability'] +
                 result['hold_probability'] +
                 result['kill_probability'])
        assert total == pytest.approx(100.0, abs=0.2)

    def test_profit_percentiles_are_ordered(self, sim):
        result = sim.predict(500, 350, 14)
        assert result['profit_p10'] <= result['profit_mean'] <= result['profit_p90']

    def test_low_cpa_gives_high_scale_probability(self, sim):
        # CPA på 150 kr er langt under max (458 kr) → høy SCALE-sannsynlighet
        result = sim.predict(500, 150, 30)
        assert result['scale_probability'] > 60

    def test_high_cpa_gives_high_kill_probability(self, sim):
        # CPA på 700 kr er langt over max (458 kr) → høy KILL-sannsynlighet
        result = sim.predict(500, 700, 30)
        assert result['kill_probability'] > 50

    def test_reproducibility_with_same_seed(self, engine):
        sim1 = CampaignSimulator(engine, random_seed=42)
        sim2 = CampaignSimulator(engine, random_seed=42)
        r1 = sim1.predict(500, 350, 14)
        r2 = sim2.predict(500, 350, 14)
        assert r1['profit_mean'] == r2['profit_mean']
        assert r1['scale_probability'] == r2['scale_probability']
