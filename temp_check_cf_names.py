# temp_check_cf_names.py
import yfinance as yf

for symbol in ["VEDL.NS", "YESBANK.NS"]:
    print(f"\n=== {symbol} ===")
    cf = yf.Ticker(symbol).quarterly_cashflow
    if cf is not None and not cf.empty:
        print(list(cf.index))
    else:
        print("No cashflow data at all")