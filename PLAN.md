# Waqf Analyst - plan, timeline and sketch

**One sentence:** an AI analyst for a UK mosque's waqf (endowment) with $100,000 -
it screens stocks for Shariah compliance with the evidence for every verdict,
splits the money with transparent maths, and shows what a bad year means in
scholarships.

> Educational hackathon project. Not financial advice. Not a fatwa - the output
> is what a Shariah board would review, not a ruling.

## The client

- UK mosque waqf, $100,000, must last forever (capital preserved).
- Pays out ~4% a year (~$4,000) = **8 scholarships at $500**.
- Must be Shariah-compliant: no interest, no prohibited businesses.

## How it works

```
 SEC EDGAR financials ──► ratio screen (Python) ──┐
                                                  ├─► PASS / FAIL / REVIEW  ──► allocation (Python) ──► stress test + purification
 SEC 10-K "Item 1" text ──► business screen (AI) ─┘      + evidence + source       60% equities           "2022 = 6 scholarships"
                                                                                   30% sukuk (SPSK)       "donate $X of dividends"
                                                                                   10% non-interest cash
                                          AI coach answers trustees' questions ONLY from these results
```

- **AI reads, maths decides.** The AI only reads 10-K text (what share of revenue
  is non-compliant, with a quote). Ratios, weights, stress test and purification
  are plain Python - repeatable and explainable.
- **Two standards, one toggle:** FTSE Shariah (LSEG's own index, ratios vs total
  assets) and AAOIFI (ratios vs market cap). Some companies flip - show it live.
- **REVIEW, not guess:** missing data -> "needs human review".

## Screen sketch

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ WAQF ANALYST                     Educational project · Not advice · Not fatwa │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ CLIENT        │ [1 Screening] [2 Allocation] [3 Stress & purification] [4 Ask]│
│ Endowment $   │                                                              │
│  100,000      │  ┌ PASS 18 ┐ ┌ FAIL 11 ┐ ┌ REVIEW 3 ┐                        │
│ Standard      │                                                              │
│ (•) FTSE      │  Ticker  Verdict  Debt   Cash  Non-compl.  Why / Evidence     │
│ ( ) AAOIFI    │  AAPL    PASS     22%    17%    0.3%      meets all screens  │
│ Payout 4%     │  JPM     FAIL     7%     ..     100%      conventional bank  │
│ Scholarship   │  LMT     FAIL     34%    ..     100%      "...missiles..."   │
│  $500         │  XOM     PASS     7%     4%     0.0%      ...                │
│ Equities 60%  │                                                              │
│ Sukuk    30%  │  Tab 2: sunburst of the $100k + table of holdings            │
│ [x] AI reads  │  Tab 3: 2008 / 2020 / 2022 -> scholarships; $ to purify      │
│     10-Ks     │  Tab 4: preset questions + chat ("Why was JPM excluded?")    │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

## What's built (in this repo)

| File | Does | Status |
|---|---|---|
| `shariah/edgar.py` | SEC financials + 10-K business text, cached | works |
| `shariah/screen.py` | FTSE + AAOIFI ratio rules, PASS/FAIL/REVIEW with reasons | works |
| `shariah/prices.py` | Price history (Yahoo chart API, Stooq backup), cached | works |
| `shariah/portfolio.py` | Inverse-volatility weights, sleeves, stress test, purification | works |
| `shariah/llm.py` | AI business screen + coach (Azure, key from `.env`) | **untested - needs key** |
| `app.py` | Streamlit app, 4 tabs | **not yet run** |
| `smoke_test.py` | Pipeline check without the UI | passes (AAPL/XOM pass, JPM/MO/LMT fail) |

Run: copy `.env.example` to `.env`, add the key, then
`pip install openai python-dotenv streamlit pandas plotly requests` and
`streamlit run app.py`.

## Timeline (today)

| Time | Goal | Who |
|---|---|---|
| **13:30-14:00** | Everyone runs `smoke_test.py` and `streamlit run app.py`; fix anything broken | all |
| **14:00-14:45** | AI business screen working on 10 companies (check quotes make sense) | Chuen |
| | Universe final (~30), check verdicts vs SPUS / HLAL holdings, note agreement % | Saba |
| | Allocation + stress test look right; warm the cache for all tickers | Frederick |
| | Slides skeleton: client, problem, how it works, demo, why trust it | Benjamin |
| **14:45-15:30** | AI coach + memo; FTSE vs AAOIFI "flip" example found | Chuen + Frederick |
| | Purification + scholarships numbers sanity-checked | Saba |
| **15:30-16:00** | Polish: theme, captions, one screen recording as backup | all |
| **16:00** | **FEATURE FREEZE** - commit `data_cache/` so the demo runs offline | |
| **16:00-17:30** | Rehearse the 8-minute demo out loud twice; prepare Q&A | all |

## 8-minute demo script

1. **(1 min)** The client: a mosque waqf, $100k, 8 scholarships a year, must be halal.
2. **(2 min)** Screening live: a bank fails (business), Lockheed fails (defence),
   Apple passes. Toggle FTSE -> AAOIFI: one company flips. Every verdict has a quote + link.
3. **(1.5 min)** The split: 60/30/10, why inverse-volatility, "matches SPUS on X%".
4. **(1.5 min)** Stress test: "in a 2008-type year, 6 scholarships instead of 8."
   Purification: "donate $X of this year's dividends."
5. **(1 min)** Ask: "Why was JPM excluded?" - the coach answers from the data.
6. **(1 min)** Why trust it: AI reads, maths decides; REVIEW instead of guessing;
   checked against real Shariah ETFs; built on LSEG's own FTSE Shariah rules.

## Q&A prep

- *How accurate is it?* -> agreement % with SPUS/HLAL, and what we checked by hand.
- *Why not let the AI pick stocks?* -> not repeatable or auditable; trustees need reasons.
- *Is this a fatwa?* -> no; it's the evidence pack a Shariah board would review.
