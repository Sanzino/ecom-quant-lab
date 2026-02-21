"""
KPI Decision Engine for ad campaign evaluation.

This module implements structured decision logic for determining
whether to scale, hold, or kill ad campaigns based on performance
metrics and statistical confidence.

Core insight: a good CPA with only 3 sales is meaningless noise.
A good CPA with 50 sales is a reliable signal. The engine enforces
this by gating every decision behind a confidence level check.
"""


class KPIDecisionEngine:
    """
    Evaluate ad campaign performance and make data-driven decisions.

    Uses break-even thresholds, sample size requirements, and
    confidence levels to avoid premature scaling or killing campaigns.

    Decision framework:
        KILL  → Campaign is clearly losing money (sufficient data)
        HOLD  → Insufficient data OR marginal performance
        SCALE → Campaign is clearly profitable with sufficient data

    Usage:
        >>> from break_even import BreakEvenCalculator
        >>> calc   = BreakEvenCalculator(799, 250, 65, 0.029, 3)
        >>> engine = KPIDecisionEngine(calc)
        >>> result = engine.evaluate_campaign(spend=5000, conversions=25, revenue=12000)
        >>> print(result['decision'])
        SCALE
    """

    # Konfidens-nivåer som klassekonstanter (unngår magic strings)
    CONFIDENCE_LOW    = "low"     # < min_conversions: upålitelig data
    CONFIDENCE_MEDIUM = "medium"  # min_conversions til 3x: forsiktig
    CONFIDENCE_HIGH   = "high"    # > 3x min_conversions: pålitelig

    def __init__(self, breakeven_calculator, min_conversions=10,
                 kill_threshold=1.2, scale_threshold=0.9):
        """
        Initialize decision engine with thresholds.

        Args:
            breakeven_calculator: Instance of BreakEvenCalculator
            min_conversions:      Minimum sales for a reliable decision (int)
            kill_threshold:       CPA / max_cpa ratio that triggers KILL (float)
                                  Default 1.2 = CPA must be >20% over budget
            scale_threshold:      CPA / max_cpa ratio below which SCALE fires (float)
                                  Default 0.9 = CPA must be >10% under budget

        Why these parameters matter:
            - breakeven_calculator: Gir oss max_cpa og breakeven_roas automatisk
            - min_conversions:      Unngår beslutninger basert på for lite data
            - kill_threshold:       Buffer slik at vi ikke dreper kampanjen for tidlig
            - scale_threshold:      Buffer slik at vi bare skalerer med god margin
        """
        # Lagre breakeven calculator - henter max_cpa og breakeven_roas fra den
        self.breakeven_calc = breakeven_calculator

        # Lagre beslutnings-terskler
        self.min_conversions = min_conversions
        self.kill_threshold  = kill_threshold
        self.scale_threshold = scale_threshold

        # Hent break-even metrikker én gang ved init (unngår gjentatte kall)
        analysis            = self.breakeven_calc.get_full_analysis()
        self.max_cpa        = analysis['max_cpa']
        self.breakeven_roas = analysis['breakeven_roas']

    # ------------------------------------------------------------------ #
    #  Private helper methods (navngitt med _ = intern bruk)              #
    # ------------------------------------------------------------------ #

    def _calculate_confidence(self, conversions):
        """
        Determine data confidence level based on number of conversions.

        Statistical reasoning: the more conversions, the more your CPA
        reflects the true campaign performance rather than random chance.
        With 3 sales you could just be lucky. With 50, CPA is reliable.

        Args:
            conversions: Number of completed sales in the period (int)

        Returns:
            str: One of CONFIDENCE_LOW, CONFIDENCE_MEDIUM, CONFIDENCE_HIGH

        Thresholds (based on min_conversions, default=10):
            LOW    → < 10 conversions  (unngå beslutninger)
            MEDIUM → 10–30 conversions (forsiktige beslutninger)
            HIGH   → > 30 conversions  (pålitelige beslutninger)
        """
        # Datagrunnlaget er for lite - ikke ta beslutninger ennå
        if conversions < self.min_conversions:
            return self.CONFIDENCE_LOW

        # Moderat datagrunnlag - ta beslutninger med forsiktighet
        elif conversions < self.min_conversions * 3:
            return self.CONFIDENCE_MEDIUM

        # Solid datagrunnlag - kan ta pålitelige beslutninger
        else:
            return self.CONFIDENCE_HIGH

    def _calculate_cpa(self, spend, conversions):
        """
        Calculate Cost Per Acquisition.

        CPA = how much you paid in ads for each individual sale.
        This is the primary metric compared against max_cpa.

        Args:
            spend:       Total ad spend (float, NOK)
            conversions: Number of completed sales (int)

        Returns:
            float: CPA in NOK, or None if conversions == 0

        Formula:
            CPA = Ad Spend / Conversions
        """
        # Kan ikke dele på null - returner None hvis ingen konverteringer ennå
        if conversions == 0:
            return None

        # Beregn kostnad per salg
        return spend / conversions

    def _calculate_roas(self, revenue, spend):
        """
        Calculate Return On Ad Spend.

        ROAS = how much revenue you earned per NOK spent on ads.
        Compare against breakeven_roas to see if you're profitable.

        Args:
            revenue: Total revenue generated by ads (float, NOK)
            spend:   Total ad spend (float, NOK)

        Returns:
            float: ROAS ratio, or None if spend == 0

        Formula:
            ROAS = Revenue / Ad Spend

        Example:
            Revenue = 10 000 NOK, Spend = 5 000 NOK → ROAS = 2.0
            Meaning: you got 2 kr back for every 1 kr spent.
        """
        # Kan ikke dele på null - returner None hvis ingen spend
        if spend == 0:
            return None

        # Beregn avkastning per annonsekrone
        return revenue / spend

    def _make_decision(self, actual_cpa, confidence):
        """
        Core decision logic: combine CPA performance with data confidence.

        This method has two sequential layers:
          1. Confidence gate  – is there enough data to decide at all?
          2. Performance gate – is the CPA within the profitable range?

        Args:
            actual_cpa:  Computed CPA for this campaign period (float, NOK)
            confidence:  One of CONFIDENCE_LOW / MEDIUM / HIGH (str)

        Returns:
            tuple: (decision, reasoning)
                   decision  ∈ {"SCALE", "HOLD", "KILL"}
                   reasoning is a human-readable explanation string

        Decision matrix:
            LOW confidence               → HOLD (aldri beslutt på lite data)
            cpa_ratio > kill_threshold   → KILL (klart ulønnsom)
            cpa_ratio < scale_threshold
              AND confidence >= MEDIUM   → SCALE (klart lønnsom)
            everything else              → HOLD (marginalt eller usikkert)
        """
        # Beregn CPA som andel av maks tillatt CPA (1.0 = break-even)
        cpa_ratio = actual_cpa / self.max_cpa

        # --- LAG 1: Konfidens-gate ---
        # Ikke nok data til å ta en pålitelig beslutning uansett CPA
        if confidence == self.CONFIDENCE_LOW:
            return (
                "HOLD",
                f"Insufficient data — need at least {self.min_conversions} conversions "
                f"for a reliable signal. "
                f"Current CPA: {actual_cpa:.0f} NOK vs max {self.max_cpa:.0f} NOK. "
                "Keep running and gather more data."
            )

        # --- LAG 2: Ytelse-gate ---

        # Kampanjen er klart ulønnsom - drep den
        if cpa_ratio > self.kill_threshold:
            pct_over = (cpa_ratio - 1.0) * 100
            return (
                "KILL",
                f"CPA ({actual_cpa:.0f} NOK) is {pct_over:.0f}% above max CPA "
                f"({self.max_cpa:.0f} NOK). Campaign is losing money. Stop spend."
            )

        # Kampanjen er klart lønnsom med tilstrekkelig data - skaler
        if cpa_ratio < self.scale_threshold and confidence in (
            self.CONFIDENCE_MEDIUM, self.CONFIDENCE_HIGH
        ):
            pct_under = (1.0 - cpa_ratio) * 100
            return (
                "SCALE",
                f"CPA ({actual_cpa:.0f} NOK) is {pct_under:.0f}% below max CPA "
                f"({self.max_cpa:.0f} NOK) with {confidence} confidence. "
                "Campaign is profitable — increase budget."
            )

        # Alt imellom er HOLD - beskriv hvorfor
        if cpa_ratio >= 1.0:
            status = "over budget"
        elif cpa_ratio >= self.scale_threshold:
            status = "marginally profitable (within scale buffer)"
        else:
            status = "profitable but confidence too low to scale"

        return (
            "HOLD",
            f"CPA ({actual_cpa:.0f} NOK) is {status} vs max "
            f"({self.max_cpa:.0f} NOK). Confidence: {confidence}. "
            "Maintain current spend and monitor."
        )

    # ------------------------------------------------------------------ #
    #  Public methods                                                      #
    # ------------------------------------------------------------------ #

    def evaluate_campaign(self, spend, conversions, revenue):
        """
        Evaluate campaign performance and return a structured decision.

        This is the main public method. It orchestrates all helper
        methods and returns a complete, structured result dictionary.

        Args:
            spend:       Total ad spend in the period (float, NOK)
            conversions: Number of completed sales in the period (int)
            revenue:     Total revenue from ads in the period (float, NOK)

        Returns:
            dict with keys:
                decision   (str):  "SCALE", "HOLD", or "KILL"
                reasoning  (str):  Human-readable explanation
                confidence (str):  Data confidence level
                metrics    (dict): All computed metrics for further analysis

        Example:
            >>> result = engine.evaluate_campaign(5000, 25, 12000)
            >>> result['decision']
            'SCALE'
        """
        # Beregn alle metrikker fra input-verdiene
        actual_cpa  = self._calculate_cpa(spend, conversions)
        actual_roas = self._calculate_roas(revenue, spend)
        confidence  = self._calculate_confidence(conversions)

        # Spesialtilfelle: ingen konverteringer ennå
        if actual_cpa is None:
            return {
                'decision':   'HOLD',
                'reasoning':  'No conversions recorded yet. Cannot evaluate campaign.',
                'confidence': self.CONFIDENCE_LOW,
                'metrics': {
                    'actual_cpa':     None,
                    'max_cpa':        round(self.max_cpa, 2),
                    'cpa_ratio':      None,
                    'actual_roas':    None,
                    'breakeven_roas': round(self.breakeven_roas, 2),
                    'conversions':    conversions,
                    'spend':          spend,
                    'revenue':        revenue,
                    'confidence':     self.CONFIDENCE_LOW,
                }
            }

        # Kjør beslutningslogikken (kjernen av motoren)
        decision, reasoning = self._make_decision(actual_cpa, confidence)

        # Beregn CPA-ratio for metrikker
        cpa_ratio = actual_cpa / self.max_cpa

        # Bygg og returner komplett resultat-dictionary
        return {
            'decision':   decision,
            'reasoning':  reasoning,
            'confidence': confidence,
            'metrics': {
                'actual_cpa':     round(actual_cpa, 2),
                'max_cpa':        round(self.max_cpa, 2),
                'cpa_ratio':      round(cpa_ratio, 3),
                'actual_roas':    round(actual_roas, 2),
                'breakeven_roas': round(self.breakeven_roas, 2),
                'conversions':    conversions,
                'spend':          spend,
                'revenue':        revenue,
                'confidence':     confidence,
            }
        }

    def get_decision_report(self, spend, conversions, revenue):
        """
        Print a formatted, human-readable decision report to stdout.

        Convenience wrapper around evaluate_campaign() for interactive
        use in notebooks or the terminal.

        Args:
            spend:       Total ad spend (float, NOK)
            conversions: Number of completed sales (int)
            revenue:     Total revenue from ads (float, NOK)
        """
        # Hent evalueringsresultatet fra hoved-metoden
        result = self.evaluate_campaign(spend, conversions, revenue)
        m      = result['metrics']

        # Velg ikon basert på beslutning (gjør rapporten lettere å scanne)
        icons   = {'SCALE': '✅ SCALE', 'HOLD': '⏸  HOLD', 'KILL': '🛑 KILL'}
        verdict = icons.get(result['decision'], result['decision'])

        print("=" * 56)
        print("  KPI DECISION REPORT")
        print("=" * 56)
        print(f"  Decision:    {verdict}")
        print(f"  Confidence:  {result['confidence'].upper()}")
        print("-" * 56)
        # Bryt lang reasoning-tekst over flere linjer for lesbarhet
        words, line = result['reasoning'].split(), ""
        for word in words:
            if len(line) + len(word) + 1 > 50:
                print(f"  {line}")
                line = word
            else:
                line = f"{line} {word}".strip()
        if line:
            print(f"  {line}")
        print("-" * 56)
        print("  CAMPAIGN METRICS")
        print(f"  Conversions: {m['conversions']}")
        print(f"  Spend:       {m['spend']:>10,.0f} NOK")
        print(f"  Revenue:     {m['revenue']:>10,.0f} NOK")
        if m['actual_cpa'] is not None:
            print(f"  Actual CPA:  {m['actual_cpa']:>10,.0f} NOK")
            print(f"  Max CPA:     {m['max_cpa']:>10,.0f} NOK")
            print(f"  CPA ratio:   {m['cpa_ratio']:>10.1%} of max")
        else:
            print("  Actual CPA:       N/A")
        if m['actual_roas'] is not None:
            print(f"  Actual ROAS: {m['actual_roas']:>10.2f}x")
        print(f"  B/E ROAS:    {m['breakeven_roas']:>10.2f}x")
        print("=" * 56)
