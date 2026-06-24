

WATCHLIST = [
    ("YESBANK.NS",      "Yes Bank",             "Banking",  True),
    ("HDFCBANK.NS",     "HDFC Bank",            "Banking",  True),
    ("AXISBANK.NS",     "Axis Bank",            "Banking",  True),
    ("ICICIBANK.NS",    "ICICI Bank",           "Banking",  True),
    ("SBIN.NS",         "SBI",                  "Banking",  True),
    ("IDFCFIRSTB.NS",   "IDFC First Bank",      "Banking",  True),

    ("RELINFRA.NS",     "Reliance Infra",       "Infra",    False),
    ("SUZLON.NS",       "Suzlon Energy",        "Energy",   False),

    ("TATAPOWER.NS",    "Tata Power",           "Energy",   False),
    ("VEDL.NS",         "Vedanta",              "Metals",   False),
    ("ZEEL.NS",         "Zee Entertainment",    "Media",    False),

    ("INFY.NS",         "Infosys",              "IT",       False),
    ("TCS.NS",          "TCS",                  "IT",       False),
    ("NESTLEIND.NS",    "Nestle India",         "FMCG",     False),
    ("HINDUNILVR.NS",   "HUL",                  "FMCG",     False),

    ("JETAIRWAYS.NS", "Jet Airways",  "Aviation", False),
    ("CGPOWER.NS",    "CG Power",     "Industrials", False),
    ("FRETAIL.NS",    "Future Retail","Retail", False),
]

NIFTY500_TICKER = "^NSEI"

def get_tickers():
    return [t[0] for t in WATCHLIST]

def get_company_map():
    return {
        t[0]: {"name": t[1], "sector": t[2], "is_bank": t[3]}
        for t in WATCHLIST
    }