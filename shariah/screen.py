"""Shariah screening engine. Deterministic Python - the LLM never decides a status here.

Input: SEC financials (edgar.financials), a business-activity finding (llm.business_screen
or the SIC fallback below) and ONE standard from methodology.METHODOLOGIES.
Output: PASS / FAIL / NEEDS REVIEW for every individual screen, plus the overall status
(the worst of them), each with its value, limit, operator, clause and reason.

Missing or unverifiable data always gives NEEDS REVIEW - never a guess and never a 0.
"""
import re

from .methodology import (FAIL, METHODOLOGIES, NEEDS_REVIEW, PASS, STANDARDS, breaches, counted_categories,
                          worst)

# Kept for code that imports it; each entry is the full methodology record.
STANDARDS = {k: METHODOLOGIES[k] for k in STANDARDS}

# Low-confidence AI estimates at or above this share still go to a person rather than FAIL.
LOW_CONFIDENCE_FAIL_FLOOR = 0.15

LABELS = {"total_assets": "total assets", "total_debt": "total debt", "cash_and_interest_bearing":
          "cash and interest-bearing items", "receivables": "accounts receivable", "market_cap": "market value",
          "revenue": "total revenue", "interest_income": "interest income"}

# SEC industry (SIC) descriptions that identify a non-compliant PRIMARY business.
# Used only when the AI reading of the 10-K is unavailable.
EXCLUDED_SIC_WORDS = {
    "bank": "conventional_finance", "savings institution": "conventional_finance",
    "security brokers": "conventional_finance", "finance services": "conventional_finance",
    "insurance": "conventional_insurance", "hospital & medical service plans": "conventional_insurance",
    "cigarettes": "tobacco", "tobacco": "tobacco",
    "malt beverages": "alcohol", "wines": "alcohol", "distilled": "alcohol", "liquor": "alcohol",
    "hotels": "hotels", "amusement": "gambling", "motion picture": "cinema", "television broadcasting": "cinema",
    "guided missiles": "weapons_defence", "ordnance": "weapons_defence",
}
POSSIBLE_SIC_WORDS = {"aircraft": "weapons_defence", "eating places": "alcohol", "meat packing": "pork",
                      "sausages": "pork", "grocery": "alcohol", "retail": "alcohol"}


def sic_rule(sic_description: str) -> dict:
    """Fallback business finding from the SEC industry code (no AI). It can identify a
    non-compliant primary business, but it cannot rule out secondary non-compliant revenue."""
    d = (sic_description or "").lower()
    acts = []
    for word, cat in EXCLUDED_SIC_WORDS.items():
        if word in d:
            acts.append({"category": cat, "revenue_share_pct": 100.0, "confidence": "high",
                         "evidence": f"SEC industry code: {sic_description}", "quote_verified": True})
            break
    else:
        for word, cat in POSSIBLE_SIC_WORDS.items():
            if word in d:
                acts.append({"category": cat, "revenue_share_pct": None, "confidence": "low",
                             "evidence": f"SEC industry code: {sic_description}", "quote_verified": True})
                break
    return {"method": "SIC rule", "activities": acts, "main_business": sic_description,
            "evidence": f"SEC industry code: {sic_description}", "main_quote_verified": False}


# ---------- quote check ----------

def _norm(s: str) -> str:
    s = (s or "").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_in_text(quote: str, text: str) -> bool:
    """True if the quote appears word-for-word in the source (whitespace, curly quotes and
    case ignored). Quotes shortened with '...' must have every part present."""
    q = _norm(quote).strip(' "\'')
    if len(q) < 12:
        return False
    t = _norm(text)
    parts = [p.strip(' "\'') for p in re.split(r"\.\.\.|…", q)]
    parts = [p for p in parts if p]
    return bool(parts) and all(len(p) >= 8 and p in t for p in parts)


# ---------- individual screens ----------

def _screen(key, label, clause, text, status, value=None, limit=None, op=None, note="", inputs=None):
    return {"key": key, "label": label, "clause": clause, "rule_text": text, "status": status, "value": value,
            "limit": limit, "op": op, "note": note, "inputs": inputs or {}}


def _activity_screen(business: dict, standard: str) -> tuple[dict, float | None, float]:
    """Returns (screen, best-estimate share or None if unknown, firmly evidenced share)."""
    m = METHODOLOGIES[standard]["activity"]
    counted = counted_categories(standard)
    acts = business.get("activities") or []
    base = dict(key="activity", label="Non-permitted business activities / total revenue", clause=m["clause"],
                text=m["text"], limit=m["limit"], op=m["op"])

    if business.get("method") not in ("LLM", "SIC rule") or business.get("error"):
        return _screen(**base, status=NEEDS_REVIEW,
                       note="business activities could not be read: " + (business.get("error") or "no source")), None, 0.0

    relevant = [a for a in acts if a.get("category") in counted]
    outside = [a for a in acts if a.get("category") not in counted and (a.get("revenue_share_pct") or 0) != 0]
    unknown = [a for a in relevant if a.get("revenue_share_pct") is None]
    unverified = [a for a in relevant if not a.get("quote_verified")]
    low = [a for a in relevant if a.get("confidence") == "low" and (a.get("revenue_share_pct") or 0) > 0]
    estimate = sum((a.get("revenue_share_pct") or 0) for a in relevant) / 100
    # "Firm" share: what the verified evidence clearly supports - the AI's stated floor, or its
    # estimate when that estimate is not low-confidence.
    def _firm(a):
        if not a.get("quote_verified"):
            return 0.0
        floor = a.get("min_revenue_share_pct") or 0.0
        est = a.get("revenue_share_pct") if a.get("confidence") != "low" else None
        return max(floor, est or 0.0)
    firm = sum(_firm(a) for a in relevant) / 100
    def _describe(a):
        name = a["category"].replace("_", " ")
        if a.get("revenue_share_pct") is not None:
            return f"{name} ~{a['revenue_share_pct']:.0f}%"
        if a.get("min_revenue_share_pct"):
            return f"{name} at least {a['min_revenue_share_pct']:.0f}%"
        return f"{name} (share unknown)"
    found = ", ".join(_describe(a) for a in relevant)

    problems = []
    if unknown:
        problems.append("revenue share not stated for " + ", ".join(a["category"].replace("_", " ") for a in unknown))
    if unverified:
        problems.append("quote could not be found in the filing for " +
                        ", ".join(a["category"].replace("_", " ") for a in unverified))
    if low:
        problems.append("low-confidence estimate for " + ", ".join(a["category"].replace("_", " ") for a in low))
    if outside:
        problems.append("activity found that this standard's verified list does not name: " +
                        ", ".join(a["category"].replace("_", " ") for a in outside))
    if business.get("method") == "SIC rule" and not relevant:
        problems.append("only the SEC industry code was checked (no AI reading of the annual report) - "
                        "secondary non-compliant revenue cannot be ruled out")
    if business.get("method") == "LLM" and not relevant and not business.get("main_quote_verified"):
        problems.append("the AI's description of the main business could not be matched to the filing text")

    estimate_or_none = None if unknown else estimate
    primary = [a for a in relevant if a.get("primary_business") and a.get("quote_verified")]
    if primary:
        names = ", ".join(a["category"].replace("_", " ") for a in primary)
        return _screen(**base, status=FAIL, value=estimate_or_none,
                       note=f"main business is a non-permitted activity ({names}), shown by a verified 10-K quote"
                       + (f"; {found}" if found else "")), estimate_or_none, firm
    if firm > 0 and breaches(firm, m["limit"], m["op"]):
        return _screen(**base, status=FAIL, value=firm, note=found), estimate_or_none, firm
    if estimate > 0 and breaches(estimate, m["limit"], m["op"]) and estimate >= LOW_CONFIDENCE_FAIL_FLOOR \
            and not unverified and not unknown:
        return _screen(**base, status=FAIL, value=estimate, note=found + " (estimate)"), estimate, firm
    if problems or (estimate > 0 and breaches(estimate, m["limit"], m["op"])):
        if estimate > 0 and breaches(estimate, m["limit"], m["op"]):
            problems.insert(0, f"estimated {estimate:.1%} is over the limit but the estimate is uncertain")
        return _screen(**base, status=NEEDS_REVIEW, value=estimate_or_none, note="; ".join(problems)
                       + (f" ({found})" if found else "")), estimate_or_none, firm
    return _screen(**base, status=PASS, value=estimate, note=found or "no non-permitted activity found in the filing"), \
        estimate, firm


def _ratio_screen(rule: dict, fin: dict, market_cap: dict | None, standard: str) -> dict:
    den_key = rule["denominator"]
    den = (market_cap or {}).get("value") if den_key == "market_cap" else fin.get(den_key)
    nums = {k: fin.get(k) for k in rule["numerator"]}
    inputs = {**{k: v for k, v in nums.items()}, den_key: den}
    base = dict(key=rule["key"], label=rule["label"], clause=rule["clause"], text=rule["text"], limit=rule["limit"], op=rule["op"], inputs=inputs)
    missing = [LABELS.get(k, k) for k, v in nums.items() if v is None] + ([] if den else [LABELS.get(den_key, den_key)])
    if missing:
        return _screen(**base, status=NEEDS_REVIEW, note="missing " + ", ".join(missing) + " - cannot calculate")
    value = sum(nums.values()) / den
    status = FAIL if breaches(value, rule["limit"], rule["op"]) else PASS
    notes = []

    # Long-term interest-bearing securities: counted separately so a person can decide.
    lt = fin.get("long_term_interest_bearing")
    if "cash_and_interest_bearing" in rule["numerator"] and lt:
        extended = (sum(nums.values()) + lt) / den
        inputs["long_term_interest_bearing"] = lt
        if status == PASS and breaches(extended, rule["limit"], rule["op"]):
            status = NEEDS_REVIEW
            notes.append(f"adding long-term interest-bearing securities (${lt / 1e9:,.1f}bn) gives {extended:.1%}, "
                         f"over the limit - the rule names 'interest-bearing items' without a maturity cut-off")
        else:
            notes.append(f"with long-term interest-bearing securities: {extended:.1%}")

    band = METHODOLOGIES[standard].get("monitoring_band")
    if band and rule["key"] in band["ratios"] and band["low"] <= value < band["high"]:
        if status == PASS:
            status = NEEDS_REVIEW
            notes.append("inside the FTSE monitoring band (31.667%-35%): a company that was non-compliant last "
                         "quarter stays non-compliant here; quarter-on-quarter history is not checked")
        else:
            notes.append("inside the FTSE monitoring band (31.667%-35%): a company compliant last quarter may "
                         "remain compliant for up to two quarters; history is not checked")
    return _screen(**base, status=status, value=value, note="; ".join(notes))


def _income_screen(fin: dict, standard: str, activity_estimate, activity_firm, activity_status) -> dict:
    m = METHODOLOGIES[standard]["income"]
    base = dict(key="noncompliant_income", label="Interest + non-compliant income / total revenue",
                clause=m["clause"], text=m["text"], limit=m["limit"], op=m["op"],
                inputs={"interest_income": fin.get("interest_income"), "revenue": fin.get("revenue")})
    rev, ii = fin.get("revenue"), fin.get("interest_income")
    if not rev:
        return _screen(**base, status=NEEDS_REVIEW, note="total revenue not reported in XBRL - cannot calculate")
    ii_share = ii / rev if ii is not None else None
    firm_total = (ii_share or 0) + activity_firm
    if breaches(firm_total, m["limit"], m["op"]):
        return _screen(**base, status=FAIL, value=firm_total,
                       note=f"interest {ii_share or 0:.1%} + non-permitted activities {activity_firm:.1%}")
    problems = []
    if ii_share is None:
        problems.append("interest income not tagged in XBRL - check the income-statement notes")
    if activity_estimate is None or activity_status == NEEDS_REVIEW:
        problems.append("non-permitted activity share is uncertain")
    total = (ii_share or 0) + (activity_estimate or 0)
    detail = f"interest {ii_share:.1%}" if ii_share is not None else "interest unknown"
    detail += f" + activities {activity_estimate:.1%}" if activity_estimate is not None else " + activities unknown"
    if problems:
        return _screen(**base, status=NEEDS_REVIEW, value=None if ii_share is None or activity_estimate is None
                       else total, note="; ".join(problems) + f" ({detail})")
    status = FAIL if breaches(total, m["limit"], m["op"]) else PASS
    return _screen(**base, status=status, value=total, note=detail)


def verdict(fin: dict, business: dict, standard: str, market_cap: dict | None = None) -> dict:
    """Run every screen of ONE standard. market_cap is required for AAOIFI:
    {"value": ..., "note": ...} (12-month average price x shares outstanding)."""
    if standard not in METHODOLOGIES:
        raise ValueError(f"unknown standard {standard!r}")
    meth = METHODOLOGIES[standard]
    screens = []
    act, act_estimate, act_firm = _activity_screen(business, standard)
    screens.append(act)
    for rule in meth["ratios"]:
        screens.append(_ratio_screen(rule, fin, market_cap, standard))
    screens.append(_income_screen(fin, standard, act_estimate, act_firm, act["status"]))
    if fin.get("stale"):
        screens.append(_screen("freshness", "Data freshness", "-", "Screens use the latest reported figures",
                               NEEDS_REVIEW, note=f"balance sheet dated {fin.get('period_end')} is over 15 months old"))

    def say(s):
        val = f" {s['value']:.1%}" if s.get("value") is not None else ""
        lim = f" (limit {s['op']} {s['limit']:.3%})" if s.get("limit") is not None else ""
        return f"{s['label']}{val}{lim}" + (f": {s['note']}" if s.get("note") else "")

    income = next(s for s in screens if s["key"] == "noncompliant_income")
    return {
        "standard": standard, "methodology": {k: meth[k] for k in ("name", "source", "url", "verified_on",
                                                                   "verification_note")},
        "status": worst(s["status"] for s in screens),
        "screens": screens,
        "reasons": [say(s) for s in screens if s["status"] == FAIL],
        "review": [say(s) for s in screens if s["status"] == NEEDS_REVIEW],
        "noncompliant_income_pct": income["value"],
        "activity_share": act_estimate,
        "period_end": fin.get("period_end"), "income_period": fin.get("income_period"),
        "market_cap": market_cap,
    }
