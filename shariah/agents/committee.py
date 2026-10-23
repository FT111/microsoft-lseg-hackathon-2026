"""Orchestrator. Order and precedence: Shariah gate -> Bull + Bear (parallel, independent)
-> Risk reviewer -> Python validation -> Shariah audit. Plain Python, no agent framework."""
from concurrent.futures import ThreadPoolExecutor

from .. import pipeline, signals
from ..methodology import FAIL
from . import analysts, evidence, shariah_checker

DISCLAIMER = "Educational project. Not financial advice. Not a fatwa - passing these screens is not a religious ruling."


def run(result: dict, metrics: dict | None = None, rank_row: dict | None = None, position: dict | None = None,
        stress: list | None = None) -> dict:
    gate = shariah_checker.gate(result)
    pack = evidence.build(result, metrics, rank_row, position, stress)
    base = {"ticker": result["ticker"], "company": result["fin"]["name"], "standard": gate["standard"],
            "gate": gate, "facts": pack.facts, "disclaimer": DISCLAIMER}
    if gate["status"] == FAIL:   # the gate has the final word: nothing to argue about
        return {**base, "ran": False, "bull": None, "bear": None, "risk": None, "audit": None}

    payload = {"stock": f"{pack.company} ({pack.ticker})", "standard": pack.standard,
               "gate_status": gate["status"], "evidence": pack.as_prompt()}
    with ThreadPoolExecutor(max_workers=2) as ex:
        fb, fr = ex.submit(analysts.bull, payload, pack.facts), ex.submit(analysts.bear, payload, pack.facts)
        bull, bear = fb.result(), fr.result()
    risk = analysts.risk(payload, pack.facts, bull, bear)

    statements = {}
    for role, case in (("BU", bull), ("BE", bear)):
        if case.get("thesis"):
            statements[f"{role}0"] = case["thesis"]
        for i, p in enumerate(case["points"], 1):
            statements[f"{role}{i}"] = p["claim"]
        if case.get("change"):
            statements[f"{role}X"] = case["change"]
    for i, p in enumerate(risk["key_risks"], 1):
        statements[f"RK{i}"] = p["claim"]
    if risk.get("summary"):
        statements["RK0"] = risk["summary"]
    audit = shariah_checker.audit(gate, statements)

    # Remove whatever the audit rejected.
    def strip(case, role):
        if case.get("thesis") and f"{role}0" in audit["removed"]:
            case["thesis"] = ""
        if case.get("change") and f"{role}X" in audit["removed"]:
            case["change"] = ""
        case["points"] = [p for i, p in enumerate(case["points"], 1) if f"{role}{i}" not in audit["removed"]]
    strip(bull, "BU")
    strip(bear, "BE")
    risk["key_risks"] = [p for i, p in enumerate(risk["key_risks"], 1) if f"RK{i}" not in audit["removed"]]
    if "RK0" in audit["removed"]:
        risk["summary"] = ""
    audit["removed_text"] = {k: statements[k] for k in audit["removed"]}
    return {**base, "ran": True, "bull": bull, "bear": bear, "risk": risk, "audit": audit}


def run_for_ticker(ticker: str, standard: str, use_ai: bool = True) -> dict:
    """Stand-alone run (used by warm_cache.py): screens the stock, adds price metrics."""
    result = pipeline.screen_one(ticker, standard, use_ai)
    try:
        metrics = signals.price_metrics(ticker)
    except Exception:
        metrics = None
    return run(result, metrics)
