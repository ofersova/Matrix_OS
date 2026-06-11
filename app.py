import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
import requests

# --- פונקציות חישוב ---
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

# --- פונקציות נתונים ---
@st.cache_data(ttl=15)
def fetch_macro_data():
    return yf.download(['SPY', '^VIX', '^TNX', 'CL=F'], period='45d', interval='1d', auto_adjust=True, progress=False)

@st.cache_data(ttl=15)
def fetch_sector_data(ticker):
    return yf.download(ticker, period='5d', interval='15m', auto_adjust=True, progress=False)

# --- עיצוב ---
st.set_page_config(page_title="Matrix OS", layout="wide")
st.markdown("""
    <style>
    .stApp *:not(.blink) { opacity: 1 !important; transition: none !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }
    </style>
""", unsafe_allow_html=True)

now_dt = datetime.now()
st.title("⚡ Matrix OS - מערכת פיקוד מוסדית")
st.write(f"🔄 מתעדכן חי | {now_dt.strftime('%H:%M:%S')}")

# --- מנוע פיננסי ---
sectors = {
    'QQQ': {'name': 'טכנולוגיה', 'long_3x': 'TQQQ', 'short_3x': 'SQQQ'},
    'SOXX': {'name': 'שבבים', 'long_3x': 'SOXL', 'short_3x': 'SOXS'},
    'XLF': {'name': 'פיננסים', 'long_3x': 'FAS', 'short_3x': 'FAZ'},
    'IWM': {'name': 'ראסל 2000', 'long_3x': 'TNA', 'short_3x': 'TZA'},
    'XLE': {'name': 'אנרגיה', 'long_3x': 'ERX', 'short_3x': 'ERY'},
    'XLRE': {'name': 'נדלן', 'long_3x': 'DRN', 'short_3x': 'DRV'},
    'XBI': {'name': 'ביוטק', 'long_3x': 'LABU', 'short_3x': 'LABD'},
    'XLV': {'name': 'בריאות', 'long_3x': 'CURE', 'short_3x': 'RXD'},
    'XLU': {'name': 'תשתיות', 'long_3x': 'UTSL', 'short_3x': 'XLU'},
    'XLI': {'name': 'תעשייה', 'long_3x': 'DUSL', 'short_3x': 'XLI'},
    'XLY': {'name': 'צריכה-מ', 'long_3x': 'WANT', 'short_3x': 'XLY'},
    'XLP': {'name': 'צריכה-ב', 'long_3x': 'NEED', 'short_3x': 'XLP'},
    'XLB': {'name': 'חומרי גלם', 'long_3x': 'XLB', 'short_3x': 'XLB'},
    'URA': {'name': 'גרעין', 'long_3x': 'URA', 'short_3x': 'URA'},
    'QTUM': {'name': 'קוואנטום', 'long_3x': 'QTUM', 'short_3x': 'QTUM'},
    'ARKX': {'name': 'חלל', 'long_3x': 'ARKX', 'short_3x': 'ARKX'}
}

# --- חישוב מאקרו ---
hist = fetch_macro_data()
vix_val = float(hist['Close']['^VIX'].iloc[-1])
tnx_val = float(hist['Close']['^TNX'].iloc[-1])
oil_price = float(hist['Close']['CL=F'].iloc[-1])
erp_stress = (vix_val / 100.0) + (tnx_val / 100.0)
is_gann = (20 <= now_dt.day <= 23) and (now_dt.month in [3, 6, 9, 12])

# --- בניית הטבלה ---
data_list = []
for ticker, info in sectors.items():
    df = fetch_sector_data(ticker)
    if df.empty: continue
    rsi = calculate_rsi(df).iloc[-1]
    score = (50 - rsi)
    
    # סימבולים
    syms = "🔥" if abs(50-rsi) > 10 else "➖"
    syms += "⏳" if is_gann else "➖"
    
    data_list.append({
        "פאנל": syms,
        "הדק": info['long_3x'] if score > 0 else info['short_3x'],
        "סקטור": info['name'],
        "ציון": f"{score:.1f}",
        "RSI": f"{50-rsi:.1f}"
    })

df_final = pd.DataFrame(data_list)
st.dataframe(df_final, use_container_width=True, hide_index=True, height=750)

time.sleep(15)
st.rerun()
