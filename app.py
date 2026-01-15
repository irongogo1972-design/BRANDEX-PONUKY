# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta

# --- 1. POMOCNÉ FUNKCIE (Optimalizácia) ---
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

# Inicializácia relácie (Session State)
if 'offer_items' not in st.session_state: st.session_state['offer_items'] = []
if 'client_info' not in st.session_state: 
    st.session_state['client_info'] = {"firma": "", "adresa": "", "osoba": "", "platnost": datetime.now() + timedelta(days=14), "vypracoval": ""}
if 'brand_setup' not in st.session_state:
    st.session_state['brand_setup'] = {"tech": "Sieťotlač", "popis": "", "vzorka": datetime.now()}

# --- 2. NASTAVENIA STRÁNKY A DESIGN ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide", initial_sidebar_state="expanded")

logo_b64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
<style>
    /* Reset medzier Streamlitu */
    [data-testid="stAppViewBlockContainer"] {{ padding: 0 !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stVerticalBlock"] {{ gap: 0rem !important; }}

    /* WYSIWYG PAPIER */
    .paper {{
        background: white; width: 210mm; min-height: 297mm;
        padding: 10mm 15mm; margin: 15px auto;
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

    /* HLAVIČKA */
    .header {{ text-align: center; margin-bottom: 0px; }}
    .header img {{ width: 120px; }} /* Zmenšené na 50% */
    .main-title {{ font-size: 30px; font-weight: bold; text-align: center; text-transform: uppercase; margin-top: -10px; margin-bottom: 10px; }}

    /* ORANŽOVÉ ČIARY */
    .orange-line {{ border-top: 2px solid #FF8C00; margin: 10px 0; }}

    /* INFO SEKCE (Grid) */
    .info-grid {{ display: flex; justify-content: space-between; margin-top: 15px; font-size: 12px; }}
    .info-left {{ width: 55%; }}
    .info-right {{ width: 40%; text-align: right; }}

    /* TABUĽKA */
    .items-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    .items-table th {{ background: #f2f2f2; border: 1px solid #ccc; padding: 5px; font-size: 10px; text-transform: uppercase; }}
    .items-table td {{ border: 1px solid #ccc; padding: 4px; text-align: center; font-size: 10px; vertical-align: middle; }}
    .img-cell img {{ max-width: 70px; max-height: 90px; object-fit: contain; }}

    /* REKAPITULÁCIA */
    .summary-wrapper {{ display: flex; justify-content: flex-end; margin-top: 5px; }}
    .summary-table {{ width: 280px; border-collapse: collapse; }}
    .summary-table td {{ border: none !important; border-bottom: 1px solid #eee !important; padding: 2px 5px; text-align: right; font-size: 11px; }}
    .total-row {{ font-weight: bold; background: #f9f9f9; font-size: 13px !important; }}

    /* BRANDING A GRAFIKA */
    .section-title {{ font-weight: bold; font-size: 12px; margin-top: 15px; text-transform: uppercase; }}
    .branding-flex {{ display: flex; justify-content: space-between; gap: 20px; margin-top: 5px; font-size: 11px; }}
    .graphics-container {{ display: flex; gap: 20px; margin-top: 10px; }}
    .graphic-column {{ width: 48%; display: flex; flex-direction: column; gap: 10px; }}
    .graphic-box {{ border: 1px dashed #ccc; padding: 5px; text-align: center; min-height: 100px; }}
    .graphic-box img {{ max-width: 100%; max-height: 140px; display: block; margin: 5px auto; }}

    /* PÄTA */
    .footer-box {{ font-size: 10px; text-align: center; border-top: 2px solid #FF8C00; margin-top: 30px; padding-top: 5px; }}
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR (EDITOR) ---
with st.sidebar:
    st.title("⚙️ Administrácia")
    
    with st.expander("👤 Odberateľ a Spracovateľ", expanded=False):
        st.session_state.client_info['firma'] = st.text_input("Firma", st.session_state.client_info['firma'])
        st.session_state.client_info['adresa'] = st.text_area("Adresa", st.session_state.client_info['adresa'])
        st.session_state.client_info['osoba'] = st.text_input("Kontaktná osoba", st.session_state.client_info['osoba'])
        st.session_state.client_info['platnost'] = st.date_input("Platnosť do", st.session_state.client_info['platnost'])
        st.session_state.client_info['vypracoval'] = st.text_input("Vypracoval", st.session_state.client_info['vypracoval'])

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
            link_img = st.text_input("Vlastný link na obrázok")
            
            if st.button("PRIDAŤ DO PONUKY"):
                for s in velkosti:
                    row = sub[(sub['FARBA'] == farba) & (sub['SIZE'] == s)].iloc[0]
                    img = link_img if link_img else str(row['IMG_PRODUCT'])
                    if not any(item['kod'] == row['KOD_IT'] and item['v'] == s for item in st.session_state.offer_items):
                        st.session_state.offer_items.append({
                            "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                            "ks": qty, "p": float(row['PRICE']), "z": disc, "br": br_u, "img": img
                        })
                st.rerun()

    with st.expander("🎨 Branding a Grafika", expanded=False):
        st.session_state.brand_setup['tech'] = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Subli", "Tampoprint"])
        st.session_state.brand_setup['popis'] = st.text_area("Popis")
        st.session_state.brand_setup['vzorka'] = st.date_input("Dodanie vzorky", st.session_state.brand_setup['vzorka'])
        upl_logos = st.file_uploader("LOGO (viac súborov)", type=['png','jpg','jpeg'], accept_multiple_files=True)
        upl_previews = st.file_uploader("NÁHĽAD (viac súborov)", type=['png','jpg','jpeg'], accept_multiple_files=True)

    if st.session_state.offer_items:
        st.divider()
        if st.button("🗑️ VYMAZAŤ CELÚ PONUKU"):
            st.session_state.offer_items = []
            st.rerun()
        for idx, item in enumerate(st.session_state.offer_items):
            if st.button(f"Zmazať {item['kod']} ({item['v']})", key=f"del_{idx}"):
                st.session_state.offer_items.pop(idx)
                st.rerun()

# --- 4. GENEROVANIE VÝSTUPU (Čisté HTML) ---
# Spracovanie nahraných log
html_logos = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}">' for f in upl_logos]) if upl_logos else ""
html_previews = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}">' for f in upl_previews]) if upl_previews else ""

html_output = f"""
<div class="paper">
    <div class="header">
        <img src="data:image/png;base64,{logo_b64 if logo_b64 else ''}">
    </div>
    <div class="main-title">PONUKA</div>

    <div class="info-grid">
        <div class="info-left">
            <b>ODBERATEĽ :</b><br>
            {st.session_state.client_info['firma']}<br>
            {st.session_state.client_info['adresa']}<br>
            {st.session_state.client_info['osoba']}
        </div>
        <div class="info-right">
            <b>PLATNOSŤ PONUKY DO :</b><br>
            {st.session_state.client_info['platnost'].strftime('%d. %m. %Y')}<br><br>
            <b>VYPRACOVAL :</b><br>
            {st.session_state.client_info['vypracoval']}
        </div>
    </div>

    <div class="section-title">POLOŽKY</div>
    <table class="items-table">
        <thead>
            <tr>
                <th style="width:80px">Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th>
                <th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th>
            </tr>
        </thead>
        <tbody>
"""

total_items = 0
total_brand = 0
if st.session_state.offer_items:
    df_items = pd.DataFrame(st.session_state.offer_items)
    groups = df_items.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state.offer_items[idx]
            pz = it['p'] * (1 - it['z']/100)
            row_sum = it['ks'] * (pz + it['br'])
            total_items += (it['ks'] * pz)
            total_brand += (it['ks'] * it['br'])
            
            html_output += "<tr>"
            if i == 0:
                img = it['img'] if it['img'] != 'nan' else ""
                html_output += f'<td rowspan="{g_size}" class="img-cell"><img src="{img}"></td>'
            
            html_output += f"""
                <td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>
                <td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td>
                <td>{it['br']:.2f} €</td><td>{row_sum:.2f} €</td>
            </tr>"""
            idx += 1

base_vat = total_items + total_brand
html_output += f"""
        </tbody>
    </table>

    <div class="summary-wrapper">
        <table class="summary-table">
            <tr><td>Suma položiek bez DPH:</td><td>{total_items:.2f} €</td></tr>
            <tr><td>Branding celkom bez DPH:</td><td>{total_brand:.2f} €</td></tr>
            <tr class="total-row"><td>Základ DPH:</td><td>{base_vat:.2f} €</td></tr>
            <tr><td>DPH (23%):</td><td>{base_vat * 0.23:.2f} €</td></tr>
            <tr class="total-row"><td>CELKOM S DPH:</td><td>{base_vat * 1.23:.2f} €</td></tr>
        </table>
    </div>

    <div class="section-title">BRANDING</div>
    <div class="branding-grid">
        <div style="flex:1"><b>Technológia</b><br>{st.session_state.brand_setup['tech']}</div>
        <div style="flex:2"><b>Popis</b><br>{st.session_state.brand_setup['popis']}</div>
        <div style="flex:1"><b>Dodanie vzorky</b><br>{st.session_state.brand_setup['vzorka'].strftime('%d. %m. %Y')}</div>
    </div>

    <div class="graphics-grid">
        <div class="graphic-column">
            <div class="section-title">LOGO KLIENTA</div>
            <div class="graphic-box">{html_logos}</div>
        </div>
        <div class="graphic-column">
            <div class="section-title">NÁHĽAD GRAFIKY</div>
            <div class="graphic-box">{html_previews}</div>
        </div>
    </div>

    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
</div>
"""

st.markdown(html_output, unsafe_allow_html=True)

# Tlačidlo
st.write("")
if st.button("🖨️ Tlačiť ponuku", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)