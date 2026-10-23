"""Shariah screening. Financial ratios are plain arithmetic on SEC data - no LLM.
Business activity uses the LLM to read the 10-K (see llm.py), with a rule-based
fallback on the SEC industry code so the app still works without a key.

Thresholds:
- FTSE Shariah (Yasaar), LSEG's own index series - denominator: total assets.
- AAOIFI Standard 21 - denominator: market capitalisation.
Check both against the official methodology before quoting them as exact.
"""

STANDARDS = {
    "FTSE Shariah (Yasaar)": {
        "denominator": "total_assets",
        "debt": 1 / 3, "cash": 1 / 3, "receivables_plus_cash": 0.50, "receivables": None,
        "noncompliant_revenue": 0.05,
    },
    "AAOIFI": {
        "denominator": "market_cap",
        "debt": 0.30, "cash": 0.30, "receivables_plus_cash": None, "receivables": 0.30,
        "noncompliant_revenue": 0.05,
    },
}

# SEC SIC descriptions that are excluded outright (fallback when no LLM).
EXCLUDED_SIC_WORDS = {
    "bank": "conventional finance", "savings institution": "conventional finance",
    "insurance": "conventional insurance", "hospital & medical service plans": "conventional insurance",
    "security brokers": "conventional finance", "finance services": "conventional finance",
    "cigarettes": "tobacco", "tobacco": "tobacco",
    "malt beverages": "alcohol", "wines": "alcohol", "distilled": "alcohol", "liquor": "alcohol",
    "hotels": "hotels / entertainment", "amusement": "entertainment / gambling",
    "motion picture": "entertainment", "television broadcasting": "entertainment",
    "guided missiles": "weapons / defence", "ordnance": "weapons / defence",
    "aircraft": "possible defence - check",
}


def sic_rule(sic_description: str) -> dict:
    d = (sic_description or "").lower()
    for word, why in EXCLUDED_SIC_WORDS.items():
        if word in d:
            return {"noncompliant_pct": 100.0 if "check" not in why else None,
                    "categories": [why], "evidence": f"SEC industry code: {sic_description}",
                    "confidence": "rule", "method": "SIC rule"}
    return {"noncompliant_pct": 0.0, "categories": [], "evidence": f"SEC industry code: {sic_description}",
            "confidence": "rule", "method": "SIC rule"}


# Yahoo Finance industry names (used for UK / non-SEC companies). "check" -> REVIEW, not FAIL.
EXCLUDED_INDUSTRY_WORDS = {
    "banks": "conventional finance", "credit services": "conventional finance",
    "mortgage finance": "conventional finance", "capital markets": "conventional finance",
    "financial conglomerates": "conventional finance", "insurance": "conventional insurance",
    "asset management": "conventional finance - check", "tobacco": "tobacco",
    "brewers": "alcohol", "wineries & distilleries": "alcohol", "gambling": "gambling",
    "casinos": "gambling", "lodging": "hotels / entertainment", "entertainment": "entertainment",
    "aerospace & defense": "possible defence - check", "reit": "real estate - check income sources",
}


def industry_rule(sector: str | None, industry: str | None) -> dict:
    d = f"{sector or ''} / {industry or ''}".lower()
    for word, why in EXCLUDED_INDUSTRY_WORDS.items():
        if word in d:
            return {"noncompliant_pct": 100.0 if "check" not in why else None,
                    "categories": [why], "evidence": f"Yahoo Finance industry: {industry}",
                    "confidence": "rule", "method": "Industry rule"}
    return {"noncompliant_pct": 0.0, "categories": [], "evidence": f"Yahoo Finance industry: {industry}",
            "confidence": "rule", "method": "Industry rule"}


def ratios(fin: dict, market_cap: float | None) -> dict:
    ta = fin.get("total_assets") or 0
    out = {}
    for base_name, base in (("total_assets", ta), ("market_cap", market_cap or 0)):
        if not base:
            continue
        out[base_name] = {
            "debt": fin["total_debt"] / base,
            "cash": fin["cash_and_interest_bearing"] / base,
            "receivables": fin["receivables"] / base,
            "receivables_plus_cash": (fin["receivables"] + fin["cash_and_interest_bearing"]) / base,
        }
    rev = fin.get("revenue") or 0
    out["interest_income_pct"] = (fin["interest_income"] / rev) if rev else None
    return out


def verdict(fin: dict, market_cap: float | None, business: dict, standard: str) -> dict:
    """Pass / Fail / Review with every reason spelled out."""
    rules = STANDARDS[standard]
    r = ratios(fin, market_cap)
    base = r.get(rules["denominator"])
    reasons, review = [], []

    if base is None:
        review.append(f"no {rules['denominator'].replace('_', ' ')} available")
    else:
        for key in ("debt", "cash", "receivables", "receivables_plus_cash"):
            limit = rules[key]
            if limit is None:
                continue
            val = base[key]
            label = key.replace("_", " ")
            if val >= limit:
                reasons.append(f"{label} {val:.1%} >= {limit:.1%} of {rules['denominator'].replace('_', ' ')}")
        if fin["total_debt"] == 0 and fin["sources"]["total_debt"] == "not reported":
            review.append("debt not reported in XBRL - check the balance sheet")

    nc = business.get("noncompliant_pct")
    ii = r.get("interest_income_pct") or 0
    borderline = (business.get("method") == "LLM" and business.get("confidence") == "low"
                  and nc is not None and 2 <= nc <= 15)
    if nc is None:
        review.append("business activity unclear: " + "; ".join(business.get("categories", [])))
    elif borderline:
        review.append(f"AI estimate of non-compliant revenue ~{nc:.0f}% is low-confidence and near the "
                      f"5% limit ({', '.join(business.get('categories') or [])}) - a person should check")
    if nc is not None and not borderline:
        total_nc = min(1.0, nc / 100 + ii)
        if total_nc > rules["noncompliant_revenue"]:
            cats = ", ".join(business.get("categories") or []) or "interest income"
            reasons.append(f"non-compliant income ~{total_nc:.1%} ({cats}) > {rules['noncompliant_revenue']:.0%}")

    status = "FAIL" if reasons else ("REVIEW" if review else "PASS")
    return {"status": status, "reasons": reasons, "review": review, "ratios": r,
            "noncompliant_income_pct": None if nc is None else min(1.0, nc / 100 + ii)}
