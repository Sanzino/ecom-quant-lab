"""
Tests for BreakEvenCalculator — including organic profit analysis.

Run with:
    pytest tests/test_break_even.py -v

Produktscenario:
    Portable juicer — 349 NOK, ~68.4% margin
    product_cost=72, shipping=25, Stripe 2.9%+3 NOK
    → net_profit_per_unit ≈ 238.88 NOK
    → break_even_units    ≈ 2.57  (trenger 3 salg for å gå i pluss)
"""

import sys
import pytest

sys.path.insert(0, 'src')

from break_even import BreakEvenCalculator


# ------------------------------------------------------------------ #
#  Fixtures                                                           #
# ------------------------------------------------------------------ #

@pytest.fixture
def juicer():
    """Portable juicer: 349 NOK, ~68.4% margin, 613 NOK faste kostnader."""
    return BreakEvenCalculator(
        sale_price=349,
        product_cost=72,
        shipping_cost=25,
        payment_fee_percent=0.029,
        payment_fee_fixed=3
    )


@pytest.fixture
def kaffetrakter():
    """Kaffetrakter fra break-even notebooken: 799 NOK, ~57.3% margin."""
    return BreakEvenCalculator(
        sale_price=799,
        product_cost=250,
        shipping_cost=65,
        payment_fee_percent=0.029,
        payment_fee_fixed=3
    )


# ------------------------------------------------------------------ #
#  TestNetProfit                                                       #
# ------------------------------------------------------------------ #

class TestNetProfit:

    def test_juicer_net_profit(self, juicer):
        # 349 - 72 - 25 - (349×0.029 + 3) = 238.88 NOK
        assert juicer.calculate_net_profit() == pytest.approx(238.88, rel=0.01)

    def test_kaffetrakter_net_profit(self, kaffetrakter):
        assert kaffetrakter.calculate_net_profit() == pytest.approx(457.83, rel=0.01)

    def test_net_profit_is_positive(self, juicer):
        assert juicer.calculate_net_profit() > 0


# ------------------------------------------------------------------ #
#  TestMargin                                                          #
# ------------------------------------------------------------------ #

class TestMargin:

    def test_juicer_margin_is_approx_68_percent(self, juicer):
        assert juicer.calculate_margin_percent() == pytest.approx(68.4, abs=0.2)

    def test_kaffetrakter_margin_is_approx_57_percent(self, kaffetrakter):
        assert kaffetrakter.calculate_margin_percent() == pytest.approx(57.3, abs=0.2)


# ------------------------------------------------------------------ #
#  TestOrganicProfit                                                   #
# ------------------------------------------------------------------ #

class TestOrganicProfit:

    def test_break_even_requires_3_units(self, juicer):
        # 2 salg → ikke lønnsomt
        assert juicer.calculate_organic_profit(2)['profitable'] is False
        # 3 salg → lønnsomt
        assert juicer.calculate_organic_profit(3)['profitable'] is True

    def test_break_even_units_is_approx_2_57(self, juicer):
        result = juicer.calculate_organic_profit(1)
        assert result['break_even_units'] == pytest.approx(2.57, abs=0.05)

    def test_gross_profit_at_3_units(self, juicer):
        result = juicer.calculate_organic_profit(3)
        # gross_profit = 3 × 238.88 = 716.64
        assert result['gross_profit'] == pytest.approx(716.64, rel=0.01)

    def test_net_profit_at_3_units(self, juicer):
        result = juicer.calculate_organic_profit(3)
        # net_profit = 716.64 - 613 = 103.64
        assert result['net_profit'] == pytest.approx(103.64, rel=0.05)

    def test_net_profit_at_2_units_is_negative(self, juicer):
        result = juicer.calculate_organic_profit(2)
        assert result['net_profit'] < 0

    def test_zero_units_is_loss_equal_to_fixed_cost(self, juicer):
        result = juicer.calculate_organic_profit(0)
        assert result['net_profit'] == pytest.approx(-613, abs=1)
        assert result['profitable'] is False

    def test_result_contains_required_keys(self, juicer):
        result = juicer.calculate_organic_profit(5)
        for key in ['units_sold', 'net_profit_per_unit', 'gross_profit',
                    'fixed_monthly_cost', 'net_profit', 'break_even_units', 'profitable']:
            assert key in result

    def test_units_sold_is_preserved(self, juicer):
        result = juicer.calculate_organic_profit(10)
        assert result['units_sold'] == 10

    def test_fixed_monthly_cost_is_preserved(self, juicer):
        result = juicer.calculate_organic_profit(5)
        assert result['fixed_monthly_cost'] == 613

    def test_custom_fixed_cost(self, juicer):
        # Med 800 NOK faste kostnader trenger man flere salg
        result_default = juicer.calculate_organic_profit(3, fixed_monthly_cost=613)
        result_custom  = juicer.calculate_organic_profit(3, fixed_monthly_cost=800)
        assert result_custom['net_profit'] < result_default['net_profit']
        assert result_custom['break_even_units'] > result_default['break_even_units']

    def test_high_volume_is_profitable(self, juicer):
        result = juicer.calculate_organic_profit(50)
        assert result['profitable'] is True
        assert result['net_profit'] > 0
