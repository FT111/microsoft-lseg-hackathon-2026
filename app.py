"""Shariah AI analyst - Streamlit app.  Run:  streamlit run app.py
Educational hackathon project. Not financial advice. Not a fatwa."""
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from shariah import edgar, llm, portfolio, prices, screen, signals
from shariah.universe import SUKUK_ETF, UNIVERSE

st.set_page_config(page_title="Waqf Analyst", layout="wide")
st.markdown("""<style>
div[data-testid="stMetric"] {border:1px solid #24303d; border-radius:6px; padding:10px 14px;}
.block-container {padding-top:1.5rem;}
</style>""", unsafe_allow_html=True)

st.title("Waqf Analyst")
st.caption("AI-assisted Shariah screening and allocation for a mosque endowment · "
           "Educational hackathon project. Not financial advice. Not a fatwa.")

# ---------------- sidebar: the client ----------------
with st.sidebar:
    st.header("Client")
    amount = st.number_input("Endowment ($)", 10_000, 10_000_000, 100_000, step=10_000)
    standard = st.radio("Screening standard", list(screen.STANDARDS))
    payout = st.slider("Annual payout to scholarships", 0.02, 0.06, 0.04, 0.005, format="%.3f")
    cost = st.number_input("Cost of one scholarship ($)", 100, 10_000, 500, step=100)
    top_n = st.slider("Stocks to hold", 3, 20, 10)
    eq = st.slider("Share in Shariah stocks", 0.5, 1.0, 1.0, 0.05)
    sk = st.slider("Sukuk (optional)", 0.0, 1.0 - eq, 0.0, 0.05) if eq < 1.0 else 0.0
    use_llm = st.toggle("Use AI to read 10-Ks", value=llm.available(), disabled=not llm.available(),
                        help="Needs OPENAI_API_KEY in .env. Without it, a rule on the SEC industry code is used.")
    tickers = st.multiselect("Universe", UNIVERSE, default=UNIVERSE)


# ---------------- screening ----------------
@st.cache_data(show_spinner=False)
def screen_one(t: str, std: str, use_ai: bool):
    fin = edgar.financials(t)
    sub = edgar.submissions(t)
    try:
        mcap = (fin["shares_outstanding"] or 0) * prices.last_price(t)
    except Exception:
        mcap = None
    if use_ai:
        item1 = edgar.business_section(t)
        business = llm.business_screen(fin["name"], item1["text"]) if item1["text"] else screen.sic_rule(sub["sicDescription"])
        business["source_url"] = item1.get("url")
    else:
        business = screen.sic_rule(sub["sicDescription"])
        business["source_url"] = (sub.get("latest_10k") or {}).get("url")
    v = screen.verdict(fin, mcap, business, std)
    return {"fin": fin, "sic": sub["sicDescription"], "mcap": mcap, "business": business, "verdict": v}


tab_screen, tab_picks, tab_alloc, tab_stress, tab_ask = st.tabs(["1 · Screening", "2 · Stock picks", "3 · Allocation", "4 · Stress test & purification", "5 · Ask"])

results, errors = {}, []
with st.spinner("Screening..."):
    for t in tickers:
        try:
            results[t] = screen_one(t, standard, use_llm)
        except Exception as e:  # keep the demo alive; show what failed
            errors.append(f"{t}: {e}")

with tab_screen:
    rows = []
    for t, r in results.items():
        v, b = r["verdict"], r["business"]
        base = v["ratios"].get(screen.STANDARDS[standard]["denominator"], {})
        rows.append({"Ticker": t, "Company": r["fin"]["name"], "Verdict": v["status"],
                     "Debt": base.get("debt"), "Cash": base.get("cash"),
                     "Non-compliant income": v["noncompliant_income_pct"],
                     "Why": "; ".join(v["reasons"] + v["review"]) or "meets all screens",
                     "Evidence": b.get("evidence", ""), "Method": b.get("method")})
    df = pd.DataFrame(rows)
    c1, c2, c3 = st.columns(3)
    for col, s in zip((c1, c2, c3), ("PASS", "FAIL", "REVIEW")):
        col.metric(s.title(), int((df["Verdict"] == s).sum()) if not df.empty else 0)
    st.dataframe(df, use_container_width=True, hide_index=True, column_config={
        "Debt": st.column_config.NumberColumn(format="percent"),
        "Cash": st.column_config.NumberColumn(format="percent"),
        "Non-compliant income": st.column_config.NumberColumn(format="percent")})
    st.caption(f"Standard: {standard}. Ratios from SEC EDGAR XBRL (latest 10-K). REVIEW = not enough data to decide - "
               "we flag rather than guess.")
    if errors:
        with st.expander(f"{len(errors)} tickers could not be loaded"):
            st.write(errors)

passing = [t for t, r in results.items() if r["verdict"]["status"] == "PASS"]
ranking = signals.rank({t: results[t] for t in passing}, screen.STANDARDS[standard]) if passing else pd.DataFrame()
picks = [] if ranking.empty else ranking[~ranking["signal"].str.startswith("Watch - near")]["ticker"].head(top_n).tolist()

with tab_picks:
    if ranking.empty:
        st.info("No compliant stocks to rank yet.")
    else:
        a, b, c = st.columns(3)
        a.metric("Compliant stocks", len(ranking))
        b.metric("Strong candidates", int((ranking["signal"] == "Strong candidate").sum()))
        c.metric("Near a Shariah limit", int(ranking["signal"].str.startswith("Watch - near").sum()))
        st.plotly_chart(px.bar(ranking, x="ticker", y="score", color="signal", template="plotly_dark",
                               color_discrete_map={"Strong candidate": "#3FB68B", "Watch": "#D4A72C",
                                                   "Lower priority": "#6B7785", "Watch - near Shariah limit": "#E5534B"}),
                        use_container_width=True)
        show = ranking[["ticker", "company", "signal", "score", "price", "return_1y", "momentum_12_1",
                        "volatility", "max_drawdown_1y", "headroom"]]
        st.dataframe(show, use_container_width=True, hide_index=True, column_config={
            "score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f"),
            "price": st.column_config.NumberColumn(format="dollar"),
            **{k: st.column_config.NumberColumn(format="percent") for k in
               ("return_1y", "momentum_12_1", "volatility", "max_drawdown_1y", "headroom")}})
        st.caption("Score = 35% momentum (12-1 month) + 25% low volatility + 15% smaller drawdown + 25% compliance "
                   "headroom. Headroom = distance below the nearest Shariah limit: a stock close to a limit may have "
                   "to be sold if it breaches it. This ranks candidates; it does not predict prices.")

        st.subheader("Analyst view")
        pick = st.selectbox("Stock", ranking["ticker"].tolist())
        row = ranking.set_index("ticker").loc[pick]
        r = results[pick]
        st.write(f"**{row['signal']}** · {signals.reasons(row)}")
        st.write("Shariah screen: " + ("; ".join(r["verdict"]["reasons"] + r["verdict"]["review"]) or "meets all screens")
                 + (f" · evidence: “{r['business'].get('evidence')}”" if r["business"].get("evidence") else ""))
        if llm.available() and st.button(f"Write the AI analyst note for {pick}"):
            facts = {"ticker": pick, "company": row["company"], "signal": row["signal"], "score": round(row["score"]),
                     "metrics": {k: round(float(row[k]), 4) for k in ("return_1y", "momentum_12_1", "volatility",
                                                                       "max_drawdown_1y", "headroom")},
                     "shariah": {"standard": standard, "status": r["verdict"]["status"],
                                 "evidence": r["business"].get("evidence")}}
            st.markdown(llm.ask(
                "You are an equity analyst writing for a Shariah-conscious investor. Using ONLY the JSON facts, write: "
                "1) a two-sentence view, 2) three bullet reasons for, 3) two bullet risks (include Shariah-compliance "
                "risk if headroom is low), 4) what would change the view. No price targets. No invented numbers. "
                "End with: Educational project, not financial advice.", json.dumps(facts, default=str)))

with tab_alloc:
    if not (picks or passing):
        st.info("No stocks pass yet.")
    else:
        alloc = portfolio.build(picks or passing, amount, eq, sk, SUKUK_ETF)
        st.session_state["alloc"] = alloc
        a, b, c = st.columns(3)
        a.metric("Holdings", len(alloc))
        b.metric("Annual payout", f"${amount * payout:,.0f}")
        c.metric("Scholarships / year", int(amount * payout // cost))
        st.plotly_chart(px.sunburst(alloc, path=["sleeve", "holding"], values="amount",
                                    template="plotly_dark"), use_container_width=True)
        st.dataframe(alloc, use_container_width=True, hide_index=True,
                     column_config={"weight": st.column_config.NumberColumn(format="percent"),
                                    "amount": st.column_config.NumberColumn(format="dollar")})
        st.caption("Equities: inverse-volatility weights (calmer stocks get more), max 10% of the fund each. "
                   "Deterministic maths - the AI does not choose the numbers.")

with tab_stress:
    alloc = st.session_state.get("alloc")
    if alloc is not None:
        stt = portfolio.stress_test(alloc, payout_rate=payout, scholarship_cost=cost, amount=amount)
        st.subheader("What a bad year means for scholarships")
        st.dataframe(stt, use_container_width=True, hide_index=True,
                     column_config={"portfolio_return": st.column_config.NumberColumn(format="percent"),
                                    "value_after": st.column_config.NumberColumn(format="dollar")})
        nc = {t: results[t]["verdict"]["noncompliant_income_pct"] for t in passing}
        pur = portfolio.purification(alloc, {t: results[t]["fin"] for t in passing}, nc)
        st.subheader("Purification - dividends to donate")
        if not pur.empty:
            st.metric("To donate this year", f"${pur['to_purify'].sum():,.2f}")
            st.dataframe(pur, use_container_width=True, hide_index=True)

with tab_ask:
    if not llm.available():
        st.info("Add OPENAI_API_KEY to .env to enable the AI coach.")
    else:
        context = {"client": {"type": "UK mosque waqf", "amount": amount, "payout": payout,
                              "scholarship_cost": cost, "standard": standard},
                   "screen": {t: {"status": r["verdict"]["status"], "reasons": r["verdict"]["reasons"],
                                  "review": r["verdict"]["review"], "evidence": r["business"].get("evidence")}
                              for t, r in results.items()},
                   "stock_ranking": ranking.drop(columns=[c for c in ranking.columns if c.startswith("s_")]).to_dict("records") if not ranking.empty else [],
                   "allocation": st.session_state["alloc"].to_dict("records")
                   if st.session_state.get("alloc") is not None else []}
        system = ("You explain an investment recommendation to the trustees of a mosque endowment. Answer ONLY from "
                  "the JSON context. If the answer is not in it, say so. Plain English, short. Not financial advice.\n"
                  + json.dumps(context, default=str))
        presets = ["Which stocks look strongest and why?", "Why was this split chosen?", "Which companies failed and why?",
                   "What happens to scholarships in a bad year?", "What would make you change this?"]
        cols = st.columns(len(presets))
        q = None
        for col, p in zip(cols, presets):
            if col.button(p):
                q = p
        q = st.chat_input("Ask about this recommendation") or q
        if q:
            st.chat_message("user").write(q)
            st.chat_message("assistant").write(llm.ask(system, q))
