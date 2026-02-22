"""
Tests for CompetitorScanner (DuckDuckGo + Prisjakt + AliExpress).

All external calls are mocked — no real network requests are made.

Run with:
    pytest tests/test_competitor_scanner.py -v

Testscenario:
    elektrisk juicemaskin bærbar — 349 NOK, 68.4% margin
"""

import csv
import os
import sys
import pytest

from unittest.mock import patch, MagicMock

sys.path.insert(0, 'src')

from competitor_scanner import CompetitorScanner, CSV_COLUMNS


# ------------------------------------------------------------------ #
#  Mock-data                                                           #
# ------------------------------------------------------------------ #

DDG_RESULTS = [
    {"title": "Juicer på nett",  "href": "https://nettbutikk.no/juicer",  "body": "Kjøp juicer for 299 kr"},
    {"title": "Juicer Premium",  "href": "https://premium.no/juicer",     "body": "Fra 399 kr"},
    {"title": "Juicer tilbud",   "href": "https://tilbud.no/juicer",      "body": "Nå kun 319 kr"},
]

DDG_ALIEXPRESS_RESULTS = [
    {"title": "Portable juicer AliExpress", "href": "https://aliexpress.com/item/1", "body": "US$4.99 fast shipping"},
    {"title": "Mini juicer",                "href": "https://aliexpress.com/item/2", "body": "USD 6.50 free shipping"},
]

PRISJAKT_HTML = """
<html><body>
  <li class="product-list-item">
    <h2>Bærbar juicer 2L</h2>
    <span class="price">329 kr</span>
    <a href="/produkt/juicer-2l">Se pris</a>
  </li>
  <li class="product-list-item">
    <h2>Elektrisk Juicer Pro</h2>
    <span class="price">419 kr</span>
    <a href="/produkt/juicer-pro">Se pris</a>
  </li>
</body></html>
"""

PRISJAKT_BLOCKED_HTML = ""


def _make_response(html: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text        = html
    return mock


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def scanner(tmp_path, monkeypatch):
    """
    CompetitorScanner med juicer-produkt.
    Bruker midlertidig mappe for å isolere CSV-filer fra prosjektet.
    """
    monkeypatch.chdir(tmp_path)
    return CompetitorScanner(
        keyword    = "elektrisk juicemaskin bærbar",
        our_price  = 349,
        our_margin = 0.684,
    )


@pytest.fixture
def scanner_with_data(scanner):
    """Scanner med forhåndsinnlastet CSV-data (simulerer en tidligere scan)."""
    rows = [
        {
            "timestamp":        "2024-01-15T10:00:00",
            "keyword":          "elektrisk juicemaskin bærbar",
            "source":           "google",
            "title":            "Juicer nettbutikk",
            "url":              "https://example.com/a",
            "price_nok":        299,
            "snippet":          "kjøp juicer",
            "our_price":        349,
            "our_margin":       68.4,
            "price_difference": 50.0,
            "we_are_cheaper":   False,
        },
        {
            "timestamp":        "2024-01-15T10:00:00",
            "keyword":          "elektrisk juicemaskin bærbar",
            "source":           "prisjakt",
            "title":            "Butikk B juicer",
            "url":              "https://prisjakt.no/b",
            "price_nok":        399,
            "snippet":          "399 kr fri frakt",
            "our_price":        349,
            "our_margin":       68.4,
            "price_difference": -50.0,
            "we_are_cheaper":   True,
        },
        {
            "timestamp":        "2024-01-15T10:00:00",
            "keyword":          "elektrisk juicemaskin bærbar",
            "source":           "aliexpress",
            "title":            "Mini juicer Ali",
            "url":              "https://aliexpress.com/1",
            "price_nok":        50,
            "snippet":          "US$5.00",
            "our_price":        349,
            "our_margin":       68.4,
            "price_difference": 299.0,
            "we_are_cheaper":   False,
        },
    ]
    with open(scanner.csv_path, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerows(rows)
    return scanner


# ------------------------------------------------------------------ #
#  TestInit                                                            #
# ------------------------------------------------------------------ #

class TestInit:

    def test_attributes_are_stored(self, scanner):
        assert scanner.keyword    == "elektrisk juicemaskin bærbar"
        assert scanner.our_price  == 349
        assert scanner.our_margin == 0.684

    def test_csv_file_is_created_with_header(self, scanner):
        assert os.path.exists(scanner.csv_path)
        with open(scanner.csv_path) as f:
            header = f.readline().strip()
        assert "timestamp" in header
        assert "source"    in header
        assert "price_nok" in header
        assert "snippet"   in header

    def test_data_directory_is_created(self, scanner):
        assert os.path.isdir("data")

    def test_csv_path_contains_todays_date(self, scanner):
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in scanner.csv_path

    def test_csv_path_is_date_based_filename(self, scanner):
        assert "competitor_scan_" in scanner.csv_path
        assert scanner.csv_path.endswith(".csv")


# ------------------------------------------------------------------ #
#  TestParsePriceNok                                                   #
# ------------------------------------------------------------------ #

class TestParsePriceNok:

    def test_simple_integer(self, scanner):
        assert scanner._parse_price_nok("349 kr") == 349.0

    def test_thousand_separator_dot(self, scanner):
        assert scanner._parse_price_nok("1.299 kr") == 1299.0

    def test_decimal_comma(self, scanner):
        assert scanner._parse_price_nok("349,00 kr") == 349.0

    def test_dot_and_comma_combined(self, scanner):
        assert scanner._parse_price_nok("1.299,99") == pytest.approx(1299.99)

    def test_nok_prefix(self, scanner):
        assert scanner._parse_price_nok("NOK 799") == 799.0

    def test_dash_suffix(self, scanner):
        result = scanner._parse_price_nok("499,-")
        assert result == pytest.approx(499.0, abs=1)

    def test_empty_string_returns_none(self, scanner):
        assert scanner._parse_price_nok("") is None

    def test_no_digits_returns_none(self, scanner):
        assert scanner._parse_price_nok("ukjent pris") is None


# ------------------------------------------------------------------ #
#  TestExtractPriceFromText                                            #
# ------------------------------------------------------------------ #

class TestExtractPriceFromText:

    def test_extracts_kr_price(self, scanner):
        assert scanner._extract_price_from_text("Kjøp nå for 299 kr") == 299.0

    def test_extracts_kr_prefix(self, scanner):
        assert scanner._extract_price_from_text("kr 349 inkl frakt") == 349.0

    def test_converts_usd_to_nok(self, scanner):
        # USD 5.00 × 10 = 50.0 NOK
        result = scanner._extract_price_from_text("US$5.00 fast shipping")
        assert result == pytest.approx(50.0, abs=1)

    def test_converts_dollar_sign(self, scanner):
        result = scanner._extract_price_from_text("only $4.99")
        assert result == pytest.approx(49.9, abs=1)

    def test_none_on_no_price(self, scanner):
        assert scanner._extract_price_from_text("great product, buy now") is None

    def test_none_on_empty(self, scanner):
        assert scanner._extract_price_from_text("") is None


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
        assert scanner._fetch("https://example.com") is None

    @patch("competitor_scanner.requests.get")
    def test_blocked_429_returns_none(self, mock_get, scanner):
        mock_get.return_value = _make_response("", status_code=429)
        assert scanner._fetch("https://example.com") is None

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    def test_network_error_retries_3_times(self, mock_get, mock_sleep, scanner):
        import requests as req
        mock_get.side_effect = req.RequestException("timeout")
        assert scanner._fetch("https://example.com") is None
        assert mock_get.call_count == 3


# ------------------------------------------------------------------ #
#  TestSearchDuckDuckGo                                                #
# ------------------------------------------------------------------ #

class TestSearchDuckDuckGo:

    @patch("competitor_scanner.DDGS")
    def test_returns_list_of_dicts(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_RESULTS
        results = scanner._search_duckduckgo("juicer")
        assert isinstance(results, list)

    @patch("competitor_scanner.DDGS")
    def test_maps_keys_correctly(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_RESULTS[:1]
        results = scanner._search_duckduckgo("juicer")
        assert results[0]["title"]   == "Juicer på nett"
        assert results[0]["url"]     == "https://nettbutikk.no/juicer"
        assert results[0]["snippet"] == "Kjøp juicer for 299 kr"

    @patch("competitor_scanner.DDGS")
    def test_exception_returns_empty_list(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.side_effect = Exception("network error")
        results = scanner._search_duckduckgo("juicer")
        assert results == []

    @patch("competitor_scanner.DDGS")
    def test_none_response_returns_empty_list(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = None
        results = scanner._search_duckduckgo("juicer")
        assert results == []


# ------------------------------------------------------------------ #
#  TestSearchGoogleOrganic                                             #
# ------------------------------------------------------------------ #

class TestSearchGoogleOrganic:

    @patch("competitor_scanner.DDGS")
    def test_returns_list(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_RESULTS
        results = scanner._search_google_organic()
        assert isinstance(results, list)
        assert len(results) == len(DDG_RESULTS)

    @patch("competitor_scanner.DDGS")
    def test_source_is_google(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_RESULTS
        results = scanner._search_google_organic()
        assert all(r["source"] == "google" for r in results)

    @patch("competitor_scanner.DDGS")
    def test_extracts_price_from_snippet(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_RESULTS[:1]
        results = scanner._search_google_organic()
        # Snippet inneholder "299 kr"
        assert results[0]["price_nok"] == 299.0

    @patch("competitor_scanner.DDGS")
    def test_ddg_error_returns_empty_list(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.side_effect = Exception("blocked")
        results = scanner._search_google_organic()
        assert results == []


# ------------------------------------------------------------------ #
#  TestScrapePrisjakt                                                  #
# ------------------------------------------------------------------ #

class TestScrapePrisjakt:

    @patch("competitor_scanner.requests.get")
    def test_returns_list_of_dicts(self, mock_get, scanner):
        mock_get.return_value = _make_response(PRISJAKT_HTML)
        results = scanner._scrape_prisjakt()
        assert isinstance(results, list)

    @patch("competitor_scanner.requests.get")
    def test_extracts_prices(self, mock_get, scanner):
        mock_get.return_value = _make_response(PRISJAKT_HTML)
        results = scanner._scrape_prisjakt()
        prices = [r["price_nok"] for r in results]
        assert 329.0 in prices
        assert 419.0 in prices

    @patch("competitor_scanner.requests.get")
    def test_source_is_prisjakt(self, mock_get, scanner):
        mock_get.return_value = _make_response(PRISJAKT_HTML)
        results = scanner._scrape_prisjakt()
        assert all(r["source"] == "prisjakt" for r in results)

    @patch("competitor_scanner.requests.get")
    def test_blocked_returns_empty_list(self, mock_get, scanner):
        mock_get.return_value = _make_response("", status_code=403)
        assert scanner._scrape_prisjakt() == []

    @patch("competitor_scanner.requests.get")
    def test_prisjakt_url_is_correct(self, mock_get, scanner):
        mock_get.return_value = _make_response(PRISJAKT_HTML)
        scanner._scrape_prisjakt()
        called_url = mock_get.call_args[0][0]
        assert "prisjakt.no" in called_url
        assert "juicemaskin" in called_url


# ------------------------------------------------------------------ #
#  TestSearchAliExpress                                                #
# ------------------------------------------------------------------ #

class TestSearchAliExpress:

    @patch("competitor_scanner.DDGS")
    def test_returns_list(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_ALIEXPRESS_RESULTS
        results = scanner._search_aliexpress()
        assert isinstance(results, list)

    @patch("competitor_scanner.DDGS")
    def test_source_is_aliexpress(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_ALIEXPRESS_RESULTS
        results = scanner._search_aliexpress()
        assert all(r["source"] == "aliexpress" for r in results)

    @patch("competitor_scanner.DDGS")
    def test_extracts_usd_price_from_snippet(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = DDG_ALIEXPRESS_RESULTS[:1]
        results = scanner._search_aliexpress()
        # "US$4.99" → ~49.9 NOK
        assert results[0]["price_nok"] == pytest.approx(49.9, abs=1)

    @patch("competitor_scanner.DDGS")
    def test_query_includes_site_aliexpress(self, mock_ddgs, scanner):
        mock_ddgs.return_value.text.return_value = []
        scanner._search_aliexpress()
        called_query = mock_ddgs.return_value.text.call_args[0][0]
        assert "aliexpress.com" in called_query


# ------------------------------------------------------------------ #
#  TestBuildRow                                                        #
# ------------------------------------------------------------------ #

class TestBuildRow:

    def _sample_result(self, source="google", price=299.0):
        return {
            "source":    source,
            "title":     "Test juicer",
            "url":       "https://example.com",
            "price_nok": price,
            "snippet":   "Kjøp nå",
        }

    def test_contains_all_csv_columns(self, scanner):
        row = scanner._build_row(self._sample_result())
        for col in CSV_COLUMNS:
            assert col in row

    def test_price_difference_positive_when_competitor_is_cheaper(self, scanner):
        row = scanner._build_row(self._sample_result(price=299.0))
        assert row["price_difference"] == pytest.approx(50.0)
        assert row["we_are_cheaper"]   is False

    def test_price_difference_negative_when_we_are_cheaper(self, scanner):
        row = scanner._build_row(self._sample_result(price=499.0))
        assert row["price_difference"] == pytest.approx(-150.0)
        assert row["we_are_cheaper"]   is True

    def test_none_price_gives_none_fields(self, scanner):
        result = {"source": "google", "title": "X", "url": "", "price_nok": None, "snippet": ""}
        row = scanner._build_row(result)
        assert row["price_difference"] is None
        assert row["we_are_cheaper"]   is None

    def test_our_margin_stored_as_percent(self, scanner):
        row = scanner._build_row(self._sample_result())
        assert row["our_margin"] == pytest.approx(68.4, abs=0.1)

    def test_source_is_preserved(self, scanner):
        row = scanner._build_row(self._sample_result(source="prisjakt"))
        assert row["source"] == "prisjakt"

    def test_keyword_is_preserved(self, scanner):
        row = scanner._build_row(self._sample_result())
        assert row["keyword"] == "elektrisk juicemaskin bærbar"


# ------------------------------------------------------------------ #
#  TestAppendToCsv                                                      #
# ------------------------------------------------------------------ #

class TestAppendToCsv:

    def _make_row(self, scanner, price=299.0, source="google"):
        return scanner._build_row({
            "source": source, "title": "X",
            "url": "", "price_nok": price, "snippet": "",
        })

    def test_rows_are_appended(self, scanner):
        scanner._append_to_csv([self._make_row(scanner, 299), self._make_row(scanner, 399)])
        with open(scanner.csv_path) as f:
            content = f.read()
        assert "299" in content
        assert "399" in content

    def test_existing_data_is_not_overwritten(self, scanner_with_data):
        new_row = scanner_with_data._build_row({
            "source": "google", "title": "Ny", "url": "", "price_nok": 499.0, "snippet": "",
        })
        scanner_with_data._append_to_csv([new_row])

        with open(scanner_with_data.csv_path) as f:
            rows = list(csv.DictReader(f))

        titles = [r["title"] for r in rows]
        assert "Juicer nettbutikk" in titles
        assert "Ny"                in titles

    def test_empty_list_does_nothing(self, scanner):
        before = os.path.getsize(scanner.csv_path)
        scanner._append_to_csv([])
        assert os.path.getsize(scanner.csv_path) == before


# ------------------------------------------------------------------ #
#  TestScan                                                            #
# ------------------------------------------------------------------ #

class TestScan:

    def _mock_scan(self, mock_ddgs, mock_get):
        """Hjelpefunksjon: setter opp standard mocks for scan()."""
        mock_ddgs.return_value.text.return_value = DDG_RESULTS
        mock_get.return_value = _make_response(PRISJAKT_HTML)

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    @patch("competitor_scanner.DDGS")
    def test_scan_returns_list(self, mock_ddgs, mock_get, mock_sleep, scanner):
        self._mock_scan(mock_ddgs, mock_get)
        results = scanner.scan()
        assert isinstance(results, list)

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    @patch("competitor_scanner.DDGS")
    def test_scan_writes_to_csv(self, mock_ddgs, mock_get, mock_sleep, scanner):
        self._mock_scan(mock_ddgs, mock_get)
        scanner.scan()
        with open(scanner.csv_path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) > 0

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    @patch("competitor_scanner.DDGS")
    def test_scan_includes_all_three_sources(self, mock_ddgs, mock_get, mock_sleep, scanner):
        mock_ddgs.return_value.text.return_value = DDG_RESULTS
        mock_get.return_value = _make_response(PRISJAKT_HTML)
        results = scanner.scan()
        sources = {r["source"] for r in results}
        assert "google"     in sources
        assert "prisjakt"   in sources
        assert "aliexpress" in sources

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    @patch("competitor_scanner.DDGS")
    def test_scan_graceful_when_all_sources_fail(self, mock_ddgs, mock_get, mock_sleep, scanner):
        mock_ddgs.return_value.text.side_effect = Exception("blocked")
        mock_get.return_value = _make_response("", status_code=403)
        results = scanner.scan()
        assert results == []

    @patch("competitor_scanner.time.sleep")
    @patch("competitor_scanner.requests.get")
    @patch("competitor_scanner.DDGS")
    def test_second_scan_appends_not_overwrites(self, mock_ddgs, mock_get, mock_sleep, scanner):
        self._mock_scan(mock_ddgs, mock_get)
        scanner.scan()
        scanner.scan()
        with open(scanner.csv_path) as f:
            rows = list(csv.DictReader(f))
        # To scan-runder skal gi dobbelt så mange rader
        assert len(rows) >= 4


# ------------------------------------------------------------------ #
#  TestGetSummary                                                       #
# ------------------------------------------------------------------ #

class TestGetSummary:

    def test_no_data_returns_error(self, scanner):
        result = scanner.get_summary()
        assert "error" in result

    def test_wrong_keyword_returns_error(self, scanner_with_data, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        other = CompetitorScanner("kaffetrakter", 799, 0.573)
        result = other.get_summary()
        assert "error" in result

    def test_summary_contains_required_keys(self, scanner_with_data):
        summary = scanner_with_data.get_summary()
        for key in [
            "keyword", "our_price", "competitor_count",
            "min_price", "max_price", "avg_price",
            "cheaper_than_us", "more_expensive_than_us",
            "we_are_cheapest", "margin_at_avg_price", "positioning",
        ]:
            assert key in summary

    def test_min_max_only_uses_norwegian_sources(self, scanner_with_data):
        summary = scanner_with_data.get_summary()
        # Norske priser: 299 (google) og 399 (prisjakt)
        assert summary["min_price"] == pytest.approx(299.0)
        assert summary["max_price"] == pytest.approx(399.0)

    def test_avg_price_correct(self, scanner_with_data):
        # (299 + 399) / 2 = 349
        summary = scanner_with_data.get_summary()
        assert summary["avg_price"] == pytest.approx(349.0)

    def test_positioning_is_pa_snitt(self, scanner_with_data):
        # Vår pris 349, snitt 349 → diff=0 → PÅ SNITT
        summary = scanner_with_data.get_summary()
        assert summary["positioning"] == "VI ER PÅ SNITT"

    def test_aliexpress_avg_included_when_data_exists(self, scanner_with_data):
        summary = scanner_with_data.get_summary()
        assert "aliexpress_avg_price" in summary
        assert summary["aliexpress_avg_price"] == pytest.approx(50.0)

    def test_positioning_billigst(self, scanner, tmp_path, monkeypatch):
        """Vi er billigst når konkurrentene er dyrest."""
        monkeypatch.chdir(tmp_path)
        s = CompetitorScanner("testprodukt", 200, 0.5)
        rows = [
            {"timestamp": "2024-01-15T10:00:00", "keyword": "testprodukt",
             "source": "google", "title": "X", "url": "", "price_nok": 400,
             "snippet": "", "our_price": 200, "our_margin": 50.0,
             "price_difference": -200, "we_are_cheaper": True},
        ]
        with open(s.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerows(rows)
        summary = s.get_summary()
        assert summary["positioning"] == "VI ER BILLIGST"

    def test_positioning_dyrest(self, scanner, tmp_path, monkeypatch):
        """Vi er dyrest når konkurrentene er billigst."""
        monkeypatch.chdir(tmp_path)
        s = CompetitorScanner("testprodukt", 600, 0.5)
        rows = [
            {"timestamp": "2024-01-15T10:00:00", "keyword": "testprodukt",
             "source": "google", "title": "X", "url": "", "price_nok": 200,
             "snippet": "", "our_price": 600, "our_margin": 50.0,
             "price_difference": 400, "we_are_cheaper": False},
        ]
        with open(s.csv_path, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=CSV_COLUMNS).writerows(rows)
        summary = s.get_summary()
        assert summary["positioning"] == "VI ER DYREST"

    def test_we_are_cheapest_false_when_competitor_is_cheaper(self, scanner_with_data):
        summary = scanner_with_data.get_summary()
        # Konkurrent 299 < vår 349 → vi er IKKE billigst
        assert summary["we_are_cheapest"] is False


# ------------------------------------------------------------------ #
#  TestReusability                                                      #
# ------------------------------------------------------------------ #

class TestReusability:

    def test_two_scanners_different_keywords_dont_mix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        s_a = CompetitorScanner("juicer",       349, 0.684)
        s_b = CompetitorScanner("kaffetrakter", 799, 0.573)

        row_a = s_a._build_row({"source": "google", "title": "A", "url": "", "price_nok": 299.0, "snippet": ""})
        row_b = s_b._build_row({"source": "google", "title": "B", "url": "", "price_nok": 750.0, "snippet": ""})

        s_a._append_to_csv([row_a])
        s_b._append_to_csv([row_b])

        sum_a = s_a.get_summary()
        sum_b = s_b.get_summary()

        assert sum_a["keyword"]   == "juicer"
        assert sum_b["keyword"]   == "kaffetrakter"
        assert sum_a["avg_price"] == pytest.approx(299.0)
        assert sum_b["avg_price"] == pytest.approx(750.0)

    def test_our_price_and_margin_stored_correctly(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        s   = CompetitorScanner("testprodukt", 500, 0.50)
        row = s._build_row({"source": "google", "title": "X", "url": "", "price_nok": 450.0, "snippet": ""})
        assert row["our_price"]  == 500
        assert row["our_margin"] == pytest.approx(50.0)
