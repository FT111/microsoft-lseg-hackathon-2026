"""Shariah AI analyst - Streamlit app.  Run:  streamlit run app.py
Educational hackathon project. Not financial advice. Not a fatwa."""
import html
import json

import pandas as pd
import plotly.express as px
import streamlit as st

from shariah import edgar, llm, portfolio, prices, screen, signals
from shariah.universe import SUKUK_ETF, UNIVERSE

st.set_page_config(page_title="Halal Stock Analyst", page_icon="✦", layout="wide")

# Look and feel follows the team's "Amanat" mock (origin/main): Alice-blue page, Baltic-blue accents,
# white rounded cards, DM Sans body + Space Grotesk headings.
BLUES = ["#05668d", "#427aa1", "#77a6c2", "#a8c9df", "#d2e4ef", "#0b3c5d", "#5c95b8", "#8fb8d2",
         "#034b68", "#9fc2d8", "#2f6f95", "#bcd6e6"]
SIGNAL_COLOURS = {"Strong candidate": "#05668d", "Watch": "#77a6c2", "Lower priority": "#a8c9df",
                  "Watch - near Shariah limit": "#c8553d"}
STATUS_LABEL = {"PASS": "✅ Pass", "FAIL": "❌ Fail", "REVIEW": "🔎 Needs review"}

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {--baltic:#05668d; --cerulean:#427aa1; --alice:#ebf2fa; --ink:#123047; --muted:#6e8799;
       --line:rgba(5,102,141,.12); --pass:#2a9d8f; --fail:#c8553d; --review:#c9971c;}
html, body, [data-testid="stAppViewContainer"] {background:var(--alice); color:var(--ink); font-family:'DM Sans',sans-serif;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stDecoration"], footer {display:none;}
.block-container {padding-top:1rem; max-width:1240px;}
h1, h2, h3 {font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.04em; color:var(--ink);}

[data-testid="stSidebar"] {background:#ffffff; border-right:1px solid var(--line);}
[data-testid="stSidebar"] h2 {font-size:1.15rem;}

.topbar {display:flex; align-items:center; justify-content:space-between; padding:.6rem 0 0;}
.brand {color:var(--baltic); font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:700; letter-spacing:-.04em;}
.brand-mark {display:inline-grid; width:27px; height:27px; margin-right:.45rem; place-items:center; border-radius:9px;
             background:var(--baltic); color:var(--alice); font-size:.9rem;}
.topbar-note {color:var(--muted); font-size:.8rem;}
.hero {margin:1.8rem 0 1.8rem; animation:arrive .9s cubic-bezier(.22,1,.36,1) both;}
.eyebrow {color:var(--cerulean); font-size:.78rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase;}
.hero h1 {max-width:760px; margin:.5rem 0 .7rem; font-size:clamp(2.2rem,4.4vw,3.9rem); letter-spacing:-.06em; line-height:1; padding:0;}
.hero p {max-width:620px; margin:0; color:var(--muted); font-size:1.03rem; line-height:1.6;}
@keyframes arrive {from {opacity:0; transform:translateY(18px);} to {opacity:1; transform:none;}}

.section-heading {display:flex; align-items:end; justify-content:space-between; margin:2rem 0 .8rem;}
.section-title {font-family:'Space Grotesk',sans-serif; font-size:1.4rem; font-weight:600; letter-spacing:-.04em; color:var(--ink);}
.section-heading span {color:var(--muted); font-size:.8rem;}

.stats {display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:1rem;}
@media (min-width:1100px) {.stats.five {grid-template-columns:repeat(5,1fr);}}
.card {padding:1.15rem 1.3rem; border:1px solid var(--line); border-radius:22px; background:rgba(255,255,255,.75);
       box-shadow:0 14px 35px rgba(35,72,99,.055);}
.label {color:var(--muted); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase;}
.big {margin:.3rem 0 .15rem; font-family:'Space Grotesk',sans-serif; font-size:1.8rem; font-weight:600; letter-spacing:-.05em;}
.sub {color:var(--muted); font-size:.8rem; line-height:1.45;}
.good {color:var(--pass);} .bad {color:var(--fail);}

.row {display:grid; grid-template-columns:1fr auto; gap:.15rem 1rem; align-items:center; padding:.85rem 0; border-bottom:1px solid var(--line);}
.row:last-child {border-bottom:0;}
.name {font-size:.95rem; font-weight:700;}
.meta {color:var(--muted); font-size:.78rem;}
.score {color:var(--baltic); font-weight:700;}
.tag {display:inline-block; margin-top:.45rem; padding:.22rem .6rem; border-radius:999px; font-size:.7rem; font-weight:700;
      background:rgba(66,122,161,.12); color:var(--cerulean);}
.tag.warn {background:rgba(200,85,61,.12); color:var(--fail);}

/* Streamlit containers made with key="panel_*" render as cards */
[class*="st-key-panel"] {padding:1.2rem 1.3rem; border:1px solid var(--line); border-radius:22px; background:rgba(255,255,255,.75);
                         box-shadow:0 14px 35px rgba(35,72,99,.055);}

.stTabs [data-baseweb="tab-list"] {gap:.4rem; border-bottom:0;}
.stTabs [data-baseweb="tab"] {padding:.45rem 1rem; border-radius:999px !important; background:rgba(255,255,255,.7); border:1px solid var(--line);}
.stTabs button[role="tab"] {border-radius:999px !important; padding:.45rem 1rem !important;}
.stTabs [aria-selected="true"] {background:var(--baltic); color:#fff !important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none;}

.stButton > button {border:1px solid rgba(5,102,141,.18); border-radius:999px; background:var(--cerulean); color:var(--alice) !important; font-weight:700;}
.stButton > button:hover {border-color:var(--baltic); background:var(--baltic);}
[data-testid="stDataFrame"] {border-radius:14px; overflow:hidden;}
.disclaimer {margin-top:2.5rem; color:var(--muted); font-size:.75rem; text-align:center;}
</style>""", unsafe_allow_html=True)


def card(label: str, value: str, sub: str = "", cls: str = "") -> str:
    return (f'<div class="card"><div class="label">{label}</div><div class="big {cls}">{value}</div>'
            f'<div class="sub">{sub}</div></div>')


def heading(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-heading"><div class="section-title">{title}</div><span>{note}</span></div>', unsafe_allow_html=True)


def styled(fig, height=340):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="DM Sans, sans-serif", color="#123047"), height=height,
                      margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    return fig


# ---------------- sidebar: the client ----------------
with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">✦</span>Your plan</div>', unsafe_allow_html=True)
    st.caption("Tell us about you - everything on the page updates as you change these.")
    amount = st.number_input("How much are you investing? ($)", 1_000, 10_000_000, 100_000, step=5_000)
    risk = st.radio("How much ups and downs can you live with?", list(signals.PROFILES), index=1, horizontal=True,
                    help="Cautious favours steadier stocks; Adventurous favours stronger recent momentum.")
    top_n = st.slider("How many stocks to hold", 3, 20, 10)
    with st.expander("More options"):
        standard = st.radio("Shariah screening standard", list(screen.STANDARDS),
                            help="FTSE measures ratios against total assets; AAOIFI against market value.")
        eq = st.slider("Share in Shariah stocks", 0.5, 1.0, 1.0, 0.05)
        sk = st.slider("Sukuk (Islamic bonds)", 0.0, 1.0 - eq, 0.0, 0.05) if eq < 1.0 else 0.0
        use_llm = st.toggle("Use AI to read annual reports (10-Ks)", value=llm.available(), disabled=not llm.available(),
                            help="Needs OPENAI_API_KEY in .env. Without it, a rule on the SEC industry code is used.")
        tickers = st.multiselect("Stocks to consider", UNIVERSE, default=UNIVERSE)


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
    if fin["name"].isupper():
        fin = {**fin, "name": fin["name"].title()}
    return {"fin": fin, "sic": sub["sicDescription"], "mcap": mcap, "business": business, "verdict": v}


results, errors = {}, []
with st.spinner("Checking companies against the Shariah screens..."):
    for t in tickers:
        try:
            results[t] = screen_one(t, standard, use_llm)
        except Exception as e:  # keep the demo alive; show what failed
            errors.append(f"{t}: {e}")

counts = {s: sum(r["verdict"]["status"] == s for r in results.values()) for s in STATUS_LABEL}
passing = [t for t, r in results.items() if r["verdict"]["status"] == "PASS"]
ranking = signals.rank({t: results[t] for t in passing}, screen.STANDARDS[standard], signals.PROFILES[risk]) if passing else pd.DataFrame()
picks = [] if ranking.empty else ranking[~ranking["signal"].str.startswith("Watch - near")]["ticker"].head(top_n).tolist()

alloc = portfolio.build(picks or passing, amount, eq, sk, SUKUK_ETF) if (picks or passing) else None
stt = pur = None
if alloc is not None:
    try:
        stt = portfolio.stress_test(alloc, amount=amount)
        nc = {t: results[t]["verdict"]["noncompliant_income_pct"] for t in passing}
        pur = portfolio.purification(alloc, {t: results[t]["fin"] for t in passing}, nc)
    except Exception as e:
        errors.append(f"stress test / purification: {e}")

# ---------------- header + "your plan" summary ----------------
st.markdown(f"""
<div class="topbar"><div class="brand"><span class="brand-mark">✦</span>Halal Stock Analyst</div>
<div class="topbar-note">Educational project · Not financial advice · Not a fatwa</div></div>
<div class="hero"><div class="eyebrow">Your plan, screened for Shariah</div>
<h1>Halal investing, explained.</h1>
<p>We check {len(results)} US companies against the {html.escape(standard)} rules, rank the ones that pass for a
<b>{risk.lower()}</b> investor, and show what that means for your ${amount:,.0f} - with the evidence behind every verdict.</p></div>
""", unsafe_allow_html=True)

heading("Your plan at a glance", f"{standard} standard · {risk} profile")
worst = stt.loc[stt["portfolio_return"].idxmin()] if stt is not None and not stt.empty else None
cards = [
    card("Invested", f"${amount:,.0f}", f"{eq:.0%} Shariah stocks" + (f" · {sk:.0%} sukuk" if sk else "")),
    card("Companies that pass", f"{counts['PASS']} of {len(results)}",
         f"{counts['FAIL']} fail · {counts['REVIEW']} need a person to check"),
    card("Stocks in your plan", str(len(picks or passing)), "Top-ranked, max 10% in any one"),
    card(f"In a bad year ({int(worst['year'])})" if worst is not None else "In a bad year",
         f"${worst['value_after']:,.0f}" if worst is not None else "-",
         f"{worst['gain_or_loss']:+,.0f} vs today" if worst is not None else "Not enough price history",
         "bad" if worst is not None and worst["gain_or_loss"] < 0 else ""),
    card("Give to charity this year", f"${pur['to_purify'].sum():,.2f}" if pur is not None and not pur.empty else "$0.00",
         "Purification of dividends"),
]
st.markdown(f'<div class="stats five">{"".join(cards)}</div>', unsafe_allow_html=True)

if alloc is not None:
    heading("Where your money goes", "Calmer stocks get more")
    left, right = st.columns([1, 1.2], gap="large")
    with left, st.container(key="panel_donut"):
        st.markdown(f'<div class="label">Portfolio value</div><div class="big">${amount:,.0f}</div>', unsafe_allow_html=True)
        names = {r["ticker"]: r["company"] for _, r in ranking.iterrows()} if not ranking.empty else {}
        donut = alloc.assign(label=alloc["holding"].map(lambda h: names.get(h, h)))
        fig = px.pie(donut, names="label", values="amount", hole=.62, color_discrete_sequence=BLUES)
        fig.update_traces(textinfo="none", hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>")
        fig.update_layout(legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", yanchor="top"))
        st.plotly_chart(styled(fig, 460), width="stretch")
    with right, st.container(key="panel_top"):
        st.markdown(f'<div class="label">Top picks for a {risk.lower()} investor</div>', unsafe_allow_html=True)
        rows = []
        for _, r in ranking.head(5).iterrows():
            share = alloc.set_index("holding")["amount"].get(r["ticker"])
            rows.append(f'<div class="row"><div><div class="name">{html.escape(r["company"])}</div>'
                        f'<div class="meta">{r["ticker"]} · {r["return_1y"]:+.0%} over the past year'
                        + (f" · ${share:,.0f} in your plan" if share else "") + '</div>'
                        f'<span class="tag{" warn" if r["signal"].startswith("Watch - near") else ""}">{r["signal"]}</span></div>'
                        f'<div class="score">{r["score"]:.0f}/100</div></div>')
        st.markdown("".join(rows) or '<div class="sub">No compliant stocks to rank yet.</div>', unsafe_allow_html=True)

# ---------------- details ----------------
heading("Explore the details", "Every number can be traced to its source")
tab_screen, tab_picks, tab_alloc, tab_stress, tab_ask = st.tabs(
    ["Shariah check", "Stock picks", "Your portfolio", "Bad years & charity", "Ask the analyst"])

with tab_screen:
    rows = []
    for t, r in results.items():
        v, b = r["verdict"], r["business"]
        base = v["ratios"].get(screen.STANDARDS[standard]["denominator"], {})
        rows.append({"Ticker": t, "Company": r["fin"]["name"], "Result": STATUS_LABEL[v["status"]],
                     "Debt ratio": base.get("debt"), "Cash ratio": base.get("cash"),
                     "Non-compliant income": v["noncompliant_income_pct"],
                     "Why": "; ".join(v["reasons"] + v["review"]) or "meets all screens",
                     "Evidence from annual report": b.get("evidence", ""), "Checked by": b.get("method")})
    df = pd.DataFrame(rows)
    show = st.segmented_control("Show", ["All"] + list(STATUS_LABEL.values()), default="All", key="screen_filter")
    if show and show != "All" and not df.empty:
        df = df[df["Result"] == show]
    st.dataframe(df, width="stretch", hide_index=True, column_config={
        "Debt ratio": st.column_config.NumberColumn(format="percent"),
        "Cash ratio": st.column_config.NumberColumn(format="percent"),
        "Non-compliant income": st.column_config.NumberColumn(format="percent")})
    st.caption(f"Standard: {standard}. Ratios from SEC EDGAR (latest annual report). \"Needs review\" means there "
               "isn't enough data to decide - we flag it rather than guess.")
    if errors:
        with st.expander(f"{len(errors)} items could not be loaded"):
            st.write(errors)

with tab_picks:
    if ranking.empty:
        st.info("No compliant stocks to rank yet.")
    else:
        st.plotly_chart(styled(px.bar(ranking, x="ticker", y="score", color="signal",
                                      color_discrete_map=SIGNAL_COLOURS,
                                      labels={"ticker": "", "score": "Score (0-100)"})), width="stretch")
        show = ranking[["ticker", "company", "signal", "score", "price", "return_1y", "momentum_12_1",
                        "volatility", "max_drawdown_1y", "headroom"]]
        st.dataframe(show, width="stretch", hide_index=True, column_config={
            "ticker": "Ticker", "company": "Company", "signal": "Signal",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
            "price": st.column_config.NumberColumn("Price", format="dollar"),
            "return_1y": st.column_config.NumberColumn("1-year return", format="percent"),
            "momentum_12_1": st.column_config.NumberColumn("Momentum", format="percent"),
            "volatility": st.column_config.NumberColumn("Volatility", format="percent"),
            "max_drawdown_1y": st.column_config.NumberColumn("Worst fall (1y)", format="percent"),
            "headroom": st.column_config.NumberColumn("Room below Shariah limit", format="percent")})
        st.caption("Score = momentum + steadiness + smaller falls + room below the Shariah limits, weighted for your risk "
                   "appetite. A stock close to a limit may have to be sold if it breaches it. This ranks candidates; "
                   "it does not predict prices.")

        with st.container(key="panel_analyst"):
            st.subheader("Analyst view")
            pick = st.selectbox("Pick a stock", ranking["ticker"].tolist(),
                                format_func=lambda t: f"{t} · {ranking.set_index('ticker').loc[t, 'company']}")
            row = ranking.set_index("ticker").loc[pick]
            r = results[pick]
            st.markdown(f"**{row['signal']}** · {signals.reasons(row)}")
            st.markdown("**Shariah check:** " + ("; ".join(r["verdict"]["reasons"] + r["verdict"]["review"]) or "meets all screens")
                        + (f" · evidence: “{r['business'].get('evidence')}”" if r["business"].get("evidence") else ""))
            if llm.available() and st.button(f"Write the AI analyst note for {pick}"):
                facts = {"ticker": pick, "company": row["company"], "signal": row["signal"], "score": round(row["score"]),
                         "metrics": {k: round(float(row[k]), 4) for k in ("return_1y", "momentum_12_1", "volatility",
                                                                           "max_drawdown_1y", "headroom")},
                         "shariah": {"standard": standard, "status": r["verdict"]["status"],
                                     "evidence": r["business"].get("evidence")}}
                with st.spinner("Writing the note..."):
                    st.markdown(llm.ask(
                        "You are an equity analyst writing for a Shariah-conscious investor. Using ONLY the JSON facts, write: "
                        "1) a two-sentence view, 2) three bullet reasons for, 3) two bullet risks (include Shariah-compliance "
                        "risk if headroom is low), 4) what would change the view. No price targets. No invented numbers. "
                        "End with: Educational project, not financial advice.", json.dumps(facts, default=str)))

with tab_alloc:
    if alloc is None:
        st.info("No stocks pass yet.")
    else:
        st.plotly_chart(styled(px.sunburst(alloc, path=["sleeve", "holding"], values="amount",
                                           color_discrete_sequence=BLUES), 420), width="stretch")
        st.dataframe(alloc, width="stretch", hide_index=True, column_order=["holding", "sleeve", "weight", "amount"],
                     column_config={"holding": "Holding", "sleeve": "Type",
                                    "weight": st.column_config.NumberColumn("Share", format="percent"),
                                    "amount": st.column_config.NumberColumn("Amount", format="dollar")})
        st.caption("Top-ranked compliant stocks, inverse-volatility weights (calmer stocks get more), max 10% each. "
                   "Deterministic maths - the AI does not choose the numbers.")

with tab_stress:
    if stt is None:
        st.info("Build a portfolio first.")
    else:
        st.subheader(f"What past years would have done to your ${amount:,.0f}")
        year_cards = [card(str(int(y["year"])), f"${y['value_after']:,.0f}",
                           f"{y['gain_or_loss']:+,.0f} ({y['portfolio_return']:+.0%})"
                           + (f"<br>No data for {html.escape(y['no_data_for'])}" if y["no_data_for"] else ""),
                           "good" if y["gain_or_loss"] >= 0 else "bad") for _, y in stt.iterrows()]
        st.markdown(f'<div class="stats">{"".join(year_cards)}</div>', unsafe_allow_html=True)
        st.caption("2008: financial crisis · 2020: Covid crash and recovery · 2022: rate-rise sell-off. "
                   "Holdings that didn't exist yet count as 0%.")
        st.subheader("Purification - the share of your dividends to give to charity")
        if pur is not None and not pur.empty:
            st.markdown(f'<div class="stats">{card("To donate this year", f"${pur["to_purify"].sum():,.2f}", "Dividends × the company’s non-compliant income share")}</div>',
                        unsafe_allow_html=True)
            st.dataframe(pur, width="stretch", hide_index=True, column_config={
                "holding": "Holding",
                "dividend_yield": st.column_config.NumberColumn("Dividend yield", format="percent"),
                "dividend_received": st.column_config.NumberColumn("Dividends you'd receive", format="dollar"),
                "noncompliant_share": st.column_config.NumberColumn("Non-compliant income", format="percent"),
                "to_purify": st.column_config.NumberColumn("To donate", format="dollar")})
        else:
            st.info("None of your holdings pay dividends that need purifying.")

with tab_ask:
    if not llm.available():
        st.info("Add OPENAI_API_KEY to .env to enable the AI coach.")
    else:
        context = {"investor": {"type": "individual Muslim investor", "amount": amount, "risk_appetite": risk,
                                "standard": standard},
                   "screen": {t: {"status": r["verdict"]["status"], "reasons": r["verdict"]["reasons"],
                                  "review": r["verdict"]["review"], "evidence": r["business"].get("evidence")}
                              for t, r in results.items()},
                   "stock_ranking": ranking.drop(columns=[c for c in ranking.columns if c.startswith("s_")]).to_dict("records") if not ranking.empty else [],
                   "allocation": alloc.to_dict("records") if alloc is not None else []}
        system = ("You explain a Shariah-compliant stock recommendation to an everyday Muslim investor. Answer ONLY from "
                  "the JSON context. If the answer is not in it, say so. Plain English, short. Not financial advice.\n"
                  + json.dumps(context, default=str))
        presets = ["Which stocks look strongest and why?", "Why was this split chosen?", "Which companies failed and why?",
                   "What would a bad year do to my money?", "What would make you change this?"]
        st.caption("Try a question, or type your own below. Answers come only from the results on this page.")
        cols = st.columns(len(presets))
        q = None
        for col, p in zip(cols, presets):
            if col.button(p, width="stretch"):
                q = p
        q = st.chat_input("Ask about this recommendation") or q
        if q:
            st.chat_message("user").write(q)
            with st.spinner("Thinking..."):
                st.chat_message("assistant").write(llm.ask(system, q))

st.markdown('<div class="disclaimer">Educational hackathon project (Microsoft × LSEG 2026). Not financial advice. '
            'Not a fatwa - this is the evidence a Shariah scholar would review, not a ruling.</div>', unsafe_allow_html=True)
