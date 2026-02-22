"""
Competitor price scanner for Norwegian e-commerce products.

Scrapes finn.no/shop and Google Shopping Norway to track competitor
pricing and compare against our own product economics.
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

CSV_PATH = "data/competitor_data.csv"

CSV_COLUMNS = [
    "timestamp", "keyword", "seller", "price_nok", "url",
    "our_price", "our_margin", "price_difference", "we_are_cheaper",
]

RETRY_ATTEMPTS = 3
RETRY_DELAY    = 2   # sekunder mellom forsøk


# ------------------------------------------------------------------ #
#  Klasse                                                              #
# ------------------------------------------------------------------ #

class CompetitorScanner:
    """
    Scan competitor prices from finn.no and Google Shopping Norway.

    Compares competitor prices against our own product economics and
    appends all findings to a CSV file for historical price tracking.

    Usage:
        >>> scanner = CompetitorScanner("juicer bærbar", our_price=349, our_margin=0.684)
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

        # Opprett data-mappe hvis den ikke finnes ennå
        os.makedirs("data", exist_ok=True)

        # Skriv CSV-header hvis filen er ny
        if not os.path.exists(CSV_PATH):
            with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()

    # ---------------------------------------------------------------- #
    #  HTTP-hjelper                                                      #
    # ---------------------------------------------------------------- #

    def _get_headers(self) -> dict:
        """
        Build HTTP request headers with a randomly chosen user-agent.

        Roterer brukeragenter for å redusere sjansen for blokkering.

        Returns:
            dict: HTTP headers
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
        Returnerer None — krasjer aldri — slik at en blokkert kilde
        ikke stopper scanning fra andre kilder.

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

                # Blokkert av nettstedet
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

        # Behold bare sifre, komma og punktum
        cleaned = re.sub(r"[^\d.,]", "", price_text)

        if not cleaned:
            return None

        # Norsk format: 1.299,00 → fjern tusenskilletegn, konverter desimalkomma
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            parts = cleaned.split(",")
            # Desimalkomma: "349,00" → to desimaler etter komma
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                # Tusenskilletegn: "1,299" → fjern komma
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

    # ---------------------------------------------------------------- #
    #  Scraping                                                          #
    # ---------------------------------------------------------------- #

    def _scrape_finn(self) -> list[dict]:
        """
        Scrape product listings from finn.no/shop.

        Finn.no er Norges største markedsplass og gir relevant
        prisdata for norske forbrukere.

        Returns:
            list of dicts with keys: seller, price_nok, url
        """
        results  = []
        encoded  = quote_plus(self.keyword)
        url      = f"https://www.finn.no/shop/search.html?q={encoded}"

        soup = self._fetch(url)
        if soup is None:
            print("  [FINN] Ingen data hentet")
            return results

        # finn.no bruker <article>-elementer for produktkort
        articles = soup.find_all("article")

        # Fallback: søk etter div med produktrelaterte klasser
        if not articles:
            articles = soup.find_all(
                "div",
                class_=lambda c: c and "product" in c.lower(),
            )

        for article in articles[:10]:
            try:
                # Produktnavn / selger
                name_tag = (
                    article.find("h2") or
                    article.find("h3") or
                    article.find(class_=lambda c: c and "title" in str(c).lower())
                )
                seller = name_tag.get_text(strip=True) if name_tag else "Ukjent selger"
                if len(seller) > 80:
                    seller = seller[:77] + "..."

                # Pris
                price_tag = article.find(
                    class_=lambda c: c and "price" in str(c).lower()
                )
                if price_tag:
                    price_nok = self._parse_price_nok(price_tag.get_text(strip=True))
                else:
                    # Fallback: søk etter "kr" i teksten
                    raw = article.get_text()
                    match = re.search(r"[\d\s.,]+\s*kr", raw, re.IGNORECASE)
                    price_nok = self._parse_price_nok(match.group(0)) if match else None

                # URL til produktsiden
                link_tag    = article.find("a", href=True)
                product_url = link_tag["href"] if link_tag else url
                if product_url.startswith("/"):
                    product_url = "https://www.finn.no" + product_url

                if price_nok and price_nok > 0:
                    results.append({
                        "seller":    seller,
                        "price_nok": price_nok,
                        "url":       product_url,
                    })

            except Exception:
                # Én ugyldig artikkel stopper ikke hele scanningen
                continue

        print(f"  [FINN] Fant {len(results)} resultater")
        return results

    def _scrape_google_shopping(self) -> list[dict]:
        """
        Scrape product listings from Google Shopping Norway.

        Bruker Google Shopping (tbm=shop) med norsk lokalisering (hl=no&gl=no).
        Google blokkerer scraping aggressivt — returnerer tom liste ved CAPTCHA.

        Returns:
            list of dicts with keys: seller, price_nok, url
        """
        results = []
        encoded = quote_plus(self.keyword)
        url     = f"https://www.google.no/search?q={encoded}&tbm=shop&hl=no&gl=no"

        soup = self._fetch(url)
        if soup is None:
            print("  [GOOGLE] Ingen data hentet")
            return results

        # Google sender CAPTCHA ved mistenkt bot-trafikk
        page_text = soup.get_text().lower()
        if soup.find(id="recaptcha") or "unusual traffic" in page_text:
            print("  [GOOGLE] CAPTCHA-svar mottatt — blokkert")
            return results

        # Google Shopping bruker gridresultat-divs
        product_divs = (
            soup.find_all("div", class_="sh-dgr__grid-result") or
            soup.find_all("div", attrs={"data-sh-or": True}) or
            soup.find_all("div", class_="g")
        )

        for div in product_divs[:10]:
            try:
                # Produktnavn
                name_tag = (
                    div.find("h3") or
                    div.find("h4") or
                    div.find(class_=lambda c: c and "title" in str(c).lower())
                )
                seller = name_tag.get_text(strip=True) if name_tag else "Ukjent selger"
                if len(seller) > 80:
                    seller = seller[:77] + "..."

                # Pris
                price_tag = div.find(
                    class_=lambda c: c and "price" in str(c).lower()
                )
                if price_tag:
                    price_nok = self._parse_price_nok(price_tag.get_text(strip=True))
                else:
                    raw   = div.get_text()
                    match = re.search(r"[\d\s.,]+\s*kr", raw, re.IGNORECASE)
                    price_nok = self._parse_price_nok(match.group(0)) if match else None

                # URL
                link_tag    = div.find("a", href=True)
                product_url = link_tag["href"] if link_tag else url

                if price_nok and price_nok > 0:
                    results.append({
                        "seller":    seller,
                        "price_nok": price_nok,
                        "url":       product_url,
                    })

            except Exception:
                continue

        print(f"  [GOOGLE] Fant {len(results)} resultater")
        return results

    # ---------------------------------------------------------------- #
    #  CSV-hjelper                                                       #
    # ---------------------------------------------------------------- #

    def _build_row(self, result: dict) -> dict:
        """
        Build a CSV row dict from a scraped product result.

        Beregner prisforskjell og posisjonering mot egne priser.

        Args:
            result: Dict with keys seller, price_nok, url

        Returns:
            dict matching CSV_COLUMNS schema
        """
        price_nok        = result["price_nok"]
        price_difference = round(self.our_price - price_nok, 2)
        we_are_cheaper   = self.our_price < price_nok

        return {
            "timestamp":        datetime.now().isoformat(timespec="seconds"),
            "keyword":          self.keyword,
            "seller":           result.get("seller", "Ukjent"),
            "price_nok":        price_nok,
            "url":              result.get("url", ""),
            "our_price":        self.our_price,
            "our_margin":       round(self.our_margin * 100, 1),  # lagres som %-tall
            "price_difference": price_difference,
            "we_are_cheaper":   we_are_cheaper,
        }

    def _append_to_csv(self, rows: list[dict]) -> None:
        """
        Append rows to the CSV file. Never overwrites existing data.

        Historiske prisdata er verdifulle — vi legger alltid til,
        sletter aldri. Lar deg se prisutviklingen over tid.

        Args:
            rows: List of row dicts matching CSV_COLUMNS
        """
        if not rows:
            return

        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerows(rows)

    # ---------------------------------------------------------------- #
    #  Offentlige metoder                                                #
    # ---------------------------------------------------------------- #

    def scan(self) -> list[dict]:
        """
        Run full competitor scan across all sources.

        Scraper finn.no og Google Shopping, lagrer alle funn til CSV,
        og returnerer listen med konkurransedata.

        Returns:
            list of dicts — same schema as CSV_COLUMNS
        """
        print(f"\nScanner konkurrenter for: '{self.keyword}'")
        print("-" * 50)

        all_results = []

        # Kilde 1: finn.no
        for item in self._scrape_finn():
            all_results.append(self._build_row(item))

        # Liten pause mellom kildene — høflig mot serverne
        time.sleep(1)

        # Kilde 2: Google Shopping
        for item in self._scrape_google_shopping():
            all_results.append(self._build_row(item))

        # Lagre til CSV (append-only)
        self._append_to_csv(all_results)

        print(f"\nTotalt: {len(all_results)} konkurrenter funnet")
        if all_results:
            prices = [r["price_nok"] for r in all_results]
            print(f"Prisintervall: {min(prices):.0f} – {max(prices):.0f} NOK")

        return all_results

    def get_summary(self) -> dict:
        """
        Compute a positioning summary from the most recent scan.

        Leser CSV-filen og returnerer aggregert statistikk for den
        siste scannebølgen. Inkluderer hva vår margin ville vært
        om vi hadde priset oss på konkurrentens gjennomsnittspris.

        Returns:
            dict with keys:
                - keyword:                Our search keyword
                - our_price:              Our sale price (NOK)
                - competitor_count:       Number of competitors in latest scan
                - min_price:              Cheapest competitor (NOK)
                - max_price:              Most expensive competitor (NOK)
                - avg_price:              Average competitor price (NOK)
                - cheaper_than_us:        Count of competitors cheaper than us
                - more_expensive_than_us: Count of competitors more expensive
                - we_are_cheapest:        True if our price beats all competitors
                - margin_at_avg_price:    Our margin % if we matched avg price
        """
        if not os.path.exists(CSV_PATH):
            return {"error": "Ingen data — kjør scan() først"}

        # Les alle rader for dette søkeordet
        rows = []
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["keyword"] == self.keyword:
                    rows.append(row)

        if not rows:
            return {"error": f"Ingen data for '{self.keyword}' — kjør scan() først"}

        # Hent kun den siste scannerunden (nyeste timestamp)
        last_ts = max(r["timestamp"] for r in rows)
        latest  = [r for r in rows if r["timestamp"] == last_ts]

        prices = [float(r["price_nok"]) for r in latest]
        if not prices:
            return {"error": "Ingen gyldige priser i siste scan"}

        avg_price = sum(prices) / len(prices)

        # Hva ville vår margin vært om vi matchet gjennomsnittsprisen?
        # Våre kostnader = our_price × (1 - our_margin)
        our_costs           = self.our_price * (1 - self.our_margin)
        margin_at_avg_price = (avg_price - our_costs) / avg_price if avg_price > 0 else 0.0

        cheaper_than_us = sum(1 for p in prices if p < self.our_price)
        more_expensive  = sum(1 for p in prices if p >= self.our_price)

        return {
            "keyword":                self.keyword,
            "our_price":              self.our_price,
            "competitor_count":       len(prices),
            "min_price":              round(min(prices), 2),
            "max_price":              round(max(prices), 2),
            "avg_price":              round(avg_price, 2),
            "cheaper_than_us":        cheaper_than_us,
            "more_expensive_than_us": more_expensive,
            "we_are_cheapest":        self.our_price <= min(prices),
            "margin_at_avg_price":    round(margin_at_avg_price * 100, 1),
        }
