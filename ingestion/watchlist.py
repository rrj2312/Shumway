# NSE suffix: .NS   BSE suffix: .BO
# Format: (ticker_symbol, display_name, sector, is_bank)

WATCHLIST = [
    # Banking & NBFC — distress-prone sector, bank-specific signals apply
    ("YESBANK.NS",      "Yes Bank",             "Banking",  True),
    ("HDFCBANK.NS",     "HDFC Bank",            "Banking",  True),
    ("AXISBANK.NS",     "Axis Bank",            "Banking",  True),
    ("ICICIBANK.NS",    "ICICI Bank",           "Banking",  True),
    ("SBIN.NS",         "SBI",                  "Banking",  True),
    ("IDFCFIRSTB.NS",   "IDFC First Bank",      "Banking",  True),

    # Infrastructure / Conglomerate — historically distress-prone
    ("RELINFRA.NS",     "Reliance Infra",       "Infra",    False),
    ("SUZLON.NS",       "Suzlon Energy",        "Energy",   False),

    # Manufacturing / Consumer
    ("TATAPOWER.NS",    "Tata Power",           "Energy",   False),
    ("VEDL.NS",         "Vedanta",              "Metals",   False),
    ("ZEEL.NS",         "Zee Entertainment",    "Media",    False),

    # Healthy benchmarks — needed for the 0-label class
    ("INFY.NS",         "Infosys",              "IT",       False),
    ("TCS.NS",          "TCS",                  "IT",       False),
    ("NESTLEIND.NS",    "Nestle India",         "FMCG",     False),
    ("HINDUNILVR.NS",   "HUL",                  "FMCG",     False),
]

# Nifty 500 proxy — used to compute relative size and excess return
NIFTY500_TICKER = "^CNX500"

def get_tickers():
    return [t[0] for t in WATCHLIST]

def get_company_map():
    """Returns {ticker: {name, sector, is_bank}}"""
    return {
        t[0]: {"name": t[1], "sector": t[2], "is_bank": t[3]}
        for t in WATCHLIST
    }