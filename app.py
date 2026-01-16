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

st.markdown(f"""
<style>
    [data-testid="stAppViewBlockContainer"] {{ padding: 0 !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    
    .paper {{
        background: white; width: 210mm; min-height: 297mm;
        padding: 12mm 15mm; margin: 10px auto;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        color: black; font-family: "Arial", sans-serif;
        line-height: 1.2;
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
    .header img {{ width: 125px; }} 
    .main-title {{ font-size: 28px; font-weight: bold; text-align: center; text-transform: uppercase; margin: 5px 0 15px 0; }}

    .orange-line {{ border-top: 2px solid #FF8C00; margin: 10px 0; }}

    .info-grid {{ display: flex; justify-content: space-between; margin-top: 15px; font-size: 11px; }}
    .info-left {{ width: 55%; text-align: left; line-height: 1.1; }}
    .info-right {{ width: 40%; text-align: right; line-height: 1.1; }}

    table.items-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; color: black; }}
    table.items-table th {{ background: #f2f2f2; border: 1px solid #ccc; padding: 5px; font-size: 9px; text-transform: uppercase; }}
    table.items-table td {{ border: 1px solid #ccc; padding: 4px; text-align: center; font-size: 10px; vertical-align: middle; }}
    .img-cell img {{ max-width: 80px; max-height: 100px; object-fit: contain; }}

    .summary-wrapper {{ display: flex; justify-content: flex-end; margin-top: 10px; }}
    .summary-table {{ width: 280px; border-collapse: collapse; }}
    .summary-table td {{ border-bottom: 1px solid #eee; padding: 3px 8px; text-align: right; font-size: 11px; }}
    .total-row {{ font-weight: bold; background: #fdf2e9; font-size: 13px !important; border-bottom: 2px solid #FF8C00 !important; }}

    .section-title {{ font-weight: bold; font-size: 12px; margin-top: 15px; text-transform: uppercase; }}
    .branding-row {{ display: flex; justify-content: space-between; gap: 20px; margin-top: 5px; font-size: 11px; }}
    .graphics-row {{ display: flex; gap: 20px; margin-top: 10px; }}
    .graphic-col {{ width: 48%; }}
    .graphic-box {{ border: 1px dashed #ccc; padding: 5px; text-align: center; min-height: 100px; display: flex; flex-direction: column; gap: 10px; }}
    .graphic-box img {{ max-width: 100%; max-height: 150px; display: block; margin: 0 auto; }}

    .footer-box {{ font-size: 10px; text-align: center; border-top: 2px solid #FF8C00; margin-top: 40px; padding-top: 5px; line-height: 1.4; }}
    .paper input {{ border: none !important; background: transparent !important; }}
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR (VŠETKY VSTUPY) ---
with st.sidebar:
    st.title("👔 Brandex Editor")
    
    with st.expander("👤 Odberateľ a Termíny", expanded=False):
        c_firma = st.text_input("Firma", "")
        c_adresa = st.text_area("Adresa", "")
        c_osoba = st.text_input("Kontakt")
        c_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
        c_dodanie = st.text_input("Doba dodania", "10-14 pracovných dní")
        c_vypracoval = st.text_input("Ponuku vypracoval")

    if os.path.exists("produkty.xlsx"):
        df_db = pd.read_excel("produkty.xlsx", engine="openpyxl").iloc[:, [0, 5, 6, 7, 13, 16]]
        df_db.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        
        with st.expander("➕ Pridať položky", expanded=True):
            model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
            sub = df_db[df_db['SKUPINOVY_NAZOV'] == model]
            farba = st.selectbox("Farba", sorted(sub['FARBA'].unique()))
            
            # --- LOGIKA PRE NAČÍTANIE OBRÁZKA ZO STĹPCA Q ---
            # Nájdeme prvý riadok pre daný model a farbu, ktorý má vyplnený obrázok v stĺpci Q
            color_sub = sub[sub['FARBA'] == farba]
            # Podľa vašej požiadavky berieme prvý obrázok v poradí (zvyčajne 2. riadok v Exceli je 1. v Pandas)
            suggested_img = ""
            if not color_sub.empty:
                valid_imgs = color_sub['IMG_PRODUCT'].dropna().tolist()
                if valid_imgs:
                    suggested_img = str(valid_imgs[0]) # Prvý nájdený link

            velkosti = st.multiselect("Veľkosti", sort_sizes(color_sub['SIZE'].unique()))
            qty = st.number_input("Počet ks", 1, 5000, 1)
            disc = st.number_input("Zľava %", 0, 100, 0)
            br_u = st.number_input("Branding/ks €", 0.0, 50.0, 0.0, step=0.1)
            
            # Predvyplnené pole s linkom z Excelu
            link_img = st.text_input("Link na obrázok (z Excelu Q)", value=suggested_img)
            
            if st.button("PRIDAŤ DO TABUĽKY"):
                for s in velkosti:
                    row = color_sub[color_sub['SIZE'] == s].iloc[0]
                    # Použije sa link z poľa (buď ten predvyplnený alebo manuálne upravený)
                    img_to_use = link_img if link_img else ""
                    
                    if not any(item['kod'] == row['KOD_IT'] and item['v'] == s for item in st.session_state.offer_items):
                        st.session_state.offer_items.append({
                            "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                            "ks": qty, "p": float(row['PRICE']), "z": disc, "br": br_u, "img": img_to_use
                        })
                st.rerun()

    with st.expander("🎨 Branding a Grafika", expanded=False):
        b_tech = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Subli", "Tampoprint"])
        b_desc = st.text_area("Popis")
        b_date = st.date_input("Dátum vzorky", datetime.now())
        upl_logos = st.file_uploader("LOGÁ", type=['png','jpg','jpeg'], accept_multiple_files=True)
        upl_previews = st.file_uploader("NÁHĽADY", type=['png','jpg','jpeg'], accept_multiple_files=True)

    if st.session_state.offer_items:
        st.divider()
        if st.button("🗑️ VYMAZAŤ CELÚ PONUKU"):
            st.session_state.offer_items = []
            st.rerun()
        for idx, item in enumerate(st.session_state.offer_items):
            if st.button(f"Zmazať {item['kod']} ({item['v']})", key=f"del_{idx}"):
                st.session_state.offer_items.pop(idx)
                st.rerun()

# --- 4. ZOSTAVENIE HTML VÝSTUPU ---
html_logos = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}">' for f in upl_logos]) if upl_logos else ""
html_previews = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}">' for f in upl_previews]) if upl_previews else ""

table_rows = ""
t_items = 0
t_brand = 0

if st.session_state.offer_items:
    df_items = pd.DataFrame(st.session_state.offer_items)
    groups = df_items.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state.offer_items[idx]
            pz = it['p'] * (1 - it['z']/100)
            row_sum = it['ks'] * (pz + it['br'])
            t_items += (it['ks'] * pz)
            t_brand += (it['ks'] * it['br'])
            row_html = "<tr>"
            if i == 0:
                img = it['img'] if it['img'] != 'nan' and it['img'] != "" else ""
                row_html += f'<td rowspan="{g_size}" class="img-cell"><img src="{img}"></td>'
            row_html += f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td><td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{it['br']:.2f} €</td><td>{row_sum:.2f} €</td></tr>"
            table_rows += row_html
            idx += 1

sum_vat_base = t_items + t_brand

doc_html = f"""
<div class="paper">
    <div class="header"><img src="data:image/png;base64,{logo_main_b64 if logo_main_b64 else ''}"></div>
    <div class="main-title">PONUKA</div>

    <div class="info-grid">
        <div class="info-left"><b>ODBERATEĽ :</b><br>{c_firma}<br>{c_adresa}<br>{c_osoba}</div>
        <div class="info-right">
            <b>PLATNOSŤ PONUKY DO :</b><br>{c_platnost.strftime('%d. %m. %Y')}<br><br>
            <b>PREDPOKLADANÁ DOBA DODANIA :</b><br>{c_dodanie}<br>
            <span style="font-size:9px; font-style:italic;">od schválenia vzoriek</span><br><br>
            <b>VYPRACOVAL :</b><br>{c_vypracoval}
        </div>
    </div>

    <div class="section-header">POLOŽKY</div>
    <table class="items-table">
        <thead>
            <tr><th style="width:80px">Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th></tr>
        </thead>
        <tbody>{table_rows if table_rows else "<tr><td colspan='10'>Žiadne položky</td></tr>"}</tbody>
    </table>

    <div class="summary-wrapper">
        <table class="summary-table">
            <tr><td>Suma položiek bez DPH:</td><td>{t_items:.2f} €</td></tr>
            <tr><td>Branding celkom bez DPH:</td><td>{t_brand:.2f} €</td></tr>
            <tr style="font-weight:bold;"><td>Základ DPH:</td><td>{sum_vat_base:.2f} €</td></tr>
            <tr><td>DPH (23%):</td><td>{sum_vat_base * 0.23:.2f} €</td></tr>
            <tr class="total-row"><td>CELKOM S DPH:</td><td>{sum_vat_base * 1.23:.2f} €</td></tr>
        </table>
    </div>

    <div class="section-header">BRANDING</div>
    <div class="branding-row">
        <div style="flex:1"><b>Technológia</b><br>{b_tech}</div>
        <div style="flex:2"><b>Popis</b><br>{b_desc if b_desc else "..."}</div>
        <div class="text-right" style="flex:1"><b>Dodanie vzorky</b><br>{b_date.strftime('%d. %m. %Y')}</div>
    </div>

    <div class="graphics-row">
        <div class="graphic-col"><div class="section-header">LOGO KLIENTA</div><div class="graphic-box">{html_logos}</div></div>
        <div class="graphic-col"><div class="section-header">NÁHĽAD GRAFIKY</div><div class="graphic-box">{html_previews}</div></div>
    </div>

    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
</div>
"""

# ZOBRAZENIE
st.html(doc_html)

# TLAČ
if st.button("🖨️ Tlačiť ponuku", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)