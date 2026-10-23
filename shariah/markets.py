"""Presence in Muslim-majority markets, read from the company's own annual report.

Plain Python: the latest 10-K is scanned for the names of Muslim-majority countries and regions.
Each hit keeps the sentence it came from, so every pick shows a verbatim quote from the filing.
This is EVIDENCE OF PRESENCE (operations, sales, offices, customers in those markets) - not an
ethics rating, not a statement about anyone's faith, and not part of the Shariah screen."""
import re

from . import edgar
from .cache import cached

# OIC member states with Muslim-majority populations, plus common regional terms.
COUNTRIES = [
    "Indonesia", "Malaysia", "Saudi Arabia", "United Arab Emirates", "Turkey", "Türkiye", "Egypt", "Pakistan",
    "Bangladesh", "Nigeria", "Qatar", "Kuwait", "Bahrain", "Oman", "Morocco", "Algeria", "Tunisia",
    "Kazakhstan", "Uzbekistan", "Azerbaijan", "Iraq", "Iran", "Senegal", "Mali", "Brunei", "Maldives", "Albania",
    "Kosovo", "Libya", "Sudan", "Somalia", "Afghanistan", "Yemen", "Syria", "Lebanon", "Kyrgyzstan", "Tajikistan",
    "Turkmenistan", "Mauritania", "Niger", "Chad", "Guinea", "Gambia", "Djibouti", "Comoros", "Sierra Leone",
]
REGIONS = ["Middle East", "Gulf Cooperation Council", "GCC", "Islamic", "Muslim"]
ALIASES = {"UAE": "United Arab Emirates", "Dubai": "United Arab Emirates", "Abu Dhabi": "United Arab Emirates",
           "Riyadh": "Saudi Arabia", "Jakarta": "Indonesia", "Kuala Lumpur": "Malaysia", "Istanbul": "Turkey",
           "Cairo": "Egypt", "Karachi": "Pakistan", "Dhaka": "Bangladesh", "Lagos": "Nigeria", "Doha": "Qatar",
           "Türkiye": "Turkey"}
_PATTERN = re.compile(r"\b(" + "|".join(re.escape(x) for x in COUNTRIES + REGIONS + list(ALIASES)) + r")\b")
# "Jordan" is left out: in filings it is usually Nike's brand, not the country.
# Sentences about sanctions, wars, export controls or other risks are not evidence of doing business there.
_NOISE = re.compile(r"(?i)(risk factor|sanction|embargo|\bwar\b|warfare|conflict|terror|hostilit|unrest|boycott|"
                    r"export control|export restriction|licen[cs]ing requirement|geopolitic|tension|invasion|gaza|"
                    r"military action|instability|political|tariff)")
_BUSINESS = re.compile(r"(?i)(operat|office|customer|sales|revenue|manufactur|facilit|employee|plant|market|distribut|"
                       r"subsidiar|store|retail|supplier|assembl|data cent|launch|partner|serve|sell)")


def _canonical(name: str) -> str:
    return ALIASES.get(name, name)


def mentions(ticker: str) -> dict:
    """{'countries': {name: count}, 'regions': {term: count}, 'sentences': [...], 'url', 'date'} from the
    latest 10-K. Empty when there is no SEC filing text (e.g. UK companies)."""
    sub = edgar.submissions(ticker)
    tenk = sub.get("latest_10k")
    if not tenk:
        return {"countries": {}, "regions": {}, "sentences": [], "url": None, "date": None}
    def produce():
        text = edgar._filing_text(tenk["url"])
        countries, regions, sentences, seen = {}, {}, [], set()
        for sent in re.split(r"(?<=[.;])\s+", text):
            if len(sent) < 40 or len(sent) > 500:
                continue
            hits = _PATTERN.findall(sent)
            if not hits:
                continue
            if _NOISE.search(sent) or sent in seen:   # risk-factor boilerplate is not a business footprint
                continue
            seen.add(sent)
            names = {_canonical(h) for h in hits}
            for n in names:
                bucket = regions if n in REGIONS else countries
                bucket[n] = bucket.get(n, 0) + 1
            business = len(_BUSINESS.findall(sent))
            sentences.append({"text": sent.strip(), "names": sorted(n for n in names if n not in REGIONS),
                              "regions": sorted(n for n in names if n in REGIONS), "business": business})
        sentences.sort(key=lambda s: -(len(s["names"]) * 2 + len(s["regions"]) + min(3, s["business"])))
        return {"countries": countries, "regions": regions, "sentences": sentences[:12], "url": tenk["url"],
                "date": tenk["date"]}
    return cached(f"markets_v2_{ticker}_{tenk['accession']}", produce)


def score(m: dict) -> int:
    """Distinct Muslim-majority countries named, plus 1 per regional term type (capped)."""
    return len(m.get("countries", {})) * 2 + min(3, len(m.get("regions", {})))


def rank(tickers: list[str], top: int = 3) -> list[dict]:
    """Best-evidenced presence first. Only tickers whose filing names at least one country or region."""
    out = []
    for t in tickers:
        try:
            m = mentions(t)
        except Exception:
            continue
        s = score(m)
        if s == 0:
            continue
        best = next((x for x in m["sentences"] if x["names"] and x.get("business")),
                    next((x for x in m["sentences"] if x["names"]), m["sentences"][0] if m["sentences"] else None))
        out.append({"ticker": t, "score": s, "countries": sorted(m["countries"], key=lambda k: -m["countries"][k]),
                    "regions": sorted(m["regions"]), "quote": best["text"] if best else "", "url": m["url"],
                    "date": m["date"]})
    out.sort(key=lambda x: -x["score"])
    return out[:top]
