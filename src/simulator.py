"""
Campaign simulator for ad spend prediction.

Uses Monte Carlo simulation to predict the probability distribution of
campaign outcomes before committing real budget.
"""
import numpy as np

class CampaignSimulator:
    """
    Predict ad campaign outcomes using Monte Carlo simulation.

    Runs thousands of simulated campaigns with realistic CPA variation
    and uses KPIDecisionEngine to evaluate each outcome.

    Usage:
        >>> sim = CampaignSimulator(engine)
        >>> sim.get_prediction_report(daily_budget=500, expected_cpa=350, days=14)
    """

    def __init__(self, kpi_engine, n_simulations=1000, random_seed=42):
        """
        Initialize simulator.

        Args:
            kpi_engine:    Instance of KPIDecisionEngine
            n_simulations: Number of Monte Carlo runs (int, default 1000)
            random_seed:   Seed for reproducibility (int, default 42)

        Hvorfor disse parameterne:
            - kpi_engine:    Vi trenger max_cpa og beslutningslogikken
            - n_simulations: Flere kjøringer = mer pålitelig statistikk
            - random_seed:   Gjør resultatene reproduserbare (samme tall hver gang)
        """
        # Lagre engine — vi trenger max_cpa og sale_price fra den
        self.engine = kpi_engine

        # Lagre simuleringsparametere
        self.n_simulations = n_simulations

        # Bruk numpy sin moderne random generator med fast seed
        self.rng = np.random.default_rng(random_seed)

    def _sample_cpa(self, expected_cpa, cpa_cv=0.3):
        """
        Sample realistic CPA values using log-normal distribution.

        Log-normal er realistisk fordi:
        - CPA er alltid positiv (kan ikke bli negativ)
        - CPA er høyreskjev — noen konverteringer koster mye mer enn snitt
        - Vanlig antagelse i marketing analytics

        Args:
            expected_cpa: Forventet CPA (float, NOK)
            cpa_cv:       Variabilitet — 0.3 = 30% standardavvik (float)

        Returns:
            ndarray: n_simulations tilfeldige CPA-verdier
        """
        # Beregn log-normal parametere fra ønsket gjennomsnitt og variabilitet
        sigma_sq = np.log(1 + cpa_cv ** 2)
        mu       = np.log(expected_cpa) - sigma_sq / 2

        # Trekk n_simulations tilfeldige CPA-verdier
        return self.rng.lognormal(mu, np.sqrt(sigma_sq), self.n_simulations)
    
    def predict(self, daily_budget, expected_cpa, days, cpa_cv=0.3):
        """
        Run Monte Carlo simulation and return prediction results.

        Args:
            daily_budget: Daglig ad spend (float, NOK)
            expected_cpa: Forventet CPA (float, NOK)
            days:         Kampanjevarighet i dager (int)
            cpa_cv:       CPA-variabilitet, default 0.3 = 30% (float)

        Returns:
            dict: Simuleringsresultater med sannsynligheter og profit-prediksjon
        """
        # Beregn total budsjett for perioden
        total_budget = daily_budget * days

        # Simulator 1000 ulike CPA-verdier (kjernen av Monte Carlo)
        simulated_cpas = self._sample_cpa(expected_cpa, cpa_cv)

        # Beregn Konverteringer per simulering: budsjett / CPA
        simulated_conversions = np.maximum(
            np.round(total_budget / simulated_cpas).astype(int),0
        )

        # Beregn revenue: konverteringer * salgspris
        sales_price = self.engine.breakeven_calc.sale_price
        simulated_revenues = simulated_conversions * sales_price

        # Kjør KPIDecisionEngine på hvert simulert scenario
        decisions = []
        profits  = []

        for i in range(self.n_simulations):
            result = self.engine.evaluate_campaign(
                spend       = total_budget,
                conversions = int(simulated_conversions[i]),
                revenue     = float(simulated_revenues[i])
            )
            decisions.append(result['decision'])

            # Profit per salg = max_cpa - faktisk CPA
            profit = int(simulated_conversions[i]) * (self.engine.max_cpa - simulated_cpas[i])
            profits.append(profit)

        decisions = np.array(decisions)
        profits   = np.array(profits)

        # Aggreger til sannsynligheter og statistikk
        return {
            'total_budget':         total_budget,
            'expected_conversions': round(total_budget / expected_cpa),
            'days':                 days,
            'scale_probability':    round((decisions == 'SCALE').mean() * 100, 1),
            'hold_probability':     round((decisions == 'HOLD').mean()  * 100, 1),
            'kill_probability':     round((decisions == 'KILL').mean()  * 100, 1),
            'profit_mean':          round(profits.mean()),
            'profit_p10':           round(np.percentile(profits, 10)),
            'profit_p90':           round(np.percentile(profits, 90)),
            'simulated_cpas':       simulated_cpas,
            'simulated_profits':    profits,
            'decisions':            decisions,
        }
    
    def get_prediction_report(self, daily_budget, expected_cpa, days, cpa_cv=0.3):
        """
        Print formatted strategy prediction report.

        Convenience wrapper around predict() for interactive
        use in terminal or notebooks.

        Args:
            daily_budget: Daglig ad spend (float, NOK)
            expected_cpa: Forventet CPA (float, NOK)
            days:         Kampanjevarighet i dager (int)
            cpa_cv:       CPA-variabilitet, default 0.3 (float)
        """
        # Hent simuleringsresultater
        r = self.predict(daily_budget, expected_cpa, days, cpa_cv)

        # Hjelpefunksjon for å tegne en enkel bar
        def bar(pct, width=20):
            filled = round(pct / 100 * width)
            return '█' * filled + '░' * (width - filled)

        # Velg anbefaling basert på sannsynligheter
        if r['scale_probability'] >= 60:
            anbefaling = f"Kjør kampanjen. {r['scale_probability']}% sjanse for SCALE."
        elif r['kill_probability'] >= 50:
            anbefaling = f"Unngå kampanjen. {r['kill_probability']}% sjanse for KILL."
        elif r['profit_mean'] > 0:
            anbefaling = "Forsiktig — positiv forventet profit men høy usikkerhet."
        else:
            anbefaling = "Ikke anbefalt — negativ forventet profit."

        print("=" * 56)
        print("  STRATEGI-PREDIKSJON")
        print("=" * 56)
        print(f"  Budsjett:   {r['total_budget']:>8,.0f} NOK  ({daily_budget:.0f} kr/dag × {days} dager)")
        print(f"  Forv. CPA:  {expected_cpa:>8,.0f} NOK")
        print(f"  Forv. salg: {r['expected_conversions']:>8} stk")
        print("-" * 56)
        print("  SANNSYNLIGHET FOR BESLUTNING")
        print(f"  SCALE  {r['scale_probability']:>5.1f}%  {bar(r['scale_probability'])}")
        print(f"  HOLD   {r['hold_probability']:>5.1f}%  {bar(r['hold_probability'])}")
        print(f"  KILL   {r['kill_probability']:>5.1f}%  {bar(r['kill_probability'])}")
        print("-" * 56)
        print("  PROFIT-PREDIKSJON")
        print(f"  Beste  (topp 10%):  {r['profit_p90']:>+10,.0f} NOK")
        print(f"  Forventet:          {r['profit_mean']:>+10,.0f} NOK")
        print(f"  Verste (bunn 10%):  {r['profit_p10']:>+10,.0f} NOK")
        print("-" * 56)
        print(f"  ANBEFALING: {anbefaling}")
        print("=" * 56)