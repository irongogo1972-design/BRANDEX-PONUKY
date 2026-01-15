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
    return ""

def sort_sizes(size_list):
    order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL']
    return sorted(size_list, key=lambda x: order.index(x) if x in order else 99)

# Inicializácia pamäte hneď na začiatku
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. NASTAVENIA STRÁNKY A CSS ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide", initial_sidebar_state="expanded")

logo_base64_main = get_base64_image("brandex_logo.PNG")

# CSS pre WYSIWYG a Tlač
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
            text-align: center; border-top: 1px solid black;
            padding: 5px 0; background: white; font-size: 8px;
        }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    .header-wrapper {{ text-align: center; margin-bottom: 5px; }}
    .main-title {{ font-size: 32px; font-weight: bold; text-align: center; text-transform: uppercase; margin-top: -10px; }}

    .info-grid {{ display: flex; justify-content: space-between; margin-top: 20px; font-size: 12px; }}
    .info-left {{ width: 50%; text-align: left; }}
    .info-right {{ width: 40%; text-align: right; }}

    table.items-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; color: black; table-layout: fixed; }}
    table.items-table th {{ background: #f2f2f2; border: 1px solid #ccc; padding: 5px; font-size: 10px; text-transform: uppercase; }}
    table.items-table td {{ border: 1px solid #ccc; padding: 4px; text-align: center; font-size: 10px; vertical-align: middle; }}
    .img-cell img {{ max-width: 80px; max-height: 100px; object-fit: contain; }}

    .summary-wrapper {{ display: flex; justify-content: flex-end; margin-top: 10px; }}
    .summary-table {{ width: 280px; border-collapse: collapse; border: none !important; }}
    .summary-table td {{ border: none !important; border-bottom: 1px solid #eee !important; padding: 3px 8px; text-align: right; font-size: 12px; }}
    .total-row {{ font-weight: bold; background: #f9f9f9; }}

    .section-title {{ font-weight: bold; font-size: 13px; margin-top: 20px; border-bottom: 1px solid #000; padding-bottom: 2px; text-transform: uppercase; }}
    .branding-grid {{ display: flex; justify-content: space-between; gap: 20px; margin-top: 10px; font-size: 11px; }}
    .graphics-grid {{ display: flex; gap: 20px; margin-top: 10px; }}
    .graphic-box {{ border: 1px dashed #ccc; padding: 5px; text-align: center; width: 48%; min-height: 100px; }}
    .graphic-box img {{ max-width: 100%; max-height: 90px; }}

    .footer-box {{ font-size: 10px; text-align: center; border-top: 1px solid black; margin-top: 30px; padding-top: 5px; line-height: 1.4; }}
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR (Editor) ---
with st.sidebar:
    st.title("⚙️ Editor Ponuky")
    
    with st.expander("👤 Odberateľ a Spracovateľ", expanded=False):
        c_firma = st.text_input("Firma", "Názov firmy")
        c_adresa = st.text_input("Adresa")
        c_osoba = st.text_input("Kontaktná osoba")
        c_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
        c_vypracoval = st.text_input("Ponuku vypracoval", "Meno a priezvisko")

    if os.path.exists("produkty.xlsx"):
        df_db = pd.read_excel("produkty.xlsx", engine="openpyxl").iloc[:, [0, 5, 6, 7, 13, 16]]
        df_db.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        
        with st.expander("➕ Pridať tovar", expanded=True):
            model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
            sub = df_db[df_db['SKUPINOVY_NAZOV'] == model]
            farba = st.selectbox("Farba", sorted(sub['FARBA'].unique()))
            velkosti = st.multiselect("Veľkosti", sort_sizes(sub[sub['FARBA'] == farba]['SIZE'].unique()))
            qty = st.number_input("Počet ks", min_value=1, value=1)
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

    with st.expander("🎨 Branding a Grafika", expanded=False):
        b_tech = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Subli"])
        b_desc = st.text_area("Popis")
        b_date = st.date_input("Dodanie vzorky", datetime.now())
        upl_logo = st.file_uploader("Logo klienta", type=['png','jpg','jpeg'])
        upl_prev = st.file_uploader("Náhľad grafiky", type=['png','jpg','jpeg'])

    if st.session_state.offer_items:
        st.divider()
        if st.button("🗑️ Vymazať všetko"):
            st.session_state.offer_items = []
            st.rerun()
        for idx, item in enumerate(st.session_state.offer_items):
            if st.button(f"Zmazať {item['kod']} ({item['v']})", key=f"del_{idx}"):
                st.session_state.offer_items.pop(idx)
                st.rerun()

# --- 4. GENEROVANIE PAPIERA (WYSIWYG) ---
b64_logo_klient = f"data:image/png;base64,{file_to_base64(upl_logo)}" if upl_logo else ""
b64_prev_klient = f"data:image/png;base64,{file_to_base64(upl_prev)}" if upl_prev else ""

# Zostavenie HTML stringu
html_lines = []
html_lines.append(f'<div class="paper">')
html_lines.append(f'<div class="header"><img src="data:image/png;base64,{logo_base64_main}"><h1>Ponuka</h1></div>')

html_lines.append(f'''
<div class="info-grid">
    <div class="info-left">
        <b>ODBERATEĽ :</b><br>
        {c_firma}<br>{c_adresa}<br>{c_osoba}
    </div>
    <div class="info-right">
        <b>PLATNOSŤ PONUKY DO :</b><br>
        {c_platnost.strftime('%d. %m. %Y')}<br><br>
        <b>VYPRACOVAL :</b><br>
        {c_vypracoval}
    </div>
</div>
''')

html_lines.append('<div class="section-title">POLOŽKY</div>')
html_lines.append('<table class="items-table"><thead><tr>')
html_lines.append('<th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th>')
html_lines.append('</tr></thead><tbody>')

total_i = 0
total_b = 0
if st.session_state.offer_items:
    df_items = pd.DataFrame(st.session_state.offer_items)
    groups = df_items.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state.offer_items[idx]
            pz = it['p'] * (1 - it['z']/100)
            row_sum = it['ks'] * (pz + it['br'])
            total_i += (it['ks'] * pz)
            total_b += (it['ks'] * it['br'])
            
            html_lines.append('<tr>')
            if i == 0:
                img_url = it['img'] if it['img'] != 'nan' else ""
                html_lines.append(f'<td rowspan="{g_size}" class="img-cell"><img src="{img_url}"></td>')
            
            html_lines.append(f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>")
            html_lines.append(f"<td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{it['br']:.2f} €</td><td>{row_sum:.2f} €</td>")
            html_lines.append('</tr>')
            idx += 1

sum_z = total_i + total_b
html_lines.append('</tbody></table>')

html_lines.append(f'''
<div class="summary-wrapper">
    <table class="summary-table">
        <tr><td>Suma položiek bez DPH:</td><td>{total_i:.2f} €</td></tr>
        <tr><td>Branding celkom bez DPH:</td><td>{total_b:.2f} €</td></tr>
        <tr class="total-row"><td>Základ DPH:</td><td>{sum_z:.2f} €</td></tr>
        <tr><td>DPH (23%):</td><td>{sum_z * 0.23:.2f} €</td></tr>
        <tr class="total-row"><td>CELKOM S DPH:</td><td>{sum_z * 1.23:.2f} €</td></tr>
    </table>
</div>
''')

html_lines.append(f'''
<div class="section-title">BRANDING</div>
<div class="branding-grid">
    <div><b>Technológia</b><br>{b_tech}</div>
    <div style="flex-grow:2;"><b>Popis</b><br>{b_desc}</div>
    <div><b>Dodanie vzorky</b><br>{b_date.strftime('%d. %m. %Y')}</div>
</div>

<div class="graphics-grid">
    <div class="graphic-box">
        <div style="font-weight:bold; margin-bottom:5px;">LOGO KLIENTA</div>
        {"<img src='"+b64_logo_klient+"'>" if b64_logo_klient else ""}
    </div>
    <div class="graphic-box">
        <div style="font-weight:bold; margin-bottom:5px;">NÁHĽAD GRAFIKY</div>
        {"<img src='"+b64_prev_klient+"'>" if b64_prev_klient else ""}
    </div>
</div>
''')

html_lines.append(f'''
<div class="footer-box">
    BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
    tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
</div>
</div>
''')

# Finálne vykreslenie
st.markdown("".join(html_lines), unsafe_allow_html=True)

# Tlačidlo pre tlač
st.write("")
if st.button("🖨️ Tlačiť ponuku", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)