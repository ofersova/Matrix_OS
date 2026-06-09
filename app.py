import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import datetime

# --- הגדרות תצוגה ---
st.set_page_config(page_title="Matrix OS - Live Dashboard", layout="wide", page_icon="📈")
st.title("📈 Matrix OS - מערכת פיקוד ובקרה מוסדית")
st.markdown("---")

# --- רשימות מעקב (Tickers) ---
macro_tickers = {'VIX': '^VIX', 'DXY': 'DX-Y.NYB', 'US 10Y': '^TNX'}
sectors = {
    'Tech': 'XLK', 'Energy': 'XLE', 'Financials': 'XLF', 'Utilities': 'XLU',
    'Materials': 'XLB', 'Staples': 'XLP', 'Real Estate': 'XLRE', 'Nuclear': 'URA', 'Quantum': 'QTUM'
}
commodities = {
    'Crude Oil': 'CL=F', 'Silver': 'SI=F', 'Platinum': 'PL=F', 
    'Sugar': 'SB=F', 'Wheat': 'ZW=F', 'Nat Gas': 'NG=F'
}
micro_intraday = {'ASTS': 'ASTS', 'NNE': 'NNE', 'IREN': 'IREN', 'DASH': 'DASH', 'TQQQ': 'TQQQ', 'SQQQ': 'SQQQ', 'TZA': 'TZA'}

# --- פונקציות משיכת נתונים וחישובים ---
@st.cache_data(ttl=60) # רענון כל 60 שניות
def fetch_data(ticker_dict):
    data = []
    for name, ticker in ticker_dict.items():
        try:
            hist = yf.Ticker(ticker).history(period="1mo")
            if hist.empty: continue
            
            close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = ((close - prev_close) / prev_close) * 100
            
            # חישוב RSI של 14 יום (לזיהוי מכירת יתר)
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            data.append({'Name': name, 'Price': round(close, 2), 'Change (%)': round(change, 2), 'RSI': round(rsi, 1)})
        except:
            pass
    return pd.DataFrame(data)

# --- קומת המאקרו: שעון הריסק ---
st.subheader("🌐 שכבת המאקרו: Risk-On / Risk-Off")
macro_df = fetch_data(macro_tickers)

if not macro_df.empty:
    vix_val = macro_df[macro_df['Name'] == 'VIX']['Price'].values[0] if 'VIX' in macro_df['Name'].values else 20
    dxy_val = macro_df[macro_df['Name'] == 'DXY']['Price'].values[0] if 'DXY' in macro_df['Name'].values else 100
    
    # אלגוריתם פשוט לשעון הריסק: שקלול של VIX ו-DXY
    # ציון 100 = ירוק (אופטימי), ציון 0 = אדום (פאניקה)
    risk_score = 100 - ((min(vix_val, 40) / 40) * 50) - ((max(dxy_val - 95, 0) / 15) * 50)
    risk_score = max(min(risk_score, 100), 0)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = risk_score,
            title = {'text': "מדד סביבת סיכון (מוכוון VIX ו-DXY)"},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "white"},
                'steps': [
                    {'range': [0, 35], 'color': "red"},
                    {'range': [35, 65], 'color': "yellow"},
                    {'range': [65, 100], 'color': "green"}],
                'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': risk_score}
            }
        ))
        fig.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)
        
    with col1:
        st.metric("VIX (מדד הפחד)", f"{vix_val:.2f}", "פאניקה אם > 30" if vix_val > 30 else "רוגע", delta_color="inverse")
    with col3:
        st.metric("DXY (מדד הדולר)", f"{dxy_val:.2f}", "פוגע בסחורות אם > 100" if dxy_val > 100 else "תומך בסחורות", delta_color="inverse")

st.markdown("---")

# --- שכבת הרוטציה והסחורות ---
col_sec, col_com = st.columns(2)

with col_sec:
    st.subheader("🔄 רוטציית סקטורים")
    df_sec = fetch_data(sectors)
    if not df_sec.empty:
        # צביעה מותנית
        def color_change(val):
            color = 'green' if val > 0 else 'red'
            return f'color: {color}'
        st.dataframe(df_sec.style.map(color_change, subset=['Change (%)']), use_container_width=True)

with col_com:
    st.subheader("🛢️ סחורות (קורלציות ועונתיות)")
    df_com = fetch_data(commodities)
    if not df_com.empty:
        # הוספת הערות עונתיות
        notes = []
        for name in df_com['Name']:
            if name == 'Wheat': notes.append("עונתיות ינואר: חשש למזג אוויר")
            elif name == 'Sugar': notes.append("קורלציה לנפט גולמי")
            elif name in ['Platinum', 'Silver']: notes.append("קורלציה ל-Risk-On תעשייתי")
            else: notes.append("-")
        df_com['הערות'] = notes
        st.dataframe(df_com, use_container_width=True)

st.markdown("---")

# --- שכבת המיקרו: סווינג ומסחר יומי ---
st.subheader("🎯 מיקרו: סווינג ומסחר תוך-יומי ממונף")
st.markdown("*זיהוי שינויי מגמה מבוססי פונדמנטל / ARK ותעודות שורט*")
df_micro = fetch_data(micro_intraday)

if not df_micro.empty:
    def highlight_rsi(val):
        if val < 30: return 'background-color: lightgreen; color: black; font-weight: bold'
        elif val > 70: return 'background-color: lightcoral; color: black; font-weight: bold'
        return ''
    
    st.dataframe(df_micro.style.map(highlight_rsi, subset=['RSI']), use_container_width=True)
    
    # מנגנון התראות למכירת יתר (Oversold)
    oversold = df_micro[df_micro['RSI'] < 30]['Name'].tolist()
    if oversold:
        st.success(f"🚨 איתות ריסק-און: הנכסים הבאים נמצאים במכירת יתר קיצונית ויש לחפש בהם טריגר כניסה: {', '.join(oversold)}")

if st.button("🔄 רענן נתונים בזמן אמת"):
    st.rerun()
