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

# Inicializácia pamäte hneď na začiatku
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. NASTAVENIA STRÁNKY A CSS ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide", initial_sidebar_state="expanded")

logo_base64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
<style>
    /* RESET MEDZIER A VIDITEĽNOSŤ SIDEBARU */
    [data-testid="stAppViewBlockContainer"] {{ 
        padding-top: 0rem !important; 
        padding-bottom: 0rem !important;
    }}
    [data-testid="stHeader"] {{ display: none !important; }}
    
    /* Vynútenie šípky sidebaru ak by zmizla */
    [data-testid="collapsedControl"] {{
        display: flex !important;
        color: #ff4b4b !important;
    }}

    /* ODSTRÁNENIE ŠEDÝCH PLÔCH */
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

    /* PAPIER NA OBRAZOVKE */
    @media screen {{
        .paper {{
            background: white; width: 210mm; min-height: 297mm;
            padding: 5mm 15mm; margin: 0px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2); color: black;
            font-family: 'Arial', sans-serif;
        }}
    }}

    /* NASTAVENIA TLAČE */
    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"] {{
            display: none !important;
        }}
        .paper {{ 
            margin: 0 !important; box-shadow: none !important; width: 100% !important; 
            padding: 0 !important; padding-top: 5mm !important;
        }}
        .footer-box {{
            position: fixed; bottom: 0; left: 0; right: 0;
            text-align: center; border-top: 1px solid black;
            padding: 5px 0; background: white; font-size: 8px;
        }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    .header-wrapper {{ text-align: center; margin-bottom: -15px; }}
    .main-title-text {{ font-size: 32px; font-weight: bold; text-align: center; text-transform: uppercase; margin: 0; }}

    /* ODBERATEĽ (VĽAVO) */
    .client-box {{ font-size: 11px !important; color: black; line-height: 0.9 !important; text-align: left; }}
    
    /* PLATNOSŤ A VYPRACOVAL (VPRAVO) */
    .right-info-box {{ text-align: right !important; font-size: 11px; line-height: 0.9; width: 100%; }}
    .right-info-box input {{ text-align: right !important; font-size: 11px !important; border: none !important; background: transparent !important; }}

    /* TABUĽKA */
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; color: black; table-layout: fixed; }}
    th, td {{ border: 1px solid #999; padding: 4px; text-align: center; font-size: 10px; }}
    th {{ background-color: #f2f2f2; font-weight: bold; }}
    .img-cell img {{ max-width: 100px; max-height: 180px; object-fit: contain; }}

    /* SUMÁR DOPRAVA */
    .summary-container {{ width: 100%; display: flex; justify-content: flex-end; margin-top: 5px; }}
    .summary-table {{ border: none !important; width: 280px; }}
    .summary-table td {{ border: none !important; text-align: right; padding: 1px 5px; font-size: 11px; }}
</style>
""", unsafe_allow_html=True)

# --- 3. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        df = pd.read_excel(file, engine="openpyxl")
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]] # Stĺpce A, F, G, H, N, Q
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except:
        return pd.DataFrame()

df_db = load_excel()

# --- 4. SIDEBAR OVLÁDANIE ---
with st.sidebar:
    st.header("⚙️ Správa ponuky")
    if df_db.empty:
        st.error("Súbor 'produkty.xlsx' nenájdený!")
    else:
        st.subheader("➕ Pridať tovar")
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        sub_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        velkosti = st.multiselect("Veľkosti", sort_sizes(sub_df[sub_df['FARBA'] == farba]['SIZE'].unique()))
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        br_u = st.number_input("Branding / ks €", min_value=0.0, step=0.1, value=0.0)
        link_img = st.text_input("Link na obrázok (voliteľné)", placeholder="https://...")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in velkosti:
                row = sub_df[(sub_df['FARBA'] == farba) & (sub_df['SIZE'] == s)].iloc[0]
                img_f = link_img if link_img else str(row['IMG_PRODUCT'])
                if img_f == 'nan' or not img_f.startswith('http'): img_f = ""
                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc, "img": img_f, "br": br_u
                })
            st.rerun()

    if st.session_state['offer_items']:
        st.divider()
        st.subheader("🗑️ Zmazať")
        for idx, item in enumerate(st.session_state['offer_items']):
            if st.button(f"Zmazať {item['kod']} ({item['v']})", key=f"del_{idx}"):
                st.session_state['offer_items'].pop(idx)
                st.rerun()

# --- 5. DOKUMENT A4 ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# HLAVIČKA
if logo_base64:
    st.markdown(f'<div class="header-wrapper"><img src="data:image/png;base64,{logo_base64}" width="220"><div class="main-title-text">PONUKA</div></div>', unsafe_allow_html=True)

# ODBERATEĽ & PLATNOSŤ + VYPRACOVAL
st.write("")
col_l, col_r = st.columns([1.5, 1])
with col_l:
    st.markdown("<div class='client-box'><b>ODBERATEĽ :</b>", unsafe_allow_html=True)
    st.text_input("Firma", "Názov firmy", key="cf", label_visibility="collapsed")
    st.text_input("Adresa", "Adresa", key="ca", label_visibility="collapsed")
    st.text_input("Kontakt", "Kontaktná osoba", key="co", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
with col_r:
    st.markdown("<div class='right-info-box'><b>PLATNOSŤ PONUKY DO :</b>", unsafe_allow_html=True)
    st.date_input("Dátum", value=datetime.now() + timedelta(days=14), label_visibility="collapsed", key="v_date")
    st.markdown("<br><b>VYPRACOVAL :</b>", unsafe_allow_html=True)
    st.text_input("Meno", "Vaše meno a priezvisko", key="proc_name", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

# TABUĽKA
total_i_net = 0
total_b_net = 0
if st.session_state['offer_items']:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    html = '<table><thead><tr><th style="width:100px;">Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava %</th><th>Branding</th><th>Suma bez DPH</th></tr></thead><tbody>'
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

# PÄTA
st.markdown("""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# TLAČIDLO TLAČE
if st.button("🖨️ Tlačiť ponuku"):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)