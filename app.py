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

# --- 2. NASTAVENIA STRÁNKY ---
st.set_page_config(page_title="Brandex Creator", layout="wide", initial_sidebar_state="expanded")

logo_main_b64 = get_base64_image("brandex_logo.PNG")

# --- 3. SIDEBAR (VŠETKY VSTUPY SÚ TU) ---
with st.sidebar:
    st.title("👔 Brandex Editor")
    
    with st.expander("👤 Odberateľ a Spracovateľ", expanded=False):
        c_firma = st.text_input("Firma", "Názov firmy")
        c_adresa = st.text_area("Adresa", "Ulica, Mesto")
        c_osoba = st.text_input("Kontakt", "Meno kontaktnej osoby")
        c_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
        c_vypracoval = st.text_input("Ponuku vypracoval", "Vaše meno a email")

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
            link_img = st.text_input("Vlastný link na obrázok (voliteľné)")
            
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
        b_tech = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Subli", "Tampoprint"])
        b_desc = st.text_area("Popis brandingu")
        b_date = st.date_input("Dodanie vzorky", datetime.now())
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

# --- 4. ZOSTAVENIE HTML DOKUMENTU ---
# Logá a náhľady
html_logos = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}" style="max-width:100%; max-height:120px; display:block; margin:5px auto;">' for f in upl_logos]) if upl_logos else ""
html_previews = "".join([f'<img src="data:image/png;base64,{file_to_base64(f)}" style="max-width:100%; max-height:120px; display:block; margin:5px auto;">' for f in upl_previews]) if upl_previews else ""

# Tabuľka Položiek
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
            r_sum = it['ks'] * (pz + it['br'])
            t_items += (it['ks'] * pz)
            t_brand += (it['ks'] * it['br'])
            
            table_rows += "<tr>"
            if i == 0:
                img_url = it['img'] if it['img'] != 'nan' else ""
                table_rows += f'<td rowspan="{g_size}" style="width:85px; text-align:center; border:1px solid #ccc;"><img src="{img_url}" style="max-width:75px; max-height:100px;"></td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["kod"]}</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["n"]}</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["f"]}</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["v"]}</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["ks"]}</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["p"]:.2f} €</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["z"]}%</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{it["br"]:.2f} €</td>'
            table_rows += f'<td style="border:1px solid #ccc; padding:4px; text-align:center;">{r_sum:.2f} €</td></tr>'
            idx += 1

sum_vat_base = t_items + t_brand

# KONŠTRUKCIA CELÉHO HTML
final_html = f"""
<div style="background: white; width: 210mm; min-height: 290mm; padding: 15mm; margin: 0 auto; color: black; font-family: Arial, sans-serif; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
    
    <!-- HLAVIČKA -->
    <div style="text-align: center;">
        <img src="data:image/png;base64,{logo_main_b64 if logo_main_b64 else ''}" style="width:220px;">
        <h1 style="font-size: 32px; font-weight: bold; text-transform: uppercase; margin: -5px 0 20px 0;">Ponuka</h1>
    </div>

    <!-- ODBERATEĽ A PLATNOSŤ -->
    <div style="display: flex; justify-content: space-between; font-size: 12px; margin-top: 20px;">
        <div style="width: 55%;">
            <b>ODBERATEĽ :</b><br>
            {c_firma}<br>{c_adresa}<br>{c_osoba}
        </div>
        <div style="width: 40%; text-align: right;">
            <b>PLATNOSŤ PONUKY DO :</b><br>
            {c_platnost.strftime('%d. %m. %Y')}<br><br>
            <b>VYPRACOVAL :</b><br>
            {c_vypracoval}
        </div>
    </div>

    <!-- POLOŽKY -->
    <div style="font-weight: bold; font-size: 13px; margin-top: 25px; border-bottom: 2px solid #FF8C00; padding-bottom: 3px; text-transform: uppercase;">Položky</div>
    <table style="width: 100%; border-collapse: collapse; margin-top: 10px; color: black;">
        <thead style="background: #f2f2f2;">
            <tr>
                <th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th>
                <th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th>
            </tr>
        </thead>
        <tbody>
            {table_rows if table_rows else "<tr><td colspan='10' style='text-align:center; padding:20px;'>Žiadne položky</td></tr>"}
        </tbody>
    </table>

    <!-- SUMÁR -->
    <div style="display: flex; justify-content: flex-end; margin-top: 10px;">
        <table style="width: 280px; border-collapse: collapse; font-size: 12px;">
            <tr><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">Suma položiek bez DPH:</td><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">{t_items:.2f} €</td></tr>
            <tr><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">Branding celkom bez DPH:</td><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">{t_brand:.2f} €</td></tr>
            <tr style="font-weight: bold;"><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">Základ DPH:</td><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">{sum_vat_base:.2f} €</td></tr>
            <tr><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">DPH (23%):</td><td style="text-align: right; padding: 3px 8px; border-bottom: 1px solid #eee;">{sum_vat_base * 0.23:.2f} €</td></tr>
            <tr style="font-weight: bold; background: #fdf2e9; border-bottom: 2px solid #FF8C00;"><td style="text-align: right; padding: 5px 8px;">CELKOM S DPH:</td><td style="text-align: right; padding: 5px 8px;">{sum_vat_base * 1.23:.2f} €</td></tr>
        </table>
    </div>

    <!-- BRANDING -->
    <div style="font-weight: bold; font-size: 13px; margin-top: 25px; border-bottom: 2px solid #FF8C00; padding-bottom: 3px; text-transform: uppercase;">Branding</div>
    <div style="display: flex; justify-content: space-between; gap: 20px; margin-top: 10px; font-size: 12px;">
        <div style="flex: 1;"><b>Technológia</b><br>{b_tech}</div>
        <div style="flex: 2;"><b>Popis</b><br>{b_desc if b_desc else "..."}</div>
        <div style="flex: 1; text-align: right;"><b>Dodanie vzorky</b><br>{b_date.strftime('%d. %m. %Y')}</div>
    </div>

    <!-- GRAFIKA -->
    <div style="display: flex; justify-content: space-between; gap: 20px; margin-top: 20px;">
        <div style="width: 48%;">
            <div style="font-weight: bold; font-size: 12px; border-bottom: 1px solid #ccc; margin-bottom: 5px;">LOGO KLIENTA</div>
            <div style="border: 1px dashed #ccc; padding: 10px; min-height: 120px; text-align: center;">{html_logos}</div>
        </div>
        <div style="width: 48%;">
            <div style="font-weight: bold; font-size: 12px; border-bottom: 1px solid #ccc; margin-bottom: 5px;">NÁHĽAD GRAFIKY</div>
            <div style="border: 1px dashed #ccc; padding: 10px; min-height: 120px; text-align: center;">{html_previews}</div>
        </div>
    </div>

    <!-- PÄTA -->
    <div style="margin-top: auto; padding-top: 10px; border-top: 2px solid #FF8C00; text-align: center; font-size: 10px; line-height: 1.4; color: #333;">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
</div>
"""

# ZOBRAZENIE (Tento riadok je kľúčový pre WYSIWYG)
st.html(final_html)

# TLAČIDLO PRE TLAČ
st.write("")
if st.button("🖨️ TLAČIŤ PONUKU", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)