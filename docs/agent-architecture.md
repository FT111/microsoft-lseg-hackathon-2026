# Investment committee — agent architecture

Status: **built** on branch `shariah-agent-committee` (23 Oct 2026). Tests: `tests/test_agents.py`,
`tests/test_shariah_screen.py`. Where the build differs from the original design, it is noted below.

## What the app does today

```
universe.py (32 US tickers)
  -> edgar.py      SEC XBRL financials + 10-K "Item 1" text      (cached in data_cache/)
  -> screen.py     ratio screen (Python) + business screen (LLM via llm.py, SIC-code fallback)
                   -> PASS / FAIL / NEEDS REVIEW with reasons
  -> signals.py    rank the PASS stocks: momentum, volatility, drawdown, Shariah headroom
  -> portfolio.py  inverse-volatility allocation, 2008/2020/2022 stress test, purification
  -> app.py        Streamlit: summary cards + 5 tabs; one-shot "AI analyst note"; "Ask" chat
```

Rule the whole app follows: **the AI reads and explains, Python decides the numbers.**
The agents below keep that rule. They never compute ratios, scores or weights.

## The agents

One gatekeeper and three analysts. The gatekeeper outranks all of them.

| # | Agent | Job | Can it change the outcome? |
|---|---|---|---|
| 1 | **Shariah Compliance Checker** | Decide whether the stock may be considered at all, and audit the final write-up | **Yes - veto.** Its status overrides everything |
| 2 | Bull analyst | Best evidence-backed case for holding the stock | No - advisory |
| 3 | Bear analyst | Best evidence-backed case against | No - advisory |
| 4 | Risk reviewer | Judge both cases, flag unsupported claims, name the risks that matter for this investor | Can add a warning flag; cannot raise a status or change a number |

Order of precedence when they disagree: **Shariah Checker > Risk reviewer > Bull = Bear.**
A bullish case never rescues a FAIL or a NEEDS REVIEW.

## Flow per stock

```
                   ┌──────────────────────────────┐
 Evidence pack ───►│ 1. SHARIAH CHECKER - GATE    │
 (facts F1..Fn,    │  a) ratio screens   (Python) │
  each with source │  b) activity screen (LLM)    │
  URL + period)    │  c) quote check     (Python) │
                   └──────────────┬───────────────┘
              FAIL ◄──────────────┼──────────────► NEEDS REVIEW
          stop here.              │ PASS              agents run, output marked
          show reasons,           ▼                   "conditional"; not allocated
          no bull/bear     ┌─────────────┐  ┌─────────────┐
                           │ 2. BULL     │  │ 3. BEAR     │   run in parallel, can't
                           └──────┬──────┘  └──────┬──────┘   see each other (no anchoring)
                                  └───────┬────────┘
                                          ▼
                                 ┌──────────────────┐
                                 │ 4. RISK REVIEWER │  sees both + risk metrics
                                 └────────┬─────────┘
                                          ▼
                                 ┌──────────────────┐
                                 │ Python validator │  every cited fact exists; every number
                                 └────────┬─────────┘  in the text appears in the pack
                                          ▼
                   ┌──────────────────────────────┐
                   │ 1. SHARIAH CHECKER - AUDIT   │  last word on the final memo
                   └──────────────┬───────────────┘
                                  ▼
                        Committee memo in the UI
```

The Shariah Checker runs **twice**: as a gate before anyone argues, and as an auditor
after. That is what "highest priority" means in practice: it acts first, has the last
word, and nothing downstream can override it.

## 0. Evidence pack (Python, no LLM)

New module `shariah/agents/evidence.py`. Builds one dict per stock from data the app
already has, and gives every fact an ID so agents cite instead of inventing:

```python
{
  "ticker": "MRK", "company": "Merck & Co", "standard": "FTSE Yasaar Global Equity Shariah",
  "facts": {
    "F1": {"label": "Total debt", "value": 3.5e10, "unit": "USD", "period_end": "2026-06-30",
           "source": "XBRL LongTermDebt", "url": "https://data.sec.gov/..."},
    "F7": {"label": "Debt / total assets", "value": 0.29, "limit": 0.3333, "status": "PASS"},
    "F12": {"label": "12-1 momentum", "value": 0.14, "source": "Yahoo adj. close"},
    ...
  },
  "missing": ["receivables not reported in XBRL"],
  "filing_text": "<10-K Item 1 excerpt>",   # untrusted - see Security
}
```

## 1. Shariah Compliance Checker (priority 1)

Module `shariah/agents/shariah_checker.py`.

**Gate - three steps, each producing its own status:**

| Step | Who | Output |
|---|---|---|
| a) Financial ratios: debt, cash + interest-bearing items, receivables + cash, non-compliant income | `screen.py` (Python) | PASS / FAIL / NEEDS REVIEW per ratio, with value, limit, operator, denominator, period |
| b) Business activities: conventional finance, alcohol, pork, gambling, tobacco, and the other exclusions in the FTSE Yasaar rules | LLM reads 10-K Item 1 | per-category finding, estimated revenue share, verbatim quote, confidence |
| c) Quote check | Python | if the LLM's quote is not found word-for-word in the filing text -> NEEDS REVIEW |

**Overall status = worst of the individual statuses** (FAIL > NEEDS REVIEW > PASS).

Hard rules, enforced in Python, not in the prompt:
- Any required input missing -> that screen is NEEDS REVIEW, never treated as 0.
- LLM confidence "low", or estimate within a set margin of the 5% limit -> NEEDS REVIEW.
- LLM reply unreadable or no quote -> NEEDS REVIEW.
- FAIL -> bull, bear and risk agents do not run for this stock (saves cost, and there
  is nothing to argue).
- NEEDS REVIEW -> the committee may run, but the memo is headed "Conditional - a person
  must check X first", and the stock stays out of the allocation (as today).

**Audit (after the debate)** - checks the final memo and returns `approved` or a list of
problems. Python checks first (cheap and certain), LLM second:
- Forbidden wording: "halal", "haram", "Shariah-certified", "guaranteed compliant",
  "fatwa" (except in the disclaimer). Passing the screens is not a religious ruling.
- No suggestion of things the methodology or the app's framing rules out: margin,
  short selling, options/derivatives, conventional bonds, interest-bearing deposits.
- The memo states the Shariah status exactly as the gate produced it, with its
  reporting date.
- If the audit fails: drop the offending agent text and show the gate result alone,
  with a note. Don't loop the LLM to "fix" it during a live demo.

## 2. Bull analyst / 3. Bear analyst

Built in `shariah/agents/analysts.py` (one file for all three analysts). Same input (evidence pack + gate result, read-only),
opposite brief. Output JSON:

```json
{"thesis": "one sentence",
 "points": [{"claim": "...", "facts": ["F12", "F7"]}],
 "what_would_change_my_mind": "..."}
```

- Every point must cite at least one fact ID. Points with no valid citation are dropped
  by the validator and the drop is shown.
- The bull may cite Shariah headroom as a strength; the bear must raise it if headroom
  is low (stock may breach a limit and have to be sold).
- No price targets, no predictions, "invest and hold" framing.

## 4. Risk reviewer

In `analysts.py`. Sees the evidence pack, bull and bear output, and the risk numbers
already computed in Python (volatility, worst 1-year fall, stress-test years, headroom,
position size in the allocation).

Output JSON:

```json
{"stronger_case": "bull" | "bear" | "balanced",
 "unsupported_claims": ["..."],
 "key_risks": [{"risk": "...", "facts": ["F15"]}],
 "flag": null | "concentration" | "near Shariah limit" | "data stale" | "data missing",
 "summary_for_investor": "2-3 plain sentences"}
```

The flag is shown in the UI next to the stock. It does **not** change the score or
weight - those stay in `signals.py` / `portfolio.py`.

## Shared plumbing

`shariah/agents/base.py`:
- `run_agent(name, system, payload) -> dict` - wraps `llm.ask` (so every call is
  cached in `data_cache/` and the demo replays offline), extracts JSON, retries once
  on unreadable JSON, then gives up with a NEEDS REVIEW-style "agent unavailable" result.
- `validate(output, pack)` - fact IDs exist; any number written in the text matches a
  fact value (within rounding); otherwise the sentence is removed and logged.

`shariah/agents/committee.py` - plain Python orchestrator (no agent framework needed):

```python
def run(ticker, pack) -> dict:
    gate = shariah_checker.gate(pack)
    if gate["status"] == "FAIL":
        return {"gate": gate, "memo": None}
    bull, bear = run_parallel(bull_agent, bear_agent, pack, gate)
    risk = risk_agent(pack, gate, bull, bear)
    memo = compose(gate, bull, bear, risk)          # Python template, not LLM
    audit = shariah_checker.audit(memo, gate)
    return {"gate": gate, "bull": bull, "bear": bear, "risk": risk,
            "memo": memo if audit["approved"] else None, "audit": audit}
```

Cost: up to 5 LLM calls per stock (gate activity screen, bull, bear, risk, audit). Run it
on demand for the selected stock in the "Analyst view", and pre-warm the demo stocks in
`warm_cache.py`.

## UI (app.py, "Investment committee" tab)

A dedicated tab with a "Convene the committee" button for any screened company:
1. Shariah gate banner at the top - status, each screen's value vs limit, quote with
   10-K link and reporting date. Always shown, even if the LLM is off.
2. Bull and bear side by side, each point with its fact chips (hover -> source).
3. Risk reviewer box with any flag.
4. Audit line: "Shariah audit: approved" or what was removed and why.

## Security

- 10-K text is untrusted. Pass it inside clear delimiters and tell the model to ignore
  any instructions in it. Only the Shariah Checker's activity step sees raw filing text;
  bull, bear and risk see the evidence pack only.
- API key stays in `.env` (`OPENAI_API_KEY`), as now.

## Tests (fictional data, clearly labelled)

`tests/test_agents.py`, with `llm.ask` mocked:
- FAIL gate -> bull/bear/risk never called.
- Quote not in the filing text -> NEEDS REVIEW.
- Missing receivables / cash / interest income -> NEEDS REVIEW, not 0.
- Ratio exactly at the limit -> the operator the methodology specifies.
- Validator drops a claim with a made-up number or a non-existent fact ID.
- Audit rejects a memo containing "halal" or recommending margin.
- Unreadable LLM JSON -> "agent unavailable", app keeps running.

## Fixed before building the Shariah Checker

1. **Two standards** - kept, as requested, but strictly separate: each run uses ONE standard from
   `shariah/methodology.py`; no rule is shared or combined.
2. **Thresholds verified** - FTSE Yasaar against the official Ground Rules v4.6 (Feb 2026), rules
   4.3.1-4.4. AAOIFI SS 21 clause 3/4 via the Muscat Stock Exchange's published guide (official text is
   subscription-only). Operators: FTSE ratios `<`, FTSE income `<=` ("should not exceed"), AAOIFI `<=`.
   AAOIFI's old 30% receivables rule was removed - it is not in the verified text.
3. **Missing data** - required figures that are missing are `None` and give NEEDS REVIEW. All
   balance-sheet items now come from one reporting date (previously each item could come from a
   different quarter). Revenue now uses the latest period across all revenue tags (Apple was
   previously read from 2018).
4. **Excluded activities** - both standards' full lists are implemented, including alcohol vendors,
   non-halal food, cannabis, cinema, music, hotels and weapons (FTSE) and the MSX/AAOIFI list. The AI
   also gets every sentence in the whole 10-K that mentions a screened activity.
5. **Quotes checked** - every AI quote is matched word-for-word against the filing text in Python.
6. **Status name** - `NEEDS REVIEW` everywhere.
7. **Interest** - interest income counts in the non-compliant income screen; "cash and interest-bearing
   items" includes short-term investments, and long-term interest-bearing securities send the screen to
   NEEDS REVIEW if they would break the limit.
