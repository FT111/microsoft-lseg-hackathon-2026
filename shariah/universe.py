"""The stocks we screen. A deliberate mix: some should pass, some should fail on
business activity (banks, alcohol, tobacco, defence, entertainment, hotels), and
some sit near the financial-ratio thresholds."""

UNIVERSE = [
    # tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "ADBE", "CSCO", "TXN", "INTC",
    # consumer / retail
    "AMZN", "TSLA", "NKE", "HD", "COST", "PG", "KO", "PEP", "WMT",
    # healthcare
    "JNJ", "LLY", "ABT", "MRK", "UNH",
    # energy
    "XOM", "CVX",
    # expected business-activity fails
    "JPM", "BAC", "MO", "LMT", "DIS", "MAR", "STZ",
]

# Sukuk (Islamic bond) ETF used for the fixed-income sleeve.
SUKUK_ETF = "SPSK"

# Real Shariah ETFs to compare our verdicts against (holdings checked by hand).
REFERENCE_ETFS = ["SPUS", "HLAL", "ISWD"]
