# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta

# --- 1. POMOCNÉ FUNKCIE ---
@st.cache_data
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def file_to_base64(uploaded_file):
    if uploaded_file is not None:
        return base64.b64encode(uploaded_file.getvalue()).decode()
    return ""

def sort_sizes(size_list):
    order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL']
    return sorted(size_list, key=lambda x: order.index(x) if x in order else 99)

# Inicializácia pamäte
if 'offer_items' not in st.session_state: st.session_state['offer_items'] = []

# --- 2. NASTAVENIA STRÁNKY A CSS ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide", initial_sidebar_state="expanded")

logo_main_b64 = get_base64_image("brandex_logo.PNG")

# Definícia štýlov (Orange Brandex Style)
st.markdown(f"""
<style>
    [data-testid="stAppViewBlockContainer"] {{ padding: 0 !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    
    .paper {{
        background: white; width: 210mm; min-height: 297mm;
        padding: 15mm; margin: 10px auto;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        color: black; font-family: "Arial", sans-serif;
    }}

    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"], .stFileUploader {{
            display: none !important;
        }}
        .paper {{ margin: 0 !important; box-shadow: none !important; width: 100% !important; padding: 0 !important; }}
        .footer-box {{
            position: fixed; bottom: 0; left: 0; right: 0;
            text-align: center; border-top: 2px solid #FF8C00;
            padding: 5px 0; background: white; font-size: 8px;
        }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    .header-logo {{ text-align: center; margin-bottom: 5px; }}
    .header-logo img {{ width: 125px; }}
    .main-title {{ font-size: 32px; font-weight: bold; text-align: center; text-transform: uppercase; margin: 0 0 20px 0; }}

    /* Layout pre info sekcie */
    .grid-2 {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 20px; margin-top: 10px; font-size: 12px; }}
    .text-right {{ text-align: right; }}

    /* Oranžové čiary a nadpisy */
    .section-header {{ 
        font-weight: bold; font-size: 13px; margin-top: 20px; 
        border-bottom: 2px solid #FF8C00; padding-bottom: 3px; text-transform: uppercase; 
    }}

    /* Tabuľka položiek */
    .items-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    .items-table th {{ background: #f8f8f8; border: 1px solid #ddd; padding: 6px; font-size: 10px; text-transform: uppercase; }}
    .items-table td {{ border: 1px solid #ddd; padding: 5px; text-align: center; font-size: 11px; vertical-align: middle; }}
    .img-cell img {{ max-width: 70px; max-height: 90px; object-fit: contain; }}

    /* Sumarizácia */
    .summary-wrapper {{ display: flex; justify-content: flex-end; margin-top: 10px; }}
    .summary-table {{ width: 280px; border-collapse: collapse; }}
    .summary-table td {{ border-bottom: 1px solid #eee; padding: 3px 8px; text-align: right; font-size: 12px; }}
    .total-row {{ font-weight: bold; background: #fdf2e9; font-size: 14px !important; border-bottom: 2px solid #FF8C00 !important; }}

    /* Branding Grid */
    .branding-row {{ display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 20px; margin-top: 5px; font-size: 12px; }}
    .graphics-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }}
    .graphic-box {{ border: 1px dashed #ccc; padding: 10px; text-align: center; min-height: 120px; display: flex; flex-direction: column; gap: 10px; align-items: center; }}
    .graphic-box img {{ max-width: 100%; max-height: 120px; }}

    .footer-box {{ font-size: 10px; text-align: center; border-top: 2px solid #FF8C00; margin-top: 40px; padding-top: 8px; line-height: 1.4; }}
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR (VŠETKY VSTUPY) ---
with st.sidebar:
    st.title("👔 Brandex Editor")
    
    with st.expander("👤 Odberateľ", expanded=False):
        c_firma = st.text_input("Firma", "")
        c_adresa = st.text_area("Adresa", "")
        c_osoba = st.text_input("Kontakt")
        c_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
        c_vypracoval = st.text_input("Ponuku vypracoval")

    if os.path.exists("produkty.xlsx"):
        df_db = pd.read_excel("produkty.xlsx", engine="openpyxl").iloc[:, [0, 5, 6, 7, 13, 16]]
        df_db.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        
        with st.expander("➕ Pridať položky", expanded=True):
            model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
            sub = df_db[df_db['SKUPINOVY_NAZOV'] == model]
            farba = st.selectbox("Farba", sorted(sub['FARBA'].unique()))
            velkosti = st.multiselect("Veľkosti", sort_sizes(sub[sub['FARBA'] == farba]['SIZE'].unique()))
            qty = st.number_input("Počet ks", 1, 5000, 1)
            disc = st.number_input("Zľava %", 0, 100, 0)
            br_u = st.number_input("Branding/ks €", 0.0, 50.0, 0.0, step=0.1)
            link_img = st.text_input("Link na obrázok (voliteľné)")
            
            if st.button("PRIDAŤ DO TABUĽKY"):
                for s in velkosti:
                    row = sub[(sub['FARBA'] == farba) & (sub['SIZE'] == s)].iloc[0]
                    img = link_img if link_img else str(row['IMG_PRODUCT'])
                    if not any(item['kod'] == row['KOD_IT'] and item['v'] == s for item in st.session_state.offer_items):
                        st.session_state.offer_items.append({
                            "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                            "ks": qty, "p": float(row['PRICE']), "z": disc, "br": br_u, "img": img
                        })
                st.rerun()

    with st.expander("🎨 Branding a Logá", expanded=False):
        b_tech = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Tampoprint"])
        b_desc = st.text_area("Popis umiestnenia")
        b_date = st.date_input("Dátum vzorky", datetime.now())
        upl_logos = st.file_uploader("LOGÁ", type=['png','jpg','jpeg'], accept_multiple_files=True)
        upl_previews = st.file_uploader("NÁHĽADY", type=['png','jpg','jpeg'], accept_multiple_files=True)

    if st.session_state.offer_items:
        st.divider()
        if st.button("🗑️ Vymazať všetko"):
            st.session_state.offer_items = []
            st.rerun()
        for idx, item in enumerate(st.session_state.offer_items):
            if st.button(f"Zmazať {item['kod']} ({item['v']})", key=f"del_{idx}"):
                st.session_state.offer_items.pop(idx)
                st.rerun()

# --- 4. TVORBA HTML VÝSTUPU ---
# Prevody uploadov na Base64
html_logos = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}">' for f in upl_logos]) if upl_logos else ""
html_previews = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}">' for f in upl_previews]) if upl_previews else ""

# Zostavenie tabuľky
table_rows = ""
total_items_net = 0
total_brand_net = 0

if st.session_state.offer_items:
    df_items = pd.DataFrame(st.session_state.offer_items)
    groups = df_items.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state.offer_items[idx]
            pz = it['p'] * (1 - it['z']/100)
            row_sum = it['ks'] * (pz + it['br'])
            total_items_net += (it['ks'] * pz)
            total_brand_net += (it['ks'] * it['br'])
            
            row_html = "<tr>"
            if i == 0:
                img = it['img'] if it['img'] != 'nan' else ""
                row_html += f'<td rowspan="{g_size}" class="img-cell"><img src="{img}"></td>'
            
            row_html += f"""
                <td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>
                <td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td>
                <td>{it['br']:.2f} €</td><td>{row_sum:.2f} €</td></tr>
            """
            table_rows += row_html
            idx += 1

sum_vat_base = total_items_net + total_brand_net

# KOMPLETNÝ HTML DOKUMENT
final_html = f"""
<div class="paper">
    <div class="header">
        <img src="data:image/png;base64,{logo_main_b64 if logo_main_b64 else ''}">
    </div>
    <div class="main-title">PONUKA</div>

    <div class="info-grid">
        <div class="info-left">
            <b>ODBERATEĽ :</b><br>
            {c_firma if c_firma else "........................"}<br>
            {c_adresa if c_adresa else ""}<br>
            {c_osoba if c_osoba else ""}
        </div>
        <div class="info-right">
            <b>PLATNOSŤ PONUKY DO :</b><br>
            {c_platnost.strftime('%d. %m. %Y')}<br><br>
            <b>VYPRACOVAL :</b><br>
            {c_vypracoval if c_vypracoval else "........................"}
        </div>
    </div>

    <div class="section-header">POLOŽKY</div>
    <table class="items-table">
        <thead>
            <tr>
                <th style="width:80px">Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th>
                <th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th>
            </tr>
        </thead>
        <tbody>
            {table_rows if table_rows else "<tr><td colspan='10'>Žiadne položky</td></tr>"}
        </tbody>
    </table>

    <div class="summary-wrapper">
        <table class="summary-table">
            <tr><td>Suma položiek bez DPH:</td><td>{total_items_net:.2f} €</td></tr>
            <tr><td>Branding celkom bez DPH:</td><td>{total_brand_net:.2f} €</td></tr>
            <tr class="total-row"><td>Základ DPH:</td><td>{sum_vat_base:.2f} €</td></tr>
            <tr><td>DPH (23%):</td><td>{sum_vat_base * 0.23:.2f} €</td></tr>
            <tr class="total-row"><td>CELKOM S DPH:</td><td>{sum_vat_base * 1.23:.2f} €</td></tr>
        </table>
    </div>

    <div class="section-header">BRANDING</div>
    <div class="branding-row">
        <div><b>Technológia</b><br>{b_tech}</div>
        <div><b>Popis</b><br>{b_desc if b_desc else "..."}</div>
        <div><b>Dodanie vzorky</b><br>{b_date.strftime('%d. %m. %Y')}</div>
    </div>

    <div class="graphics-row">
        <div>
            <div class="section-header">LOGO KLIENTA</div>
            <div class="graphic-box">{html_logos}</div>
        </div>
        <div>
            <div class="section-header">NÁHĽAD GRAFIKY</div>
            <div class="graphic-box">{html_previews}</div>
        </div>
    </div>

    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
</div>
"""

# Zobrazenie bez rizika "kódu"
st.components.v1.html(f"""
    <div style="display: flex; justify-content: center;">
        {final_html}
    </div>
    <style>
        body {{ background-color: #f0f2f6; margin: 0; }}
    </style>
""", height=1200, scrolling=True)

# Tlačidlo pre tlač (ostáva Streamlitové pre jednoduchosť)
if st.button("🖨️ Tlačiť ponuku", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)