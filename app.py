import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
import requests
import pandas_market_calendars as mcal

# --- פונקציות מתמטיות של צינור הנתונים המוסדי ---
@st.cache_data(ttl=3600)
def calculate_hurst(series):
    if len(series) < 30: return 0.5
    lags = range(2, 15)
    tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(data, window=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=window).mean()
    return atr

# --- פונקציות זיכרון מטמון למניעת הבהובים מול Yahoo Finance ---
@st.cache_data(ttl=15)
def fetch_macro_data():
    return yf.download(['SPY', '^VIX', '^TNX', 'CL=F'], period='45d', interval='1d', auto_adjust=True, progress=False)

@st.cache_data(ttl=15)
def fetch_sector_data(ticker):
    return yf.download(ticker, period='5d', interval='15m', auto_adjust=True, progress=False)

# --- הגדרות עמוד ועיצוב מוסדי ---
st.set_page_config(page_title="Matrix OS V6", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .green-text { color: #00ff00; font-weight: bold; font-size: 16px; }
    .red-text { color: #ff0000; font-weight: bold; font-size: 16px; }
    .blink { animation: blinker 1.5s linear infinite; color: #ffcc00; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
    
    /* מניעת שקיפות/הבהוב באופן כירורגי מבלי לפגוע ברקע המקורי */
    [data-testid="stAppViewBlockContainer"], 
    [data-testid="stVerticalBlock"], 
    [data-testid="stDataFrame"] {
        opacity: 1 !important;
        transition: none !important;
    }
    div[data-testid="stStatusWidget"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

now_dt = datetime.now()

st.title("⚡ Matrix OS - מערכת פיקוד מוסדית (גרסת נרות יפניים)")
st.write(f"🔄 מתעדכן חי (ללא הבהוב) | זמן מערכת: {now_dt.strftime('%H:%M:%S')}")
st.markdown("---")

# --- רשימות נכסים ומעקב (מותאם ל-Finviz) ---
assets = {
    'S&P 500 (SPY)': 'SPY', 'Nasdaq 100 (QQQ)': 'QQQ', 'VIX Index': '^VIX',
    'Crude Oil': 'CL=F', 'Silver': 'SI=F', 'Platinum': 'PL=F', 
    'Wheat': 'ZW=F', 'Natural Gas': 'NG=F',
    'AST SpaceMobile': 'ASTS', 'Nano Nuclear': 'NNE', 'Iris Energy': 'IREN'
}

sectors = {
    'Tech (XLK)': 'XLK', 'Energy (XLE)': 'XLE', 'Financials (XLF)': 'XLF', 
    'Utilities (XLU)': 'XLU', 'Materials (XLB)': 'XLB', 'Staples (XLP)': 'XLP', 
    'Real Estate (XLRE)': 'XLRE', 'Nuclear (URA)': 'URA', 'Quantum (QTUM)': 'QTUM'
}

# --- מנוע נרות יפניים תוך-יומיים וחישוב מגמות ---
def get_asset_metrics(name, ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.fast_info
        prev_close_daily = info.previous_close
        current_price = info.last_price
        
        if pd.isna(current_price) or current_price == 0:
            df_fallback = ticker_obj.history(period="1d", interval="1m")
            if df_fallback.empty: return None
            current_price = df_fallback['Close'].iloc[-1]
            
        daily_change = ((current_price - prev_close_daily) / prev_close_daily) * 100
        df_1m = ticker_obj.history(period="1d", interval="1m")
        if df_1m.empty or len(df_1m) < 20: df_1m = ticker_obj.history(period="5d", interval="1m")
            
        p_1m = df_1m['Close'].iloc[-2] if len(df_1m) >= 2 else current_price
        p_5m = df_1m['Close'].iloc[-6] if len(df_1m) >= 6 else current_price
        p_15m = df_1m['Close'].iloc[-16] if len(df_1m) >= 16 else current_price
        
        def get_arrow_html(curr, past):
            return "<span style='color: #00ff00;'>🔼</span>" if curr >= past else "<span style='color: #ff0000;'>🔽</span>"
            
        arrow_1m = get_arrow_html(current_price, p_1m)
        arrow_5m = get_arrow_html(current_price, p_5m)
        arrow_15m = get_arrow_html(current_price, p_15m)
        
        df_15m = ticker_obj.history(period="1d", interval="15m")
        if df_15m.empty: df_15m = df_1m 
        
        fig = go.Figure(data=[go.Candlestick(
            x=df_15m.index, open=df_15m['Open'], high=df_15m['High'],
            low=df_15m['Low'], close=df_15m['Close'],
            increasing_line_color='#00ff00', increasing_fillcolor='#00ff00',
            decreasing_line_color='#ff0000', decreasing_fillcolor='#ff0000'
        )])
        
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=60, width=180,
            xaxis_rangeslider_visible=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        return {
            'נכס': name,
            'מחיר אחרון': f"{current_price:.2f}" if current_price > 1 else f"{current_price:.4f}",
            'שינוי יומי': f"{daily_change:.2f}%",
            'מגמת 1m': arrow_1m,
            'מגמת 5m': arrow_5m,
            'מגמת 15m': arrow_15m,
            'גרף': fig,
            'is_positive': daily_change >= 0
        }
    except:
        return None

# --- קומת המאקרו העליונה ---
col_m1, col_m2, col_m3 = st.columns([1, 2, 1])

with col_m2:
    try:
        vix_df = yf.Ticker('^VIX').history(period="1d")
        vix_now = vix_df['Close'].iloc[-1] if not vix_df.empty else 20
        fg_score = 100 - (vix_now * 2.5)
        fg_score = max(min(fg_score, 100), 0)
    except:
        fg_score = 50
        
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = fg_score,
        title = {'text': "מדד פחד וחמדנות משוקלל (VIX סינתטי)"},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "white"},
            'steps': [{'range': [0, 25], 'color': "darkred"}, {'range': [25, 45], 'color': "red"},
                {'range': [45, 55], 'color': "gray"}, {'range': [55, 75], 'color': "lightgreen"}, {'range': [75, 100], 'color': "green"}]}
    ))
    fig_gauge.update_layout(height=180, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_m1:
    try:
        dxy_val = yf.Ticker('DX-Y.NYB').history(period="1d")['Close'].iloc[-1]
        st.metric("DXY Dollar Index", f"{dxy_val:.2f}", "רוח גבית לסחורות" if dxy_val < 100 else "לחץ מוכר בסחורות", delta_color="inverse")
    except:
        st.metric("DXY Dollar Index", "99.82")
        
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            cnn_score = int(data['fear_and_greed']['score'])
            cnn_rating = data['fear_and_greed']['rating'].capitalize()
            st.metric("CNN Fear & Greed", f"{cnn_score} / 100", cnn_rating, delta_color="off")
        else:
            st.metric("CNN Fear & Greed", "--", "שגיאת חיבור")
    except:
        st.metric("CNN Fear & Greed", "--", "שגיאת רשת")

with col_m3:
    st.markdown("### 📢 משבשי מגמה ומבזקים")
    st.markdown("<p class='blink'>🚨 התראת מאקרו: שים לב לפרסום נתוני נפט/אינפלציה בלוח!</p>", unsafe_allow_html=True)
    st.info("💡 שים לב: פריצה של נר 15 דק' אחרון בגרף מלווה בחצים ירוקים מעידה על כניסת מוסדיים.")

st.markdown("---")

# --- עורק הנתונים המרכזי ---
st.subheader("📊 סריקה רוחבית (מומנטום ונרות יפניים מהפתיחה)")
rows_data = []
for name, ticker in assets.items():
    res = get_asset_metrics(name, ticker)
    if res: rows_data.append(res)

if rows_data:
    cols = st.columns([2, 1.5, 1.5, 1, 1, 1, 3])
    cols[0].markdown("**שם הנכס**")
    cols[1].markdown("**מחיר**")
    cols[2].markdown("**שינוי יומי**")
    cols[3].markdown("**1 דק'**")
    cols[4].markdown("**5 דק'**")
    cols[5].markdown("**15 דק'**")
    cols[6].markdown("**גרף תוך-יומי (נר = 15 דק')**")
    st.markdown("<hr style='margin:4px 0px;'>", unsafe_allow_html=True)
    
    for row in rows_data:
        c = st.columns([2, 1.5, 1.5, 1, 1, 1, 3])
        c[0].write(row['נכס'])
        color_class = "green-text" if row['is_positive'] else "red-text"
        c[1].markdown(f"<span class='{color_class}'>{row['מחיר אחרון']}</span>", unsafe_allow_html=True)
        c[2].markdown(f"<span class='{color_class}'>{row['שינוי יומי']}</span>", unsafe_allow_html=True)
        c[3].markdown(row['מגמת 1m'], unsafe_allow_html=True)
        c[4].markdown(row['מגמת 5m'], unsafe_allow_html=True)
        c[5].markdown(row['מגמת 15m'], unsafe_allow_html=True)
        c[6].plotly_chart(row['גרף'], config={'displayModeBar': False})

st.markdown("---")

# --- רוטציית סקטורים ---
st.subheader("🔄 מפת רוטציית כספים וסקטורים")
sec_data = []
for name, ticker in sectors.items():
    try:
        t_obj = yf.Ticker(ticker)
        i = t_obj.fast_info
        c_p = i.last_price
        p_p = i.previous_close
        chg = ((c_p - p_p) / p_p) * 100
        sec_data.append({'name': name, 'price': f"{c_p:.2f}", 'chg': f"{chg:.2f}%", 'pos': chg >= 0})
    except: pass

if sec_data:
    sec_cols = st.columns(3)
    for idx, s in enumerate(sec_data):
        with sec_cols[idx % 3]:
            txt_color = "green-text" if s['pos'] else "red-text"
            st.markdown(f"**{s['name']}**: {s['price']} | <span class='{txt_color}'>{s['chg']}</span>", unsafe_allow_html=True)

st.markdown("---")

# --- מנוע החישוב האמיתי (Data Pipeline לפרק 8 ו-12) ---
st.subheader("🌍 קומת מאקרו: סביבת שוק וזרימת הון")

try:
    # שימוש בפונקציית המטמון המהירה
    hist_market = fetch_macro_data()
    if isinstance(hist_market.columns, pd.MultiIndex):
        hist_market.columns = [f"{col[0]}_{col[1]}" for col in hist_market.columns]
    
    spy_closes = hist_market['Close_SPY'].dropna().values
    vix_val = float(hist_market['Close_^VIX'].dropna().iloc[-1])
    tnx_val = float(hist_market['Close_^TNX'].dropna().iloc[-1])
    oil_price = float(hist_market['Close_CL=F'].dropna().iloc[-1])
    
    hurst_spy = calculate_hurst(spy_closes)
    erp_stress = (vix_val / 100.0) + (tnx_val / 100.0)
    term_structure = "Backwardation" if oil_price > 80 else "Contango"
except:
    hurst_spy, erp_stress, tnx_val, oil_price = 0.5, 0.20, 4.0, 75.0
    term_structure = "ניטרלי"

current_day = now_dt.day
current_month = now_dt.month

is_tom_active = True if current_day >= 26 or current_day <= 4 else False
is_pre_tom_active = True if 15 <= current_day <= 22 else False
is_gann_window = True if (20 <= current_day <= 23) and (current_month in [3, 6, 9, 12]) else False

tom_color = "normal" if is_tom_active else "off"

col_mac1, col_mac2, col_mac3, col_mac4 = st.columns(4)
col_mac1.metric("📉 משטר שוק (Hurst)", f"{hurst_spy:.2f}", "מגמתי שורי (H > 0.5)" if hurst_spy > 0.5 else "שוק דשדוש", delta_color="normal" if hurst_spy > 0.5 else "inverse")
col_mac2.metric("🛢️ עקום הנפט (WTI)", f"{oil_price:.2f}$", f"{term_structure} (הגנת לונג)", delta_color="normal" if "Backwardation" in term_structure else "inverse")
col_mac3.metric("🚨 ערוץ לחץ (ERP Stress)", f"{erp_stress:.2f}", "שוק רגוע (Risk-On)" if erp_stress < 0.25 else "שוק בסיכון", delta_color="inverse")

if is_tom_active:
    cal_status = "TOM פעיל"
elif is_pre_tom_active:
    cal_status = "Pre-TOM משיכות"
else:
    cal_status = "שגרה"
col_mac4.metric("📅 סטטוס קלנדרי", cal_status, "חלון מוסדי פעיל" if cal_status != "שגרה" else "", delta_color=tom_color)

st.markdown("<hr style='border: 1px solid #333;'>", unsafe_allow_html=True)
st.subheader("📊 טבלת צלפים: סנכרון רב-ממדי (The 6-Pillar Confluence)")

matrix_sectors = {
    'QQQ': {'name': 'טכנולוגיה ונאסד"ק', 'long_3x': 'TQQQ', 'short_3x': 'SQQQ', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'SOXX': {'name': 'שבבים (SOXX)', 'long_3x': 'SOXL', 'short_3x': 'SOXS', 'base_weight': -15 if erp_stress > 0.25 else 0},
    'XLF': {'name': 'פיננסים (XLF)', 'long_3x': 'FAS', 'short_3x': 'FAZ', 'base_weight': 10 if tnx_val > 4.2 else 0},
    'IWM': {'name': 'ראסל 2000 (IWM)', 'long_3x': 'TNA', 'short_3x': 'TZA', 'base_weight': -15 if tnx_val > 4.2 else 0},
    'XLE': {'name': 'אנרגיה (XLE)', 'long_3x': 'ERX', 'short_3x': 'ERY', 'base_weight': 15 if "Backwardation" in term_structure else 0},
    'XLRE': {'name': 'נדל"ן (XLRE)', 'long_3x': 'DRN', 'short_3x': 'DRV', 'base_weight': -20 if tnx_val > 4.2 else 0},
    'XBI': {'name': 'ביוטק (XBI)', 'long_3x': 'LABU', 'short_3x': 'LABD', 'base_weight': 0}
}

matrix_table_data = []

for ticker, info in matrix_sectors.items():
    try:
        # שימוש בפונקציית המטמון המהירה
        df_sector = fetch_sector_data(ticker)
        if not df_sector.empty:
            if isinstance(df_sector.columns, pd.MultiIndex):
                df_sector.columns = [col[0] for col in df_sector.columns]
                
            df_sector['RSI'] = calculate_rsi(df_sector)
            last_row = df_sector.iloc[-1]
            rsi = float(last_row['RSI'])
            
            base_w = info['base_weight']
            rsi_w = 50.0 - rsi
            
            cal_w = 0
            if is_tom_active: cal_w = 25
            elif is_pre_tom_active: cal_w = -25
            
            confluence_score = base_w + rsi_w + cal_w
            
            hurst_mult_str = "x1.5" if hurst_spy < 0.5 else "x1.0"
            gann_mult_str = "x1.2" if is_gann_window else "x1.0"
            
            if hurst_spy < 0.5: confluence_score *= 1.5 
            if is_gann_window: confluence_score *= 1.2
            
            lead_reason = ""
            is_macro_aligned = False
            
            if ticker == 'XLF' and tnx_val > 4.2: 
                lead_reason = "TNX זינוק"
                is_macro_aligned = (confluence_score > 0)
            elif ticker in ['IWM', 'XLRE'] and tnx_val > 4.2: 
                lead_reason = "TNX לחץ"
                is_macro_aligned = (confluence_score < 0)
            elif ticker == 'XLE' and "Backwardation" in term_structure: 
                lead_reason = "נפט ב-Backwardation"
                is_macro_aligned = (confluence_score > 0)
            elif ticker in ['QQQ', 'SOXX'] and erp_stress < 0.25: 
                lead_reason = "VIX בשפל"
                is_macro_aligned = (confluence_score > 0)
            elif ticker in ['QQQ', 'SOXX'] and erp_stress > 0.25: 
                lead_reason = "ERP זינוק"
                is_macro_aligned = (confluence_score < 0)
            else: 
                lead_reason = "זרימה פנימית"
                is_macro_aligned = False

            sym_rsi = "🔥" if abs(rsi_w) > 10 else "➖"
            sym_hurst = "📉" if hurst_spy < 0.5 else "➖"
            sym_gann = "⏳" if is_gann_window else "➖"
            sym_tom = "📅" if cal_w != 0 else "➖"
            sym_lead = "🧭" if is_macro_aligned else "➖"
            sym_macro = "🌍" if base_w != 0 else "➖"
            
            sym_panel = f"\u200E{sym_rsi} {sym_hurst} {sym_gann} {sym_tom} {sym_lead} {sym_macro}"
            
            if confluence_score > 25:
                status_text = f"🟢 +{confluence_score:.1f} (לונג)"
                trigger_text = f"{info['long_3x']}"
            elif confluence_score < -25:
                status_text = f"🔴 {confluence_score:.1f} (שורט)"
                trigger_text = f"{info['short_3x']}"
            elif confluence_score > 10:
                status_text = f"⚪ +{confluence_score:.1f}"
                trigger_text = "--"
            elif confluence_score < -10:
                status_text = f"⚪ {confluence_score:.1f}"
                trigger_text = "--"
            else:
                status_text = f"⚪ {confluence_score:.1f}"
                trigger_text = "--"

            matrix_table_data.append({
                "פאנל חיווי": sym_panel,
                "הדק\n(ביצוע)": trigger_text,
                "סקטור\n(בסיס)": info['name'],
                "קפיץ\nמשוקלל": status_text,
                "🔥 (RSI)\nמתיחת מיקרו": f"{rsi_w:+.1f}",
                "📉 (Hurst)\nמכפיל הגנה": hurst_mult_str,
                "⏳ (Gann)\nתזמון": gann_mult_str,
                "📅 (TOM)\nעונתיות": f"{cal_w:+d}",
                "🧭 (Lead)\nאיתות": lead_reason,
                "🌍 (Macro)\nמשקל": f"{base_w:+d}",
                "score": confluence_score
            })
    except: pass

if matrix_table_data:
    df_matrix = pd.DataFrame(matrix_table_data)
    df_matrix['abs_score'] = df_matrix['score'].abs()
    df_matrix = df_matrix.sort_values(by='abs_score', ascending=False).drop(columns=['abs_score', 'score'])
    
    df_matrix = df_matrix[[
        'פאנל חיווי',
        'הדק\n(ביצוע)',
        'סקטור\n(בסיס)',
        'קפיץ\nמשוקלל',
        '🔥 (RSI)\nמתיחת מיקרו',
        '📉 (Hurst)\nמכפיל הגנה',
        '⏳ (Gann)\nתזמון',
        '📅 (TOM)\nעונתיות',
        '🧭 (Lead)\nאיתות',
        '🌍 (Macro)\nמשקל'
    ]]

    def style_matrix(row):
        styles = [''] * len(row)
        score_val = str(row['קפיץ\nמשוקלל'])
        sym_panel = str(row['פאנל חיווי'])
        
        active_symbols = len([s for s in sym_panel if s not in ["➖", "\u200E", " "]])
        
        if active_symbols >= 3:
            if "לונג" in score_val: 
                return ['background-color: rgba(0, 255, 0, 0.1); border-bottom: 1px solid #00ff00;'] * len(row)
            elif "שורט" in score_val: 
                return ['background-color: rgba(255, 0, 0, 0.1); border-bottom: 1px solid #ff0000;'] * len(row)
        return styles

    st.dataframe(df_matrix.style.apply(style_matrix, axis=1), use_container_width=True, hide_index=True)

time.sleep(15)
st.rerun()
