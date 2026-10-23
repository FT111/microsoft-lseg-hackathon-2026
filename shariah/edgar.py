"""SEC EDGAR: structured financials (XBRL company facts) and the 10-K business
section. Free, no key. SEC requires a User-Agent with a contact email."""
import os
import re
import time

import requests
from dotenv import load_dotenv

from .cache import cached

load_dotenv()
# SEC asks for a real contact: set SEC_USER_AGENT="Your Name your@email" in .env
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "LSEG hackathon team research-contact@example.org")}
_last_call = [0.0]


def _get(url: str) -> requests.Response:
    # SEC allows ~10 requests/second; stay well under.
    wait = 0.15 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


def ticker_to_cik() -> dict:
    def produce():
        data = _get("https://www.sec.gov/files/company_tickers.json").json()
        return {row["ticker"]: str(row["cik_str"]).zfill(10) for row in data.values()}
    return cached("edgar_tickers", produce)


def company_facts(ticker: str) -> dict:
    cik = ticker_to_cik()[ticker.upper()]
    def produce():
        facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").json()
        # keep only what we use - the full file is several MB
        keep = {}
        for ns in ("us-gaap", "dei"):
            for name, body in facts.get("facts", {}).get(ns, {}).items():
                if name in CONCEPTS_USED:
                    keep[name] = body.get("units", {})
        return {"cik": cik, "name": facts.get("entityName"), "facts": keep}
    return cached(f"edgar_facts_v2_{ticker}", produce)


def submissions(ticker: str) -> dict:
    cik = ticker_to_cik()[ticker.upper()]
    def produce():
        s = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
        recent = s.get("filings", {}).get("recent", {})
        tenk = None
        for form, acc, doc, date in zip(recent.get("form", []), recent.get("accessionNumber", []),
                                        recent.get("primaryDocument", []), recent.get("filingDate", [])):
            if form == "10-K":
                tenk = {"accession": acc, "doc": doc, "date": date,
                        "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}"}
                break
        return {"name": s.get("name"), "sic": s.get("sic"), "sicDescription": s.get("sicDescription"),
                "latest_10k": tenk}
    return cached(f"edgar_subs_{ticker}", produce)


# Words that point at activities the Shariah methodologies exclude. Sentences containing them are
# pulled from the WHOLE 10-K, so the AI also sees what Item 1's first pages leave out.
ACTIVITY_KEYWORDS = r"(alcohol|beer|wine|spirits|liquor|brew|distill|tobacco|cigar|cigarette|vape|vapor|nicotine|cannabis|" \
                    r"pork|ham|bacon|sausage|meat|casino|gambling|gaming|betting|lotter|wager|hotel|resort|cinema|film|movie|" \
                    r"music|streaming|adult|weapon|missile|munition|defen[cs]e|military|ammunition|firearm|bank|lending|" \
                    r"loans? to customers|credit card|mortgage|insurance|underwrit|interest income)"


def _filing_text(url: str) -> str:
    html = _get(url).text
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"&#160;|&nbsp;|&#xa0;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&#8217;|&rsquo;", "'", text)
    text = re.sub(r"&#[0-9]+;|&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text)


def business_section(ticker: str, max_chars: int = 12000, max_snippet_chars: int = 8000) -> dict:
    """Text of 10-K 'Item 1. Business' (best effort) plus keyword sentences from the whole
    filing, and the source URL. The AI reads `text`; quotes are checked against it."""
    sub = submissions(ticker)
    tenk = sub.get("latest_10k")
    if not tenk:
        return {"text": "", "url": None}
    def produce():
        text = _filing_text(tenk["url"])
        # find the real Item 1 (skip the table of contents: take the longest chunk up to Item 1A)
        starts = [m.start() for m in re.finditer(r"(?i)item\s*1\.?\s*business", text)]
        body = ""
        for s in starts:
            end = re.search(r"(?i)item\s*1a\.?\s*risk\s*factors", text[s + 200:])
            chunk = text[s: s + 200 + end.start()] if end else text[s: s + max_chars]
            if len(chunk) > len(body):
                body = chunk
        body = (body or text[:max_chars])[:max_chars]
        snippets, seen, total = [], set(), 0
        for sent in re.split(r"(?<=[.;])\s+", text):
            if len(sent) < 40 or len(sent) > 600 or sent in seen or sent in body:
                continue
            if re.search(ACTIVITY_KEYWORDS, sent, re.I):
                seen.add(sent)
                snippets.append(sent)
                total += len(sent)
                if total > max_snippet_chars:
                    break
        full = body + ("\n\n[Other sentences from the same 10-K that mention screened activities]\n" +
                       "\n".join(snippets) if snippets else "")
        return {"text": full, "item1_chars": len(body), "snippets": len(snippets), "url": tenk["url"],
                "date": tenk["date"]}
    return cached(f"edgar_10k_item1_v2_{ticker}", produce)


# ---------- picking values out of XBRL ----------
# Required items: if missing, the screen that needs them becomes NEEDS REVIEW (never 0).
# Optional components (short-term investments, borrowings, commercial paper...) are often
# legitimately absent; they count as 0 and the note says so.

ASSETS = ["Assets"]
DEBT_COMBINED = ["DebtLongtermAndShorttermCombinedAmount"]
DEBT_LT_INCL_CURRENT = ["LongTermDebt"]
DEBT_LT_NONCURRENT = ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations"]
DEBT_LT_CURRENT = ["LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"]
DEBT_ALL_CURRENT = ["DebtCurrent"]
DEBT_SHORT = ["ShortTermBorrowings", "CommercialPaper"]
CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]
SHORT_TERM_INTEREST_BEARING = ["ShortTermInvestments", "MarketableSecuritiesCurrent",
                               "AvailableForSaleSecuritiesDebtSecuritiesCurrent"]
LONG_TERM_INTEREST_BEARING = ["MarketableSecuritiesNoncurrent", "AvailableForSaleSecuritiesDebtSecuritiesNoncurrent"]
DEBT_SECURITIES_TOTAL = ["AvailableForSaleSecuritiesDebtSecurities", "HeldToMaturitySecurities"]
RECEIVABLES = ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent", "AccountsNotesAndLoansReceivableNetCurrent",
               "AccountsAndOtherReceivablesNetCurrent"]
REVENUE = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
           "RevenueFromContractWithCustomerIncludingAssessedTax"]
# Interest income, best concept first. Broader concepts (that also include dividends or
# other income) overstate interest - the conservative direction - and the note says so.
INTEREST_INCOME = [
    ("InvestmentIncomeInterest", ""),
    ("InterestIncomeOther", ""),
    ("InterestIncomeOperatingAndNonoperating", ""),
    ("InterestIncomeShortTermInvestmentOther", ""),
    ("InvestmentIncomeInterestAndDividend", "includes dividends - overstates interest (conservative)"),
    ("InterestAndOtherIncome", "includes other income - overstates interest (conservative)"),
    ("InvestmentIncomeNet", "net investment income used as a proxy - overstates interest (conservative)"),
]
DIVIDENDS = ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"]
SHARES = ["CommonStockSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"]

CONCEPTS_USED = set(ASSETS + DEBT_COMBINED + DEBT_LT_INCL_CURRENT + DEBT_LT_NONCURRENT + DEBT_LT_CURRENT
                    + DEBT_ALL_CURRENT + DEBT_SHORT + CASH + SHORT_TERM_INTEREST_BEARING
                    + LONG_TERM_INTEREST_BEARING + DEBT_SECURITIES_TOTAL + RECEIVABLES + REVENUE
                    + [c for c, _ in INTEREST_INCOME] + DIVIDENDS + SHARES + ["EntityCommonStockSharesOutstanding"])
FORMS = ("10-K", "10-K/A", "10-Q", "10-Q/A")
STALE_AFTER_DAYS = 480   # ~15 months: older balance sheets are flagged as outdated


def _days(s: str) -> int:
    import datetime as _dt
    return _dt.date.fromisoformat(s).toordinal()


def _rows(facts: dict, concept: str) -> list:
    units = facts["facts"].get(concept) or {}
    rows = units.get("USD") or units.get("shares") or (next(iter(units.values())) if units else [])
    return [r for r in rows if r.get("form") in FORMS]


def _instant(facts: dict, concept: str, end: str):
    """Value of a balance-sheet item at exactly `end` (latest filing wins, so restatements apply)."""
    rows = [r for r in _rows(facts, concept) if r["end"] == end and "start" not in r]
    if not rows:
        return None
    best = max(rows, key=lambda r: r.get("filed", ""))
    return {"value": float(best["val"]), "concept": concept, "period_end": end, "form": best["form"],
            "filed": best.get("filed")}


def _first_instant(facts, concepts, end):
    for c in concepts:
        v = _instant(facts, c, end)
        if v:
            return v
    return None


def _annual(facts: dict, concept: str, end: str | None = None):
    """Latest ~12-month value (or the 12-month value ending exactly at `end`)."""
    best = None
    for r in _rows(facts, concept):
        if "start" not in r or not 300 <= _days(r["end"]) - _days(r["start"]) <= 380:
            continue
        if end and r["end"] != end:
            continue
        if best is None or (r["end"], r.get("filed", "")) > (best["end"], best.get("filed", "")):
            best = r
    if not best:
        return None
    return {"value": float(best["val"]), "concept": concept, "period_start": best["start"],
            "period_end": best["end"], "form": best["form"], "filed": best.get("filed")}


def _sum(parts: list, label: str):
    parts = [p for p in parts if p]
    if not parts:
        return None
    return {"value": sum(p["value"] for p in parts), "concept": " + ".join(p["concept"] for p in parts),
            "period_end": parts[0]["period_end"], "label": label}


def _debt(f, end):
    combined = _first_instant(f, DEBT_COMBINED, end)
    if combined:
        return combined
    short = [_instant(f, c, end) for c in DEBT_SHORT]
    lt = _first_instant(f, DEBT_LT_INCL_CURRENT, end)
    if lt:
        return _sum([lt] + short, "total debt")
    nc = _first_instant(f, DEBT_LT_NONCURRENT, end)
    if not nc:
        return None
    all_current = _first_instant(f, DEBT_ALL_CURRENT, end)
    if all_current:          # DebtCurrent already includes commercial paper and short-term borrowings
        return _sum([nc, all_current], "total debt")
    return _sum([nc, _first_instant(f, DEBT_LT_CURRENT, end)] + short, "total debt")


def _balance_sheet(f, end):
    notes = []
    cash = _first_instant(f, CASH, end)
    st = _first_instant(f, SHORT_TERM_INTEREST_BEARING, end)
    if cash and not st:
        notes.append("no short-term investments tagged - counted as 0")
    lt = _first_instant(f, LONG_TERM_INTEREST_BEARING, end)
    if not lt:   # derive the long-term part from a total debt-securities figure, if one is tagged
        total = _sum([_instant(f, c, end) for c in DEBT_SECURITIES_TOTAL], "debt securities")
        if total and total["value"] > (st["value"] if st else 0):
            lt = {**total, "value": total["value"] - (st["value"] if st else 0),
                  "concept": total["concept"] + (f" - {st['concept']}" if st else "")}
    debt = _debt(f, end)
    items = {
        "total_assets": _instant(f, "Assets", end),
        "total_debt": debt,
        "cash": cash,
        "short_term_interest_bearing": st,
        "long_term_interest_bearing": lt,
        "receivables": _first_instant(f, RECEIVABLES, end),
    }
    items["cash_and_interest_bearing"] = (_sum([cash, st], "cash + short-term interest-bearing items")
                                          if cash else None)
    return items, notes


def _shares(f):
    """Shares outstanding: cover-page count if recent, else balance-sheet count, else weighted average.
    Companies with several share classes are often only right in the last two."""
    dei = _rows(f, "EntityCommonStockSharesOutstanding")
    candidates = []
    if dei:
        last = max(r["end"] for r in dei)
        vals = [r for r in dei if r["end"] == last]
        candidates.append(({"value": float(sum({r["val"] for r in vals})), "concept": "dei:EntityCommonStockSharesOutstanding",
                            "period_end": last}))
    for c in SHARES:
        rows = _rows(f, c)
        if rows:
            last = max(r["end"] for r in rows)
            candidates.append({"value": float(max(r["val"] for r in rows if r["end"] == last)), "concept": c,
                               "period_end": last})
    if not candidates:
        return None
    newest = max(c["period_end"] for c in candidates)
    recent = [c for c in candidates if _days(newest) - _days(c["period_end"]) <= 120]
    return recent[0]


def financials(ticker: str, today: str | None = None) -> dict:
    """Every number the Shariah screens need, each with its XBRL concept and reporting date.
    Balance-sheet items all come from ONE balance-sheet date. Missing required items are None."""
    import datetime as _dt
    f = company_facts(ticker)
    dates = sorted({r["end"] for r in _rows(f, "Assets") if "start" not in r}, reverse=True)
    annual_dates = sorted({r["end"] for r in _rows(f, "Assets") if r["form"].startswith("10-K")}, reverse=True)
    out = {"ticker": ticker, "name": f["name"], "cik": f["cik"], "notes": []}

    # Use the latest balance sheet; if a required item is missing there, try the latest 10-K date.
    chosen = None
    for end in dict.fromkeys(dates[:1] + annual_dates[:1]):
        items, notes = _balance_sheet(f, end)
        missing = [k for k in ("total_assets", "total_debt", "cash", "receivables") if not items[k]]
        if chosen is None or len(missing) < len(chosen[3]):
            chosen = (end, items, notes, missing)
    if chosen is None:
        out.update({"period_end": None, "items": {}, "missing": ["balance sheet"]})
        return out
    end, items, notes, _ = chosen
    out["period_end"], out["notes"] = end, notes

    # Most recent 12-month revenue across all revenue concepts (companies switch concepts over time).
    revs = [r for r in (_annual(f, c) for c in REVENUE) if r]
    rev = max(revs, key=lambda r: (r["period_end"], -REVENUE.index(r["concept"]))) if revs else None
    if rev and _days(end) - _days(rev["period_end"]) > STALE_AFTER_DAYS:
        out["notes"].append(f"latest annual revenue ({rev['period_end']}) is much older than the balance sheet")
        rev = None
    items["revenue"] = rev
    items["interest_income"] = None
    if rev:
        for c, note in INTEREST_INCOME:
            v = _annual(f, c, rev["period_end"])
            if v and v["value"] >= 0:
                items["interest_income"] = v
                if note:
                    out["notes"].append(f"interest income: {c} {note}")
                break
        items["dividends_paid"] = next((v for v in (_annual(f, c, rev["period_end"]) for c in DIVIDENDS) if v), None)
    else:
        items["dividends_paid"] = None
    items["shares_outstanding"] = _shares(f)

    out["items"] = items
    out["missing"] = [k for k in ("total_assets", "total_debt", "cash", "receivables", "revenue", "interest_income",
                                  "shares_outstanding") if not items.get(k)]
    today = today or _dt.date.today().isoformat()
    out["stale"] = _days(today) - _days(end) > STALE_AFTER_DAYS
    out["income_period"] = (rev["period_start"], rev["period_end"]) if rev else None
    # Flat values for convenience (None when missing).
    for k, v in items.items():
        out[k] = v["value"] if v else None
    out["sources"] = {k: (v["concept"] if v else "not reported") for k, v in items.items()}
    return out


def facts_url(cik: str) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
