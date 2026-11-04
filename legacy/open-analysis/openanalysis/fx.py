"""USD to AUD at the Reserve Bank of Australia daily rate.

The RBA publishes A$1 = USD at 4pm Sydney time on business days. On weekends and
public holidays the most recent published rate is used and its date is recorded.
"""

import csv
import io
import xml.etree.ElementTree as ET
from datetime import date, datetime

RBA_CSV_URL = "https://www.rba.gov.au/statistics/tables/csv/f11.1-data.csv"
RBA_RSS_URL = "https://www.rba.gov.au/rss/rss-cb-exchange-rates.xml"
RBA_PAGE_URL = "https://www.rba.gov.au/statistics/frequency/exchange-rates.html"

_CB = "{http://www.cbwiki.net/wiki/index.php/Specification_1.2/}"


def parse_csv(text, on_or_before):
    """Latest (date, A$1=USD) from the RBA F11.1 table on or before the given date."""
    rows = list(csv.reader(io.StringIO(text)))
    column = None
    for row in rows:
        if row and row[0] == "Series ID" and "FXRUSD" in row:
            column = row.index("FXRUSD")
            break
    if column is None:
        raise ValueError("RBA CSV: FXRUSD series not found")
    best = None
    for row in rows:
        if len(row) <= column or not row[column].strip():
            continue
        try:
            day = datetime.strptime(row[0], "%d-%b-%Y").date()
        except ValueError:
            continue
        if day <= on_or_before and (best is None or day > best[0]):
            best = (day, float(row[column]))
    if best is None:
        raise ValueError(f"RBA CSV: no AUD/USD rate on or before {on_or_before}")
    return best


def parse_rss(text):
    """(date, A$1=USD) from the RBA exchange-rate RSS feed, which carries the latest day only."""
    for element in ET.fromstring(text).iter(f"{_CB}exchangeRate"):
        if element.findtext(f"{_CB}targetCurrency") == "USD":
            value = element.findtext(f"{_CB}observation/{_CB}value")
            period = element.findtext(f"{_CB}observationPeriod/{_CB}period")
            return date.fromisoformat(period), float(value)
    raise ValueError("RBA RSS: USD rate not found")


def resolve(snapshot_date, csv_text=None, rss_text=None, previous=None):
    """Pick the rate for a snapshot: CSV table, then RSS feed, then yesterday's snapshot."""
    rate_date = aud_usd = method = None
    if csv_text:
        try:
            rate_date, aud_usd = parse_csv(csv_text, snapshot_date)
            method = "rba_f11.1_csv"
        except ValueError:
            pass
    if method is None and rss_text:
        try:
            rss_date, rss_rate = parse_rss(rss_text)
            if rss_date <= snapshot_date:
                rate_date, aud_usd, method = rss_date, rss_rate, "rba_rss"
        except (ValueError, ET.ParseError):
            pass
    if method is None and previous:
        rate_date = date.fromisoformat(previous["rate_date"])
        aud_usd, method = previous["aud_usd"], "carried_forward_from_previous_snapshot"
    if method is None:
        raise RuntimeError("No RBA exchange rate available (CSV, RSS and previous snapshot all failed)")
    return {
        "aud_usd": aud_usd,
        "usd_to_aud": round(1 / aud_usd, 6),
        "rate_date": rate_date.isoformat(),
        "days_old": (snapshot_date - rate_date).days,
        "method": method,
        "description": "A$1 = USD, RBA 4pm Sydney representative rate. AUD = USD / aud_usd.",
        "source": "Reserve Bank of Australia",
        "source_url": RBA_PAGE_URL,
    }
