import concurrent.futures
import json
import time
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
import ta
import yfinance as yf
from supabase import create_client, Client

# --- SECRETS & SUPABASE INIT ---
BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            return None
    return None

supabase = init_supabase()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="AlphaScan Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- MODERN FUTURISTIC CSS DESIGN SYSTEM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg-core: #05070A;
        --surface-1: rgba(15, 20, 31, 0.6);
        --surface-2: rgba(23, 30, 46, 0.7);
        --border-glass: rgba(255, 255, 255, 0.08);
        --border-glass-hover: rgba(0, 229, 255, 0.3);
        --accent-glow: #00E5FF;
        --accent-green: #10B981;
        --text-main: #F3F4F6;
        --text-muted: #9CA3AF;
        --font-sans: 'Plus Jakarta Sans', sans-serif;
        --font-heading: 'Space Grotesk', sans-serif;
        --font-code: 'JetBrains Mono', monospace;
    }

    .stApp {
        background: radial-gradient(circle at 50% 0%, #0D1527 0%, #05070A 70%) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-main);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding: 1.5rem 3rem !important;
        max-width: 1400px !important;
    }

    /* Glass Navbar */
    .nav-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 24px;
        background: var(--surface-1);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-glass);
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.4);
    }

    .brand-title {
        font-family: var(--font-heading);
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #FFFFFF 0%, #00E5FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: var(--accent-green);
        border-radius: 50%;
        box-shadow: 0 0 12px var(--accent-green);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Futuristic Interactive Cards */
    .glow-card {
        background: var(--surface-1);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-glass);
        border-radius: 14px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        position: relative;
        overflow: hidden;
    }

    .glow-card:hover {
        transform: translateY(-4px);
        border-color: var(--border-glass-hover);
        box-shadow: 0 12px 30px rgba(0, 229, 255, 0.15);
    }

    .stat-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
        font-weight: 600;
        margin-bottom: 6px;
    }

    .stat-value {
        font-family: var(--font-heading);
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-main);
    }

    /* Streamlit Button Tweaks */
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 229, 255, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%) !important;
        border: 1px solid var(--border-glass-hover) !important;
        color: var(--accent-glow) !important;
        border-radius: 10px !important;
        padding: 0.6rem 1.5rem !important;
        font-family: var(--font-sans) !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #00E5FF 0%, #10B981 100%) !important;
        color: #000000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(0, 229, 255, 0.4) !important;
    }

    /* Clean Form Styling */
    div[data-testid="stForm"] {
        background: var(--surface-1) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 16px !important;
        padding: 2.5rem !important;
        backdrop-filter: blur(16px);
    }

    .stTextInput>div>div>input {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid var(--border-glass) !important;
        color: var(--text-main) !important;
        border-radius: 8px !important;
    }

    .stTextInput>div>div>input:focus {
        border-color: var(--accent-glow) !important;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = None
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = ""

# --- TELEGRAM HELPER ---
def send_telegram_alert(message, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=8)
        return res.status_code == 200
    except Exception:
        return False

# --- LANDING PAGE (AUTHENTICATION) ---
if not st.session_state.user:
    st.markdown("""
        <div class="nav-container">
            <div class="brand-title">⚡ ALPHASCAN <span style="font-size:0.7rem; color:var(--accent-glow); padding:2px 8px; border:1px solid var(--border-glass-hover); border-radius:12px;">PRO</span></div>
            <div style="display:flex; align-items:center; gap:10px; font-size:0.85rem; color:var(--text-muted);">
                <div class="pulse-dot"></div> QUANT NETWORK ACTIVE
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="text-align: center; padding: 4rem 1rem 2rem 1rem;">
            <h1 style="font-family:var(--font-heading); font-size: 3.5rem; font-weight:700; line-height:1.1; margin-bottom: 1rem; background: linear-gradient(180deg, #FFFFFF 0%, #6B7280 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Next-Gen Market Intelligence Terminal
            </h1>
            <p style="color: var(--text-muted); font-size: 1.15rem; max-width: 650px; margin: 0 auto 2.5rem auto;">
                Real-time technical parameter scanning, automated weekly 10 EMA support tracking, and instant multi-channel signal routing.
            </p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown('<div class="glow-card"><div class="stat-label">Coverage</div><div class="stat-value">2,000+</div><div style="color:var(--text-muted); font-size:0.8rem;">NSE Equities</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="glow-card"><div class="stat-label">Algorithm</div><div class="stat-value">10 EMA</div><div style="color:var(--text-muted); font-size:0.8rem;">Weekly Support</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="glow-card"><div class="stat-label">Execution</div><div class="stat-value">Parallel</div><div style="color:var(--text-muted); font-size:0.8rem;">30x Threads</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown('<div class="glow-card"><div class="stat-label">Latency</div><div class="stat-value">&lt; 0.5s</div><div style="color:var(--text-muted); font-size:0.8rem;">Alert Dispatch</div></div>', unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
        if st.button("🔑 Enter Terminal", use_container_width=True):
            st.session_state.auth_mode = "login"
    with col_btn2:
        if st.button("📝 Create Account", use_container_width=True):
            st.session_state.auth_mode = "register"

    if st.session_state.auth_mode == "login":
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.subheader("🔑 Sign In to Terminal")
            email = st.text_input("Account Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Authenticate"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    if res.user and res.user.user_metadata:
                        st.session_state.telegram_chat_id = res.user.user_metadata.get("telegram_chat_id", "")
                    st.success("Authorized! Loading terminal...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    elif st.session_state.auth_mode == "register":
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("register_form"):
            st.subheader("📝 Register Trader Profile")
            email = st.text_input("Email Address")
            password = st.text_input("Password (min 6 characters)", type="password")
            if st.form_submit_button("Create Account"):
                try:
                    res = supabase.auth.sign_up({"email": email, "password": password})
                    st.success("Account created successfully! Click 'Enter Terminal' above.")
                except Exception as e:
                    st.error(f"Error: {e}")

    st.stop()

# --- AUTHENTICATED TERMINAL DASHBOARD ---
user_email = st.session_state.user.email

st.markdown(f"""
    <div class="nav-container">
        <div class="brand-title">⚡ ALPHASCAN PRO</div>
        <div style="display:flex; align-items:center; gap:20px;">
            <span style="color:var(--text-muted); font-size:0.9rem;">Connected: <b style="color:var(--text-main);">{user_email}</b></span>
            <div class="pulse-dot"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab1, tab2, tab3 = st.tabs(["📊 Terminal & Scanner", "📲 Routing & Settings", "📈 TradingView Chart Engine"])

# --- TAB 1: TERMINAL SCANNER ---
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    c_config, c_results = st.columns([1, 2.5])

    with c_config:
        st.markdown('<div class="glow-card">', unsafe_allow_html=True)
        st.subheader("⚙️ Control Engine")
        scan_mode = st.radio("Market Universe", ["Custom Watchlist", "Nifty 50", "Full NSE (2000+ Stocks)"])
        buffer_pct = st.slider("10 EMA Tolerance Buffer (%)", 0.5, 3.0, 2.0, 0.1)

        symbols_to_scan = []
        if scan_mode == "Custom Watchlist":
            custom_input = st.text_area("Watchlist Tickers", "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO, ADANIPOWER")
            symbols_to_scan = [f"{s.strip().upper()}.NS" for s in custom_input.split(",") if s.strip() != ""]
        elif scan_mode == "Nifty 50":
            symbols_to_scan = ["ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "LT.NS", "RELIANCE.NS", "SBIN.NS", "TCS.NS", "TITAN.NS"]
        else:
            def get_all_nse_symbols():
                url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
                headers = {"User-Agent": "Mozilla/5.0"}
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
            symbols_to_scan = get_all_nse_symbols()

        st.markdown("<br>", unsafe_allow_html=True)
        run_scan = st.button("🚀 Run Live Scanner", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_results:
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

                if (lower_bound <= current_low <= upper_bound) or (current_low <= ema10 and current_close >= ema10):
                    stock_name = symbol.replace(".NS", "")
                    diff_pct = round(((current_close - ema10) / ema10) * 100, 2)
                    return {
                        "Ticker": stock_name,
                        "LTP (₹)": current_close,
                        "Weekly Low (₹)": current_low,
                        "10 EMA (₹)": ema10,
                        "Spread (%)": f"{diff_pct}%",
                    }
            except Exception:
                return None
            return None

        if run_scan:
            st.info(f"Scanning {len(symbols_to_scan)} stock symbols...")
            progress_bar = st.progress(0)
            results = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
                futures = {executor.submit(process_single_stock, sym, buffer_pct): sym for sym in symbols_to_scan}
                completed = 0
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        results.append(res)
                    completed += 1
                    progress_bar.progress(completed / len(symbols_to_scan))

            st.session_state.scan_results = pd.DataFrame(results) if results else pd.DataFrame()

        if st.session_state.scan_results is not None:
            df_res = st.session_state.scan_results

            r1, r2 = st.columns([1, 1])
            r1.markdown(f'<div class="glow-card"><div class="stat-label">Identified Matches</div><div class="stat-value" style="color:var(--accent-green);">{len(df_res)}</div></div>', unsafe_allow_html=True)
            r2.markdown(f'<div class="glow-card"><div class="stat-label">Current Buffer</div><div class="stat-value">±{buffer_pct}%</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            if not df_res.empty:
                st.dataframe(df_res, use_container_width=True)

                if st.button("📲 Dispatch Signals to Telegram Bot"):
                    active_chat_id = st.session_state.telegram_chat_id
                    if not active_chat_id:
                        st.error("Telegram Chat ID missing! Configure it in 'Routing & Settings' tab.")
                    else:
                        matches_text = [
                            f"• *{row['Ticker']}*: LTP Rs.{row['LTP (₹)']} | 10 EMA Rs.{row['10 EMA (₹)']} ({row['Spread (%)']})"
                            for _, row in df_res.iterrows()
                        ]
                        total_sent = 0
                        for i in range(0, len(matches_text), 15):
                            chunk = matches_text[i : i + 15]
                            msg = f"⚡ *ALPHASCAN QUANT SIGNALS*\n\n" + "\n".join(chunk)
                            if send_telegram_alert(msg, active_chat_id):
                                total_sent += 1
                            time.sleep(0.4)

                        if total_sent > 0:
                            st.success("Signals sent to Telegram successfully!")
                        else:
                            st.error("Alert delivery failed.")
            else:
                st.warning("No setup triggers matched the criteria.")

# --- TAB 2: ROUTING & SETTINGS ---
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="glow-card" style="max-width: 600px; margin: 0 auto;">', unsafe_allow_html=True)
    st.subheader("📲 Telegram Routing Configuration")
    
    current_val = st.session_state.telegram_chat_id
    telegram_id_input = st.text_input("Telegram Chat ID:", value=current_val)

    if st.button("Save Chat ID"):
        clean_id = telegram_id_input.strip()
        if clean_id:
            try:
                res = supabase.auth.update_user({"data": {"telegram_chat_id": clean_id}})
                if res.user:
                    st.session_state.user = res.user
                st.session_state.telegram_chat_id = clean_id
                st.success("✅ Chat ID Linked & Saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Save error: {e}")
        else:
            st.warning("Please provide a valid Chat ID.")

    st.markdown("""
    <p style="color:var(--text-muted); font-size:0.85rem; margin-top:1rem;">
    1. Search <code>@userinfobot</code> on Telegram to get your numeric ID.<br>
    2. Paste it here and click Save.<br>
    3. Ensure you click <b>/start</b> on your alert bot once.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:var(--border-glass);'>", unsafe_allow_html=True)
    if st.button("🚪 Logout Account", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.session_state.user = None
        st.session_state.auth_mode = None
        st.session_state.telegram_chat_id = ""
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: OFFICIAL TRADINGVIEW LIGHTWEIGHT CANVAS ENGINE ---
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    col_input, _ = st.columns([1, 2])
    with col_input:
        chart_symbol = st.text_input("Enter Ticker Symbol (e.g. ADANIPOWER, RELIANCE, INFY):", value="ADANIPOWER").upper().strip()
    
    clean_ticker = chart_symbol.replace(".NS", "").replace("NSE:", "").replace("BSE:", "")
    yf_symbol = f"{clean_ticker}.NS"
    
    st.markdown(f"### 📈 TradingView Engine: `{clean_ticker}` (Weekly Candles + 10 EMA)")
    
    try:
        stock_df = yf.Ticker(yf_symbol).history(period="2y", interval="1wk")
        if not stock_df.empty and len(stock_df) > 10:
            stock_df["EMA10"] = ta.trend.ema_indicator(close=stock_df["Close"], window=10)
            
            # Format candles for TradingView Lightweight Charts
            candle_data = []
            ema_data = []
            for date, row in stock_df.iterrows():
                time_str = date.strftime("%Y-%m-%d")
                candle_data.append({
                    "time": time_str,
                    "open": round(float(row["Open"]), 2),
                    "high": round(float(row["High"]), 2),
                    "low": round(float(row["Low"]), 2),
                    "close": round(float(row["Close"]), 2)
                })
                if pd.notna(row["EMA10"]):
                    ema_data.append({
                        "time": time_str,
                        "value": round(float(row["EMA10"]), 2)
                    })
            
            candle_json = json.dumps(candle_data)
            ema_json = json.dumps(ema_data)
            
            tv_lightweight_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
                <style>
                    body {{ margin: 0; padding: 0; background-color: #080A0F; overflow: hidden; }}
                    #chart-container {{ width: 100%; height: 580px; position: relative; }}
                    .legend {{
                        position: absolute; top: 12px; left: 16px; z-index: 10;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        color: #9CA3AF; font-size: 13px; font-weight: 500;
                        background: rgba(15, 20, 31, 0.75); padding: 6px 12px;
                        border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);
                    }}
                </style>
            </head>
            <body>
                <div id="chart-container">
                    <div class="legend">
                        <span style="color: #FFFFFF; font-weight: 700;">{clean_ticker}</span> 
                        • 1W Candles 
                        • <span style="color: #00E5FF;">10 EMA</span>
                    </div>
                </div>
                <script>
                    const container = document.getElementById('chart-container');
                    const chart = LightweightCharts.createChart(container, {{
                        width: container.clientWidth,
                        height: 580,
                        layout: {{
                            background: {{ type: 'solid', color: '#080A0F' }},
                            textColor: '#8B949E',
                        }},
                        grid: {{
                            vertLines: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                            horzLines: {{ color: 'rgba(255, 255, 255, 0.04)' }},
                        }},
                        crosshair: {{
                            mode: LightweightCharts.CrosshairMode.Normal,
                        }},
                        rightPriceScale: {{
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                        }},
                        timeScale: {{
                            borderColor: 'rgba(255, 255, 255, 0.1)',
                            timeVisible: true,
                        }},
                    }});

                    const candleSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {{
                        upColor: '#10B981',
                        downColor: '#EF4444',
                        borderVisible: false,
                        wickUpColor: '#10B981',
                        wickDownColor: '#EF4444',
                    }});
                    candleSeries.setData({candle_json});

                    const emaSeries = chart.addSeries(LightweightCharts.LineSeries, {{
                        color: '#00E5FF',
                        lineWidth: 2,
                        crosshairMarkerVisible: true,
                    }});
                    emaSeries.setData({ema_json});

                    window.addEventListener('resize', () => {{
                        chart.applyOptions({{ width: container.clientWidth }});
                    }});
                </script>
            </body>
            </html>
            """
            components.html(tv_lightweight_html, height=600)
        else:
            st.error(f"No market data found for `{clean_ticker}`.")
    except Exception as e:
        st.error(f"Chart Render Error: {e}")