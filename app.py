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

# --- פונקציות שאיבת נתונים עם זיכרון מטמון למניעת הבהוב ---
@st.cache_data(ttl=15)
def get_macro_data():
    return yf.download(['SPY', '^VIX', '^TNX', 'CL=F'], period='45d', interval='1d', auto_adjust=True, progress=False)

@st.cache_data(ttl=15)
def get_sector_data(ticker):
    return yf.download(ticker, period='5d', interval='15m', auto_adjust=True, progress=False)

@st.cache_data(ttl=60)
def get_cnn_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        return r.json() if r.status_code == 200 else None
    except:
        return None

# --- הגדרות עמוד ועיצוב מוסדי ---
st.set_page_config(page_title="Matrix OS V6", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .green-text { color: #00ff00; font-weight: bold; font-size: 16px; }
    .red-text { color: #ff0000; font-weight: bold; font-size: 16px; }
    .blink { animation: blinker 1.5s linear infinite; color: #ffcc00; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
""", unsafe_allow_html=True)

now_dt = datetime.now()
st.title("⚡ Matrix OS - מערכת פיקוד מוסדית")
st.write(f"🔄 מתעדכן חי (מבוסס מטמון) | זמן מערכת: {now_dt.strftime('%H:%M:%S')}")
st.markdown("---")

# --- רשימות נכסים ומעקב ---
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
        title = {'text': "מדד פחד וחמדנות (VIX סינתטי)"},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "white"},
            'steps': [{'range': [0, 25], 'color': "darkred"}, {'range': [25, 45], 'color': "red"},
                {'range': [45, 55], 'color': "gray"}, {'range': [55, 75], 'color': "lightgreen"}, {'range': [75, 100], 'color': "green"}]}
    ))
    fig_gauge.update_layout(height=180, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_m1:
    try:
        dxy_val = yf.Ticker('DX-Y.NYB').history(period="1d")['Close'].iloc[-1]
        st.metric("DXY Dollar Index", f"{dxy_val:.2f}", "רוח גבית לסחורות" if dxy_val < 100 else "לחץ מוכר", delta_color="inverse")
    except:
        st.metric("DXY Dollar Index", "99.82")
        
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    cnn_data = get_cnn_fear_greed()
    if cnn_data:
        cnn_score = int(cnn_data['fear_and_greed']['score'])
        cnn_rating = cnn_data['fear_and_greed']['rating'].capitalize()
        st.metric("CNN Fear & Greed", f"{cnn_score} / 100", cnn_rating, delta_color="off")
    else:
        st.metric("CNN Fear & Greed", "--", "שגיאת רשת")

with col_m3:
    st.markdown("### 📢 מבזקי מערכת")
    st.markdown("<p class='blink'>🚨 התראת מאקרו: שים לב לאירועים בלוח!</p>", unsafe_allow_html=True)

st.markdown("---")

# --- מנוע החישוב האמיתי (Data Pipeline לפרק 8 ו-12) ---
st.subheader("🌍 קומת מאקרו: סביבת שוק וזרימת הון")

try:
    hist_market = get_macro_data()
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

if is_tom_active: cal_status = "TOM פעיל"
elif is_pre_tom_active: cal_status = "Pre-TOM משיכות"
else: cal_status = "שגרה"
col_mac4.metric("📅 סטטוס קלנדרי", cal_status, "חלון מוסדי פעיל" if cal_status != "שגרה" else "", delta_color=tom_color)

st.markdown("<hr style='border: 1px solid #333;'>", unsafe_allow_html=True)
st.subheader("📊 טבלת צלפים: סנכרון רב-ממדי (The 6-Pillar Confluence)")

matrix_sectors = {
    'QQQ': {'name': 'טכנולוגיה', 'long_3x': 'TQQQ', 'short_3x': 'SQQQ', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'SOXX': {'name': 'שבבים', 'long_3x': 'SOXL', 'short_3x': 'SOXS', 'base_weight': -15 if erp_stress > 0.25 else 0},
    'XLF': {'name': 'פיננסים', 'long_3x': 'FAS', 'short_3x': 'FAZ', 'base_weight': 10 if tnx_val > 4.2 else 0},
    'IWM': {'name': 'ראסל 2000', 'long_3x': 'TNA', 'short_3x': 'TZA', 'base_weight': -15 if tnx_val > 4.2 else 0},
    'XLE': {'name': 'אנרגיה', 'long_3x': 'ERX', 'short_3x': 'ERY', 'base_weight': 15 if "Backwardation" in term_structure else 0},
    'XLRE': {'name': 'נדל"ן', 'long_3x': 'DRN', 'short_3x': 'DRV', 'base_weight': -20 if tnx_val > 4.2 else 0},
    'XBI': {'name': 'ביוטק', 'long_3x': 'LABU', 'short_3x': 'LABD', 'base_weight': 0}
}

matrix_table_data = []

for ticker, info in matrix_sectors.items():
    try:
        df_sector = get_sector_data(ticker)
        if not df_sector.empty:
            if isinstance(df_sector.columns, pd.MultiIndex):
                df_sector.columns = [col[0] for col in df_sector.columns]
                
            df_sector['RSI'] = calculate_rsi(df_sector)
            rsi = float(df_sector.iloc[-1]['RSI'])
            
            base_w = info['base_weight']
            rsi_w = 50.0 - rsi
            cal_w = 25 if is_tom_active else (-25 if is_pre_tom_active else 0)
            
            confluence_score = base_w + rsi_w + cal_w
            
            hurst_mult_str = "x1.5" if hurst_spy < 0.5 else "x1.0"
            gann_mult_str = "x1.2" if is_gann_window else "x1.0"
            if hurst_spy < 0.5: confluence_score *= 1.5 
            if is_gann_window: confluence_score *= 1.2
            
            lead_reason = ""
            is_macro_aligned = False
            if ticker == 'XLF' and tnx_val > 4.2: 
                lead_reason, is_macro_aligned = "TNX זינוק", (confluence_score > 0)
            elif ticker in ['IWM', 'XLRE'] and tnx_val > 4.2: 
                lead_reason, is_macro_aligned = "TNX לחץ", (confluence_score < 0)
            elif ticker == 'XLE' and "Backwardation" in term_structure: 
                lead_reason, is_macro_aligned = "נפט מוגן", (confluence_score > 0)
            elif ticker in ['QQQ', 'SOXX'] and erp_stress < 0.25: 
                lead_reason, is_macro_aligned = "VIX בשפל", (confluence_score > 0)
            elif ticker in ['QQQ', 'SOXX'] and erp_stress > 0.25: 
                lead_reason, is_macro_aligned = "ERP זינוק", (confluence_score < 0)
            else: 
                lead_reason = "זרימה פנימית"

            sym_rsi = "🔥" if abs(rsi_w) > 10 else "➖"
            sym_hurst = "📉" if hurst_spy < 0.5 else "➖"
            sym_gann = "⏳" if is_gann_window else "➖"
            sym_tom = "📅" if cal_w != 0 else "➖"
            sym_lead = "🧭" if is_macro_aligned else "➖"
            sym_macro = "🌍" if base_w != 0 else "➖"
            sym_panel = f"\u200E{sym_rsi} {sym_hurst} {sym_gann} {sym_tom} {sym_lead} {sym_macro}"
            
            if confluence_score > 25: status_text, trigger_text = f"🟢 +{confluence_score:.1f}", f"{info['long_3x']}"
            elif confluence_score < -25: status_text, trigger_text = f"🔴 {confluence_score:.1f}", f"{info['short_3x']}"
            else: status_text, trigger_text = f"⚪ {confluence_score:.1f}", "--"

            matrix_table_data.append({
                "פאנל חיווי": sym_panel,
                "הדק (ביצוע)": trigger_text,
                "סקטור (בסיס)": info['name'],
                "קפיץ משוקלל": status_text,
                "🔥 מתיחת (RSI)": f"{rsi_w:+.1f}",
                "📉 הגנת (Hurst)": hurst_mult_str,
                "⏳ תזמון (Gann)": gann_mult_str,
                "📅 עונתיות (TOM)": f"{cal_w:+d}",
                "🧭 איתות (Lead)": lead_reason,
                "🌍 משקל (מאקרו)": f"{base_w:+d}",
                "score": confluence_score
            })
    except: pass

if matrix_table_data:
    df_matrix = pd.DataFrame(matrix_table_data)
    df_matrix['abs_score'] = df_matrix['score'].abs()
    df_matrix = df_matrix.sort_values(by='abs_score', ascending=False).drop(columns=['abs_score', 'score'])
    
    # סידור העמודות המקורי והטוב
    df_matrix = df_matrix[[
        'פאנל חיווי',
        'הדק (ביצוע)',
        'סקטור (בסיס)',
        'קפיץ משוקלל',
        '🔥 מתיחת (RSI)',
        '📉 הגנת (Hurst)',
        '⏳ תזמון (Gann)',
        '📅 עונתיות (TOM)',
        '🧭 איתות (Lead)',
        '🌍 משקל (מאקרו)'
    ]]

    def style_matrix(row):
        styles = [''] * len(row)
        score_val = str(row['קפיץ משוקלל'])
        sym_panel = str(row['פאנל חיווי'])
        active_symbols = len([s for s in sym_panel if s not in ["➖", "\u200E", " "]])
        
        if active_symbols >= 3:
            if "🟢" in score_val: 
                return ['background-color: rgba(0, 255, 0, 0.1); border-bottom: 1px solid #00ff00;'] * len(row)
            elif "🔴" in score_val: 
                return ['background-color: rgba(255, 0, 0, 0.1); border-bottom: 1px solid #ff0000;'] * len(row)
        return styles

    st.dataframe(df_matrix.style.apply(style_matrix, axis=1), use_container_width=True, hide_index=True)

time.sleep(15)
st.rerun()
