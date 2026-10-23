"""Bull analyst, Bear analyst and Risk reviewer. Advisory only: they explain, they never
change a status, score or weight. Their output is validated in Python (base.py) and then
audited by the Shariah Compliance Checker."""
from .base import COMMON_RULES, clean_sentence, run_agent, validate_points

POINT_SCHEMA = """{"thesis": "<one sentence>",
 "points": [{"claim": "<one or two sentences>", "facts": ["F1", "F2"]}],
 "what_would_change_my_mind": "<one sentence>"}"""

BULL_SYSTEM = COMMON_RULES + f"""
Your role: BULL ANALYST. Make the strongest honest case FOR holding this stock for the long term.
At most 3 points. If the facts give little support, say so - do not stretch.
Reply with JSON only: {POINT_SCHEMA}"""

BEAR_SYSTEM = COMMON_RULES + f"""
Your role: BEAR ANALYST. Make the strongest honest case AGAINST holding this stock.
At most 3 points. You must raise Shariah-compliance risk if headroom below a limit is small
(under 25%) or any screen is NEEDS REVIEW: if a screen is breached, the stock would no longer pass the
investor's screening policy and would have to be sold.
Reply with JSON only: {POINT_SCHEMA}"""

RISK_SYSTEM = COMMON_RULES + """
Your role: RISK REVIEWER. You receive the evidence pack and the bull and bear cases. Do not take a
side for the sake of it. Name claims that the cited facts do not actually support, the risks that
matter most for this investor, and one flag if needed.
Reply with JSON only:
{"stronger_case": "bull"|"bear"|"balanced",
 "unsupported_claims": ["<short description>"],
 "key_risks": [{"claim": "<risk in one sentence>", "facts": ["F1"]}],
 "flag": null | "concentration" | "near Shariah limit" | "data stale" | "data missing" | "high volatility",
 "summary_for_investor": "<2-3 plain sentences>"}"""

FLAGS = {None, "concentration", "near Shariah limit", "data stale", "data missing", "high volatility"}


def _case(system: str, payload: dict, facts: dict, role: str) -> dict:
    out = run_agent(system, payload)
    if not out:
        return {"role": role, "available": False, "points": [], "dropped": [], "thesis": "", "change": ""}
    points, dropped = validate_points(out.get("points"), facts)
    thesis, d1 = clean_sentence(out.get("thesis"), facts)
    change, d2 = clean_sentence(out.get("what_would_change_my_mind"), facts)
    return {"role": role, "available": True, "thesis": thesis, "points": points[:3], "change": change,
            "dropped": dropped + d1 + d2}


def bull(payload: dict, facts: dict) -> dict:
    return _case(BULL_SYSTEM, payload, facts, "bull")


def bear(payload: dict, facts: dict) -> dict:
    return _case(BEAR_SYSTEM, payload, facts, "bear")


def risk(payload: dict, facts: dict, bull_case: dict, bear_case: dict) -> dict:
    p = {**payload, "bull_case": {k: bull_case.get(k) for k in ("thesis", "points")},
         "bear_case": {k: bear_case.get(k) for k in ("thesis", "points")}}
    out = run_agent(RISK_SYSTEM, p)
    if not out:
        return {"role": "risk", "available": False, "key_risks": [], "dropped": [], "summary": "", "flag": None,
                "stronger_case": None, "unsupported_claims": []}
    risks, dropped = validate_points(out.get("key_risks"), facts)
    summary, d1 = clean_sentence(out.get("summary_for_investor"), facts)
    flag = out.get("flag") if out.get("flag") in FLAGS else None
    stronger = out.get("stronger_case") if out.get("stronger_case") in ("bull", "bear", "balanced") else None
    return {"role": "risk", "available": True, "stronger_case": stronger, "key_risks": risks[:4],
            "unsupported_claims": [str(x)[:200] for x in (out.get("unsupported_claims") or [])][:5],
            "flag": flag, "summary": summary, "dropped": dropped + d1}
