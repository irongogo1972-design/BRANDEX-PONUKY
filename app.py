# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta

# --- 1. POMOCNÉ FUNKCIE ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def sort_sizes(size_list):
    order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL']
    return sorted(size_list, key=lambda x: order.index(x) if x in order else 99)

# Inicializácia pamäte
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. NASTAVENIA STRÁNKY A AGRESÍVNY DESIGN ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")

logo_base64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
    <style>
    /* ODSTRÁNENIE ŠEDÝCH PLÔCH A SYSTÉMOVÝCH PRVKOV */
    [data-testid="stAppViewBlockContainer"] {{ padding-top: 1rem !important; }}
    [data-testid="stHeader"] {{ display: none; }}
    [data-testid="stVerticalBlock"] > div {{ padding: 0px !important; gap: 0rem !important; }}
    
    /* Vynútenie priehľadnosti pre všetky Streamlit widgety */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="base-input"], .stTextInput div, .stTextArea div, .stDateInput div {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    .stTextInput input, .stTextArea textarea, .stSelectbox div, .stDateInput input {{
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        color: black !important;
        min-height: 20px !important;
    }}

    @media screen {{
        .paper {{
            background: white; width: 210mm; min-height: 297mm;
            padding: 10mm 15mm; margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2); color: black;
            font-family: 'Helvetica', 'Arial', sans-serif;
        }}
    }}

    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"], .stFileUploader, .stDownloadButton {{
            display: none !important;
        }}
        .paper {{ 
            margin: 0 !important; box-shadow: none !important; width: 100% !important; 
            padding: 0 !important; padding-top: 0 !important;
        }}
        .footer-box {{
            position: fixed; bottom: 0; left: 0; right: 0;
            text-align: center; border-top: 1px solid black;
            padding: 5px 0; background: white; font-size: 8px;
        }}
        .side-by-side {{ display: flex !important; flex-direction: row !important; gap: 40px !important; }}
        .half-width {{ width: 50% !important; }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    /* DESIGN HLAVIČKY */
    .header-wrapper {{ text-align: center; margin-bottom: -15px; }}
    .main-title-text {{ font-size: 32px; font-weight: bold; text-align: center; text-transform: uppercase; margin: 0; padding: 0; }}

    /* ODBERATEĽ A PLATNOSŤ */
    .client-label {{ font-size: 11px; font-weight: bold; margin-bottom: 0px; }}
    .client-box {{ font-size: 11px !important; color: black; line-height: 1.0 !important; }}
    .validity-box {{ text-align: right; font-size: 11px; line-height: 1.0; }}

    /* TABUĽKA */
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; color: black; table-layout: fixed; }}
    th, td {{ border: 1px solid #ccc; padding: 4px; text-align: center; font-size: 10px; }}
    th {{ background-color: #f8f8f8; font-weight: bold; }}
    .img-cell img {{ max-width: 100px; max-height: 150px; object-fit: contain; }}

    /* SUMÁR */
    .summary-container {{ width: 100%; display: flex; justify-content: flex-end; margin-top: 5px; }}
    .summary-table {{ border: none !important; width: 280px; border-collapse: collapse; }}
    .summary-table td {{ border: 1px solid #eee !important; text-align: right; padding: 2px 5px; font-size: 11px; }}
    .total-row {{ background-color: #f2f2f2; font-weight: bold; }}

    .section-title {{ font-weight: bold; font-size: 12px; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; border-bottom: 1px solid #eee; }}
    .processor-box {{ text-align: right; font-size: 11px; margin-top: 20px; font-style: italic; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        df = pd.read_excel(file, engine="openpyxl")
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]] # A, F, G, H, N, Q
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except: return pd.DataFrame()

df_db = load_excel()

# --- 4. SIDEBAR OVLÁDANIE ---
with st.sidebar:
    st.header("🛒 Správa položiek")
    proc_user = st.text_input("Ponuku vypracoval", placeholder="Vaše meno")
    
    if not df_db.empty:
        st.subheader("➕ Pridať tovar")
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        sub_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        
        # Zoradené veľkosti
        avail_sizes = sub_df[sub_df['FARBA'] == farba]['SIZE'].unique()
        velkosti = st.multiselect("Veľkosti", sort_sizes(avail_sizes))
        
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        br_u = st.number_input("Branding / ks €", min_value=0.0, step=0.1, value=0.0)
        
        link_img = st.text_input("Vlastný link na obrázok", placeholder="https://...")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in velkosti:
                row = sub_df[(sub_df['FARBA'] == farba) & (sub_df['SIZE'] == s)].iloc[0]
                img_f = link_img if link_img else str(row['IMG_PRODUCT'])
                if img_f == 'nan' or not img_f.startswith('http'): img_f = ""
                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc, 
                    "img": img_f, "br": br_u
                })
            st.rerun()

    if st.session_state['offer_items']:
        st.divider()
        st.subheader("Editácia / Mazanie")
        for idx, item in enumerate(st.session_state['offer_items']):
            col_d1, col_d2 = st.columns([3, 1])
            col_d1.write(f"{item['kod']} ({item['v']})")
            if col_d2.button("🗑️", key=f"del_{idx}"):
                st.session_state['offer_items'].pop(idx)
                st.rerun()
        if st.button("❌ VYMAZAŤ VŠETKO"):
            st.session_state['offer_items'] = []
            st.rerun()

# --- 5. VIZUÁL A4 ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# HLAVIČKA
if logo_base64:
    st.markdown(f"""
        <div class="header-wrapper">
            <img src="data:image/png;base64,{logo_base64}" width="220">
            <div class="main-title-text">PONUKA</div>
        </div>
        """, unsafe_allow_html=True)

# ODBERATEĽ & PLATNOSŤ (V jednom riadku)
c_row1, c_row2 = st.columns([1.5, 1])
with c_row1:
    st.markdown("<div class='client-box'><b>Odberateľ:</b>", unsafe_allow_html=True)
    st.text_input("Firma", "Názov firmy", key="cf", label_visibility="collapsed")
    st.text_input("Adresa", "Adresa", key="ca", label_visibility="collapsed")
    st.text_input("Kontakt", "Kontaktná osoba", key="co", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
with c_row2:
    st.markdown("<div class='validity-box'><b>Platnosť ponuky do:</b>", unsafe_allow_html=True)
    st.date_input("Dátum", value=datetime.now() + timedelta(days=14), label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

# TABUĽKA
total_i_net = 0
total_b_net = 0
if st.session_state['offer_items']:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    html = '<table><thead><tr>'
    html += '<th style="width:90px;">Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava %</th><th>Branding</th><th>Suma bez DPH</th>'
    html += '</tr></thead><tbody>'
    
    groups = items_df.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state['offer_items'][idx]
            p_disc = it['p'] * (1 - it['z']/100)
            row_tot = it['ks'] * (p_disc + it['br'])
            total_i_net += (it['ks'] * p_disc)
            total_b_net += (it['ks'] * it['br'])
            
            html += '<tr>'
            if i == 0:
                img_src = it['img'] if it['img'] else ""
                html += f'<td rowspan="{g_size}" class="img-cell"><img src="{img_src}"></td>'
            
            html += f"""
                <td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>
                <td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{it['br']:.2f} €</td><td>{row_tot:.2f} €</td></tr>
            """
            idx += 1
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    # SUMÁR
    sum_z = total_i_net + total_b_net
    dph = sum_z * 0.23
    st.markdown(f"""
    <div class="summary-container">
        <table class="summary-table">
            <tr><td>Suma položiek bez DPH:</td><td>{total_i_net:.2f} €</td></tr>
            <tr><td>Branding celkom bez DPH:</td><td>{total_b_net:.2f} €</td></tr>
            <tr><td><b>Základ DPH:</b></td><td><b>{sum_z:.2f} €</b></td></tr>
            <tr><td>DPH (23%):</td><td>{dph:.2f} €</td></tr>
            <tr class="total-row"><td>CELKOM S DPH:</td><td>{sum_z + dph:.2f} €</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# BRANDING (Technológia, Popis, Vzorka v jednom riadku)
st.markdown("<div class='section-title'>BRANDING</div>", unsafe_allow_html=True)
b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
with b_col1:
    st.markdown("<small>Technológia</small>", unsafe_allow_html=True)
    st.selectbox("T", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"], label_visibility="collapsed")
with b_col2:
    st.markdown("<small>Popis</small>", unsafe_allow_html=True)
    st.text_area("P", placeholder="Popis a umiestnenie...", label_visibility="collapsed", height=65)
with b_col3:
    st.markdown("<small>Dodanie vzorky</small>", unsafe_allow_html=True)
    st.date_input("V", label_visibility="collapsed")

# LOGO A NÁHĽAD (Vynútené vedľa seba pri tlači)
st.markdown('<div class="side-by-side">', unsafe_allow_html=True)
l_col, n_col = st.columns(2)
with l_col:
    st.markdown("<div class='half-width'><div class='section-title'>LOGO</div>", unsafe_allow_html=True)
    upl_l = st.file_uploader("L", accept_multiple_files=True, key="l", label_visibility="collapsed")
    if upl_l:
        cols = st.columns(2)
        for i, f in enumerate(upl_l[:2]): cols[i].image(f, width=100)
    st.markdown("</div>", unsafe_allow_html=True)
with n_col:
    st.markdown("<div class='half-width'><div class='section-title'>NÁHĽAD</div>", unsafe_allow_html=True)
    upl_n = st.file_uploader("N", accept_multiple_files=True, key="n", label_visibility="collapsed")
    if upl_n:
        cols = st.columns(2)
        for i, f in enumerate(upl_n[:2]): cols[i].image(f, width=100)
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# VYPRACCOVAL
if proc_user:
    st.markdown(f'<div class="processor-box">Ponuku vypracoval: {proc_user}</div>', unsafe_allow_html=True)

# PÄTA
st.markdown("""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- FUNKČNÉ TLAČIDLO TLAČE ---
if st.button("🖨️ Tlačiť ponuku"):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)