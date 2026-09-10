import concurrent.futures
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st
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

    .stTextInput>div>div>input, div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid var(--border-glass) !important;
        color: var(--text-main) !important;
        border-radius: 8px !important;
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

# --- NSE TICKER & COMPANY MAPPING ENGINE ---
@st.cache_data(ttl=86400)
def load_nse_universe():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(resp.content.decode("utf-8")))
            df = df[df[" SERIES"] == "EQ"]
            records = {}
            for _, row in df.iterrows():
                symbol = str(row["SYMBOL"]).strip()
                name = str(row["NAME OF COMPANY"]).strip()
                label = f"{symbol} — {name}"
                records[label] = f"{symbol}.NS"
            return records
    except Exception:
        pass
    fallback = {
        "ADANIPOWER — Adani Power Limited": "ADANIPOWER.NS",
        "RELIANCE — Reliance Industries Limited": "RELIANCE.NS",
        "TATASTEEL — Tata Steel Limited": "TATASTEEL.NS",
        "INFY — Infosys Limited": "INFY.NS",
        "ICICIBANK — ICICI Bank Limited": "ICICIBANK.NS",
        "SBIN — State Bank of India": "SBIN.NS",
        "HDFCBANK — HDFC Bank Limited": "HDFCBANK.NS",
        "TCS — Tata Consultancy Services Limited": "TCS.NS",
        "LT — Larsen & Toubro Limited": "LT.NS",
        "ZOMATO — Zomato Limited": "ZOMATO.NS"
    }
    return fallback

nse_universe_dict = load_nse_universe()

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

tab1, tab2, tab3 = st.tabs(["📊 Terminal & Scanner", "📲 Routing & Settings", "📈 Interactive Technical Chart"])

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
            symbols_to_scan = list(nse_universe_dict.values())

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

# --- TAB 3: INTERACTIVE TECHNICAL CHART ENGINE (AUTO-SUGGEST + DRAWINGS + INDICATORS) ---
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)

    c_search, c_tf, c_ind = st.columns([2, 1, 2])

    with c_search:
        options_list = list(nse_universe_dict.keys())
        default_index = 0
        for i, opt in enumerate(options_list):
            if opt.startswith("ADANIPOWER"):
                default_index = i
                break

        selected_label = st.selectbox(
            "🔍 Search Stock by Name or Symbol (Auto-Suggest):",
            options=options_list,
            index=default_index,
            help="Type company name (e.g. Tata, Adani, Reliance) or ticker"
        )
        selected_yf_symbol = nse_universe_dict[selected_label]
        clean_stock_ticker = selected_yf_symbol.replace(".NS", "")

    with c_tf:
        timeframe = st.selectbox("Timeframe", ["1W (Weekly)", "1D (Daily)", "1M (Monthly)"], index=0)
        interval_map = {"1W (Weekly)": "1wk", "1D (Daily)": "1d", "1M (Monthly)": "1mo"}
        period_map = {"1W (Weekly)": "2y", "1D (Daily)": "1y", "1M (Monthly)": "5y"}

    with c_ind:
        selected_indicators = st.multiselect(
            "📈 Overlay Indicators:",
            ["10 EMA", "20 EMA", "50 EMA", "200 EMA", "Volume"],
            default=["10 EMA", "Volume"]
        )

    try:
        data = yf.Ticker(selected_yf_symbol).history(
            period=period_map[timeframe],
            interval=interval_map[timeframe]
        )

        if not data.empty and len(data) >= 5:
            # Indicator Calculations
            if "10 EMA" in selected_indicators:
                data["EMA10"] = ta.trend.ema_indicator(data["Close"], window=10)
            if "20 EMA" in selected_indicators:
                data["EMA20"] = ta.trend.ema_indicator(data["Close"], window=20)
            if "50 EMA" in selected_indicators:
                data["EMA50"] = ta.trend.ema_indicator(data["Close"], window=50)
            if "200 EMA" in selected_indicators and len(data) > 200:
                data["EMA200"] = ta.trend.ema_indicator(data["Close"], window=200)

            # Subplots for Price and Volume
            has_vol = "Volume" in selected_indicators and "Volume" in data.columns
            fig = make_subplots(
                rows=2 if has_vol else 1,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.8, 0.2] if has_vol else [1.0]
            )

            # Interactive Candlesticks
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data["Open"],
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                name="Price",
                increasing_line_color="#10B981",
                decreasing_line_color="#EF4444"
            ), row=1, col=1)

            # EMA Lines Overlay
            if "10 EMA" in selected_indicators and "EMA10" in data:
                fig.add_trace(go.Scatter(x=data.index, y=data["EMA10"], line=dict(color="#00E5FF", width=1.5), name="10 EMA"), row=1, col=1)
            if "20 EMA" in selected_indicators and "EMA20" in data:
                fig.add_trace(go.Scatter(x=data.index, y=data["EMA20"], line=dict(color="#F59E0B", width=1.5), name="20 EMA"), row=1, col=1)
            if "50 EMA" in selected_indicators and "EMA50" in data:
                fig.add_trace(go.Scatter(x=data.index, y=data["EMA50"], line=dict(color="#EC4899", width=1.5), name="50 EMA"), row=1, col=1)
            if "200 EMA" in selected_indicators and "EMA200" in data:
                fig.add_trace(go.Scatter(x=data.index, y=data["EMA200"], line=dict(color="#8B5CF6", width=2), name="200 EMA"), row=1, col=1)

            # Volume Bar Subplot
            if has_vol:
                colors = ["#10B981" if c >= o else "#EF4444" for c, o in zip(data["Close"], data["Open"])]
                fig.add_trace(go.Bar(
                    x=data.index,
                    y=data["Volume"],
                    marker_color=colors,
                    name="Volume",
                    opacity=0.5
                ), row=2, col=1)

            # High-end Dark Layout & Drawing Toolbar Enablement
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(15, 20, 31, 0.7)",
                plot_bgcolor="rgba(5, 7, 10, 0.9)",
                height=650,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                dragmode="drawline"  # Default interaction: Draw Trendline
            )

            # Config with Full Drawing Tools (Lines, Rectangles, Circles, Shapes, Text)
            config = {
                "scrollZoom": True,
                "displayModeBar": True,
                "modeBarButtonsToAdd": [
                    "drawline",
                    "drawopenpath",
                    "drawclosedpath",
                    "drawcircle",
                    "drawrect",
                    "eraseshape"
                ],
                "toImageButtonOptions": {"format": "png", "filename": f"{clean_stock_ticker}_chart"}
            }

            st.plotly_chart(fig, use_container_width=True, config=config)
            st.caption("🛠️ **Drawing Tools Active:** Use the top-right toolbar to draw trendlines, support/resistance boxes, or erase shapes.")
        else:
            st.error(f"No price history returned for `{clean_stock_ticker}`.")
    except Exception as e:
        st.error(f"Failed to fetch real-time chart: {e}")