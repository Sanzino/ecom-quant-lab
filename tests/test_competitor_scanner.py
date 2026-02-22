"""
Tests for CompetitorScanner.

All HTTP calls are mocked — no real network requests are made.

Run with:
    pytest tests/test_competitor_scanner.py -v

Testscenario:
    juicer bærbar — 349 NOK, 68.4% margin
    Konkurrenter: 299 NOK (billigere), 399 NOK (dyrere), 349 NOK (lik pris)
"""

import csv
import os
import sys
import tempfile
import pytest

from unittest.mock import patch, MagicMock

sys.path.insert(0, 'src')

from competitor_scanner import CompetitorScanner, CSV_PATH, CSV_COLUMNS


# ------------------------------------------------------------------ #
#  Hjelpefunksjoner for mock-respons                                   #
# ------------------------------------------------------------------ #

def _make_response(html: str, status_code: int = 200) -> MagicMock:
    """Lag en falsk requests.Response med gitt HTML og statuskode."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.text        = html
    return mock_resp


FINN_HTML = """
<html><body>
  <article>
    <h2>Bærbar juicer 349kr</h2>
    <span class="price">299 kr</span>
    <a href="/shop/product/1">Se mer</a>
  </article>
  <article>
    <h2>Juicer Premium</h2>
    <span class="price">399 kr</span>
    <a href="/shop/product/2">Se mer</a>
  </article>
</body></html>
"""

GOOGLE_HTML = """
<html><body>
  <div class="sh-dgr__grid-result">
    <h3>Juicer Tilbud</h3>
    <span class="price">349 kr</span>
    <a href="https://example.com/juicer">Kjøp</a>
  </div>
</body></html>
"""

BLOCKED_HTML = ""


# ------------------------------------------------------------------ #
#  Fixture                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def scanner(tmp_path, monkeypatch):
    """
    CompetitorScanner med juicer-produkt.
    Bruker en midlertidig mappe slik at CSV-filen ikke forurenser prosjektet.
    """
    # Pek CSV_PATH til tmp-mappe
    monkeypatch.chdir(tmp_path)
    return CompetitorScanner(
        keyword    = "juicer bærbar",
        our_price  = 349,
        our_margin = 0.684,
    )


@pytest.fixture
def scanner_with_data(scanner):
    """Scanner med forhåndsinnlastet CSV-data (simulerer en tidligere scan)."""
    rows = [
        {
            "timestamp":        "2024-01-15T10:00:00",
            "keyword":          "juicer bærbar",
            "seller":           "Butikk A",
            "price_nok":        299,
            "url":              "https://example.com/a",
            "our_price":        349,
            "our_margin":       68.4,
            "price_difference": 50.0,
            "we_are_cheaper":   False,
        },
        {
            "timestamp":        "2024-01-15T10:00:00",
            "keyword":          "juicer bærbar",
            "seller":           "Butikk B",
            "price_nok":        399,
            "url":              "https://example.com/b",
            "our_price":        349,
            "our_margin":       68.4,
            "price_difference": -50.0,
            "we_are_cheaper":   True,
        },
    ]
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writerows(rows)
    return scanner


# ------------------------------------------------------------------ #
#  TestInit                                                            #
# ------------------------------------------------------------------ #

class TestInit:

    def test_attributes_are_stored(self, scanner):
        assert scanner.keyword    == "juicer bærbar"
        assert scanner.our_price  == 349
        assert scanner.our_margin == 0.684

    def test_csv_file_is_created_with_header(self, scanner):
        assert os.path.exists(CSV_PATH)
        with open(CSV_PATH, "r") as f:
            header = f.readline().strip()
        assert "timestamp" in header
        assert "price_nok" in header
        assert "we_are_cheaper" in header

    def test_data_directory_is_created(self, scanner):
        assert os.path.isdir("data")


# ------------------------------------------------------------------ #
#  TestParsePriceNok                                                   #
# ------------------------------------------------------------------ #

class TestParsePriceNok:

    def test_simple_integer(self, scanner):
        assert scanner._parse_price_nok("349 kr") == 349.0

    def test_thousand_separator_dot(self, scanner):
        # Norsk tusenskilletegn: 1.299 kr
        assert scanner._parse_price_nok("1.299 kr") == 1299.0

    def test_decimal_comma(self, scanner):
        assert scanner._parse_price_nok("349,00 kr") == 349.0

    def test_dot_and_comma_combined(self, scanner):
        # 1.299,99 → 1299.99
        assert scanner._parse_price_nok("1.299,99") == pytest.approx(1299.99)

    def test_nok_prefix(self, scanner):
        assert scanner._parse_price_nok("NOK 799") == 799.0

    def test_dash_suffix(self, scanner):
        # "499,-" format
        result = scanner._parse_price_nok("499,-")
        assert result == pytest.approx(499.0, abs=1)

    def test_empty_string_returns_none(self, scanner):
        assert scanner._parse_price_nok("") is None

    def test_no_digits_returns_none(self, scanner):
        assert scanner._parse_price_nok("ukjent pris") is None


# ------------------------------------------------------------------ #
#  TestFetch                                                           #
# ------------------------------------------------------------------ #

class TestFetch:

    @patch("competitor_scanner.requests.get")
    def test_successful_fetch_returns_soup(self, mock_get, scanner):
        mock_get.return_value = _make_response("<html><body>OK</body></html>")
        soup = scanner._fetch("https://example.com")
        assert soup is not None
        assert soup.find("body") is not None

    @patch("competitor_scanner.requests.get")
    def test_blocked_403_returns_none(self, mock_get, scanner):
        mock_get.return_value = _make_response("", status_code=403)
        result = scanner._fetch("https://example.com")
        assert result is None

    @patch("competitor_scanner.requests.get")
    def test_blocked_429_returns_none(self, mock_get, scanner):
        mock_get.return_value = _make_response("", status_code=429)
        result = scanner._fetch("https://example.com")
        assert result is None

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    def test_network_error_retries_and_returns_none(self, mock_get, mock_sleep, scanner):
        import requests as req
        mock_get.side_effect = req.RequestException("timeout")
        result = scanner._fetch("https://example.com")
        assert result is None
        # Skal ha prøvd 3 ganger → 2 pauser mellom forsøkene
        assert mock_get.call_count == 3


# ------------------------------------------------------------------ #
#  TestScrapeFinn                                                       #
# ------------------------------------------------------------------ #

class TestScrapeFinn:

    @patch("competitor_scanner.requests.get")
    def test_returns_list_of_dicts(self, mock_get, scanner):
        mock_get.return_value = _make_response(FINN_HTML)
        results = scanner._scrape_finn()
        assert isinstance(results, list)

    @patch("competitor_scanner.requests.get")
    def test_extracts_prices(self, mock_get, scanner):
        mock_get.return_value = _make_response(FINN_HTML)
        results = scanner._scrape_finn()
        prices = [r["price_nok"] for r in results]
        assert 299.0 in prices
        assert 399.0 in prices

    @patch("competitor_scanner.requests.get")
    def test_blocked_returns_empty_list(self, mock_get, scanner):
        mock_get.return_value = _make_response("", status_code=403)
        results = scanner._scrape_finn()
        assert results == []

    @patch("competitor_scanner.requests.get")
    def test_finn_url_contains_keyword(self, mock_get, scanner):
        mock_get.return_value = _make_response(FINN_HTML)
        scanner._scrape_finn()
        called_url = mock_get.call_args[0][0]
        assert "finn.no" in called_url
        assert "juicer" in called_url


# ------------------------------------------------------------------ #
#  TestScrapeGoogleShopping                                            #
# ------------------------------------------------------------------ #

class TestScrapeGoogleShopping:

    @patch("competitor_scanner.requests.get")
    def test_returns_list_of_dicts(self, mock_get, scanner):
        mock_get.return_value = _make_response(GOOGLE_HTML)
        results = scanner._scrape_google_shopping()
        assert isinstance(results, list)

    @patch("competitor_scanner.requests.get")
    def test_captcha_returns_empty_list(self, mock_get, scanner):
        captcha_html = "<html><body>unusual traffic from your computer</body></html>"
        mock_get.return_value = _make_response(captcha_html)
        results = scanner._scrape_google_shopping()
        assert results == []

    @patch("competitor_scanner.requests.get")
    def test_google_url_contains_tbm_shop(self, mock_get, scanner):
        mock_get.return_value = _make_response(GOOGLE_HTML)
        scanner._scrape_google_shopping()
        called_url = mock_get.call_args[0][0]
        assert "tbm=shop" in called_url


# ------------------------------------------------------------------ #
#  TestBuildRow                                                         #
# ------------------------------------------------------------------ #

class TestBuildRow:

    def test_contains_all_csv_columns(self, scanner):
        row = scanner._build_row({"seller": "Test", "price_nok": 299.0, "url": "https://x.com"})
        for col in CSV_COLUMNS:
            assert col in row

    def test_price_difference_positive_when_competitor_is_cheaper(self, scanner):
        # Konkurrent: 299, vi: 349 → differanse +50 (vi er dyrere)
        row = scanner._build_row({"seller": "Billig", "price_nok": 299.0, "url": ""})
        assert row["price_difference"] == pytest.approx(50.0)
        assert row["we_are_cheaper"] is False

    def test_price_difference_negative_when_we_are_cheaper(self, scanner):
        # Konkurrent: 499, vi: 349 → differanse -150 (vi er billigere)
        row = scanner._build_row({"seller": "Dyr", "price_nok": 499.0, "url": ""})
        assert row["price_difference"] == pytest.approx(-150.0)
        assert row["we_are_cheaper"] is True

    def test_our_margin_stored_as_percent(self, scanner):
        row = scanner._build_row({"seller": "X", "price_nok": 350.0, "url": ""})
        # 0.684 → lagres som 68.4
        assert row["our_margin"] == pytest.approx(68.4, abs=0.1)

    def test_keyword_is_preserved(self, scanner):
        row = scanner._build_row({"seller": "X", "price_nok": 350.0, "url": ""})
        assert row["keyword"] == "juicer bærbar"


# ------------------------------------------------------------------ #
#  TestAppendToCsv                                                      #
# ------------------------------------------------------------------ #

class TestAppendToCsv:

    def test_rows_are_appended(self, scanner):
        row1 = scanner._build_row({"seller": "A", "price_nok": 299.0, "url": ""})
        row2 = scanner._build_row({"seller": "B", "price_nok": 399.0, "url": ""})
        scanner._append_to_csv([row1, row2])

        with open(CSV_PATH, "r") as f:
            content = f.read()

        assert "A" in content
        assert "B" in content

    def test_existing_data_is_not_overwritten(self, scanner_with_data):
        # Filen har allerede 2 rader fra fixture
        new_row = scanner_with_data._build_row({"seller": "Ny", "price_nok": 499.0, "url": ""})
        scanner_with_data._append_to_csv([new_row])

        with open(CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            rows   = list(reader)

        sellers = [r["seller"] for r in rows]
        assert "Butikk A" in sellers   # gammel data bevart
        assert "Butikk B" in sellers   # gammel data bevart
        assert "Ny"       in sellers   # ny rad lagt til

    def test_empty_list_does_nothing(self, scanner):
        before = os.path.getsize(CSV_PATH)
        scanner._append_to_csv([])
        after  = os.path.getsize(CSV_PATH)
        assert before == after


# ------------------------------------------------------------------ #
#  TestScan                                                             #
# ------------------------------------------------------------------ #

class TestScan:

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    def test_scan_returns_list(self, mock_get, mock_sleep, scanner):
        mock_get.return_value = _make_response(FINN_HTML)
        results = scanner.scan()
        assert isinstance(results, list)

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    def test_scan_writes_to_csv(self, mock_get, mock_sleep, scanner):
        mock_get.return_value = _make_response(FINN_HTML)
        scanner.scan()

        with open(CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            rows   = list(reader)

        # Finn-HTML har 2 produkter med pris
        assert len(rows) >= 2

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    def test_scan_graceful_on_blocked_sources(self, mock_get, mock_sleep, scanner):
        # Begge kildene er blokkert
        mock_get.return_value = _make_response("", status_code=403)
        results = scanner.scan()
        assert results == []

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    def test_second_scan_appends_not_overwrites(self, mock_get, mock_sleep, scanner):
        mock_get.return_value = _make_response(FINN_HTML)
        scanner.scan()
        scanner.scan()

        with open(CSV_PATH, "r") as f:
            reader = csv.DictReader(f)
            rows   = list(reader)

        # To scanner × 2 Finn-produkter = minimum 4 rader
        assert len(rows) >= 4


# ------------------------------------------------------------------ #
#  TestGetSummary                                                       #
# ------------------------------------------------------------------ #

class TestGetSummary:

    def test_no_data_returns_error(self, scanner):
        result = scanner.get_summary()
        assert "error" in result

    def test_wrong_keyword_returns_error(self, scanner_with_data):
        other = CompetitorScanner("kaffetrakter", 799, 0.573)
        result = other.get_summary()
        assert "error" in result

    def test_summary_contains_required_keys(self, scanner_with_data):
        summary = scanner_with_data.get_summary()
        for key in [
            "keyword", "our_price", "competitor_count",
            "min_price", "max_price", "avg_price",
            "cheaper_than_us", "more_expensive_than_us",
            "we_are_cheapest", "margin_at_avg_price",
        ]:
            assert key in summary

    def test_min_max_are_correct(self, scanner_with_data):
        summary = scanner_with_data.get_summary()
        assert summary["min_price"] == pytest.approx(299.0)
        assert summary["max_price"] == pytest.approx(399.0)

    def test_avg_price_is_correct(self, scanner_with_data):
        # (299 + 399) / 2 = 349
        summary = scanner_with_data.get_summary()
        assert summary["avg_price"] == pytest.approx(349.0)

    def test_positioning_counts(self, scanner_with_data):
        # Konkurrent A (299) er billigere enn oss (349)
        # Konkurrent B (399) er dyrere enn oss
        summary = scanner_with_data.get_summary()
        assert summary["cheaper_than_us"]        == 1
        assert summary["more_expensive_than_us"] == 1

    def test_we_are_cheapest_is_false_when_competitor_is_cheaper(self, scanner_with_data):
        # Konkurrent A selger for 299, vi for 349 → vi er IKKE billigst
        summary = scanner_with_data.get_summary()
        assert summary["we_are_cheapest"] is False

    def test_margin_at_avg_price_is_reasonable(self, scanner_with_data):
        # Avg = 349, vår pris = 349 → margin bør være lik vår margin
        summary = scanner_with_data.get_summary()
        # Margin ved 349 = (349 - kostnader) / 349
        # Kostnader = 349 * (1 - 0.684) = 110.3
        # Margin = (349 - 110.3) / 349 ≈ 68.4%
        assert summary["margin_at_avg_price"] == pytest.approx(68.4, abs=0.5)


# ------------------------------------------------------------------ #
#  TestReusability                                                      #
# ------------------------------------------------------------------ #

class TestReusability:

    def test_two_scanners_with_different_keywords(self, tmp_path, monkeypatch):
        """To ulike scannere kan bruke samme CSV uten å blande data."""
        monkeypatch.chdir(tmp_path)

        scanner_a = CompetitorScanner("juicer", 349, 0.684)
        scanner_b = CompetitorScanner("kaffetrakter", 799, 0.573)

        row_a = scanner_a._build_row({"seller": "A", "price_nok": 299.0, "url": ""})
        row_b = scanner_b._build_row({"seller": "B", "price_nok": 750.0, "url": ""})

        scanner_a._append_to_csv([row_a])
        scanner_b._append_to_csv([row_b])

        # get_summary filtrerer på keyword — ingen blanding
        summary_a = scanner_a.get_summary()
        summary_b = scanner_b.get_summary()

        assert summary_a["keyword"] == "juicer"
        assert summary_b["keyword"] == "kaffetrakter"
        assert summary_a["avg_price"] == pytest.approx(299.0)
        assert summary_b["avg_price"] == pytest.approx(750.0)

    def test_our_price_and_margin_stored_correctly(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        scanner = CompetitorScanner("testprodukt", 500, 0.50)
        row = scanner._build_row({"seller": "X", "price_nok": 450.0, "url": ""})
        assert row["our_price"]  == 500
        assert row["our_margin"] == pytest.approx(50.0)
