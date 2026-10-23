"""Shariah screening methodologies, written down as data so every rule carries its
source, clause, exact wording, threshold and comparison operator.

The two standards are kept completely separate. A screen is always run against ONE
standard; nothing here combines their rules.

Verified on 2026-10-23 against:
- FTSE Yasaar: "FTSE Yasaar Global Equity Shariah Index Series Ground Rules", v4.6,
  February 2026, rules 4.3.1, 4.3.2 and 4.4 (official LSEG / FTSE Russell PDF).
- AAOIFI: Shari'ah Standard No. 21 (Financial Papers), clause 3/4, as reproduced in the
  Muscat Stock Exchange "MSX Shariah Services Guide" (an exchange index that applies
  AAOIFI SS 21). The AAOIFI text itself sits behind a subscription and was NOT read
  directly - see VERIFICATION_NOTE in the AAOIFI entry.
"""

PASS, FAIL, NEEDS_REVIEW = "PASS", "FAIL", "NEEDS REVIEW"
STATUSES = (PASS, FAIL, NEEDS_REVIEW)
_SEVERITY = {PASS: 0, NEEDS_REVIEW: 1, FAIL: 2}


def worst(statuses) -> str:
    """Overall status = the most severe individual status (FAIL > NEEDS REVIEW > PASS)."""
    statuses = list(statuses)
    return max(statuses, key=_SEVERITY.__getitem__) if statuses else NEEDS_REVIEW


def breaches(value: float, limit: float, op: str) -> bool:
    """True when `value` does NOT satisfy the rule `value <op> limit`."""
    if op == "<":
        return not value < limit
    if op == "<=":
        return not value <= limit
    raise ValueError(f"unknown operator {op!r}")


# Business activities the AI looks for in the 10-K. These are FACT categories only;
# each standard below decides which of them it counts.
ACTIVITY_CATEGORIES = {
    "conventional_finance": "conventional (interest-based) banking, lending, mortgages or other finance",
    "conventional_insurance": "conventional (non-takaful) insurance",
    "alcohol": "alcohol or other intoxicants, anywhere in the chain: making, distributing, storing, "
               "selling (including retail sales), bars and restaurants serving it",
    "tobacco": "tobacco in any form: cigarettes, cigars, e-cigarettes, vapes, shisha, raw tobacco",
    "cannabis": "cannabis in any form",
    "pork": "pork or pork-related products",
    "non_halal_food": "other non-halal food production, packaging or processing (e.g. meat not slaughtered "
                      "to Islamic requirements)",
    "gambling": "casinos, gambling, betting, lotteries",
    "cinema": "cinema, film or TV entertainment production/distribution",
    "music": "music production, distribution or streaming",
    "adult_entertainment": "pornography or adult entertainment",
    "hotels": "hotels",
    "weapons_defence": "weapons, arms or defence manufacturing",
}

FTSE_PDF = ("https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/"
            "ftse-yasaar-global-equity-shariah-index-series-ground-rules.pdf")
MSX_PDF = ("https://www.msx.om/MSMDOCS/downloads/en_1701852937802_MSX%20Shariah%20%20Index%20rulebook%20E%20Updated.pdf")

METHODOLOGIES = {
    "FTSE Yasaar": {
        "name": "FTSE Yasaar Global Equity Shariah Index Series",
        "source": "FTSE Yasaar Global Equity Shariah Index Series Ground Rules v4.6 (February 2026)",
        "url": FTSE_PDF,
        "verified_on": "2026-10-23",
        "verification_note": "Thresholds, operators and the activity list are quoted from rules 4.3.1-4.3.2 of "
                             "the official ground rules.",
        # Rule 4.3.1 - non-permitted business sectors "should not exceed 5% of total revenue".
        "activity": {
            "clause": "4.3.1", "limit": 0.05, "op": "<=",
            "text": "Companies involved in the following activities will be considered to be non-permitted "
                    "business sectors (should not exceed 5% of total revenue)",
            "groups": {
                "A. conventional finance (non-Islamic banking, finance and insurance, etc.)":
                    ["conventional_finance", "conventional_insurance"],
                "B. alcohol and intoxicants (entire process chain, incl. distributors, vendors, bars, restaurants)":
                    ["alcohol"],
                "C. pork-related products and non-halal food production, packaging and processing":
                    ["pork", "non_halal_food"],
                "D. entertainment (casinos, gambling, cinema, music, pornography and hotels)":
                    ["gambling", "cinema", "music", "adult_entertainment", "hotels"],
                "E. tobacco in all its forms (incl. e-cigarettes, vapes, shisha) and cannabis in any form":
                    ["tobacco", "cannabis"],
                "F. weapons, arms and defence manufacturing": ["weapons_defence"],
            },
        },
        # Rule 4.3.2 A-C. Numerator / denominator names refer to keys in edgar.financials().
        "ratios": [
            {"key": "debt", "clause": "4.3.2 A", "label": "Debt / total assets",
             "numerator": ["total_debt"], "denominator": "total_assets", "limit": 1 / 3, "op": "<",
             "text": "debt is less than 33.333% of total assets"},
            {"key": "cash", "clause": "4.3.2 B", "label": "Cash and interest-bearing items / total assets",
             "numerator": ["cash_and_interest_bearing"], "denominator": "total_assets", "limit": 1 / 3, "op": "<",
             "text": "cash and Interest-bearing items are less than 33.333% of total assets"},
            # The rule says "accounts receivable and cash". We use cash AND interest-bearing items
            # (the same numerator as rule B), which is the stricter reading.
            {"key": "receivables_plus_cash", "clause": "4.3.2 C", "label": "Receivables + cash / total assets",
             "numerator": ["receivables", "cash_and_interest_bearing"], "denominator": "total_assets",
             "limit": 0.50, "op": "<",
             "text": "accounts receivable and cash are less than 50% of total assets"},
        ],
        # Rule 4.3.2 D - interest income counts as non-compliant income.
        "income": {"clause": "4.3.2 D", "limit": 0.05, "op": "<=",
                   "text": "total interest and non-compliant activities income should not exceed 5% of total revenue"},
        # Rule 4.3.2 (last paragraph): companies whose compliance changes between quarters are monitored
        # while debt or cash ratios sit within 33.333% +/- 5% (below 31.667% and 35% or above).
        "monitoring_band": {"ratios": ["debt", "cash"], "low": 0.31667, "high": 0.35,
                            "text": "Companies that change financial compliance between two successive quarters "
                                    "will be monitored to check if their debt and/or cash/interest bearing ratios "
                                    "fall within 33.333% +/- 5%"},
        "purification": {"clause": "4.4", "method": "dividends",
                         "text": "Appropriate purification of dividends at 5%. This ratio calculates the "
                                 "recommended purification amount to be paid by the investor."},
    },
    "AAOIFI": {
        "name": "AAOIFI Shari'ah Standard No. 21 (Financial Papers: Shares and Bonds)",
        "source": "AAOIFI SS 21 clause 3/4, as applied in the MSX Shariah Services Guide (Muscat Stock Exchange)",
        "url": MSX_PDF,
        "verified_on": "2026-10-23",
        "verification_note": "The official AAOIFI text is subscription-only and was not read directly. Thresholds, "
                             "wording and the activity list come from the MSX guide, which states it applies AAOIFI "
                             "standards. Treat AAOIFI results as less firmly verified than FTSE Yasaar. The guide's "
                             "summary table writes '<30%' and '<5%', but its quotation of the clause says 'should "
                             "not exceed'; we follow the clause wording (<=). A value exactly at a limit is "
                             "vanishingly rare in practice.",
        "activity": {
            "clause": "3/4 (MSX list of prohibited commercial activities)", "limit": 0.05, "op": "<=",
            "text": "The amount of revenue resulting from a prohibited item should not exceed 5% of the company's "
                    "total revenues",
            "groups": {
                "Forbidden financial services (non-takaful insurance, mortgages, traditional banking)":
                    ["conventional_finance", "conventional_insurance"],
                "Alcohol and tobacco": ["alcohol", "tobacco"],
                "Pork": ["pork"],
                "Gambling": ["gambling"],
                "Cinema": ["cinema"],
                "Music": ["music"],
                "Adult entertainment": ["adult_entertainment"],
                "Hotels proven to be in violation of Shariah": ["hotels"],
                "Arms and defense": ["weapons_defence"],
            },
        },
        "ratios": [
            {"key": "debt", "clause": "3/4/2", "label": "Interest-bearing debt / market value",
             "numerator": ["total_debt"], "denominator": "market_cap", "limit": 0.30, "op": "<=",
             "text": "The total amount borrowed with usury, whether it is a long-term or short-term loan, should "
                     "not exceed 30% of the market value of the company's total shares"},
            {"key": "cash", "clause": "3/4/3", "label": "Interest-bearing deposits / market value",
             "numerator": ["cash_and_interest_bearing"], "denominator": "market_cap", "limit": 0.30, "op": "<=",
             "text": "The total amount deposited with usury, whether the deposit period is short, medium, or long, "
                     "should not exceed 30% of the market value of the company's total shares"},
        ],
        "income": {"clause": "3/4/4", "limit": 0.05, "op": "<=",
                   "text": "The amount of revenue resulting from a prohibited item should not exceed 5% of the "
                           "company's total revenues, whether this revenue results from practicing a prohibited "
                           "activity or from owning a prohibited item"},
        "market_value_note": "Market value = 12-month average share price x shares outstanding, following the "
                             "MSX guide (\"<30% of the average market value for 12 months\").",
        "monitoring_band": None,
        "purification": {"clause": "3/4/6", "method": "income_per_share",
                         "text": "Prohibited income per share x number of shares held (MSX guide, AAOIFI SS 21 "
                                 "clause 3/4/6)."},
    },
}

STANDARDS = list(METHODOLOGIES)


def counted_categories(standard: str) -> set[str]:
    return {c for cats in METHODOLOGIES[standard]["activity"]["groups"].values() for c in cats}
