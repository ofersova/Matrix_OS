import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
import requests

# --- הגדרות עמוד ---
st.set_page_config(page_title="Matrix OS V7 - Institutional", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .green-text { color: #00ff00; font-weight: bold; font-size: 16px; }
    .red-text { color: #ff0000; font-weight: bold; font-size: 16px; }
    .orange-text { color: #ffa500; font-weight: bold; font-size: 16px; }
    .yellow-text { color: #ffff00; font-weight: bold; font-size: 16px; }
    .blink { animation: blinker 1.5s linear infinite; color: #ffcc00; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
    .stApp *:not(.blink) { opacity: 1 !important; transition: none !important; }
    div[data-testid="stStatusWidget"] { opacity: 0 !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- נתוני בסיס סטטיים מ-Finviz (רוטציית סקטורים חודשית ורבעונית) ---
sector_perf_history = {
    'XLK': {'qtr': 27.13, 'mo': 2.52},
    'XLF': {'qtr': 11.46, 'mo': 4.60},
    'XLU': {'qtr': -4.30, 'mo': -1.52},
    'XLE': {'qtr': 0.67, 'mo': -1.58},
    'XLRE': {'qtr': 6.94, 'mo': 2.46},
    'XLV': {'qtr': 3.22, 'mo': 3.11},
    'XLI': {'qtr': 9.17, 'mo': 1.64},
    'XLY': {'qtr': 4.66, 'mo': -4.19},
    'XLP': {'qtr': 0.32, 'mo': -0.77},
    'XLB': {'qtr': 4.24, 'mo': -4.96},
    'URA': {'qtr': 5.0, 'mo': 1.0},
    'QTUM': {'qtr': 15.0, 'mo': 2.0},
    'ARKX': {'qtr': 8.0, 'mo': 1.0}
}

# --- פונקציות מתמטיות ---
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

def create_sparkline(series, color):
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode='lines', line=dict(color=color, width=2)))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=50, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False)
    return fig

# --- זיכרון מטמון ---
@st.cache_data(ttl=15)
def fetch_macro_data():
    return yf.download(['SPY', '^VIX', '^TNX', 'CL=F', 'DX-Y.NYB', 'BTC-USD', 'QQQ', 'DIA'], period='5d', interval='5m', auto_adjust=True, progress=False)

@st.cache_data(ttl=15)
def fetch_sector_data(ticker):
    return yf.download(ticker, period='5d', interval='15m', auto_adjust=True, progress=False)

now_dt = datetime.utcnow() + timedelta(hours=3)

st.title("⚡ Matrix OS - מערכת פיקוד מוסדית")
st.write(f"🔄 מתעדכן חי | זמן מערכת: {now_dt.strftime('%H:%M:%S')}")
st.markdown("---")

# ==========================================
# 1. קומת המאקרו והאינדיקטורים המקדימים
# ==========================================
col_m1, col_m2, col_m3 = st.columns([1.2, 1.8, 1])

try:
    hist_macro = fetch_macro_data()
    if isinstance(hist_macro.columns, pd.MultiIndex):
        hist_macro.columns = [f"{col[0]}_{col[1]}" for col in hist_macro.columns]
except:
    hist_macro = pd.DataFrame()

with col_m2:
    try:
        vix_val = hist_macro['Close_^VIX'].dropna().iloc[-1]
        fg_score = 100 - (vix_val * 2.5)
        fg_score = max(min(fg_score, 100), 0)
    except:
        fg_score = 35
        
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
        dxy_s = hist_macro['Close_DX-Y.NYB'].dropna().tail(24*12)
        dxy_val, dxy_start = float(dxy_s.iloc[-1]), float(dxy_s.iloc[0])
        dxy_color = "#00ff00" if dxy_val >= dxy_start else "#ff0000"
    except:
        dxy_s = pd.Series([99, 99]); dxy_val, dxy_color = 99.5, "#00ff00"
        
    c1_a, c1_b = st.columns([1.5, 1])
    with c1_a: st.metric("DXY Dollar Index", f"{dxy_val:.2f}", "רוח גבית לסחורות" if dxy_val < 100 else "לחץ מוכר בסחורות", delta_color="inverse")
    with c1_b: st.plotly_chart(create_sparkline(dxy_s, dxy_color), use_container_width=True, config={'displayModeBar': False})
    
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/current"
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            cnn_score = int(float(r.json()['fear_and_greed']['score']))
            cnn_rating = str(r.json()['fear_and_greed']['rating']).capitalize()
        else: raise Exception
    except:
        cnn_score, cnn_rating = 35, "Fear"
        
    try:
        vix_s = hist_macro['Close_^VIX'].dropna().tail(24*12)
        fg_s = 100 - (vix_s * 2.5)
        fg_color = "#00ff00" if fg_s.iloc[-1] >= fg_s.iloc[0] else "#ff0000"
    except:
        fg_s = pd.Series([35, 35]); fg_color = "#ff0000"
        
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    c2_a, c2_b = st.columns([1.5, 1])
    with c2_a: st.metric("CNN Fear & Greed", f"{cnn_score} / 100", cnn_rating, delta_color="off")
    with c2_b: st.plotly_chart(create_sparkline(fg_s, fg_color), use_container_width=True, config={'displayModeBar': False})

with col_m3:
    st.markdown("### 📢 משבשי מגמה ומבזקים")
    st.markdown("<p class='blink'>🚨 התראת מאקרו: שים לב לפער בין הדולר לנאסדק!</p>", unsafe_allow_html=True)
    st.info("💡 ארבעת מצבי החץ: 🔴 ירידה חדה | 🟠 תחילת איסוף (הכן פקודה) | 🟢 עלייה מובהקת | 🟡 תחילת פיזור (התכונן למכור)")

st.markdown("---")

# ==========================================
# 2. חדר מלחמה: מודל מקרו-היפוך תוך יומי (RORO)
# ==========================================
st.subheader("🌐 חדר מלחמה (Macro-Reversal & Liquidity Walls)")
col_rev1, col_rev2 = st.columns([1, 1.5])

lead_data = []
for tick, name in [('DX-Y.NYB', 'דולר (DXY)'), ('^TNX', 'תשואות (TNX)'), ('BTC-USD', 'ביטקוין (BTC)'), ('CL=F', 'נפט (Oil)')]:
    try:
        s = hist_macro[f'Close_{tick}'].dropna()
        c_p = float(s.iloc[-1]); p_p = float(s.iloc[-72]) if len(s)>72 else float(s.iloc[0])
        chg = ((c_p - p_p) / p_p) * 100
        arr = "🔴 יורד (Risk-On)" if chg < 0 else "🟢 עולה (Risk-Off)"
        if tick == 'BTC-USD': arr = "🟢 עולה (Risk-On)" if chg > 0 else "🔴 יורד (Risk-Off)"
        if tick == 'CL=F': arr = "🔴 יורד (הקלה)" if chg < 0 else "🟢 עולה (לחץ אינפלציה)"
        lead_data.append({"נכס מקדים": name, "שינוי יומי": f"{chg:+.2f}%", "מגמה": arr})
    except: pass

with col_rev1:
    st.markdown("**🧭 סמנים מקדימים (זרימת נזילות)**")
    if lead_data:
        st.dataframe(pd.DataFrame(lead_data), use_container_width=True, hide_index=True)

def get_4state_arrow(series_1m, series_5m, curr_price, val, vah):
    if len(series_5m) < 5: return "⚪", 0, 0
    mom_1m = float(series_1m.iloc[-1] - series_1m.iloc[-5]) if len(series_1m)>5 else 0
    mom_5m = float(series_5m.iloc[-1] - series_5m.iloc[-3])
    
    score = np.sign(mom_1m) + np.sign(mom_5m)
    upside = ((vah - curr_price) / curr_price) * 100
    downside = ((curr_price - val) / curr_price) * 100
    
    if curr_price < val and score > 0:
        return f"🟠 איסוף ללונג 🔼\n(יעד: +{upside:.2f}%)", upside, downside
    elif curr_price > vah and score < 0:
        return f"🟡 פיזור לשורט 🔽\n(יעד: -{downside:.2f}%)", upside, downside
    elif score >= 1:
        return f"🟢 עלייה חזקה 🔼\n(יעד: +{upside:.2f}%)", upside, downside
    elif score <= -1:
        return f"🔴 ירידה חדה 🔽\n(יעד: -{downside:.2f}%)", upside, downside
    else:
        return f"⚪ דשדוש\n(רצפה: -{downside:.2f}%)", upside, downside

indices_data = []
for tick, name in [('SPY', 'S&P 500 (SPY)'), ('QQQ', 'Nasdaq (QQQ)'), ('DIA', 'Dow Jones (DIA)')]:
    try:
        df_5m = hist_macro[f'Close_{tick}'].dropna()
        curr_price = float(df_5m.iloc[-1])
        vols = hist_macro[f'Volume_{tick}'].dropna()
        bins = np.linspace(df_5m.min(), df_5m.max(), 50)
        digitized = np.digitize(df_5m, bins)
        vol_profile = np.zeros(len(bins)-1)
        for i in range(1, len(bins)): vol_profile[i-1] = vols[digitized == i].sum()
        poc_idx = np.argmax(vol_profile)
        
        va_volume = vol_profile[poc_idx]
        target_volume = vol_profile.sum() * 0.70
        upper_idx, lower_idx = poc_idx, poc_idx
        while va_volume < target_volume:
            can_up, can_down = upper_idx < len(vol_profile)-1, lower_idx > 0
            if not can_up and not can_down: break
            if can_up and (not can_down or vol_profile[upper_idx+1] >= vol_profile[lower_idx-1]):
                upper_idx += 1; va_volume += vol_profile[upper_idx]
            else:
                lower_idx -= 1; va_volume += vol_profile[lower_idx]
                
        vah = (bins[upper_idx] + bins[upper_idx+1])/2
        val = (bins[lower_idx] + bins[lower_idx+1])/2
        
        df_1m = yf.download(tick, period='1d', interval='1m', progress=False)['Close'].dropna()
        arrow_state, up_pct, dn_pct = get_4state_arrow(df_1m, df_5m, curr_price, val, vah)
        
        indices_data.append({
            "מדד מוביל": name,
            "מחיר": f"{curr_price:.2f}$",
            "מכונת מצבים ויעדי נזילות": arrow_state
        })
    except: pass

with col_rev2:
    st.markdown("**🎯 המדדים המובילים (מכונת 4-מצבים ונזילות)**")
    if indices_data:
        st_df = pd.DataFrame(indices_data)
        def color_state(val):
            if "🟢" in val: return "color: #00ff00; font-weight: bold; white-space: pre-wrap;"
            if "🔴" in val: return "color: #ff0000; font-weight: bold; white-space: pre-wrap;"
            if "🟠" in val: return "color: #ffa500; font-weight: bold; white-space: pre-wrap;"
            if "🟡" in val: return "color: #ffff00; font-weight: bold; white-space: pre-wrap;"
            return "white-space: pre-wrap;"
        st.dataframe(st_df.style.applymap(color_state, subset=['מכונת מצבים ויעדי נזילות']), use_container_width=True, hide_index=True)

st.markdown("---")

# ==========================================
# 3. טבלת סדרי עדיפויות לנכסים הממונפים (Sector Momentum Rotation)
# ==========================================
st.subheader("🔥 מנוע עדיפויות ממונף: רוטציית כסף חכם")
st.markdown("דירוג אוטומטי של תעודות הסל לביצוע עסקאות לפי עוצמת הכסף שנכנס לסקטור (חודשי, רבעוני ותוך-יומי).")

lev_pairs = {
    'טכנולוגיה': {'base': 'XLK', 'long': 'TQQQ', 'short': 'SQQQ'},
    'שבבים': {'base': 'SOXX', 'long': 'SOXL', 'short': 'SOXS'},
    'פיננסים': {'base': 'XLF', 'long': 'FAS', 'short': 'FAZ'},
    'אנרגיה': {'base': 'XLE', 'long': 'ERX', 'short': 'ERY'},
    'בריאות': {'base': 'XLV', 'long': 'CURE', 'short': 'RXD'},
    'תעשייה': {'base': 'XLI', 'long': 'DUSL', 'short': 'XLI'},
}

momentum_rank = []
for sec_name, data in lev_pairs.items():
    try:
        base_tick = data['base']
        s_data = fetch_sector_data(base_tick)
        intra_chg = 0.0
        
        if not s_data.empty:
            # תיקון שגיאת המבנה המורכב של הפאנדס (MultiIndex)
            if isinstance(s_data.columns, pd.MultiIndex):
                closes = s_data['Close'].iloc[:, 0].dropna()
            else:
                closes = s_data['Close'].dropna()
                
            c_last = float(closes.iloc[-1])
            c_first = float(closes.iloc[0])
            intra_chg = ((c_last - c_first) / c_first) * 100
            
        qtr_p = float(sector_perf_history.get(base_tick, {}).get('qtr', 0))
        mo_p = float(sector_perf_history.get(base_tick, {}).get('mo', 0))
        
        # נוסחת שקלול המומנטום (וידוא שהתוצאה היא מספר עשרוני טהור)
        power_score = float((qtr_p * 0.4) + (mo_p * 0.3) + (intra_chg * 0.3))
        
        momentum_rank.append({
            "סקטור": sec_name,
            "ציון מומנטום": power_score,
            "תעודה ללונג 🔼": data['long'],
            "תעודה לשורט 🔽": data['short'],
            "זרימת הון היסטורית": f"רבעון: {qtr_p}% | חודש: {mo_p}%"
        })
    except Exception as e: 
        pass

if momentum_rank:
    # כאן קרתה השגיאה המקורית - עכשיו כשהנתונים הם float בלבד הבעיה נפתרה!
    df_mom = pd.DataFrame(momentum_rank).sort_values(by="ציון מומנטום", ascending=False)
    df_mom['ציון מומנטום'] = df_mom['ציון מומנטום'].apply(lambda x: f"{x:+.2f}")
    
    def color_mom(row):
        try:
            score = float(str(row['ציון מומנטום']).replace('+', ''))
            if score > 5: return ['background-color: rgba(0, 255, 0, 0.2);'] * len(row)
            if score < -5: return ['background-color: rgba(255, 0, 0, 0.2);'] * len(row)
        except: pass
        return [''] * len(row)
        
    st.dataframe(df_mom.style.apply(color_mom, axis=1), use_container_width=True, hide_index=True)

st.markdown("---")

# ==========================================
# 4. טבלת סנכרון המקורית (6 Pillars)
# ==========================================
st.subheader("📊 טבלת צלפים: סנכרון רב-ממדי (The 6-Pillar Confluence)")

try:
    tnx_val = float(hist_macro['Close_^TNX'].dropna().iloc[-1])
    vix_val = float(hist_macro['Close_^VIX'].dropna().iloc[-1])
    oil_price = float(hist_macro['Close_CL=F'].dropna().iloc[-1])
    erp_stress = (vix_val / 100.0) + (tnx_val / 100.0)
    term_structure = "Backwardation" if oil_price > 80 else "Contango"
    hurst_spy = 0.6
except:
    tnx_val, erp_stress, term_structure, hurst_spy = 4.0, 0.2, "ניטרלי", 0.5

matrix_sectors = {
    'QQQ': {'name': 'טכנולוגיה', 'long_3x': 'TQQQ', 'short_3x': 'SQQQ', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'SOXX': {'name': 'שבבים (SOXX)', 'long_3x': 'SOXL', 'short_3x': 'SOXS', 'base_weight': -15 if erp_stress > 0.25 else 0},
    'XLF': {'name': 'פיננסים (XLF)', 'long_3x': 'FAS', 'short_3x': 'FAZ', 'base_weight': 10 if tnx_val > 4.2 else 0},
    'IWM': {'name': 'ראסל 2000 (IWM)', 'long_3x': 'TNA', 'short_3x': 'TZA', 'base_weight': -15 if tnx_val > 4.2 else 0},
    'XLE': {'name': 'אנרגיה (XLE)', 'long_3x': 'ERX', 'short_3x': 'ERY', 'base_weight': 15 if "Backwardation" in term_structure else 0},
    'XLRE': {'name': 'נדלן (XLRE)', 'long_3x': 'DRN', 'short_3x': 'DRV', 'base_weight': -20 if tnx_val > 4.2 else 0},
    'XBI': {'name': 'ביוטק (XBI)', 'long_3x': 'LABU', 'short_3x': 'LABD', 'base_weight': 0},
    'XLV': {'name': 'בריאות (XLV)', 'long_3x': 'CURE', 'short_3x': 'RXD', 'base_weight': 10 if erp_stress > 0.25 else 0},
    'XLU': {'name': 'תשתיות (XLU)', 'long_3x': 'UTSL', 'short_3x': 'XLU', 'base_weight': 15 if erp_stress > 0.25 else 0},
    'XLI': {'name': 'תעשייה (XLI)', 'long_3x': 'DUSL', 'short_3x': 'XLI', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'XLY': {'name': 'צריכה מחזורית (XLY)', 'long_3x': 'WANT', 'short_3x': 'XLY', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'XLP': {'name': 'צריכה בסיסית (XLP)', 'long_3x': 'NEED', 'short_3x': 'XLP', 'base_weight': 10 if erp_stress > 0.25 else 0}
}

matrix_table_data = []
for ticker, info in matrix_sectors.items():
    try:
        df_sector = fetch_sector_data(ticker)
        if not df_sector.empty:
            if isinstance(df_sector.columns, pd.MultiIndex): df_sector.columns = [col[0] for col in df_sector.columns]
            df_sector['RSI'] = calculate_rsi(df_sector)
            rsi = float(df_sector['RSI'].iloc[-1])
            base_w = info['base_weight']
            rsi_w = 50.0 - rsi
            cal_w = 0
            confluence_score = base_w + rsi_w + cal_w
            if hurst_spy < 0.5: confluence_score *= 1.5 
            
            lead_reason = "זרימה פנימית"
            is_macro_aligned = False
            
            sym_rsi = "🔥" if abs(rsi_w) > 10 else "➖"
            sym_hurst = "📉" if hurst_spy < 0.5 else "➖"
            sym_gann = "➖"
            sym_tom = "➖"
            sym_lead = "🧭" if is_macro_aligned else "➖"
            sym_macro = "🌍" if base_w != 0 else "➖"
            
            sym_panel = f"\u200E{sym_rsi} {sym_hurst} {sym_gann} {sym_tom} {sym_lead} {sym_macro}"
            
            if confluence_score > 25:
                status_text = f"🟢 +{confluence_score:.1f} (לונג)"
                trigger_text = f"{info['long_3x']}"
            elif confluence_score < -25:
                status_text = f"🔴 {confluence_score:.1f} (שורט)"
                trigger_text = f"{info['short_3x']}"
            else:
                status_text = f"⚪ {confluence_score:.1f}"
                trigger_text = "--"

            matrix_table_data.append({
                "פאנל חיווי": sym_panel,
                "הדק\n(ביצוע)": trigger_text,
                "סקטור\n(בסיס)": info['name'],
                "קפיץ\nמשוקלל": status_text,
                "🔥 (RSI)\nמתיחת מיקרו": f"{rsi_w:+.1f}",
                "📉 (Hurst)\nמכפיל הגנה": "x1.0",
                "⏳ (Gann)\nתזמון": "x1.0",
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
    df_matrix = df_matrix[['פאנל חיווי', 'הדק\n(ביצוע)', 'סקטור\n(בסיס)', 'קפיץ\nמשוקלל', '🔥 (RSI)\nמתיחת מיקרו', '📉 (Hurst)\nמכפיל הגנה', '⏳ (Gann)\nתזמון', '📅 (TOM)\nעונתיות', '🧭 (Lead)\nאיתות', '🌍 (Macro)\nמשקל']]

    def style_matrix(row):
        styles = [''] * len(row)
        score_val = str(row['קפיץ\nמשוקלל'])
        sym_panel = str(row['פאנל חיווי'])
        if len([s for s in sym_panel if s not in ["➖", "\u200E", " "]]) >= 3:
            if "לונג" in score_val: return ['background-color: rgba(0, 255, 0, 0.1); border-bottom: 1px solid #00ff00;'] * len(row)
            elif "שורט" in score_val: return ['background-color: rgba(255, 0, 0, 0.1); border-bottom: 1px solid #ff0000;'] * len(row)
        return styles
    st.dataframe(df_matrix.style.apply(style_matrix, axis=1), use_container_width=True, hide_index=True)

st.markdown("---")

# ==========================================
# 5. טבלת צלפים PRO (LVN)
# ==========================================
st.subheader("🎯 טבלת צלפים PRO (מכונת מצבים ואימות נפחי קצה - LVN)")

@st.cache_data(ttl=120)
def get_pro_state_machine_targets():
    bases = list(matrix_sectors.keys())
    lev_tickers_set = set()
    for v in matrix_sectors.values():
        if v['long_3x'] != '--': lev_tickers_set.add(v['long_3x'])
        if v['short_3x'] != '--': lev_tickers_set.add(v['short_3x'])
        
    lev_tickers = list(lev_tickers_set)
    intra_all = yf.download(bases, period="5d", interval="5m", progress=False)
    lev_data = yf.download(lev_tickers, period="1d", interval="1m", progress=False)
    
    def get_last_price(df, ticker):
        try:
            if isinstance(df.columns, pd.MultiIndex):
                if ('Close', ticker) in df.columns: return float(df[('Close', ticker)].dropna().iloc[-1])
            elif f"Close_{ticker}" in df.columns: return float(df[f"Close_{ticker}"].dropna().iloc[-1])
            elif ticker in df.columns: return float(df[ticker].dropna().iloc[-1])
        except: pass
        try: return float(yf.Ticker(ticker).fast_info.last_price)
        except: return 0.0

    results = []
    for base in bases:
        try:
            if isinstance(intra_all.columns, pd.MultiIndex):
                if ('Close', base) in intra_all.columns:
                    prices = intra_all[('Close', base)].dropna()
                    vols = intra_all[('Volume', base)].dropna()
                else: continue
            else:
                if 'Close' in intra_all.columns and len(bases) == 1:
                    prices = intra_all['Close'].dropna(); vols = intra_all['Volume'].dropna()
                else: continue
                
            if prices.empty: continue
            curr_base = float(prices.iloc[-1])
            today_date = prices.index[-1].date()
            today_prices = prices[prices.index.date == today_date]
            
            if not today_prices.empty:
                if isinstance(intra_all.columns, pd.MultiIndex):
                    try:
                        h_series = intra_all[('High', base)]
                        l_series = intra_all[('Low', base)]
                        HOD = float(h_series.dropna()[h_series.dropna().index.date == today_date].max())
                        LOD = float(l_series.dropna()[l_series.dropna().index.date == today_date].min())
                    except: HOD, LOD = float(today_prices.max()), float(today_prices.min())
                else: HOD, LOD = float(today_prices.max()), float(today_prices.min())
            else: HOD, LOD = float(prices.max()), float(prices.min())
            
            bins = np.linspace(prices.min(), prices.max(), 50)
            digitized = np.digitize(prices, bins)
            vol_profile = np.zeros(len(bins)-1)
            bin_centers = (bins[:-1] + bins[1:]) / 2
            
            for i in range(1, len(bins)): vol_profile[i-1] = vols[digitized == i].sum()
                
            poc_idx = np.argmax(vol_profile)
            poc_price = bin_centers[poc_idx]
            poc_vol = vol_profile[poc_idx]
            
            va_volume = poc_vol
            target_volume = vol_profile.sum() * 0.70
            upper_idx, lower_idx = poc_idx, poc_idx
            while va_volume < target_volume:
                can_up, can_down = upper_idx < len(vol_profile)-1, lower_idx > 0
                if not can_up and not can_down: break
                vol_up = vol_profile[upper_idx + 1] if can_up else 0
                vol_down = vol_profile[lower_idx - 1] if can_down else 0
                if vol_up >= vol_down and can_up: upper_idx += 1; va_volume += vol_up
                elif can_down: lower_idx -= 1; va_volume += vol_down
                else: break
                    
            VAH, VAL = bin_centers[upper_idx], bin_centers[lower_idx]
            
            hod_idx = np.clip(np.digitize([HOD], bins)[0] - 1, 0, len(vol_profile) - 1)
            lod_idx = np.clip(np.digitize([LOD], bins)[0] - 1, 0, len(vol_profile) - 1)
            is_hod_lvn = vol_profile[hod_idx] < (poc_vol * 0.25)
            is_lod_lvn = vol_profile[lod_idx] < (poc_vol * 0.25)
            
            long_tick = matrix_sectors[base]['long_3x']
            short_tick = matrix_sectors[base]['short_3x']
            curr_long = get_last_price(lev_data, long_tick) if long_tick != '--' else 0.0
            curr_short = get_last_price(lev_data, short_tick) if short_tick != '--' else 0.0
            if curr_long == 0 and curr_short == 0: continue
            
            def calc_lev_target(res_price, lev_price, is_long_asset):
                dist = (res_price - curr_base) / curr_base
                mult = 3 if is_long_asset else -3
                if is_long_asset and long_tick == base: mult = 1
                if not is_long_asset and short_tick == base: mult = -1
                return dist, lev_price * (1 + (dist * mult))
            
            state_color, direction, target_lev_tick, target_lev_price, target_poc_price, active_res, dist_pct, lvn_status = "white", "--", "--", "--", "--", "--", 0.0, "➖"
            
            if curr_base > VAH:
                state_color, status_text, direction, active_res = "orange", "🚨 איסוף נזילות מעל התנגדות (VAH)", "שורט", f"VAH\n({VAH:.2f}$)"
                target_lev_tick = f"{short_tick}\n({curr_short:.2f}$)"
                dist_pct, target_lev_price = calc_lev_target(VAH, curr_short, False)
                _, target_poc_price = calc_lev_target(poc_price, curr_short, False)
                lvn_status = "✅ מאושר (נפח דליל)" if is_hod_lvn else "❌ נדחה (נפח גבוה בפריצה)"
            elif curr_base < VAH and HOD > VAH:
                if is_hod_lvn:
                    state_color, status_text, direction, active_res = "green", "✅ פריצת שווא אושרה (CHOCH)", "שורט", f"VAH\n({VAH:.2f}$)"
                    target_lev_tick = f"{short_tick}\n({curr_short:.2f}$)"
                    dist_pct, target_lev_price = calc_lev_target(VAH, curr_short, False)
                    _, target_poc_price = calc_lev_target(poc_price, curr_short, False)
                    lvn_status = "✅ מאושר (נפח דליל)"
                else: state_color, status_text, direction, active_res, lvn_status = "white", "⚪ חזרה מפריצה מגמתית (אין CHOCH)", "ניטרלי", f"VAH\n({VAH:.2f}$)", "❌ נדחה (נפח גבוה בפריצה)"
            elif curr_base < VAL:
                state_color, status_text, direction, active_res = "orange", "🚨 איסוף נזילות מתחת לתמיכה (VAL)", "לונג", f"VAL\n({VAL:.2f}$)"
                target_lev_tick = f"{long_tick}\n({curr_long:.2f}$)"
                dist_pct, target_lev_price = calc_lev_target(VAL, curr_long, True)
                _, target_poc_price = calc_lev_target(poc_price, curr_long, True)
                lvn_status = "✅ מאושר (נפח דליל)" if is_lod_lvn else "❌ נדחה (נפח גבוה בשבירה)"
            elif curr_base > VAL and LOD < VAL:
                if is_lod_lvn:
                    state_color, status_text, direction, active_res = "green", "✅ שבירת שווא אושרה (CHOCH)", "לונג", f"VAL\n({VAL:.2f}$)"
                    target_lev_tick = f"{long_tick}\n({curr_long:.2f}$)"
                    dist_pct, target_lev_price = calc_lev_target(VAL, curr_long, True)
                    _, target_poc_price = calc_lev_target(poc_price, curr_long, True)
                    lvn_status = "✅ מאושר (נפח דליל)"
                else: state_color, status_text, direction, active_res, lvn_status = "white", "⚪ התאוששות (אין CHOCH)", "ניטרלי", f"VAL\n({VAL:.2f}$)", "❌ נדחה (נפח גבוה בשבירה)"
            elif abs(curr_base - poc_price) / curr_base <= 0.005:
                state_color, status_text, direction, active_res, dist_pct = "yellow", "⚖️ נתמך על ליבת הנזילות (POC)", "ניטרלי", f"POC\n({poc_price:.2f}$)", (poc_price - curr_base)/curr_base
            else:
                state_color, status_text, direction, active_res = "white", "⚪ ממתין לפריצה בתוך אזור הערך", "ניטרלי", f"VAH ({VAH:.0f}$) | VAL ({VAL:.0f}$)"
                
            results.append({'base': base, 'curr_base': curr_base, 'direction': direction, 'status': status_text, 'color': state_color, 'target_tick': target_lev_tick, 'active_res': active_res, 'dist': dist_pct, 't1': target_lev_price, 't2': target_poc_price, 'lvn': lvn_status})
        except: continue
    return results

pro_data = get_pro_state_machine_targets()
if pro_data:
    pro_table = []
    for d in pro_data:
        t1_str = f"[{d['t1']:.2f}$]" if isinstance(d['t1'], float) else "--"
        t2_str = f"[{d['t2']:.2f}$]" if isinstance(d['t2'], float) else "--"
        pro_table.append({"סקטור (בסיס)": f"{matrix_sectors[d['base']]['name']}\n({d['curr_base']:.2f}$)", "כיוון": d['direction'], "איתות מוסדי (Smart Money)": d['status'], "נפח בקצה (LVN)": d['lvn'], "נכס ביצוע": d['target_tick'], "קו מבחן": d['active_res'], "מרחק": f"{d['dist']*100:.2f}%" if d['dist']!=0 else "--", "יעד 1": t1_str, "יעד 2 (POC)": t2_str, "_color": d['color']})
    df_pro = pd.DataFrame(pro_table)
    color_list = df_pro['_color'].tolist()
    df_pro_clean = df_pro.drop(columns=['_color'])
    def style_pro_matrix(row):
        c = color_list[row.name]
        if c == 'green': return ['background-color: rgba(0, 255, 0, 0.15); border-bottom: 1px solid #00ff00;'] * len(row)
        elif c == 'orange': return ['background-color: rgba(255, 165, 0, 0.15); border-bottom: 1px solid orange;'] * len(row)
        elif c == 'yellow': return ['background-color: rgba(255, 255, 0, 0.15); border-bottom: 1px solid yellow;'] * len(row)
        return [''] * len(row)
    styled_pro = df_pro_clean.style.set_properties(**{'font-size': '15px', 'text-align': 'center', 'white-space': 'pre-wrap'}).set_table_styles([dict(selector='th', props=[('font-size', '15px'), ('text-align', 'center')])]).apply(style_pro_matrix, axis=1)
    st.dataframe(styled_pro, use_container_width=True, hide_index=True, height=650)
else:import streamlit as st
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- הגדרות עמוד ---
st.set_page_config(page_title="Matrix OS - Attack Board", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .reportview-container { background: #f4f6f9; }
    
    .long-zone { border: 3px solid #00cc00; border-radius: 10px; padding: 15px; background-color: rgba(0, 204, 0, 0.05); margin-bottom: 20px; }
    .short-zone { border: 3px solid #cc0000; border-radius: 10px; padding: 15px; background-color: rgba(204, 0, 0, 0.05); margin-bottom: 20px; }
    
    .card { background-color: #ffffff; border-radius: 8px; padding: 15px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border: 1px solid #ddd; }
    .card-title { font-size: 15px; color: #444; margin-bottom: 5px; font-weight: bold; }
    .card-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; color: #111; }
    .card-target { font-size: 18px; color: #00cc00; font-weight: bold; margin-bottom: 5px; }
    .card-target-short { font-size: 18px; color: #cc0000; font-weight: bold; margin-bottom: 5px; }
    
    .macro-white-card { background-color: #ffffff; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #e0e0e0; margin-bottom: 20px;}
    
    .arrow-huge-green { font-size: 75px; color: #00cc00; font-weight: bold; line-height: 1; margin: 10px 0; text-shadow: 1px 1px 2px #ccc; }
    .arrow-huge-red { font-size: 75px; color: #cc0000; font-weight: bold; line-height: 1; margin: 10px 0; text-shadow: 1px 1px 2px #ccc; }
    
    .arrow-prep-short {
        font-size: 75px;
        background: linear-gradient(to bottom, #00cc00 20%, #cc0000 80%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: bold; line-height: 1; margin: 10px 0;
    }
    .arrow-prep-long {
        font-size: 75px;
        background: linear-gradient(to top, #cc0000 20%, #00cc00 80%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: bold; line-height: 1; margin: 10px 0;
    }
    
    .prob-text { font-size: 16px; font-weight: bold; color: #444; background-color: #f0f0f0; padding: 5px 12px; border-radius: 20px; display: inline-block; border: 1px solid #ccc; margin-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- נתוני בסיס ---
sector_perf_history = {
    'XLK': {'qtr': 27.13, 'mo': 2.52}, 'XLF': {'qtr': 11.46, 'mo': 4.60},
    'XLU': {'qtr': -4.30, 'mo': -1.52}, 'XLE': {'qtr': 0.67, 'mo': -1.58},
    'XLRE': {'qtr': 6.94, 'mo': 2.46}, 'XLV': {'qtr': 3.22, 'mo': 3.11},
    'XLI': {'qtr': 9.17, 'mo': 1.64}, 'XLY': {'qtr': 4.66, 'mo': -4.19},
    'XLP': {'qtr': 0.32, 'mo': -0.77}, 'XLB': {'qtr': 4.24, 'mo': -4.96}
}

lev_pairs = {
    'טכנולוגיה': {'base': 'XLK', 'long': 'TQQQ', 'short': 'SQQQ'},
    'שבבים': {'base': 'SOXX', 'long': 'SOXL', 'short': 'SOXS'},
    'פיננסים': {'base': 'XLF', 'long': 'FAS', 'short': 'FAZ'},
    'אנרגיה': {'base': 'XLE', 'long': 'ERX', 'short': 'ERY'},
    'בריאות': {'base': 'XLV', 'long': 'CURE', 'short': 'RXD'},
    'תעשייה': {'base': 'XLI', 'long': 'DUSL', 'short': 'XLI'},
}

@st.cache_data(ttl=15)
def fetch_data(tickers, period='5d', interval='5m'):
    df = yf.download(tickers, period=period, interval=interval, auto_adjust=True, progress=False)
    if not df.empty:
        df = df.loc[df['Volume'].sum(axis=1) > 0] if isinstance(df.columns, pd.MultiIndex) else df.loc[df['Volume'] > 0]
    return df

def calc_volume_profile(prices, vols):
    if len(prices) < 2: return prices.iloc[-1], prices.iloc[-1], prices.iloc[-1]
    bins = np.linspace(prices.min(), prices.max(), 50)
    digitized = np.digitize(prices, bins)
    vol_profile = np.zeros(len(bins)-1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    for i in range(1, len(bins)): vol_profile[i-1] = vols.iloc[digitized == i].sum()
    poc_idx = np.argmax(vol_profile)
    va_volume = vol_profile[poc_idx]
    target_volume = vol_profile.sum() * 0.70
    upper_idx, lower_idx = poc_idx, poc_idx
    while va_volume < target_volume:
        can_up, can_down = upper_idx < len(vol_profile)-1, lower_idx > 0
        if not can_up and not can_down: break
        if can_up and (not can_down or vol_profile[upper_idx+1] >= vol_profile[lower_idx-1]):
            upper_idx += 1; va_volume += vol_profile[upper_idx]
        else:
            lower_idx -= 1; va_volume += vol_profile[lower_idx]
    return bin_centers[poc_idx], bin_centers[upper_idx], bin_centers[lower_idx]

def create_candlestick_chart(df, signals, open_price):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#00cc00', decreasing_line_color='#cc0000',
        increasing_fillcolor='#00cc00', decreasing_fillcolor='#cc0000'
    )])
    fig.add_hline(y=open_price, line_dash="dot", line_color="gray", line_width=1)
    
    for sig_time, sig_type, sig_price in signals:
        if sig_type == "prep_short": sym, c, offset = "▼", "#ff9900", 1.002
        elif sig_type == "prep_long": sym, c, offset = "▲", "#ff9900", 0.998
        elif sig_type == "short": sym, c, offset = "▼", "#cc0000", 1.002
        elif sig_type == "long": sym, c, offset = "▲", "#00cc00", 0.998
        else: continue
        
        y_pos = "bottom" if "long" in sig_type else "top"
        fig.add_annotation(x=sig_time, y=sig_price * offset, text=sym, showarrow=False, font=dict(color=c, size=26, weight="bold"), yanchor=y_pos)
        
    fig.update_layout(margin=dict(l=0, r=0, t=5, b=0), height=250, xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=True, showgrid=False), yaxis=dict(visible=True, showgrid=True, gridcolor='#eee'))
    return fig

now_dt = datetime.utcnow() + timedelta(hours=3)
st.title("⚔️ Attack Board - לוח תקיפה מוסדי")
st.write(f"זמן מערכת: {now_dt.strftime('%H:%M:%S')}")
st.markdown("---")

# ==========================================
# 1. מנוע המאקרו והסתברות ההיפוך
# ==========================================
st.markdown("### 📊 אינדיקטורים מובילים (זיהוי מגמה ומכונת מצבים נעולה)")

macro_tickers = ['DIA', 'QQQ', 'SPY']
try:
    macro_5m = fetch_data(macro_tickers, period="5d", interval="5m")
    if isinstance(macro_5m.columns, pd.MultiIndex):
        macro_5m.columns = [f"{col[0]}_{col[1]}" for col in macro_5m.columns]
except:
    macro_5m = pd.DataFrame()

names = {'DIA': 'DOW JONES', 'QQQ': 'NASDAQ 100', 'SPY': 'S&P 500'}
cols = st.columns(3)

for idx, (tick, name) in enumerate(names.items()):
    try:
        df_5m = macro_5m[[f'Open_{tick}', f'High_{tick}', f'Low_{tick}', f'Close_{tick}', f'Volume_{tick}']].dropna()
        df_5m.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        if len(df_5m) < 10: raise Exception
        
        df_5m['Vol_SMA'] = df_5m['Volume'].rolling(10).mean()
        df_5m['Mom_5m'] = df_5m['Close'].diff(1)
        df_5m['Mom_15m'] = df_5m['Close'].diff(3)
        df_5m['Trend_Score'] = np.sign(df_5m['Mom_5m']) + np.sign(df_5m['Mom_15m'])
        
        last_day = df_5m.index[-1].date()
        df_today = df_5m[df_5m.index.date == last_day].copy()
        if df_today.empty or len(df_today) < 10: df_today = df_5m.tail(78).copy() 
        
        c_p = float(df_today['Close'].iloc[-1])
        open_p = float(df_today['Open'].iloc[0])
        chg_daily = ((c_p - open_p) / open_p) * 100
        is_green = chg_daily >= 0
        
        # --- הלוגיקה המקורית מהגיבוי ללא שום שינוי מבני ---
        signals = []
        current_state = 0 # 1 = Long, -1 = Short
        prep_state = 0 # 1 = PrepLong, -1 = PrepShort
        
        poc, vah, val = calc_volume_profile(df_today['Close'], df_today['Volume'])
        
        # בדיוק כפי שהיה בגיבוי: מתחילים מ-5 כדי לתת לממוצעים להתגבש
        for i in range(5, len(df_today)):
            price = df_today['Close'].iloc[i]
            low = df_today['Low'].iloc[i]
            high = df_today['High'].iloc[i]
            vol = df_today['Volume'].iloc[i]
            vol_sma = df_today['Vol_SMA'].iloc[i]
            score = df_today['Trend_Score'].iloc[i]
            
            # ההבדל היחיד: שעת המסחר האחרונה לעומת שאר היום
            if i < 66:
                # הגיבוי הטוב שלך - בדיוק כמו שהיה!
                is_accum = (low <= val * 1.002) and (vol > vol_sma * 1.1)
                is_dist = (high >= vah * 0.998) and (vol > vol_sma * 1.1)
            else:
                # החלק האחרון של היום (שעת הכוח) - דורש נפח גבוה יותר פי 1.5 כדי לסנן סגירת MOC
                is_accum = (low <= val * 1.002) and (vol > vol_sma * 1.5)
                is_dist = (high >= vah * 0.998) and (vol > vol_sma * 1.5)
            
            # מעבר משורט להכנת לונג
            if current_state != 1 and prep_state != 1 and is_accum:
                signals.append((df_today.index[i], "prep_long", low))
                prep_state = 1
            # אישור לונג
            elif prep_state == 1 and score >= 1:
                signals.append((df_today.index[i], "long", low))
                current_state = 1
                prep_state = 0
            
            # מעבר מלונג להכנת שורט
            elif current_state != -1 and prep_state != -1 and is_dist:
                signals.append((df_today.index[i], "prep_short", high))
                prep_state = -1
            # אישור שורט
            elif prep_state == -1 and score <= -1:
                signals.append((df_today.index[i], "short", high))
                current_state = -1
                prep_state = 0
                
        # --- קביעת תצוגת הקוביה בזמן אמת ---
        prob_reversal = 100 if prep_state == 0 else 75
        
        if current_state == 1 and prep_state == 0:
            arrow_class, arrow_char, status = "arrow-huge-green", "⬆", "מגמת עלייה מאושרת"
        elif current_state == -1 and prep_state == 0:
            arrow_class, arrow_char, status = "arrow-huge-red", "⬇", "מגמת ירידה מאושרת"
        elif prep_state == 1:
            arrow_class, arrow_char, status = "arrow-prep-long", "⬆", "איסוף (הכן פקודת לונג)"
        elif prep_state == -1:
            arrow_class, arrow_char, status = "arrow-prep-short", "⬇", "פיזור (הכן פקודת שורט)"
        else:
            arrow_class, arrow_char, status = "arrow-huge-green" if is_green else "arrow-huge-red", "⬆" if is_green else "⬇", "מגמה יציבה"

        html_block = f"""
        <div class="macro-white-card">
            <div style="color: #222; font-size: 24px; font-weight: bold; margin-bottom: 10px;">{name}</div>
            <div class="prob-text">סיכוי היפוך: <span style="color:{'#cc0000' if prep_state != 0 else '#00cc00'};">{prob_reversal:.0f}%</span></div>
            <div class="{arrow_class}">{arrow_char}</div>
            <div style="color: #444; font-size: 18px; font-weight: bold; margin: 10px 0;">{status}</div>
            <div style="color: #000; font-size: 22px; font-weight: bold;">{c_p:.2f} <span style="font-size:16px; color:{'#00cc00' if is_green else '#cc0000'};">({chg_daily:+.2f}%)</span></div>
        </div>
        """
        
        with cols[idx]:
            st.markdown(html_block, unsafe_allow_html=True)
            st.plotly_chart(create_candlestick_chart(df_today, signals, open_p), use_container_width=True, config={'displayModeBar': False})
            
    except Exception as e:
        with cols[idx]: st.warning(f"אין נתונים מספיקים עבור {name}")

st.markdown("---")

# ==========================================
# 2. מנוע מומנטום וחלוקה לאזורי תקיפה
# ==========================================
st.markdown("### 🎯 אזורי תקיפה (סורק תעודות ממונפות)")

try:
    all_tickers = [data['base'] for data in lev_pairs.values()] + [data['long'] for data in lev_pairs.values()] + [data['short'] for data in lev_pairs.values()]
    intra_data = fetch_data(all_tickers, period="5d", interval="5m")
    if isinstance(intra_data.columns, pd.MultiIndex):
        intra_data.columns = [f"{col[0]}_{col[1]}" for col in intra_data.columns]
except: intra_data = pd.DataFrame()

long_candidates, short_candidates = [], []

for sec_name, data in lev_pairs.items():
    try:
        base_tick = data['base']
        s_base = intra_data[f'Close_{base_tick}'].dropna()
        v_base = intra_data[f'Volume_{base_tick}'].dropna()
        if len(s_base) < 2: continue
        
        last_day = s_base.index[-1].date()
        s_base_today = s_base[s_base.index.date == last_day]
        v_base_today = v_base[v_base.index.date == last_day]
        if s_base_today.empty: s_base_today = s_base.tail(78); v_base_today = v_base.tail(78)
        
        c_last = float(s_base_today.iloc[-1])
        intra_chg = ((c_last - float(s_base_today.iloc[0])) / float(s_base_today.iloc[0])) * 100
        qtr_p = float(sector_perf_history.get(base_tick, {}).get('qtr', 0))
        mo_p = float(sector_perf_history.get(base_tick, {}).get('mo', 0))
        power_score = float((qtr_p * 0.4) + (mo_p * 0.3) + (intra_chg * 0.3))
        
        poc, vah, val = calc_volume_profile(s_base_today, v_base_today)
        long_tick, short_tick = data['long'], data['short']
        c_long = float(intra_data[f'Close_{long_tick}'].dropna().iloc[-1])
        c_short = float(intra_data[f'Close_{short_tick}'].dropna().iloc[-1])
        
        if power_score > 0:
            target_price = vah + (vah - poc) if c_last > vah else vah
            dist_pct = ((target_price - c_last) / c_last)
            targ_long = c_long * (1 + (dist_pct * 3))
            pct_long = ((targ_long - c_long) / c_long) * 100
            
            status_html = "<span style='color:orange;'>הכן פקודה</span><br><span style='font-size:24px;color:orange;'>▲</span>" if c_last < val else "<span style='color:green;'>מגמה מאושרת</span><br><span style='font-size:24px;color:green;'>▲</span>"
            long_candidates.append({'name': long_tick, 'price': c_long, 'target': targ_long, 'pct': pct_long, 'status': status_html, 'score': power_score})
            
        else:
            target_price = val - (poc - val) if c_last < val else val
            dist_pct = ((target_price - c_last) / c_last)
            targ_short = c_short * (1 + (-dist_pct * 3)) 
            pct_short = ((targ_short - c_short) / c_short) * 100
            
            status_html = "<span style='color:orange;'>הכן פקודה</span><br><span style='font-size:24px;color:orange;'>▼</span>" if c_last > vah else "<span style='color:red;'>מגמה מאושרת</span><br><span style='font-size:24px;color:red;'>▼</span>"
            short_candidates.append({'name': short_tick, 'price': c_short, 'target': targ_short, 'pct': pct_short, 'status': status_html, 'score': power_score})
                
    except: continue

long_candidates = sorted(long_candidates, key=lambda x: x['score'], reverse=True)
short_candidates = sorted(short_candidates, key=lambda x: x['score'])

col_L, col_S = st.columns(2)

with col_L:
    st.markdown("<div class='long-zone'><h3 style='text-align: center; color: #009900;'>🟢 סקטורים ללונג</h3>", unsafe_allow_html=True)
    for item in long_candidates:
        st.markdown(f"<div class='card'><div class='card-title'>{item['name']}</div><table style='width:100%;'><tr><td style='width:33%; font-weight:bold;'>{item['status']}</td><td style='width:33%;'><div class='card-value'>{item['price']:.2f}</div><div style='font-size:12px;color:#888;'>שער נוכחי</div></td><td style='width:33%;'><div class='card-target'>{item['target']:.2f}</div><div class='card-percent'>({item['pct']:+.1f}%)</div><div style='font-size:12px;color:#888;'>יעד מתגלגל</div></td></tr></table></div><br>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with col_S:
    st.markdown("<div class='short-zone'><h3 style='text-align: center; color: #cc0000;'>🔴 סקטורים לשורט</h3>", unsafe_allow_html=True)
    for item in short_candidates:
        st.markdown(f"<div class='card'><div class='card-title'>{item['name']}</div><table style='width:100%;'><tr><td style='width:33%; font-weight:bold;'>{item['status']}</td><td style='width:33%;'><div class='card-value'>{item['price']:.2f}</div><div style='font-size:12px;color:#888;'>שער נוכחי</div></td><td style='width:33%;'><div class='card-target-short'>{item['target']:.2f}</div><div class='card-percent'>({item['pct']:+.1f}%)</div><div style='font-size:12px;color:#888;'>יעד מתגלגל</div></td></tr></table></div><br>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

time.sleep(15)
st.rerun()
