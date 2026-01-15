# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta

# --- 1. POMOCNÉ FUNKCIE (OPTIMALIZÁCIA) ---
@st.cache_data
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def files_to_base64_list(uploaded_files):
    base64_list = []
    if uploaded_files:
        for file in uploaded_files:
            b64 = base64.b64encode(file.getvalue()).decode()
            base64_list.append(f"data:image/png;base64,{b64}")
    return base64_list

def sort_sizes(size_list):
    order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL']
    return sorted(size_list, key=lambda x: order.index(x) if x in order else 99)

# Inicializácia pamäte
if 'offer_items' not in st.session_state: st.session_state['offer_items'] = []
if 'client_data' not in st.session_state: 
    st.session_state['client_data'] = {"firma": "", "adresa": "", "osoba": "", "platnost": datetime.now() + timedelta(days=14), "vypracoval": ""}

# --- 2. NASTAVENIA STRÁNKY A DESIGN ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide", initial_sidebar_state="expanded")

logo_base64_main = get_base64_image("brandex_logo.PNG")

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

    .header {{ text-align: center; margin-bottom: 5px; }}
    /* LOGO MENŠIE O 50% */
    .header img {{ width: 125px; }} 
    /* PONUKA VYCENTROVANÁ A VEĽKÝM */
    .main-title {{ font-size: 28px; font-weight: bold; text-align: center; text-transform: uppercase; margin-top: 5px; }}

    .info-grid {{ display: flex; justify-content: space-between; margin-top: 15px; font-size: 12px; }}
    .info-left {{ width: 50%; text-align: left; }}
    .info-right {{ width: 40%; text-align: right; }}

    table.items-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; color: black; table-layout: fixed; }}
    table.items-table th {{ background: #f2f2f2; border: 1px solid #ccc; padding: 5px; font-size: 10px; text-transform: uppercase; }}
    table.items-table td {{ border: 1px solid #ccc; padding: 4px; text-align: center; font-size: 10px; vertical-align: middle; }}
    .img-cell img {{ max-width: 80px; max-height: 100px; object-fit: contain; }}

    .summary-wrapper {{ display: flex; justify-content: flex-end; margin-top: 10px; }}
    .summary-table {{ width: 280px; border-collapse: collapse; border: none !important; }}
    .summary-table td {{ border: none !important; border-bottom: 1px solid #eee !important; padding: 3px 8px; text-align: right; font-size: 12px; }}
    .total-row {{ font-weight: bold; background: #f9f9f9; }}

    /* SEKČNÉ ČIARY ORANŽOVÉ */
    .section-title {{ 
        font-weight: bold; font-size: 13px; margin-top: 20px; 
        border-bottom: 2px solid #FF8C00; padding-bottom: 2px; text-transform: uppercase; 
    }}
    
    .branding-grid {{ display: flex; justify-content: space-between; gap: 20px; margin-top: 10px; font-size: 11px; }}
    .graphics-grid {{ display: flex; gap: 20px; margin-top: 10px; }}
    .graphic-box-container {{ width: 48%; display: flex; flex-direction: column; gap: 10px; }}
    .graphic-box {{ border: 1px dashed #ccc; padding: 5px; text-align: center; min-height: 100px; }}
    .graphic-box img {{ max-width: 100%; max-height: 150px; margin-bottom: 10px; }}

    .footer-box {{ font-size: 10px; text-align: center; border-top: 2px solid #FF8C00; margin-top: 30px; padding-top: 5px; line-height: 1.4; }}
    
    /* Skrytie šedých polí na papieri */
    .paper input {{ border: none !important; background: transparent !important; }}
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR (RÝCHLE ZADÁVANIE) ---
with st.sidebar:
    st.title("👔 Brandex Editor")
    
    with st.expander("👤 Hlavička", expanded=False):
        c_firma = st.text_input("Odberateľ", st.session_state.client_data['firma'])
        c_adresa = st.text_area("Adresa", st.session_state.client_data['adresa'], height=60)
        c_osoba = st.text_input("Kontakt", st.session_state.client_data['osoba'])
        c_platnost = st.date_input("Platnosť", st.session_state.client_data['platnost'])
        c_vypracoval = st.text_input("Vypracoval", st.session_state.client_data['vypracoval'])

    if os.path.exists("produkty.xlsx"):
        df_db = pd.read_excel("produkty.xlsx", engine="openpyxl").iloc[:, [0, 5, 6, 7, 13, 16]]
        df_db.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        
        with st.expander("➕ Pridať tovar", expanded=True):
            model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
            sub = df_db[df_db['SKUPINOVY_NAZOV'] == model]
            farba = st.selectbox("Farba", sorted(sub['FARBA'].unique()))
            velkosti = st.multiselect("Veľkosti", sort_sizes(sub[sub['FARBA'] == farba]['SIZE'].unique()))
            qty = st.number_input("Počet ks", 1, 1000, 1)
            disc = st.number_input("Zľava %", 0, 100, 0)
            br_u = st.number_input("Branding/ks €", 0.0, 50.0, 0.0)
            
            if st.button("PRIDAŤ DO TABUĽKY"):
                for s in velkosti:
                    row = sub[(sub['FARBA'] == farba) & (sub['SIZE'] == s)].iloc[0]
                    st.session_state.offer_items.append({
                        "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                        "ks": qty, "p": float(row['PRICE']), "z": disc, "br": br_u, "img": str(row['IMG_PRODUCT'])
                    })
                st.rerun()

    with st.expander("🎨 Grafika a Branding", expanded=False):
        b_tech = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Tampoprint"])
        b_desc = st.text_area("Popis umiestnenia")
        b_date = st.date_input("Dátum vzorky", datetime.now())
        # VIACNÁSOBNÝ UPLOAD
        upl_logos = st.file_uploader("Logá klienta", type=['png','jpg','jpeg'], accept_multiple_files=True)
        upl_previews = st.file_uploader("Náhľady grafiky", type=['png','jpg','jpeg'], accept_multiple_files=True)

    if st.session_state.offer_items:
        if st.button("🗑️ Vymazať všetko"):
            st.session_state.offer_items = []
            st.rerun()

# --- 4. GENEROVANIE PAPIERA (WYSIWYG) ---
# Predspracovanie obrázkov do Base64 (aby aplikácia nelogovala pri každom kroku)
b64_logos = files_to_base64_list(upl_logos)
b64_previews = files_to_base64_list(upl_previews)

html_lines = [f'<div class="paper">']
html_lines.append(f'<div class="header"><img src="data:image/png;base64,{logo_base64_main if logo_base64_main else ""}"></div>')
html_lines.append(f'<div class="main-title">PONUKA</div>')

html_lines.append(f'''
<div class="info-grid">
    <div class="info-left">
        <b>ODBERATEĽ :</b><br>
        {c_firma if c_firma else "..."}<br>
        {c_adresa if c_adresa else ""}<br>
        {c_osoba if c_osoba else ""}
    </div>
    <div class="info-right">
        <b>PLATNOSŤ PONUKY DO :</b><br>
        {c_platnost.strftime('%d. %m. %Y')}<br><br>
        <b>VYPRACOVAL :</b><br>
        {c_vypracoval if c_vypracoval else "..."}
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
                img = it['img'] if it['img'] != 'nan' else ""
                html_lines.append(f'<td rowspan="{g_size}" class="img-cell"><img src="{img}"></td>')
            html_lines.append(f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td><td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{it['br']:.2f} €</td><td>{row_sum:.2f} €</td></tr>")
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
    <div style="flex:1"><b>Technológia</b><br>{b_tech}</div>
    <div style="flex:2"><b>Popis</b><br>{b_desc}</div>
    <div style="flex:1"><b>Dodanie vzorky</b><br>{b_date.strftime('%d. %m. %Y')}</div>
</div>

<div class="graphics-grid">
    <div class="graphic-box-container">
        <div class="section-title">LOGO KLIENTA</div>
        <div class="graphic-box">
            {''.join([f'<img src="{img}">' for img in b64_logos]) if b64_logos else ""}
        </div>
    </div>
    <div class="graphic-box-container">
        <div class="section-title">NÁHĽAD GRAFIKY</div>
        <div class="graphic-box">
            {''.join([f'<img src="{img}">' for img in b64_previews]) if b64_previews else ""}
        </div>
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

st.markdown("".join(html_lines), unsafe_allow_html=True)

# Tlačidlo
st.write("")
if st.button("🖨️ Tlačiť ponuku", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)