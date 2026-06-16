"""Shared utilities for public-data fetchers."""

from __future__ import annotations

import datetime as dt
import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


MARYLAND_COUNTY_FIPS = {
    "24001",
    "24003",
    "24005",
    "24009",
    "24011",
    "24013",
    "24015",
    "24017",
    "24019",
    "24021",
    "24023",
    "24025",
    "24027",
    "24029",
    "24031",
    "24033",
    "24035",
    "24037",
    "24039",
    "24041",
    "24043",
    "24045",
    "24047",
    "24510",
}


def today_iso() -> str:
    return dt.date.today().isoformat()


def utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat()


def fetch_text(url: str, timeout: int = 120) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "maryland-healthcare-access-analytics/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8-sig", "replace")
    except (urllib.error.URLError, ssl.SSLError) as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return response.read().decode("utf-8-sig", "replace")


def fetch_json(url: str, timeout: int = 120) -> Any:
    return json.loads(fetch_text(url, timeout=timeout))


def as_float(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "na", "n/a", "null", "none", "not available"}:
        return None
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def percent(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round((float(numerator) / float(denominator)) * 100, 2)


def county_key(value: str) -> str:
    text = value.lower().replace("&", "and").replace("st.", "st")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\bcounty\b|\bcity\b|\bmaryland\b|\bmd\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()
