"""
Competitor price scanner for Norwegian e-commerce products.

Three sources:
  1. DuckDuckGo organic  — finds webshops ranking for the same keyword
  2. Prisjakt.no         — Norwegian price comparison aggregator
  3. AliExpress via DDG  — estimates market sourcing price
"""

import csv
import os
import re
import time
import random
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


# ------------------------------------------------------------------ #
#  Konstanter                                                          #
# ------------------------------------------------------------------ #

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
    "Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
]

CSV_COLUMNS = [
    "timestamp", "keyword", "source", "title", "url",
    "price_nok", "snippet", "our_price", "our_margin",
    "price_difference", "we_are_cheaper",
]

RETRY_ATTEMPTS = 3
RETRY_DELAY    = 2   # sekunder mellom forsøk


# ------------------------------------------------------------------ #
#  Klasse                                                              #
# ------------------------------------------------------------------ #

class CompetitorScanner:
    """
    Scan competitor prices from DuckDuckGo organic, Prisjakt.no, and AliExpress.

    Compares results against our own product economics, logs everything to
    a date-based CSV file, and prints a Norwegian market positioning summary.

    Usage:
        >>> scanner = CompetitorScanner("elektrisk juicemaskin bærbar", 349, 0.684)
        >>> results = scanner.scan()
        >>> summary = scanner.get_summary()
    """

    def __init__(self, keyword: str, our_price: float, our_margin: float):
        """
        Initialize scanner with product parameters.

        Args:
            keyword:    Search term for competitor lookup (str)
            our_price:  Our product sale price in NOK (float)
            our_margin: Our profit margin as decimal — 0.684 means 68.4% (float)
        """
        # Lagre søkeparametere — brukes i alle scraping- og CSV-metoder
        self.keyword    = keyword
        self.our_price  = our_price
        self.our_margin = our_margin

        # Opprett data-mappe og dagens CSV-fil
        os.makedirs("data", exist_ok=True)
        self._ensure_csv_exists()

    # ---------------------------------------------------------------- #
    #  CSV-sti (datobasert)                                             #
    # ---------------------------------------------------------------- #

    @property
    def csv_path(self) -> str:
        """
        Return today's CSV path.

        En ny fil per dag gir naturlig historisk struktur:
            data/competitor_scan_2026-02-22.csv
            data/competitor_scan_2026-03-01.csv
        """
        date = datetime.now().strftime("%Y-%m-%d")
        return f"data/competitor_scan_{date}.csv"

    def _ensure_csv_exists(self) -> None:
        """Opprett CSV med kolonneoverskrifter hvis filen ikke finnes ennå."""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=CSV_COLUMNS).writeheader()

    # ---------------------------------------------------------------- #
    #  HTTP-hjelper (brukt av Prisjakt-scraperen)                       #
    # ---------------------------------------------------------------- #

    def _get_headers(self) -> dict:
        """
        Build HTTP request headers with a randomly chosen user-agent.

        Roterer brukeragenter for å redusere sjansen for blokkering.
        """
        return {
            "User-Agent":      random.choice(USER_AGENTS),
            "Accept-Language": "nb-NO,nb;q=0.9,no;q=0.8,en;q=0.7",
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection":      "keep-alive",
        }

    def _fetch(self, url: str) -> BeautifulSoup | None:
        """
        Fetch a URL with retry logic and return parsed HTML.

        Prøver RETRY_ATTEMPTS ganger ved nettverksfeil.
        Returnerer None ved blokkering eller vedvarende feil.

        Args:
            url: Full URL to fetch (str)

        Returns:
            BeautifulSoup object, or None if all retries failed
        """
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                response = requests.get(
                    url,
                    headers=self._get_headers(),
                    timeout=10,
                )

                if response.status_code in (403, 429):
                    print(f"  [BLOKKERT] {url} — HTTP {response.status_code}")
                    return None

                if response.status_code != 200:
                    print(f"  [FEIL] HTTP {response.status_code} (forsøk {attempt}/{RETRY_ATTEMPTS})")
                    time.sleep(RETRY_DELAY)
                    continue

                return BeautifulSoup(response.text, "html.parser")

            except requests.RequestException as e:
                print(f"  [FEIL] Nettverksfeil forsøk {attempt}/{RETRY_ATTEMPTS}: {e}")
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_DELAY)

        return None

    # ---------------------------------------------------------------- #
    #  Pris-parser                                                       #
    # ---------------------------------------------------------------- #

    def _parse_price_nok(self, price_text: str) -> float | None:
        """
        Parse a raw price string into a float NOK value.

        Håndterer norske prisformater:
            "349 kr"   → 349.0
            "1.299,-"  → 1299.0
            "NOK 799"  → 799.0
            "1 299,00" → 1299.0

        Args:
            price_text: Raw text containing a price (str)

        Returns:
            float price in NOK, or None if parsing fails
        """
        if not price_text:
            return None

        cleaned = re.sub(r"[^\d.,]", "", price_text)

        if not cleaned:
            return None

        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "." in cleaned:
            parts = cleaned.split(".")
            # Norsk tusenskilletegn: 1.299 → nøyaktig 3 sifre etter punktum
            if len(parts) == 2 and len(parts[1]) == 3:
                cleaned = cleaned.replace(".", "")
            # Ellers: desimalpunktum (f.eks. 1.5) — la stå som det er

        try:
            return float(cleaned)
        except ValueError:
            return None

    def _extract_price_from_text(self, text: str) -> float | None:
        """
        Try to extract a price from free-text snippets.

        Brukes på DuckDuckGo-snippets der prisen ikke er strukturert HTML.
        Støtter norske kr-priser og USD/EUR (omregnes til estimert NOK).

        Args:
            text: Free text that may contain a price (str)

        Returns:
            float NOK price estimate, or None
        """
        if not text:
            return None

        # Norsk format: "349 kr" eller "kr 349"
        match = re.search(
            r'(?:kr\.?\s*)([\d\s.,]+)|(?:([\d\s.,]+)\s*kr)',
            text, re.IGNORECASE
        )
        if match:
            raw = (match.group(1) or match.group(2) or "").strip()
            price = self._parse_price_nok(raw)
            if price and price > 0:
                return price

        # USD/EUR fra AliExpress-snippets — grov omregning ×10 → NOK
        match = re.search(r'(?:US\$|USD|\$|€|EUR)\s*([\d.,]+)', text, re.IGNORECASE)
        if match:
            try:
                foreign = float(match.group(1).replace(",", "."))
                return round(foreign * 10, 2)  # estimert NOK-pris
            except ValueError:
                pass

        return None

    # ---------------------------------------------------------------- #
    #  DuckDuckGo-hjelper                                               #
    # ---------------------------------------------------------------- #

    def _search_duckduckgo(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search DuckDuckGo and return structured results.

        DuckDuckGo fungerer uten CAPTCHA og API-nøkkel — perfekt for
        organisk konkurrentscanning uten å bli blokkert.

        Args:
            query:       Search query (str)
            max_results: Maximum number of results to return (int)

        Returns:
            list of dicts with keys: title, url, snippet
        """
        try:
            raw = DDGS().text(query, max_results=max_results)
            return [
                {
                    "title":   item.get("title", ""),
                    "url":     item.get("href", ""),
                    "snippet": item.get("body", ""),
                }
                for item in (raw or [])
            ]
        except Exception as e:
            print(f"  [DDG] Feil under søk: {e}")
            return []

    # ---------------------------------------------------------------- #
    #  Scraping — tre kilder                                             #
    # ---------------------------------------------------------------- #

    def _search_google_organic(self) -> list[dict]:
        """
        Find competing webshops via DuckDuckGo organic search.

        Organiske søkeresultater viser hvilke Shopify-butikker og nettbutikker
        som ranker på samme søkeord som oss — direkte konkurrenter for SEO og ads.

        Returns:
            list of dicts with keys: source, title, url, price_nok, snippet
        """
        print("  [GOOGLE/DDG] Søker organiske konkurrenter...")
        items   = self._search_duckduckgo(self.keyword, max_results=10)
        results = []

        for item in items:
            results.append({
                "source":    "google",
                "title":     item["title"],
                "url":       item["url"],
                "price_nok": self._extract_price_from_text(item["snippet"]),
                "snippet":   item["snippet"],
            })

        print(f"  [GOOGLE/DDG] {len(results)} resultater")
        return results

    def _scrape_prisjakt(self) -> list[dict]:
        """
        Scrape product listings from prisjakt.no.

        Prisjakt er Norges største prissammenligningstjeneste og gir
        de mest pålitelige norske konkurranseprisene.

        Returns:
            list of dicts with keys: source, title, url, price_nok, snippet
        """
        results = []
        encoded = quote_plus(self.keyword)
        url     = f"https://www.prisjakt.no/search.php?search={encoded}"

        soup = self._fetch(url)
        if soup is None:
            print("  [PRISJAKT] Ingen data hentet")
            return results

        # Prisjakt bruker liste-elementer for produktkort
        products = (
            soup.find_all("li",  class_=lambda c: c and "product" in c.lower()) or
            soup.find_all("div", class_=lambda c: c and "product" in c.lower()) or
            soup.find_all("article")
        )

        for product in products[:10]:
            try:
                # Produktnavn
                name_tag = (
                    product.find("h2") or
                    product.find("h3") or
                    product.find(class_=lambda c: c and "name" in str(c).lower())
                )
                title = name_tag.get_text(strip=True) if name_tag else "Ukjent produkt"
                if len(title) > 80:
                    title = title[:77] + "..."

                # Pris
                price_tag = product.find(
                    class_=lambda c: c and "price" in str(c).lower()
                )
                raw_text  = price_tag.get_text(strip=True) if price_tag else product.get_text()
                price_nok = self._parse_price_nok(raw_text)

                # Fallback: søk etter kr-mønster i all tekst
                if not price_nok:
                    all_text = product.get_text()
                    match    = re.search(r"[\d\s.,]+\s*kr", all_text, re.IGNORECASE)
                    price_nok = self._parse_price_nok(match.group(0)) if match else None

                # URL
                link_tag    = product.find("a", href=True)
                product_url = link_tag["href"] if link_tag else url
                if product_url.startswith("/"):
                    product_url = "https://www.prisjakt.no" + product_url

                snippet = product.get_text(separator=" ", strip=True)[:200]

                if price_nok and price_nok > 0:
                    results.append({
                        "source":    "prisjakt",
                        "title":     title,
                        "url":       product_url,
                        "price_nok": price_nok,
                        "snippet":   snippet,
                    })

            except Exception:
                continue

        print(f"  [PRISJAKT] {len(results)} resultater")
        return results

    def _search_aliexpress(self) -> list[dict]:
        """
        Estimate market sourcing price via DuckDuckGo + AliExpress.

        Søker DuckDuckGo med site:aliexpress.com for å finne leverandørpriser.
        USD-priser i snippets omregnes til estimert NOK (×10).

        Returns:
            list of dicts with keys: source, title, url, price_nok, snippet
        """
        print("  [ALIEXPRESS] Søker sourcing-pris via DDG...")
        query   = f'"{self.keyword}" site:aliexpress.com'
        items   = self._search_duckduckgo(query, max_results=3)
        results = []

        for item in items:
            results.append({
                "source":    "aliexpress",
                "title":     item["title"],
                "url":       item["url"],
                "price_nok": self._extract_price_from_text(item["snippet"]),
                "snippet":   item["snippet"],
            })

        print(f"  [ALIEXPRESS] {len(results)} resultater")
        return results

    # ---------------------------------------------------------------- #
    #  CSV-hjelper                                                       #
    # ---------------------------------------------------------------- #

    def _build_row(self, result: dict) -> dict:
        """
        Build a CSV row dict from a scraped result.

        Beregner prisforskjell og posisjonering hvis prisen er kjent.
        Setter price_difference og we_are_cheaper til None når pris mangler.

        Args:
            result: Dict with keys source, title, url, price_nok, snippet

        Returns:
            dict matching CSV_COLUMNS schema
        """
        price_nok = result.get("price_nok")

        if price_nok is not None:
            price_difference = round(self.our_price - price_nok, 2)
            we_are_cheaper   = self.our_price < price_nok
        else:
            price_difference = None
            we_are_cheaper   = None

        return {
            "timestamp":        datetime.now().isoformat(timespec="seconds"),
            "keyword":          self.keyword,
            "source":           result.get("source", "unknown"),
            "title":            result.get("title", "")[:80],
            "url":              result.get("url", ""),
            "price_nok":        price_nok,
            "snippet":          result.get("snippet", "")[:200],
            "our_price":        self.our_price,
            "our_margin":       round(self.our_margin * 100, 1),
            "price_difference": price_difference,
            "we_are_cheaper":   we_are_cheaper,
        }

    def _append_to_csv(self, rows: list[dict]) -> None:
        """
        Append rows to today's CSV. Never overwrites existing data.

        Args:
            rows: List of row dicts matching CSV_COLUMNS
        """
        if not rows:
            return

        self._ensure_csv_exists()
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerows(rows)

    # ---------------------------------------------------------------- #
    #  Analyse-utskrift                                                  #
    # ---------------------------------------------------------------- #

    def _print_analysis(self, results: list[dict]) -> None:
        """
        Print a market positioning summary after scan.

        Skiller norske priser (google + prisjakt) fra AliExpress-estimater
        og gir en enkel konklusjon om vår prisposisjonering.

        Args:
            results: List of row dicts from scan()
        """
        no_prices  = [
            r["price_nok"] for r in results
            if r.get("source") in ("google", "prisjakt") and r.get("price_nok")
        ]
        ali_prices = [
            r["price_nok"] for r in results
            if r.get("source") == "aliexpress" and r.get("price_nok")
        ]

        print("\n" + "=" * 56)
        print("  KONKURRENTANALYSE")
        print("=" * 56)

        avg_no = None
        if no_prices:
            avg_no = sum(no_prices) / len(no_prices)
            print(f"  Laveste norske pris:   {min(no_prices):>8.0f} NOK")
            print(f"  Høyeste norske pris:   {max(no_prices):>8.0f} NOK")
            print(f"  Snitt norsk pris:      {avg_no:>8.0f} NOK")
        else:
            print("  Ingen norske priser funnet")

        if ali_prices:
            avg_ali = sum(ali_prices) / len(ali_prices)
            print(f"  Est. AliExpress pris:  {avg_ali:>8.0f} NOK  (USD×10, estimat)")
        else:
            print("  Ingen AliExpress-priser funnet")

        print(f"  Vår pris:              {self.our_price:>8.0f} NOK")

        if avg_no:
            diff = self.our_price - avg_no
            if diff < -30:
                conclusion = "VI ER BILLIGST"
            elif diff > 30:
                conclusion = "VI ER DYREST"
            else:
                conclusion = "VI ER PÅ SNITT"
            retning = "billigere" if diff < 0 else "dyrere"
            print(f"\n  KONKLUSJON: {conclusion}")
            print(f"  (vi er {abs(diff):.0f} NOK {retning} enn snitt-konkurrent)")

        print("=" * 56)

    # ---------------------------------------------------------------- #
    #  Offentlige metoder                                                #
    # ---------------------------------------------------------------- #

    def scan(self) -> list[dict]:
        """
        Run full competitor scan across all three sources.

        Kjører:
          1. DuckDuckGo organisk (Google-konkurrenter)
          2. Prisjakt.no (norske prisdata)
          3. AliExpress via DDG (sourcing-estimat)

        Lagrer alle funn til today's CSV og printer analyse.

        Returns:
            list of dicts — same schema as CSV_COLUMNS
        """
        print(f"\nScanner konkurrenter for: '{self.keyword}'")
        print("-" * 50)

        all_results = []

        # Kilde 1: Google organisk via DuckDuckGo
        for item in self._search_google_organic():
            all_results.append(self._build_row(item))

        time.sleep(1)

        # Kilde 2: Prisjakt.no
        for item in self._scrape_prisjakt():
            all_results.append(self._build_row(item))

        time.sleep(1)

        # Kilde 3: AliExpress via DuckDuckGo
        for item in self._search_aliexpress():
            all_results.append(self._build_row(item))

        # Lagre til CSV (append-only)
        self._append_to_csv(all_results)

        with_price = [r for r in all_results if r["price_nok"] is not None]
        print(f"\nTotalt: {len(all_results)} resultater ({len(with_price)} med pris)")

        self._print_analysis(all_results)

        return all_results

    def get_summary(self) -> dict:
        """
        Compute a positioning summary from today's scan data.

        Leser dagens CSV og returnerer aggregert statistikk.
        Skiller norske priser fra AliExpress-estimater.

        Returns:
            dict with keys:
                - keyword, our_price, competitor_count
                - min_price, max_price, avg_price
                - cheaper_than_us, more_expensive_than_us, we_are_cheapest
                - margin_at_avg_price, positioning
                - aliexpress_avg_price (optional, only if data found)
        """
        if not os.path.exists(self.csv_path):
            return {"error": "Ingen data — kjør scan() først"}

        rows = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["keyword"] == self.keyword:
                    rows.append(row)

        if not rows:
            return {"error": f"Ingen data for '{self.keyword}' — kjør scan() først"}

        # Hent kun siste scannerunde (nyeste timestamp)
        last_ts = max(r["timestamp"] for r in rows)
        latest  = [r for r in rows if r["timestamp"] == last_ts]

        no_prices = [
            float(r["price_nok"]) for r in latest
            if r.get("source") in ("google", "prisjakt") and r.get("price_nok")
        ]
        ali_prices = [
            float(r["price_nok"]) for r in latest
            if r.get("source") == "aliexpress" and r.get("price_nok")
        ]

        if not no_prices:
            return {"error": "Ingen gyldige norske priser i siste scan"}

        avg_price   = sum(no_prices) / len(no_prices)
        our_costs   = self.our_price * (1 - self.our_margin)
        margin_at_avg = (avg_price - our_costs) / avg_price if avg_price > 0 else 0.0

        cheaper_than_us = sum(1 for p in no_prices if p < self.our_price)
        more_expensive  = sum(1 for p in no_prices if p >= self.our_price)

        diff = self.our_price - avg_price
        if diff < -30:
            positioning = "VI ER BILLIGST"
        elif diff > 30:
            positioning = "VI ER DYREST"
        else:
            positioning = "VI ER PÅ SNITT"

        summary = {
            "keyword":                self.keyword,
            "our_price":              self.our_price,
            "competitor_count":       len(no_prices),
            "min_price":              round(min(no_prices), 2),
            "max_price":              round(max(no_prices), 2),
            "avg_price":              round(avg_price, 2),
            "cheaper_than_us":        cheaper_than_us,
            "more_expensive_than_us": more_expensive,
            "we_are_cheapest":        self.our_price <= min(no_prices),
            "margin_at_avg_price":    round(margin_at_avg * 100, 1),
            "positioning":            positioning,
        }

        if ali_prices:
            summary["aliexpress_avg_price"] = round(
                sum(ali_prices) / len(ali_prices), 2
            )

        return summary
