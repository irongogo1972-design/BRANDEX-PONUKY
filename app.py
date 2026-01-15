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

def file_to_base64(uploaded_file):
    if uploaded_file is not None:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return None

def sort_sizes(size_list):
    order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL']
    return sorted(size_list, key=lambda x: order.index(x) if x in order else 99)

# Inicializácia pamäte hneď na začiatku
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. NASTAVENIA STRÁNKY A AGRESÍVNE WYSIWYG CSS ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide", initial_sidebar_state="expanded")

logo_base64_main = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
    <style>
    /* RESET STREAMLIT PROSTREDIA */
    [data-testid="stAppViewBlockContainer"] {{ padding-top: 0rem !important; padding-bottom: 0rem !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stVerticalBlock"] {{ gap: 0rem !important; }}
    
    /* ODSTRÁNENIE ŠEDÝCH PLÔCH */
    .paper .stTextInput div, .paper .stTextArea div, .paper .stDateInput div, .paper .stSelectbox div, div[data-baseweb="input"] {{
        background-color: transparent !important; border: none !important; box-shadow: none !important;
    }}
    .paper input, .paper textarea {{ color: black !important; padding: 0 !important; }}

    /* SIMULÁCIA A4 NA OBRAZOVKE */
    @media screen {{
        .paper {{
            background: white; width: 210mm; min-height: 297mm;
            padding: 10mm 15mm; margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2); color: black;
            font-family: 'Arial', sans-serif;
        }}
    }}

    /* NASTAVENIA PRE TLAČ */
    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"], .stFileUploader {{
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
        /* VYNÚTENIE VEDĽA SEBA V TLAČI */
        .flex-row-print {{ display: flex !important; flex-direction: row !important; justify-content: space-between !important; align-items: flex-start !important; }}
        .col-left {{ width: 60% !important; }}
        .col-right {{ width: 35% !important; text-align: right !important; }}
        .col-branding {{ width: 33% !important; }}
        .col-half {{ width: 48% !important; }}
        
        @page {{ size: A4; margin: 1cm; }}
    }}

    /* DESIGN PRVKY */
    .header-wrapper {{ text-align: center; margin-bottom: -20px; }}
    .main-title-text {{ font-size: 32px; font-weight: bold; text-align: center; text-transform: uppercase; margin: 0; }}

    .client-box {{ font-size: 11px !important; line-height: 1.0 !important; }}
    .validity-box {{ text-align: right; font-size: 11px; line-height: 1.0; }}

    table.items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; color: black; table-layout: fixed; }}
    table.items-table th, table.items-table td {{ border: 1px solid #ccc; padding: 4px; text-align: center; font-size: 10px; }}
    th {{ background-color: #f8f8f8; font-weight: bold; }}
    .img-cell img {{ max-width: 90px; max-height: 130px; object-fit: contain; }}

    .summary-container {{ display: flex; justify-content: flex-end; margin-top: 5px; }}
    .summary-table {{ border: none !important; width: 280px; border-collapse: collapse; }}
    .summary-table td {{ border: 1px solid #eee !important; text-align: right; padding: 2px 5px; font-size: 11px; }}
    
    .section-title {{ font-weight: bold; font-size: 12px; margin-top: 10px; border-bottom: 1px solid #eee; text-transform: uppercase; }}
    .graphic-preview-box {{ border: 1px dashed #ccc; padding: 5px; margin-top: 5px; text-align: center; min-height: 100px; }}
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
    proc_name = st.text_input("Ponuku vypracoval", placeholder="Meno a email")
    
    if not df_db.empty:
        st.subheader("➕ Pridať tovar")
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        sub_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        velkosti = st.multiselect("Veľkosti", sort_sizes(sub_df[sub_df['FARBA'] == farba]['SIZE'].unique()))
        qty = st.number_input("Počet ks", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        br_u = st.number_input("Branding / ks €", min_value=0.0, step=0.1, value=0.0)
        link_img = st.text_input("Vlastný link na obrázok", placeholder="https://...")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in velkosti:
                row = sub_df[(sub_df['FARBA'] == farba) & (sub_df['SIZE'] == s)].iloc[0]
                if not any(item['kod'] == row['KOD_IT'] and item['v'] == s for item in st.session_state['offer_items']):
                    img_f = link_img if link_img else str(row['IMG_PRODUCT'])
                    if img_f == 'nan' or not img_f.startswith('http'): img_f = ""
                    st.session_state['offer_items'].append({
                        "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                        "ks": qty, "p": float(row['PRICE']), "z": disc, "img": img_f, "br": br_u
                    })
            st.rerun()

    if st.session_state['offer_items']:
        st.divider()
        st.subheader("🗑️ Editácia")
        for idx, item in enumerate(st.session_state['offer_items']):
            col_d1, col_d2 = st.columns([4, 1])
            col_d1.write(f"{item['kod']} ({item['v']})")
            if col_d2.button("❌", key=f"del_{idx}"):
                st.session_state['offer_items'].pop(idx)
                st.rerun()

# --- 5. DOKUMENT A4 ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# HLAVIČKA
if logo_base64_main:
    st.markdown(f'<div class="header-wrapper"><img src="data:image/png;base64,{logo_base64_main}" width="220"><div class="main-title-text">PONUKA</div></div>', unsafe_allow_html=True)

# ODBERATEĽ & PLATNOSŤ & VYPRACOVAL (WYSIWYG)
st.write("")
st.markdown('<div class="flex-row-print">', unsafe_allow_html=True)
c_col1, c_col2 = st.columns([1.5, 1])
with c_col1:
    st.markdown("<div class='client-box col-left'><b>ODBERATEĽ :</b>", unsafe_allow_html=True)
    st.text_input("Firma", "Názov firmy", key="cf", label_visibility="collapsed")
    st.text_input("Adresa", "Adresa", key="ca", label_visibility="collapsed")
    st.text_input("Kontakt", "Kontaktná osoba", key="co", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
with c_col2:
    st.markdown("<div class='validity-box col-right'><b>PLATNOSŤ PONUKY DO :</b>", unsafe_allow_html=True)
    st.date_input("Dátum", value=datetime.now() + timedelta(days=14), label_visibility="collapsed", key="vd")
    st.markdown("<br><b>VYPRACOVAL :</b>", unsafe_allow_html=True)
    st.write(f"{proc_name}" if proc_name else "Meno a priezvisko")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# TABUĽKA
total_i_net = 0
total_b_net = 0
if st.session_state['offer_items']:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    html = '<table class="items-table"><thead><tr>'
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
                html += f'<td rowspan="{g_size}" class="img-cell"><img src="{it["img"]}"></td>'
            html += f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td><td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{it['br']:.2f} €</td><td>{row_tot:.2f} €</td></tr>"
            idx += 1
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    # SUMÁR
    sum_z = total_i_net + total_b_net
    st.markdown(f"""
    <div class="summary-container">
        <table class="summary-table">
            <tr><td>Suma položiek bez DPH:</td><td>{total_i_net:.2f} €</td></tr>
            <tr><td>Branding celkom bez DPH:</td><td>{total_b_net:.2f} €</td></tr>
            <tr><td><b>Základ DPH:</b></td><td><b>{sum_z:.2f} €</b></td></tr>
            <tr><td>DPH (23%):</td><td>{sum_z * 0.23:.2f} €</td></tr>
            <tr style="background-color:#eee; font-weight:bold;"><td>CELKOM S DPH:</td><td>{sum_z * 1.23:.2f} €</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# BRANDING (Vedľa seba)
st.markdown("<div class='section-title'>BRANDING</div>", unsafe_allow_html=True)
st.markdown('<div class="flex-row-print">', unsafe_allow_html=True)
b_col1, b_col2, b_col3 = st.columns([1, 2, 1])
with b_col1:
    st.markdown("<small class='col-branding'>Technológia</small>", unsafe_allow_html=True)
    st.selectbox("T", ["Sieťotlač", "Výšivka", "DTF", "Laser"], label_visibility="collapsed", key="bt")
with b_col2:
    st.markdown("<small class='col-branding'>Popis</small>", unsafe_allow_html=True)
    st.text_area("P", placeholder="Umiestnenie...", label_visibility="collapsed", height=60, key="bd")
with b_col3:
    st.markdown("<small class='col-branding'>Dodanie vzorky</small>", unsafe_allow_html=True)
    st.date_input("V", label_visibility="collapsed", key="bs")
st.markdown('</div>', unsafe_allow_html=True)

# LOGO A NÁHĽAD (Vedľa seba)
st.markdown('<div class="flex-row-print">', unsafe_allow_html=True)
col_lg, col_pv = st.columns(2)
with col_lg:
    st.markdown("<div class='col-half'><div class='section-title'>LOGO KLIENTA</div>", unsafe_allow_html=True)
    f_logo = st.file_uploader("L", key="ul", label_visibility="collapsed")
    b64_l = file_to_base64(f_logo)
    if b64_l: st.markdown(f'<div class="graphic-preview-box"><img src="data:image/png;base64,{b64_l}" width="140"></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
with col_pv:
    st.markdown("<div class='col-half'><div class='section-title'>NÁHĽAD GRAFIKY</div>", unsafe_allow_html=True)
    f_prev = st.file_uploader("N", key="un", label_visibility="collapsed")
    b64_p = file_to_base64(f_prev)
    if b64_p: st.markdown(f'<div class="graphic-preview-box"><img src="data:image/png;base64,{b64_p}" width="140"></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# PÄTA
st.markdown("""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# TLAČIDLO TLAČE
if st.button("🖨️ TLAČIŤ PONUKU"):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)