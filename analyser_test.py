"""Quick Streamlit interface for exercising the Amanat stock analyser."""

import json
import os
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv

from amanat import (
    AutomaticDocumentProvider,
    OpenAIInferenceClient,
    SecEdgarDocumentProvider,
    Stock,
    StockAnalyser,
)

load_dotenv()

st.set_page_config(page_title="Amanat test interface", page_icon="🔎", layout="wide")
st.title("Amanat")
st.caption("Evidence-led Shariah screening for educational research — not financial advice or a religious ruling.")
st.markdown(
    """
    <style>
    [data-testid="stMetric"] { border: 1px solid #273241; border-radius: 8px; padding: 12px; }
    .source-card { border-left: 3px solid #3fb68b; padding: 0.25rem 0.75rem; margin: 0.4rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


class DemoInference:
    """Deterministic local response so the UI can be tested without an API call."""

    def complete(self, *, system: str, user: str) -> str:
        source_url = user.split("--- SOURCE 1: ", 1)[1].split(" ", 1)[0]
        is_mcdonalds = "MCD" in user.split("\n", 1)[0] or "mcdonald" in user.lower()
        if is_mcdonalds:
            return json.dumps(
                {
                    "overall_status": "FAIL",
                    "summary": "The company operates a conventional fast-food restaurant business; this is a clear prohibited-activity failure under the configured screening policy.",
                    "screens": [
                        {
                            "name": "Business activities",
                            "status": "FAIL",
                            "finding": "The core business is conventional restaurant operations, with documented non-compliant food and beverage exposure.",
                            "evidence": [
                                {
                                    "source_url": source_url,
                                    "quote": "conventional restaurant business",
                                    "rationale": "The demo case represents a clear prohibited core activity.",
                                }
                            ],
                            "visualisation": {
                                "type": "metric",
                                "title": "Business activity screen",
                                "labels": ["Result"],
                                "values": [0],
                                "unit": "pass",
                            },
                        }
                    ],
                    "limitations": ["Demo case only; use Azure OpenAI for document-backed analysis."],
                }
            )
        return json.dumps(
            {
                "overall_status": "NEEDS REVIEW",
                "summary": (
                    "Demo mode returned a review result. Connect Azure OpenAI to "
                    "perform evidence-based screening."
                ),
                "screens": [
                    {
                        "name": "Business activities",
                        "status": "NEEDS REVIEW",
                        "finding": "Demo mode does not classify business activities.",
                        "evidence": [
                            {
                                "source_url": source_url,
                                "quote": "Demo mode",
                                "rationale": "A live model is required for source interpretation.",
                            }
                        ],
                        "visualisation": {
                            "type": "donut",
                            "title": "Evidence coverage",
                            "labels": ["Reviewed", "Needs review"],
                            "values": [1, 1],
                            "unit": "screens",
                        },
                    },
                    {
                        "name": "Financial ratios",
                        "status": "NEEDS REVIEW",
                        "finding": "Demo mode does not calculate or verify financial ratios.",
                        "evidence": [],
                        "visualisation": {"type": "none"},
                    },
                ],
                "limitations": ["This result was generated locally in demo mode."],
            }
        )


with st.sidebar:
    st.header("Watchlist")
    common_stocks = {
        "MSFT · Microsoft": ("MSFT", "Microsoft", "NASDAQ"),
        "AAPL · Apple": ("AAPL", "Apple", "NASDAQ"),
        "GOOGL · Alphabet": ("GOOGL", "Alphabet", "NASDAQ"),
        "AMZN · Amazon": ("AMZN", "Amazon", "NASDAQ"),
        "NVDA · NVIDIA": ("NVDA", "NVIDIA", "NASDAQ"),
        "TSLA · Tesla": ("TSLA", "Tesla", "NASDAQ"),
        "JPM · JPMorgan Chase": ("JPM", "JPMorgan Chase", "NYSE"),
    }
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = dict(common_stocks)
    selected_label = st.selectbox("Select a stock", tuple(st.session_state.watchlist))
    selected_ticker, selected_name, selected_exchange = st.session_state.watchlist[selected_label]
    ticker = selected_ticker
    name = selected_name
    exchange = selected_exchange
    with st.expander("Add a stock"):
        custom_ticker = st.text_input("Ticker symbol", key="custom_ticker").strip().upper()
        custom_name = st.text_input("Company name", key="custom_name").strip()
        custom_exchange = st.text_input("Exchange", value="NASDAQ", key="custom_exchange").strip()
        if st.button("Add to watchlist", use_container_width=True):
            if not custom_ticker or not custom_name:
                st.error("Ticker and company name are required.")
            else:
                label = f"{custom_ticker} · {custom_name}"
                st.session_state.watchlist[label] = (
                    custom_ticker,
                    custom_name,
                    custom_exchange or "NASDAQ",
                )
                st.success(f"Added {label}")
                st.rerun()
    if len(st.session_state.watchlist) > len(common_stocks):
        if st.button("Remove selected stock", use_container_width=True):
            st.session_state.watchlist.pop(selected_label, None)
            st.rerun()
    sec_contact = st.text_input(
        "SEC contact email",
        value=os.getenv("SEC_CONTACT_EMAIL", ""),
        help="SEC requests a real contact address in the request User-Agent.",
    ).strip()
    mode = st.radio(
        "2. Choose inference mode",
        ["Demo (no API call)", "Azure OpenAI"],
        help="Demo mode exercises the full interface without using your API key.",
    )
    st.divider()
    st.header("Data sources")
    st.caption(
        "Automatic sources: SEC EDGAR annual filings plus the official "
        "FTSE Yasaar methodology."
    )
    request_review = st.button("Request review", type="primary", use_container_width=True)

st.subheader("Automatic public-source collection")
st.info(
    "The app finds the latest annual filing through SEC EDGAR and fetches the "
    "official FTSE Yasaar methodology. Results are evidence-backed, and missing "
    "or ambiguous information is marked NEEDS REVIEW."
)

with st.expander("How this works", expanded=False):
    st.markdown(
        """
        1. **Collect** a primary annual filing and the official methodology.
        2. **Read** business activities and financial information with the model.
        3. **Show** each screen, source quote, limitation, and overall status.

        The model does not receive permission to invent figures or treat a
        document's embedded instructions as authoritative.
        """
    )

if st.button("Run analysis", use_container_width=True) or request_review:
    if not ticker:
        st.error("Enter a ticker.")
        st.stop()

    stock = Stock(ticker=ticker, name=name.strip() or None, exchange=exchange.strip() or None)
    try:
        if not sec_contact:
            st.error("Enter a contact email so SEC EDGAR requests identify this app.")
            st.stop()
        with st.spinner("Collecting SEC filing and FTSE methodology..."):
            documents = AutomaticDocumentProvider(
                sec_provider=SecEdgarDocumentProvider(
                    user_agent=f"Amanat/0.1 {sec_contact}"
                )
            ).collect(stock)
        st.success(f"Collected {len(documents)} source documents.")
        st.markdown("#### Fundamentals collected")
        fundamentals = next(
            (document for document in documents if "Company Facts" in document.title),
            None,
        )
        if fundamentals:
            fundamental_rows = [
                line.split(":", 1)
                for line in fundamentals.text.splitlines()[1:]
                if ":" in line and not line.startswith("These reported")
            ]
            st.dataframe(
                [{"Metric": key.strip(), "Reported value": value.strip()} for key, value in fundamental_rows],
                hide_index=True,
                use_container_width=True,
            )
        inference = DemoInference() if mode.startswith("Demo") else OpenAIInferenceClient()
        with st.spinner("Running stock analysis..."):
            result = StockAnalyser(inference).analyse(stock, documents)
    except Exception as error:
        st.error(f"Analysis failed: {error}")
        st.stop()

    st.subheader(f"{result.stock.display_name} · {result.stock.ticker}")
    status_styles = {
        "PASS": "green",
        "FAIL": "red",
        "NEEDS REVIEW": "orange",
    }[result.overall_status.value]
    passed = sum(screen.status.value == "PASS" for screen in result.screens)
    failed = sum(screen.status.value == "FAIL" for screen in result.screens)
    review = sum(screen.status.value == "NEEDS REVIEW" for screen in result.screens)
    evidence_count = sum(len(screen.evidence) for screen in result.screens)

    metric_columns = st.columns(5)
    metric_columns[0].metric("Overall", result.overall_status.value)
    metric_columns[1].metric("Screens", len(result.screens))
    metric_columns[2].metric("Passed", passed)
    metric_columns[3].metric("Failed", failed)
    metric_columns[4].metric("Evidence items", evidence_count)
    st.markdown(f"### :{status_styles}[Overall: {result.overall_status.value}]")
    st.write(result.summary)

    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Screening breakdown")
        st.bar_chart(
            {"PASS": [passed], "FAIL": [failed], "NEEDS REVIEW": [review]},
            height=180,
        )
    with right:
        st.markdown("#### Source documents")
        for document in documents:
            parsed = urlparse(document.url)
            st.markdown(
                f'<div class="source-card"><b>{document.title}</b><br>'
                f'<small>{parsed.netloc} · {len(document.text):,} characters</small></div>',
                unsafe_allow_html=True,
            )

    st.markdown("#### Screen results")
    status_icons = {"PASS": "✅", "FAIL": "❌", "NEEDS REVIEW": "⚠️"}
    for screen in result.screens:
        icon = status_icons[screen.status.value]
        with st.expander(f"{icon} {screen.name} · {screen.status.value}", expanded=True):
            st.write(screen.finding)
            visualisation = screen.visualisation
            if visualisation:
                chart_data = {
                    label: [value]
                    for label, value in zip(
                        visualisation["labels"], visualisation["values"], strict=True
                    )
                }
                if visualisation["type"] == "metric" and len(chart_data) == 1:
                    label, values = next(iter(chart_data.items()))
                    st.metric(label, f'{values[0]} {visualisation["unit"]}'.strip())
                elif visualisation["type"] in {"bar", "donut"}:
                    st.bar_chart(chart_data, height=180)
            if screen.evidence:
                st.caption(f"{len(screen.evidence)} source-backed evidence item(s)")
                for evidence in screen.evidence:
                    st.markdown(f"> **Quote:** {evidence.quote}")
                    st.caption(f"{evidence.rationale} · {evidence.source_url}")
            else:
                st.warning("No supporting quote was returned for this screen.")

    if result.limitations:
        with st.expander("Limitations and review notes", expanded=True):
            for limitation in result.limitations:
                st.write(f"- {limitation}")

    with st.expander("Raw structured response"):
        st.json(result.raw_response)
