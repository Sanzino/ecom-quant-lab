# STEG 1: Klasse-skjelett og __init__
# Teori: Vi lager en klasse fordi vi vil gruppere relaterte funksjoner
# __init__ tar inn alle input-verdiene og lagrer dem som self.variable

    
"""
Break-even calculator for e-commerce products.

This module calculates profitability metrics to determine
if ad campaigns are viable.
"""


class BreakEvenCalculator:
    """
    Calculate break-even metrics for e-commerce products.
    
    Used to determine maximum sustainable ad spend and
    minimum required ROAS for profitability.
    """
    
    def __init__(self, sale_price, product_cost, shipping_cost, 
                 payment_fee_percent, payment_fee_fixed):
        """
        Initialize calculator with product economics.
        
        Args:
            sale_price: Price customer pays (float, NOK)
            product_cost: Cost of goods sold / COGS (float, NOK)
            shipping_cost: Actual shipping cost you pay (float, NOK)
            payment_fee_percent: Payment processor % (e.g., 0.029 for 2.9%)
            payment_fee_fixed: Payment processor fixed fee (float, NOK)
        """
        # Lagre alle input-verdier som instance variables
        # Disse brukes av alle beregningsmetodene senere
        self.sale_price = sale_price
        self.product_cost = product_cost
        self.shipping_cost = shipping_cost
        self.payment_fee_percent = payment_fee_percent
        self.payment_fee_fixed = payment_fee_fixed
    
    def calculate_net_profit(self):
        """
        Calculate net profit before ad spend.
        
        This is the "room" you have to spend on ads.
        If net profit = 200 NOK, you can spend max 200 NOK on ads per sale.
        
        Returns:
            float: Net profit in NOK
        
        Formula:
            Net Profit = Sale Price - Product Cost - Shipping - Payment Fees
            Payment Fee = (Sale Price × %) + Fixed Fee
        """
        # Beregn payment processing fee (prosent + fast gebyr)
        payment_fee = (self.sale_price * self.payment_fee_percent + 
                      self.payment_fee_fixed)
        
        # Trekk alle kostnader fra salgsprisen
        net_profit = (self.sale_price - 
                     self.product_cost - 
                     self.shipping_cost - 
                     payment_fee)
        
        return net_profit
    
    def calculate_margin_percent(self):
        """
        Calculate profit margin as percentage.
        
        Margin tells you how much of each NOK is actual profit.
        - 50% margin = half of the sale is profit (excellent)
        - 30% margin = 30 øre per krone is profit (solid)
        - 10% margin = only 10 øre per krone (difficult to scale)
        
        Returns:
            float: Margin percentage
        
        Formula:
            Margin % = (Net Profit / Sale Price) × 100
        """
        # Først hent net profit (bruker metoden vi nettopp lagde)
        net_profit = self.calculate_net_profit()
        
        # Beregn margin som prosent
        margin_percent = (net_profit / self.sale_price) * 100
        
        return margin_percent
    
    def calculate_max_cpa(self):
        """
        Calculate maximum Cost Per Acquisition (CPA) before losing money.
        
        This is the break-even point for ad spend per sale.
        If your actual CPA > max CPA, you lose money on every sale.
        
        Returns:
            float: Maximum CPA in NOK
        
        Formula:
            Max CPA = Net Profit (before ads)
        
        Example:
            Net Profit = 458 NOK
            Max CPA = 458 NOK
            If actual CPA = 450 NOK → profit of 8 NOK per sale
            If actual CPA = 500 NOK → loss of 42 NOK per sale
        """
        # Max CPA er simpelthen lik net profit
        # Gjenbruker calculate_net_profit() metoden
        max_cpa = self.calculate_net_profit()
        
        return max_cpa
    
    def calculate_breakeven_roas(self):
        """
        Calculate minimum ROAS (Return On Ad Spend) needed to break even.
        
        This is the critical threshold:
        - If actual ROAS > break-even ROAS → profit
        - If actual ROAS < break-even ROAS → loss
        - If actual ROAS = break-even ROAS → break-even (zero profit)
        
        Returns:
            float: Break-even ROAS
        
        Formula:
            Break-Even ROAS = Sale Price / Max CPA
            
            Alternative formula:
            Break-Even ROAS = 1 / (Margin % / 100)
        
        Example:
            Sale Price = 799 NOK
            Max CPA = 458 NOK
            Break-Even ROAS = 799 / 458 = 1.74
            
            → If ROAS = 2.0, you're profitable
            → If ROAS = 1.5, you're losing money
        """
        # Hent max CPA (gjenbruker metoden)
        max_cpa = self.calculate_max_cpa()
        
        # Beregn break-even ROAS
        breakeven_roas = self.sale_price / max_cpa
        
        return breakeven_roas
    
    def get_full_analysis(self):
        """
        Get complete break-even analysis with all metrics.
        
        This is a convenience method that calls all calculation methods
        and returns everything in a structured dictionary.
        
        Returns:
            dict: All break-even metrics
                - sale_price: Sale price (NOK)
                - product_cost: Product cost (NOK)
                - shipping_cost: Shipping cost (NOK)
                - payment_fee_percent: Payment fee percentage
                - payment_fee_fixed: Payment fixed fee (NOK)
                - total_costs: Sum of all costs (NOK)
                - net_profit: Net profit before ads (NOK)
                - margin_percent: Profit margin (%)
                - max_cpa: Maximum CPA before losing money (NOK)
                - breakeven_roas: Minimum ROAS needed to break even
        
        Example:
            >>> calc = BreakEvenCalculator(799, 250, 65, 0.029, 3)
            >>> analysis = calc.get_full_analysis()
            >>> print(analysis['margin_percent'])
            57.3
        """
        # Beregn alle metrikker (kaller alle metodene vi har lagd)
        net_profit = self.calculate_net_profit()
        margin_percent = self.calculate_margin_percent()
        max_cpa = self.calculate_max_cpa()
        breakeven_roas = self.calculate_breakeven_roas()
        
        # Beregn total costs for oversikt
        payment_fee = (self.sale_price * self.payment_fee_percent + 
                      self.payment_fee_fixed)
        total_costs = (self.product_cost + self.shipping_cost + payment_fee)
        
        # Returner alt i en strukturert dictionary
        return {
            'sale_price': self.sale_price,
            'product_cost': self.product_cost,
            'shipping_cost': self.shipping_cost,
            'payment_fee_percent': self.payment_fee_percent,
            'payment_fee_fixed': self.payment_fee_fixed,
            'total_costs': total_costs,
            'net_profit': net_profit,
            'margin_percent': margin_percent,
            'max_cpa': max_cpa,
            'breakeven_roas': breakeven_roas
        }