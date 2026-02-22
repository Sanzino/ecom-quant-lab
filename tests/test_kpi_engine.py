"""
Tests for KPIDecisionEngine.

Run with:
    pytest tests/test_kpi_engine.py -v

Produktscenario brukt i alle tester:
    BreakEvenCalculator(799, 250, 65, 0.029, 3)
    → max_cpa  ≈ 457.83 NOK
    → kill zone: CPA > 549 NOK  (120% av max)
    → scale zone: CPA < 412 NOK  (90% av max)
"""

import sys
import pytest

sys.path.insert(0, 'src')

from break_even import BreakEvenCalculator
from kpi_engine import KPIDecisionEngine


# ------------------------------------------------------------------ #
#  Fixtures — gjenbrukbare testoppsett                                #
# ------------------------------------------------------------------ #

@pytest.fixture
def calc():
    """Standard kaffetrakter-produkt: 799 kr, 250 COGS, 65 frakt."""
    return BreakEvenCalculator(
        sale_price=799,
        product_cost=250,
        shipping_cost=65,
        payment_fee_percent=0.029,
        payment_fee_fixed=3
    )


@pytest.fixture
def engine(calc):
    """Standard engine med default thresholds."""
    return KPIDecisionEngine(
        breakeven_calculator=calc,
        min_conversions=10,
        kill_threshold=1.2,
        scale_threshold=0.9
    )


# ------------------------------------------------------------------ #
#  TestConfidence — _calculate_confidence()                           #
# ------------------------------------------------------------------ #

class TestConfidence:
    """Test at konfidensnivå beregnes korrekt fra antall konverteringer."""

    def test_zero_conversions_is_low(self, engine):
        assert engine._calculate_confidence(0) == "low"

    def test_below_min_is_low(self, engine):
        # min_conversions=10, så 9 og under skal gi LOW
        assert engine._calculate_confidence(9) == "low"

    def test_exactly_min_is_medium(self, engine):
        # Grensetilfelle: nøyaktig 10 konverteringer → MEDIUM
        assert engine._calculate_confidence(10) == "medium"

    def test_between_min_and_triple_is_medium(self, engine):
        # 10 til 29 → MEDIUM (min=10, 3x=30)
        assert engine._calculate_confidence(15) == "medium"
        assert engine._calculate_confidence(29) == "medium"

    def test_exactly_triple_is_high(self, engine):
        # Grensetilfelle: nøyaktig 30 konverteringer → HIGH
        assert engine._calculate_confidence(30) == "high"

    def test_above_triple_is_high(self, engine):
        assert engine._calculate_confidence(50) == "high"
        assert engine._calculate_confidence(100) == "high"

    def test_custom_min_conversions(self, calc):
        # Sjekk at custom min_conversions respekteres
        engine_custom = KPIDecisionEngine(calc, min_conversions=20)
        assert engine_custom._calculate_confidence(19) == "low"
        assert engine_custom._calculate_confidence(20) == "medium"
        assert engine_custom._calculate_confidence(60) == "high"


# ------------------------------------------------------------------ #
#  TestCPA — _calculate_cpa()                                         #
# ------------------------------------------------------------------ #

class TestCPA:
    """Test CPA-beregning inkludert zero-division guard."""

    def test_normal_cpa(self, engine):
        # 5000 kr spend / 25 salg = 200 kr CPA
        assert engine._calculate_cpa(5000, 25) == pytest.approx(200.0)

    def test_zero_conversions_returns_none(self, engine):
        # Kan ikke dele på null — skal returnere None, ikke krasje
        assert engine._calculate_cpa(5000, 0) is None

    def test_single_conversion(self, engine):
        # 1 konvertering: CPA = spend
        assert engine._calculate_cpa(350, 1) == pytest.approx(350.0)

    def test_zero_spend(self, engine):
        # Gratis trafikk: CPA = 0
        assert engine._calculate_cpa(0, 10) == pytest.approx(0.0)


# ------------------------------------------------------------------ #
#  TestROAS — _calculate_roas()                                       #
# ------------------------------------------------------------------ #

class TestROAS:
    """Test ROAS-beregning inkludert zero-division guard."""

    def test_normal_roas(self, engine):
        # 12000 kr revenue / 5000 kr spend = 2.4x ROAS
        assert engine._calculate_roas(12000, 5000) == pytest.approx(2.4)

    def test_zero_spend_returns_none(self, engine):
        # Kan ikke beregne ROAS uten spend
        assert engine._calculate_roas(12000, 0) is None

    def test_breakeven_roas(self, engine):
        # Revenue = spend → ROAS = 1.0 (break-even på annonsering)
        assert engine._calculate_roas(5000, 5000) == pytest.approx(1.0)


# ------------------------------------------------------------------ #
#  TestDecision — _make_decision()                                    #
# ------------------------------------------------------------------ #

class TestDecision:
    """
    Test kjernelogikken: confidence gate → performance gate.

    max_cpa ≈ 457.83 NOK
    Kill zone:  CPA > 549.4 NOK  (1.2 × 457.83)
    Scale zone: CPA < 412.0 NOK  (0.9 × 457.83)
    Hold zone:  412 – 549 NOK
    """

    # --- Konfidens-gate (LAG 1) ---

    def test_low_confidence_always_hold_even_with_great_cpa(self, engine):
        # CPA på 100 kr er fantastisk, men LOW confidence → HOLD uansett
        decision, reasoning = engine._make_decision(100, "low")
        assert decision == "HOLD"
        assert "Insufficient data" in reasoning

    def test_low_confidence_always_hold_even_with_bad_cpa(self, engine):
        # Selv med dårlig CPA + lite data → HOLD, ikke KILL
        decision, _ = engine._make_decision(600, "low")
        assert decision == "HOLD"

    # --- Ytelse-gate (LAG 2) ---

    def test_kill_with_cpa_above_kill_threshold(self, engine):
        # 600 / 457.83 = 1.31 > 1.2 → KILL
        decision, reasoning = engine._make_decision(600, "medium")
        assert decision == "KILL"
        assert "losing money" in reasoning

    def test_kill_with_high_confidence_too(self, engine):
        decision, _ = engine._make_decision(600, "high")
        assert decision == "KILL"

    def test_scale_with_medium_confidence(self, engine):
        # 200 / 457.83 = 0.44 < 0.9 → SCALE
        decision, reasoning = engine._make_decision(200, "medium")
        assert decision == "SCALE"
        assert "profitable" in reasoning

    def test_scale_with_high_confidence(self, engine):
        decision, _ = engine._make_decision(200, "high")
        assert decision == "SCALE"

    def test_hold_when_cpa_in_buffer_zone(self, engine):
        # 440 / 457.83 = 0.96 → mellom 0.9 og 1.2 → HOLD
        decision, _ = engine._make_decision(440, "medium")
        assert decision == "HOLD"

    def test_hold_when_just_below_kill_threshold(self, engine):
        # 548 / 457.83 = 1.197 → akkurat under kill (1.2) → HOLD
        decision, _ = engine._make_decision(548, "high")
        assert decision == "HOLD"

    def test_hold_when_just_above_scale_threshold(self, engine):
        # 413 / 457.83 = 0.902 → akkurat over scale (0.9) → HOLD
        decision, _ = engine._make_decision(413, "high")
        assert decision == "HOLD"


# ------------------------------------------------------------------ #
#  TestEvaluateCampaign — evaluate_campaign() (full pipeline)         #
# ------------------------------------------------------------------ #

class TestEvaluateCampaign:
    """Test den offentlige hoved-metoden end-to-end."""

    def test_no_conversions_returns_hold(self, engine):
        result = engine.evaluate_campaign(spend=5000, conversions=0, revenue=0)
        assert result['decision'] == 'HOLD'
        assert result['metrics']['actual_cpa'] is None
        assert result['metrics']['actual_roas'] is None

    def test_low_conversions_returns_hold(self, engine):
        # 4 konverteringer → LOW confidence → HOLD
        result = engine.evaluate_campaign(spend=2000, conversions=4, revenue=3200)
        assert result['decision'] == 'HOLD'
        assert result['confidence'] == 'low'

    def test_kill_scenario(self, engine):
        # 9000 / 15 = 600 NOK CPA → over kill threshold → KILL
        result = engine.evaluate_campaign(spend=9000, conversions=15, revenue=7000)
        assert result['decision'] == 'KILL'

    def test_scale_scenario(self, engine):
        # 5000 / 25 = 200 NOK CPA → well below max → SCALE
        result = engine.evaluate_campaign(spend=5000, conversions=25, revenue=12000)
        assert result['decision'] == 'SCALE'

    def test_hold_marginal_scenario(self, engine):
        # 6600 / 15 = 440 NOK CPA → buffer zone → HOLD
        result = engine.evaluate_campaign(spend=6600, conversions=15, revenue=9500)
        assert result['decision'] == 'HOLD'

    # --- Struktur-tester ---

    def test_result_contains_required_keys(self, engine):
        result = engine.evaluate_campaign(5000, 25, 12000)
        for key in ['decision', 'reasoning', 'confidence', 'metrics']:
            assert key in result, f"Missing key: {key}"

    def test_metrics_contains_required_keys(self, engine):
        result = engine.evaluate_campaign(5000, 25, 12000)
        m = result['metrics']
        expected = [
            'actual_cpa', 'max_cpa', 'cpa_ratio', 'actual_roas',
            'breakeven_roas', 'conversions', 'spend', 'revenue', 'confidence'
        ]
        for key in expected:
            assert key in m, f"Missing metric key: {key}"

    def test_decision_is_valid_string(self, engine):
        result = engine.evaluate_campaign(5000, 25, 12000)
        assert result['decision'] in ('SCALE', 'HOLD', 'KILL')

    def test_cpa_ratio_matches_computation(self, engine):
        result = engine.evaluate_campaign(5000, 25, 12000)
        # CPA = 5000/25 = 200, ratio = 200 / max_cpa
        expected = 200 / engine.max_cpa
        assert result['metrics']['cpa_ratio'] == pytest.approx(expected, rel=0.01)

    def test_input_values_preserved_in_metrics(self, engine):
        result = engine.evaluate_campaign(spend=5000, conversions=25, revenue=12000)
        m = result['metrics']
        assert m['spend'] == 5000
        assert m['revenue'] == 12000
        assert m['conversions'] == 25

    def test_max_cpa_matches_engine_attribute(self, engine):
        result = engine.evaluate_campaign(5000, 25, 12000)
        assert result['metrics']['max_cpa'] == pytest.approx(engine.max_cpa, rel=0.01)


# ------------------------------------------------------------------ #
#  TestInit — __init__ og engine-attributter                          #
# ------------------------------------------------------------------ #

class TestInit:
    """Test at engine initialiseres korrekt fra BreakEvenCalculator."""

    def test_max_cpa_is_correct(self, engine):
        # max_cpa = 799 - 250 - 65 - (799*0.029 + 3) ≈ 457.83
        assert engine.max_cpa == pytest.approx(457.83, rel=0.01)

    def test_breakeven_roas_is_correct(self, engine):
        # breakeven_roas = 799 / 457.83 ≈ 1.745
        assert engine.breakeven_roas == pytest.approx(1.745, rel=0.01)

    def test_custom_thresholds_are_stored(self, calc):
        engine = KPIDecisionEngine(calc, min_conversions=20,
                                   kill_threshold=1.5, scale_threshold=0.8)
        assert engine.min_conversions == 20
        assert engine.kill_threshold  == 1.5
        assert engine.scale_threshold == 0.8
