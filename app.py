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
    
    .long-zone { border: 3px solid #00cc00; border-radius: 12px; padding: 20px; background-color: rgba(0, 204, 0, 0.03); margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,204,0,0.1);}
    .short-zone { border: 3px solid #cc0000; border-radius: 12px; padding: 20px; background-color: rgba(204, 0, 0, 0.03); margin-bottom: 25px; box-shadow: 0 4px 10px rgba(204,0,0,0.1);}
    
    .macro-white-card { background-color: #ffffff; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #e0e0e0; margin-bottom: 20px;}
    
    .arrow-huge-green { font-size: 80px; color: #00cc00; font-weight: bold; line-height: 1; margin: 10px 0; text-shadow: 1px 1px 2px #ccc;}
    .arrow-huge-red { font-size: 80px; color: #cc0000; font-weight: bold; line-height: 1; margin: 10px 0; text-shadow: 1px 1px 2px #ccc;}
    
    .arrow-prep-long {
        font-size: 80px;
        background: linear-gradient(to top, #cc0000 30%, #00cc00 70%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: bold; line-height: 1; margin: 10px 0;
    }
    .arrow-prep-short {
        font-size: 80px;
        background: linear-gradient(to bottom, #00cc00 30%, #cc0000 70%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: bold; line-height: 1; margin: 10px 0;
    }
    
    .prob-text { font-size: 18px; font-weight: bold; color: #222; background-color: #f4f4f4; padding: 5px 15px; border-radius: 25px; display: inline-block; border: 1px solid #ccc; margin-bottom: 10px;}
    .warning-text { color: #cc0000; font-size: 14px; font-weight: bold; margin-top: 5px; background-color: #ffe6e6; padding: 5px; border-radius: 5px;}
    .lmt-box { background-color: #e6f0ff; padding: 12px; border-radius: 8px; margin-top: 15px; border: 1px solid #b3d1ff; }
    </style>
""", unsafe_allow_html=True)

# --- נתוני בסיס ---
lev_pairs = {
    'S&P 500': {'base': 'SPY', 'long': 'UPRO', 'short': 'SPXU', 'lev': 3},
    'NASDAQ 100': {'base': 'QQQ', 'long': 'TQQQ', 'short': 'SQQQ', 'lev': 3},
    'DOW JONES': {'base': 'DIA', 'long': 'UDOW', 'short': 'SDOW', 'lev': 3},
    'RUSSELL 2000': {'base': 'IWM', 'long': 'URTY', 'short': 'SRTY', 'lev': 3},
    'SEMICONDUCTORS': {'base': 'SOXX', 'long': 'SOXL', 'short': 'SOXS', 'lev': 3}
}

@st.cache_data(ttl=15, show_spinner=False)
def fetch_data(tickers, period='5d', interval='5m'): 
    df = yf.download(tickers, period=period, interval=interval, auto_adjust=True, progress=False)
    if not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df = df.loc[df['Volume'].sum(axis=1) > 0]
        else: df = df.loc[df['Volume'] > 0]
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

def run_3_phase_engine(df_today, vah, val):
    signals = []
    current_state = 0 
    prep_state = 0 
    
    for i in range(5, len(df_today)):
        o, c, l, h = df_today['Open'].iloc[i], df_today['Close'].iloc[i], df_today['Low'].iloc[i], df_today['High'].iloc[i]
        vol = df_today['Volume'].iloc[i]
        vol_sma = df_today['Vol_SMA'].iloc[i]
        score = df_today['Trend_Score'].iloc[i]
        e9, e21 = df_today['EMA9'].iloc[i], df_today['EMA21'].iloc[i]
        v_prev1 = df_today['Volume'].iloc[i-1] if i > 0 else 0
        
        if i < 66:
            is_vol_spike = (vol > vol_sma * 1.1) or (vol > v_prev1 * 1.3)
            is_accum = (l <= val * 1.003) and is_vol_spike
            is_dist = (h >= vah * 0.997) and is_vol_spike
        else:
            is_vol_spike_eod = (vol > vol_sma * 1.5) or (vol > v_prev1 * 1.5)
            is_accum = (l <= val * 1.003) and is_vol_spike_eod
            is_dist = (h >= vah * 0.997) and is_vol_spike_eod

        if current_state != 1 and prep_state != 1 and is_accum:
            signals.append((df_today.index[i], "prep_long", l))
            prep_state = 1
        elif prep_state == 1:
            is_no_supply = (vol < v_prev1) and (c >= l) and (vol < vol_sma * 0.9)
            vsa_conf = is_no_supply and (i+1 < len(df_today) and df_today['Close'].iloc[i+1] > h)
            mom_conf = (e9 > e21) and (score >= 1)
            if vsa_conf or mom_conf:
                idx_sig = i+1 if (vsa_conf and not mom_conf and i+1 < len(df_today)) else i
                signals.append((df_today.index[idx_sig], "long", df_today['Low'].iloc[idx_sig]))
                current_state = 1
                prep_state = 0
        
        if current_state != -1 and prep_state != -1 and is_dist:
            signals.append((df_today.index[i], "prep_short", h))
            prep_state = -1
        elif prep_state == -1:
            is_no_demand = (vol < v_prev1) and (c <= h) and (vol < vol_sma * 0.9)
            vsa_conf_short = is_no_demand and (i+1 < len(df_today) and df_today['Close'].iloc[i+1] < l)
            mom_conf_short = (e9 < e21) and (score <= -1)
            if vsa_conf_short or mom_conf_short:
                idx_sig = i+1 if (vsa_conf_short and not mom_conf_short and i+1 < len(df_today)) else i
                signals.append((df_today.index[idx_sig], "short", df_today['High'].iloc[idx_sig]))
                current_state = -1
                prep_state = 0
                
    return signals, current_state, prep_state

def create_advanced_candlestick(df, signals, open_price, target_price=None, broken_level=None, target2_price=None, zone_type="long"):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#00cc00', decreasing_line_color='#cc0000',
        increasing_fillcolor='#00cc00', decreasing_fillcolor='#cc0000'
    )])
    fig.add_hline(y=open_price, line_dash="dot", line_color="gray", line_width=1)
    
    current_p = df['Close'].iloc[-1]
    t1_color = "#00cc00" if zone_type == "long" else "#cc0000"
    
    if target_price:
        pct_to_target = ((target_price - current_p) / current_p) * 100
        sign = "+" if pct_to_target > 0 else ""
        fig.add_hline(y=target_price, line_dash="dash", line_color=t1_color, line_width=2, 
                      annotation_text=f"<b>יעד 1: {target_price:.2f} ({sign}{pct_to_target:.2f}%)</b>", 
                      annotation_position="top right", annotation_font=dict(color=t1_color, size=22))
    
    if target2_price:
        pct_to_t2 = ((target2_price - current_p) / current_p) * 100
        sign2 = "+" if pct_to_t2 > 0 else ""
        fig.add_hline(y=target2_price, line_dash="dash", line_color="#800080", line_width=2, 
                      annotation_text=f"<b>יעד 2: {target2_price:.2f} ({sign2}{pct_to_t2:.2f}%)</b>", 
                      annotation_position="top right", annotation_font=dict(color="#800080", size=22))
                      
    if broken_level:
        fig.add_hline(y=broken_level, line_dash="dash", line_color="#00cc00", line_width=2, 
                      annotation_text="<b>תמיכה נפרצה</b>", 
                      annotation_position="bottom right", annotation_font=dict(color="#00cc00", size=22))
    
    for sig_time, sig_type, sig_price in signals:
        if sig_type == "prep_short": sym, c, offset = "▼", "#ff9900", 1.002
        elif sig_type == "prep_long": sym, c, offset = "▲", "#ff9900", 0.998
        elif sig_type == "short": sym, c, offset = "▼", "#cc0000", 1.003
        elif sig_type == "long": sym, c, offset = "▲", "#00cc00", 0.997
        else: continue
        y_pos = "bottom" if "long" in sig_type else "top"
        fig.add_annotation(x=sig_time, y=sig_price * offset, text=sym, showarrow=False, font=dict(color=c, size=32, weight="bold"), yanchor=y_pos)
        
    fig.update_layout(
        dragmode=False,
        margin=dict(l=0, r=80, t=10, b=0),
        height=380, 
        xaxis_rangeslider_visible=False, 
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        xaxis=dict(visible=True, showgrid=False, fixedrange=True), 
        yaxis=dict(visible=True, showgrid=True, gridcolor='#eee', side='right', fixedrange=True)
    )
    return fig

now_dt = datetime.utcnow() + timedelta(hours=3)
st.title("⚔️ Attack Board - לוח תקיפה מוסדי")
st.write(f"זמן מערכת (ישראל): {now_dt.strftime('%H:%M:%S')}")
st.markdown("---")

# ==========================================
# 1. מנוע המאקרו (אינדיקטורים מובילים)
# ==========================================
st.markdown("### 📊 אינדיקטורים מובילים (מנוע הגיבוי + מסנן שעת כוח)")

macro_tickers = ['DIA', 'QQQ', 'SPY']
try:
    macro_5m = fetch_data(macro_tickers, period="5d", interval="5m")
    if isinstance(macro_5m.columns, pd.MultiIndex):
        macro_5m.columns = [f"{col[0]}_{col[1]}" for col in macro_5m.columns]
except:
    macro_5m = pd.DataFrame()

names = {'DIA': 'DOW JONES', 'QQQ': 'NASDAQ 100', 'SPY': 'S&P 500'}
macro_cols = st.columns(3)

for idx, (tick, name) in enumerate(names.items()):
    try:
        cols_macro = [f'Open_{tick}', f'High_{tick}', f'Low_{tick}', f'Close_{tick}', f'Volume_{tick}']
        if not all(c in macro_5m.columns for c in cols_macro): continue
        
        df_5m = macro_5m[cols_macro].dropna()
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
        
        df_today['EMA9'] = df_today['Close'].ewm(span=9, adjust=False).mean()
        df_today['EMA21'] = df_today['Close'].ewm(span=21, adjust=False).mean()
        
        poc, vah, val = calc_volume_profile(df_today['Close'], df_today['Volume'])
        signals, current_state, prep_state = run_3_phase_engine(df_today, vah, val)
                
        prob_reversal = 100 if prep_state == 0 else 75
        
        if len(df_today) < 3:
            arrow_class, arrow_char, status = "arrow-huge-green" if is_green else "arrow-huge-red", "⏳", "ממתין להתייצבות פתיחה"
            prob_reversal = 0
        else:
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
            <div class="prob-text">סיכוי היפוך מחושב: <span style="color:{'#cc0000' if prep_state != 0 else '#00cc00'};">{prob_reversal:.0f}%</span></div>
            <div class="{arrow_class}">{arrow_char}</div>
            <div style="color: #444; font-size: 18px; font-weight: bold; margin: 10px 0;">{status}</div>
            <div style="color: #000; font-size: 22px; font-weight: bold;">{c_p:.2f} <span style="font-size:16px; color:{'#00cc00' if is_green else '#cc0000'};">({chg_daily:+.2f}%)</span></div>
        </div>
        """
        
        with macro_cols[idx]:
            st.markdown(html_block, unsafe_allow_html=True)
            st.plotly_chart(create_advanced_candlestick(df_today, signals, open_p, target_price=None, broken_level=None, target2_price=None, zone_type="macro"), use_container_width=True, config={'displayModeBar': False})
            
    except Exception as e:
        pass

st.markdown("---")

# ==========================================
# 2. אזורי תקיפה דינמיים (סורק תעודות ממונפות פי 3)
# ==========================================
st.markdown("### 🎯 אזורי תקיפה (סורק תעודות ממונפות פי 3)")

all_fetch_tickers = []
for k, v in lev_pairs.items():
    all_fetch_tickers.extend([v['base'], v['long'], v['short']])

try:
    intra_data = fetch_data(all_fetch_tickers, period="5d", interval="5m")
    if isinstance(intra_data.columns, pd.MultiIndex):
        intra_data.columns = [f"{col[0]}_{col[1]}" for col in intra_data.columns]
except: intra_data = pd.DataFrame()

long_candidates, short_candidates = [], []

for sec_name, data in lev_pairs.items():
    try:
        base_tick = data['base']
        cols_base = [f'Open_{base_tick}', f'High_{base_tick}', f'Low_{base_tick}', f'Close_{base_tick}', f'Volume_{base_tick}']
        if not all(c in intra_data.columns for c in cols_base): continue
        
        df_base = intra_data[cols_base].dropna()
        df_base.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        if len(df_base) < 10: continue
        
        df_base['Vol_SMA'] = df_base['Volume'].rolling(10).mean()
        df_base['Mom_5m'] = df_base['Close'].diff(1)
        df_base['Mom_15m'] = df_base['Close'].diff(3)
        df_base['Trend_Score'] = np.sign(df_base['Mom_5m']) + np.sign(df_base['Mom_15m'])
        df_base['EMA9'] = df_base['Close'].ewm(span=9, adjust=False).mean()
        df_base['EMA21'] = df_base['Close'].ewm(span=21, adjust=False).mean()
        
        last_day = df_base.index[-1].date()
        df_today = df_base[df_base.index.date == last_day].copy()
        if df_today.empty or len(df_today) < 10: df_today = df_base.tail(78).copy()
        
        base_c = float(df_today['Close'].iloc[-1])
        base_open = float(df_today['Open'].iloc[0])
        poc, vah, val = calc_volume_profile(df_today['Close'], df_today['Volume'])
        
        signals, current_state, prep_state = run_3_phase_engine(df_today, vah, val)
        
        va_height = max(vah - val, base_c * 0.005) 
        
        # --- לונג ממונף ---
        if current_state == 1 or prep_state == 1:
            if base_c < vah: 
                base_target_price = vah
                base_target2_price = vah + va_height
                broken_level = None
            else: 
                base_target_price = vah + va_height
                base_target2_price = vah + (va_height * 2)
                broken_level = vah
                
            dist_pct = ((base_target_price - base_c) / base_c) * 100
            dist2_pct = ((base_target2_price - base_c) / base_c) * 100
            
            long_tick = data['long']
            cols_lev = [f'Open_{long_tick}', f'High_{long_tick}', f'Low_{long_tick}', f'Close_{long_tick}']
            if not all(c in intra_data.columns for c in cols_lev): continue
            
            df_lev = intra_data[cols_lev].dropna()
            df_lev.columns = ['Open', 'High', 'Low', 'Close']
            df_lev_today = df_lev[df_lev.index.date == last_day].copy() if not df_lev.empty else df_lev
            
            if df_lev_today.empty: continue
            
            lev_c = float(df_lev_today['Close'].iloc[-1])
            lev_open = float(df_lev_today['Open'].iloc[0])
            
            lev_target = lev_c * (1 + (dist_pct/100 * data['lev']))
            lev_target2 = lev_c * (1 + (dist2_pct/100 * data['lev']))
            lev_broken = lev_c * (1 + (((broken_level - base_c) / base_c) * data['lev'])) if broken_level else None
            lev_pct = dist_pct * data['lev']
            lev_pct2 = dist2_pct * data['lev']
            
            adjusted_signals = []
            for sig_t, sig_type, sig_p in signals:
                lev_sig_price = df_lev_today['Close'].loc[sig_t] if sig_t in df_lev_today.index else lev_c
                adjusted_signals.append((sig_t, sig_type, lev_sig_price))
            
            long_candidates.append({
                'name': f"{sec_name} ({long_tick})",
                'base_df': df_lev_today,
                'signals': adjusted_signals,
                'open_p': lev_open,
                'target_base': lev_target,
                'target2_base': lev_target2,
                'broken_base': lev_broken,
                'lev_c': lev_c,
                'lev_pct': lev_pct,
                'state': 'prep' if prep_state == 1 else 'conf'
            })
            
        # --- שורט ממונף ---
        elif current_state == -1 or prep_state == -1:
            if base_c > val: 
                base_target_price = val
                base_target2_price = val - va_height
                broken_level = None
            else:
                base_target_price = val - va_height
                base_target2_price = val - (va_height * 2)
                broken_level = val
                
            dist_pct = ((base_c - base_target_price) / base_c) * 100 
            dist2_pct = ((base_c - base_target2_price) / base_c) * 100
            
            short_tick = data['short']
            cols_short = [f'Open_{short_tick}', f'High_{short_tick}', f'Low_{short_tick}', f'Close_{short_tick}']
            if not all(c in intra_data.columns for c in cols_short): continue
            
            df_lev = intra_data[cols_short].dropna()
            df_lev.columns = ['Open', 'High', 'Low', 'Close']
            df_lev_today = df_lev[df_lev.index.date == last_day].copy() if not df_lev.empty else df_lev
            
            if df_lev_today.empty: continue
            
            lev_c = float(df_lev_today['Close'].iloc[-1])
            lev_open = float(df_lev_today['Open'].iloc[0])
            
            lev_target = lev_c * (1 + (dist_pct/100 * data['lev']))
            lev_target2 = lev_c * (1 + (dist2_pct/100 * data['lev']))
            lev_broken = lev_c * (1 + (((base_c - broken_level) / base_c) * data['lev'])) if broken_level else None
            lev_pct = dist_pct * data['lev']
            lev_pct2 = dist2_pct * data['lev']
            
            adjusted_signals = []
            for sig_t, sig_type, sig_p in signals:
                lev_sig_price = df_lev_today['Close'].loc[sig_t] if sig_t in df_lev_today.index else lev_c
                if sig_type == "prep_short": adjusted_signals.append((sig_t, "prep_long", lev_sig_price))
                elif sig_type == "short": adjusted_signals.append((sig_t, "long", lev_sig_price))
            
            short_candidates.append({
                'name': f"{sec_name} ({short_tick})",
                'base_df': df_lev_today,
                'signals': adjusted_signals,
                'open_p': lev_open,
                'target_base': lev_target,
                'target2_base': lev_target2,
                'broken_base': lev_broken,
                'lev_c': lev_c,
                'lev_pct': lev_pct,
                'state': 'prep' if prep_state == -1 else 'conf'
            })
            
    except Exception as e:
        continue

long_candidates = sorted(long_candidates, key=lambda x: x['lev_pct'], reverse=True)
short_candidates = sorted(short_candidates, key=lambda x: x['lev_pct'], reverse=True)

if long_candidates:
    for item in long_candidates:
        st.markdown("<div class='long-zone'>", unsafe_allow_html=True)
        col_chart, col_text = st.columns([3, 1])
        
        with col_text:
            limit_buy_price = item['lev_c'] * 1.0015 # Marketable Limit: 0.15% buffer
            
            if item['state'] == 'prep':
                arrow_class = "arrow-prep-long"
                arrow_char = "⬆"
                status_text = "LONG הכן פקודת קניה, סכנה אל תשגר!"
                status_color = "#ff9900"
            else:
                arrow_class = "arrow-huge-green"
                arrow_char = "⬆"
                status_text = "LONG מגמה מאושרת"
                status_color = "#00cc00"
            
            st.markdown(f"""
            <div style='text-align: right; direction: rtl;'>
                <div style='font-size:32px; font-weight:bold; color:#006600; border-bottom: 2px solid #00cc00; padding-bottom: 5px; margin-bottom: 15px;'>{item['name']}</div>
                <div class='{arrow_class}'>{arrow_char}</div>
                <div style='font-size:24px; font-weight:bold; color:{status_color}; margin-bottom: 15px;'>{status_text}</div>
                <div style='font-size:22px; color:#444;'>שער נוכחי: <b>{item['lev_c']:.2f}</b></div>
                <div class='lmt-box'>
                    <div style='font-size:18px; color:#0055ff;'>שער LMT מומלץ (Marketable Limit):</div>
                    <div style='font-size:26px; font-weight:bold; color:#0055ff;'>{limit_buy_price:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_chart:
            st.plotly_chart(create_advanced_candlestick(item['base_df'], item['signals'], item['open_p'], item['target_base'], item['broken_base'], item['target2_base'], "long"), use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)

if short_candidates:
    for item in short_candidates:
        st.markdown("<div class='short-zone'>", unsafe_allow_html=True)
        col_chart, col_text = st.columns([3, 1])
        
        with col_text:
            limit_buy_price = item['lev_c'] * 1.0015 # Marketable Limit: 0.15% buffer
            
            if item['state'] == 'prep':
                arrow_class = "arrow-prep-long"
                arrow_char = "⬆"
                status_text = "SHORT הכן פקודת קניה, סכנה אל תשגר!"
                status_color = "#ff9900"
            else:
                arrow_class = "arrow-huge-green"
                arrow_char = "⬆"
                status_text = "SHORT מגמה מאושרת"
                status_color = "#00cc00"
            
            st.markdown(f"""
            <div style='text-align: right; direction: rtl;'>
                <div style='font-size:32px; font-weight:bold; color:#990000; border-bottom: 2px solid #cc0000; padding-bottom: 5px; margin-bottom: 15px;'>{item['name']}</div>
                <div class='{arrow_class}'>{arrow_char}</div>
                <div style='font-size:24px; font-weight:bold; color:{status_color}; margin-bottom: 15px;'>{status_text}</div>
                <div style='font-size:22px; color:#444;'>שער נוכחי: <b>{item['lev_c']:.2f}</b></div>
                <div class='lmt-box'>
                    <div style='font-size:18px; color:#0055ff;'>שער LMT מומלץ (Marketable Limit):</div>
                    <div style='font-size:26px; font-weight:bold; color:#0055ff;'>{limit_buy_price:.2f}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_chart:
            st.plotly_chart(create_advanced_candlestick(item['base_df'], item['signals'], item['open_p'], item['target_base'], item['broken_base'], item['target2_base'], "short"), use_container_width=True, config={'displayModeBar': False})
        st.markdown("</div>", unsafe_allow_html=True)

time.sleep(15)
st.rerun()
