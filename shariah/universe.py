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

# London-listed (FTSE 100) - the UK market Amanat targets. Same idea: likely passes,
# likely business-activity fails (banks, insurers, tobacco, alcohol, gambling, hotels, defence).
UK_UNIVERSE = [
    "AZN.L", "GSK.L", "HIK.L", "ULVR.L", "RKT.L", "TSCO.L", "SBRY.L", "NXT.L", "JD.L", "ABF.L",
    "SHEL.L", "BP.L", "RIO.L", "AAL.L", "GLEN.L", "REL.L", "EXPN.L", "AUTO.L", "RMV.L", "HLMA.L",
    "SGE.L", "CRDA.L", "ITRK.L", "VOD.L", "NG.L", "SSE.L",
    # expected business-activity fails
    "HSBA.L", "BARC.L", "LLOY.L", "LGEN.L", "BATS.L", "IMB.L", "DGE.L", "ENT.L", "IHG.L", "BA.L",
]

# Sukuk (Islamic bond) ETF used for the fixed-income sleeve.
SUKUK_ETF = "SPSK"

# Real Shariah ETFs to compare our verdicts against (holdings checked by hand).
REFERENCE_ETFS = ["SPUS", "HLAL", "ISWD"]
