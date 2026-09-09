import concurrent.futures
import time
import pandas as pd
import requests
import streamlit as st
import ta
import yfinance as yf

# Telegram Credentials
BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")

st.set_page_config(
    page_title="AlphaScan Pro | Technical Terminal",
    page_icon="⚡",
    layout="wide",
)

# Custom Styling (Pro Dark Theme)
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .stButton>button {
        background-color: #238636;
        color: white;
        border-radius: 6px;
        border: none;
        padding: 10px 20px;
        font-weight: bold;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #2ea043;
    }
    </style>
""",
    unsafe_allow_html=True,
)

if "scan_results" not in st.session_state:
    st.session_state.scan_results = None

# Automatically fetch all users who clicked /start on Telegram Bot
def get_bot_subscribers():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            chat_ids = set()
            for result in data.get("result", []):
                if "message" in result and "chat" in result["message"]:
                    chat_ids.add(result["message"]["chat"]["id"])
            return list(chat_ids)
    except Exception:
        pass
    return []

def send_telegram_alert(message, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception:
        return False

def get_all_nse_symbols():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            with open("EQUITY_L.csv", "wb") as f:
                f.write(response.content)
            df = pd.read_csv("EQUITY_L.csv")
            df = df[df[" SERIES"] == "EQ"]
            return [f"{symbol.strip()}.NS" for symbol in df["SYMBOL"]]
    except Exception:
        pass
    return ["RELIANCE.NS", "TATASTEEL.NS", "INFY.NS", "ICICIBANK.NS", "LT.NS"]

def process_single_stock(symbol, buffer_pct):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1wk")

        if df.empty or len(df) < 15:
            return None

        df["EMA10"] = ta.trend.ema_indicator(close=df["Close"], window=10)

        current_close = round(df["Close"].iloc[-1], 2)
        current_low = round(df["Low"].iloc[-1], 2)
        ema10 = round(df["EMA10"].iloc[-1], 2)

        if current_close < 5:
            return None

        lower_bound = ema10 * (1 - (buffer_pct / 100))
        upper_bound = ema10 * (1 + (buffer_pct / 100))

        if (lower_bound <= current_low <= upper_bound) or (
            current_low <= ema10 and current_close >= ema10
        ):
            stock_name = symbol.replace(".NS", "")
            diff_pct = round(((current_close - ema10) / ema10) * 100, 2)
            return {
                "Stock": stock_name,
                "Price (₹)": current_close,
                "Weekly Low (₹)": current_low,
                "10 EMA (₹)": ema10,
                "Distance from EMA (%)": f"{diff_pct}%",
            }
    except Exception:
        return None
    return None

# App UI
st.title("⚡ AlphaScan Pro Terminal")
st.caption("Custom Swing Scanner | Weekly 10 EMA Support & Dynamic Parameter Engine")
st.divider()

st.sidebar.header("⚙️ Scanner Configurations")

scan_mode = st.sidebar.radio(
    "Select Scanning Universe:",
    ["Custom Stocks", "Nifty 50", "Full NSE (2000+ Stocks)"],
)

buffer_pct = st.sidebar.slider(
    "10 EMA Tolerance Buffer (%)",
    min_value=0.5,
    max_value=3.0,
    value=2.0,
    step=0.1,
)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Telegram Bot Connection")
st.sidebar.info("Search **@RA_TRADERADAR_BOT** on Telegram & click **START** to receive alerts.")

symbols_to_scan = []

if scan_mode == "Custom Stocks":
    custom_input = st.sidebar.text_area(
        "Enter Stock Tickers (Comma Separated):",
        "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO, TATAMOTORS, SBIN",
    )
    symbols_to_scan = [
        f"{s.strip().upper()}.NS"
        for s in custom_input.split(",")
        if s.strip() != ""
    ]

elif scan_mode == "Nifty 50":
    symbols_to_scan = [
        "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS",
        "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
        "BEL.NS", "BPCL.NS", "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS",
        "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
        "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
        "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
        "ITC.NS", "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS", "KOTAKBANK.NS",
        "LT.NS", "LTIM.NS", "M&M.NS", "MARUTI.NS", "NTPC.NS", "NESTLEIND.NS",
        "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS", "SBILIFE.NS",
        "SHRIRAMFIN.NS", "SBIN.NS", "SUNPHARMA.NS", "TCS.NS",
        "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "TECHM.NS",
        "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS",
    ]
else:
    symbols_to_scan = get_all_nse_symbols()

if st.sidebar.button("🚀 Execute Scan"):
    if not symbols_to_scan:
        st.sidebar.error("Please add stocks or select a market universe.")
    else:
        st.info(f"Scanning {len(symbols_to_scan)} stocks... Please wait.")
        progress_bar = st.progress(0)
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = {
                executor.submit(process_single_stock, sym, buffer_pct): sym
                for sym in symbols_to_scan
            }
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
                completed += 1
                progress_bar.progress(completed / len(symbols_to_scan))

        if results:
            st.session_state.scan_results = pd.DataFrame(results)
            st.success("Analysis Complete!")
        else:
            st.session_state.scan_results = pd.DataFrame()
            st.warning("No setup triggers matching your exact criteria.")

if (
    st.session_state.scan_results is not None
    and not st.session_state.scan_results.empty
):
    df_res = st.session_state.scan_results

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Setups Found", len(df_res))
    with col2:
        st.metric("Selected Strategy", "Weekly 10 EMA Support")
    with col3:
        st.metric("EMA Buffer", f"±{buffer_pct}%")

    st.subheader("🎯 Setup Candidates")
    st.dataframe(df_res, use_container_width=True)

    if st.button("📲 Push Alerts to Telegram"):
        subscribers = get_bot_subscribers()
        
        if not subscribers:
            st.error("No active users found! Make sure you and Ankur have opened @RA_TRADERADAR_BOT on Telegram and clicked START.")
        else:
            matches_text = [
                f"• {row['Stock']}: Price Rs.{row['Price (₹)']} | 10 EMA Rs.{row['10 EMA (₹)']} ({row['Distance from EMA (%)']})"
                for _, row in df_res.iterrows()
            ]

            total_sent = 0
            for subscriber_id in subscribers:
                for i in range(0, len(matches_text), 15):
                    chunk = matches_text[i : i + 15]
                    msg = (
                        f"⚡ ALPHASCAN PRO ALERTS (Part {i//15 + 1})\n\n"
                        + "\n".join(chunk)
                    )
                    if send_telegram_alert(msg, subscriber_id):
                        total_sent += 1
                    time.sleep(0.5)

            if total_sent > 0:
                st.success(f"✅ Telegram Alerts Dispatched to {len(subscribers)} active bot subscriber(s)!")
            else:
                st.error("❌ Failed to send Telegram message.")