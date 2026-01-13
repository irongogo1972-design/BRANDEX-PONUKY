# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. INICIALIZÁCIA PAMÄTE (Hneď na začiatku, aby nebola chyba) ---
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. KONFIGURÁCIA STRÁNKY A ŠTÝLY ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")

st.markdown("""
    <style>
    /* Skrytie prvkov pri tlači */
    @media print {
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"] {
            display: none !important;
        }
        .paper { margin: 0 !important; box-shadow: none !important; width: 100% !important; padding: 0 !important; }
        @page { size: A4; margin: 1cm; }
    }
    
    /* Vizuál papiera na obrazovke */
    @media screen {
        .paper {
            background: white;
            width: 210mm;
            min-height: 297mm;
            padding: 15mm;
            margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            color: black;
        }
    }

    /* Špeciálny štýl pre Názov ponuky v strede */
    .stTextInput input {
        font-size: 30px !important;
        font-weight: bold !important;
        text-align: center !important;
        border: none !important;
        background-color: transparent !important;
        text-transform: uppercase;
    }
    
    /* Tabuľka */
    table { width: 100%; border-collapse: collapse; margin-top: 20px; color: black; }
    th, td { border: 1px solid black; padding: 6px; text-align: center; font-size: 12px; }
    th { background-color: #f2f2f2; }
    
    .footer-box { 
        font-size: 11px; text-align: center; margin-top: 50px; 
        border-top: 1px solid black; padding-top: 10px; line-height: 1.4; color: black;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        # A=0, F=5, G=6, H=7, N=13, Q=16
        df = pd.read_excel(file, engine="openpyxl")
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except:
        return pd.DataFrame()

df_db = load_excel()

# --- 4. OVLÁDACÍ PANEL (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Pridať položky")
    if not df_db.empty:
        model = st.selectbox("Model (F)", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        temp_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        
        farba = st.selectbox("Farba (G)", sorted(temp_df['FARBA'].unique()))
        size_df = temp_df[temp_df['FARBA'] == farba]
        
        velkosti = st.multiselect("Veľkosti (H)", sorted(size_df['SIZE'].unique()))
        
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        
        if st.button("➕ PRIDAŤ"):
            for s in velkosti:
                row = size_df[size_df['SIZE'] == s].iloc[0]
                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc,
                    "img": str(row['IMG_PRODUCT'])
                })
            st.rerun()

    st.divider()
    if st.button("🗑️ Vymazať všetko"):
        st.session_state['offer_items'] = []
        st.rerun()

# --- 5. A4 DOKUMENT ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# LOGO - Centrovanie pomocou HTML
logo_path = "brandex_logo.png"
if os.path.exists(logo_path):
    st.markdown(f'<div style="text-align: center;"><img src="app/static/{logo_path}" width="300"></div>', unsafe_allow_html=True)
    # Ak vyššie nefunguje (Streamlit static), skúsime toto:
    st.image(logo_path, width=300) 
else:
    st.markdown("<h1 style='text-align: center;'>BRANDEX</h1>", unsafe_allow_html=True)

# NÁZOV PONUKY (Upravený podľa požiadavky)
st.write("")
st.text_input("", value="CENOVÁ PONUKA", key="main_title", label_visibility="collapsed")

# PRE KOHO
st.markdown("### Pre koho:")
col_k1, col_k2 = st.columns([1, 1])
with col_k1:
    st.text_input("Firma", "Názov firmy", label_visibility="collapsed")
    st.text_input("Adresa", "Adresa", label_visibility="collapsed")
    st.text_input("Zástupca", "Meno zástupcu", label_visibility="collapsed")

# TABUĽKA POLOŽIEK (Ochrana pred ValueError)
if len(st.session_state['offer_items']) > 0:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    
    html = '<table><thead><tr>'
    html += '<th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava %</th><th>Suma</th>'
    html += '</tr></thead><tbody>'
    
    # Logika zoskupovania obrázkov (Rowspan)
    groups = items_df.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    total_sum = 0

    for g_size in groups:
        for i in range(g_size):
            it = st.session_state['offer_items'][idx]
            final_p = it['p'] * (1 - it['z']/100)
            row_sum = it['ks'] * final_p
            total_sum += row_sum
            
            html += '<tr>'
            if i == 0:
                img_url = it['img'] if it['img'] != 'nan' else ""
                html += f'<td rowspan="{g_size}"><img src="{img_url}" width="60"></td>'
            
            html += f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>"
            html += f"<td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{row_sum:.2f} €</td></tr>"
            idx += 1
            
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: right;'>Celkom bez DPH: {total_sum:.2f} €</h3>", unsafe_allow_html=True)

# BRANDING
st.divider()
st.subheader("Branding")
b1, b2, b3 = st.columns([2, 2, 1])
with b1:
    st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    st.text_area("Popis brandingu")
with b2:
    st.text_input("Umiestnenie")
    b_price = st.number_input("Cena za branding €", min_value=0.0, step=1.0)
with b3:
    logo_upl = st.file_uploader("Nahrať logo", type=['png', 'jpg'])
    if logo_upl: st.image(logo_upl, width=100)

# TERMÍNY
st.divider()
d1, d2, d3 = st.columns(3)
with d1: st.date_input("Termín dodania vzorky")
with d2: st.date_input("Termín dodania ponuky")
with d3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

# PÄTA
st.markdown("""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# TLAČIDLO TLAČE
st.markdown("""
    <div class="no-print" style="position: fixed; bottom: 20px; right: 20px;">
        <button onclick="window.print()" style="padding: 15px 30px; background: #ff4b4b; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">
            🖨️ TLAČIŤ / ULOŽIŤ PDF
        </button>
    </div>
    """, unsafe_allow_html=True)