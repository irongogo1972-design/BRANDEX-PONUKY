# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta

# --- 1. FUNKCIE PRE OBRÁZKY ---
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

# --- 2. INICIALIZÁCIA PAMÄTE ---
if 'offer_items' not in st.session_state: st.session_state['offer_items'] = []
if 'client_data' not in st.session_state: 
    st.session_state['client_data'] = {"firma": "", "adresa": "", "osoba": "", "platnost": datetime.now() + timedelta(days=14), "vypracoval": ""}
if 'branding_data' not in st.session_state:
    st.session_state['branding_data'] = {"tech": "Sieťotlač", "popis": "", "vzorka": datetime.now()}

# --- 3. NASTAVENIE STRÁNKY A CSS ---
st.set_page_config(page_title="BRANDEX Ponuka", layout="wide")

logo_b64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
<style>
    /* Odstránenie Streamlit lišty a okrajov */
    [data-testid="stHeader"], [data-testid="stToolbar"] {{ display: none !important; }}
    [data-testid="stAppViewBlockContainer"] {{ padding: 0 !important; }}

    /* WYSIWYG PAPIER */
    .paper {{
        background: white; width: 210mm; min-height: 297mm;
        padding: 15mm; margin: 20px auto;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        color: black; font-family: "Arial", sans-serif;
        display: flex; flex-direction: column;
    }}

    @media print {{
        .no-print, [data-testid="stSidebar"] {{ display: none !important; }}
        .paper {{ margin: 0 !important; box-shadow: none !important; width: 100% !important; }}
        @page {{ size: A4; margin: 0; }}
    }}

    /* HLAVIČKA */
    .header {{ text-align: center; margin-bottom: 20px; }}
    .header img {{ width: 250px; }}
    .header h1 {{ font-size: 32px; font-weight: bold; margin: -10px 0 0 0; text-transform: uppercase; }}

    /* INFO SEKCE (Grid layout vynúti stranu vedľa strany) */
    .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; margin-top: 20px; font-size: 12px; }}
    .info-right {{ text-align: right; }}

    /* TABUĽKA */
    .items-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }}
    .items-table th {{ background: #f2f2f2; border: 1px solid #ccc; padding: 6px; font-size: 11px; text-transform: uppercase; }}
    .items-table td {{ border: 1px solid #ccc; padding: 5px; text-align: center; font-size: 11px; vertical-align: middle; }}
    .img-cell img {{ max-width: 80px; max-height: 100px; object-fit: contain; }}

    /* REKAPITULÁCIA */
    .summary-wrapper {{ display: flex; justify-content: flex-end; margin-top: 10px; }}
    .summary-table {{ width: 280px; border-collapse: collapse; }}
    .summary-table td {{ border: 1px solid #eee; padding: 4px 8px; text-align: right; font-size: 12px; }}
    .total-row {{ background: #f9f9f9; font-weight: bold; font-size: 14px !important; }}

    /* BRANDING & GRAFIKA */
    .section-title {{ font-weight: bold; font-size: 14px; margin-top: 25px; border-bottom: 1px solid #000; padding-bottom: 3px; }}
    .branding-grid {{ display: grid; grid-template-columns: 1fr 2fr 1fr; gap: 10px; margin-top: 10px; font-size: 12px; }}
    .graphics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }}
    .graphic-box {{ border: 1px dashed #ccc; padding: 10px; text-align: center; min-height: 120px; }}
    .graphic-box img {{ max-width: 100%; max-height: 100px; }}

    /* PÄTA */
    .footer-box {{
        margin-top: auto; padding-top: 10px; border-top: 1px solid black;
        text-align: center; font-size: 10px; line-height: 1.4;
    }}
</style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR - VŠETKY VSTUPY TU ---
with st.sidebar:
    st.title("⚙️ Editor Ponuky")
    
    with st.expander("👤 Údaje Odberateľa", expanded=False):
        st.session_state.client_data["firma"] = st.text_input("Názov firmy", st.session_state.client_data["firma"])
        st.session_state.client_data["adresa"] = st.text_input("Adresa", st.session_state.client_data["adresa"])
        st.session_state.client_data["osoba"] = st.text_input("Kontaktná osoba", st.session_state.client_data["osoba"])
        st.session_state.client_data["platnost"] = st.date_input("Platnosť do", st.session_state.client_data["platnost"])
        st.session_state.client_data["vypracoval"] = st.text_input("Vypracoval (meno a email)", st.session_state.client_data["vypracoval"])

    # Načítanie Excelu
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
            link_img = st.text_input("Vlastný link na obrázok (voliteľné)")
            
            if st.button("PRIDAŤ DO TABUĽKY"):
                for s in velkosti:
                    row = sub[(sub['FARBA'] == farba) & (sub['SIZE'] == s)].iloc[0]
                    img = link_img if link_img else str(row['IMG_PRODUCT'])
                    st.session_state.offer_items.append({
                        "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                        "ks": qty, "p": float(row['PRICE']), "z": disc, "br": br_u, "img": img
                    })
                st.rerun()

    with st.expander("🎨 Branding a Grafika", expanded=False):
        st.session_state.branding_data["tech"] = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Subli"])
        st.session_state.branding_data["popis"] = st.text_area("Popis umiestnenia")
        st.session_state.branding_data["vzorka"] = st.date_input("Dodanie vzorky", st.session_state.branding_data["vzorka"])
        st.write("Nahrajte logá pre papier:")
        upl_logo = st.file_uploader("Logo klienta", type=['png','jpg','jpeg'])
        upl_prev = st.file_uploader("Náhľad grafiky", type=['png','jpg','jpeg'])

    if st.session_state.offer_items:
        st.divider()
        if st.button("🗑️ Vymazať celú ponuku"):
            st.session_state.offer_items = []
            st.rerun()
        for i, it in enumerate(st.session_state.offer_items):
            if st.sidebar.button(f"Zmazať {it['kod']} ({it['v']})", key=f"del_{i}"):
                st.session_state.offer_items.pop(i)
                st.rerun()

# --- 5. GENEROVANIE PAPIERA (Čisté HTML) ---
# Príprava obrázkov
b64_custom_logo = f"data:image/png;base64,{file_to_base64(upl_logo)}" if upl_logo else ""
b64_custom_prev = f"data:image/png;base64,{file_to_base64(upl_prev)}" if upl_prev else ""

html_content = f"""
<div class="paper">
    <div class="header">
        <img src="data:image/png;base64,{logo_b64 if logo_b64 else ''}">
        <h1>Ponuka</h1>
    </div>

    <div class="info-grid">
        <div class="info-left">
            <b>ODBERATEĽ :</b><br>
            {st.session_state.client_data['firma']}<br>
            {st.session_state.client_data['adresa']}<br>
            {st.session_state.client_data['osoba']}
        </div>
        <div class="info-right">
            <b>PLATNOSŤ PONUKY DO :</b><br>
            {st.session_state.client_data['platnost'].strftime('%d. %m. %Y')}<br><br>
            <b>VYPRACOVAL :</b><br>
            {st.session_state.client_data['vypracoval']}
        </div>
    </div>

    <div class="section-title">POLOŽKY</div>
    <table class="items-table">
        <thead>
            <tr>
                <th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th>
                <th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th>
            </tr>
        </thead>
        <tbody>
"""

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
            
            html_content += "<tr>"
            if i == 0:
                img_url = it['img'] if it['img'] != 'nan' else ""
                html_content += f'<td rowspan="{g_size}" class="img-cell"><img src="{img_url}"></td>'
            
            html_content += f"""
                <td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>
                <td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td>
                <td>{it['br']:.2f} €</td><td>{row_sum:.2f} €</td>
            </tr>"""
            idx += 1

sum_z = total_i + total_b
html_content += f"""
        </tbody>
    </table>

    <div class="summary-wrapper">
        <table class="summary-table">
            <tr><td>Suma položiek bez DPH:</td><td>{total_i:.2f} €</td></tr>
            <tr><td>Branding celkom bez DPH:</td><td>{total_b:.2f} €</td></tr>
            <tr class="total-row"><td>Základ DPH:</td><td>{sum_z:.2f} €</td></tr>
            <tr><td>DPH (23%):</td><td>{sum_z * 0.23:.2f} €</td></tr>
            <tr class="total-row"><td>CELKOM S DPH:</td><td>{sum_z * 1.23:.2f} €</td></tr>
        </table>
    </div>

    <div class="section-title">BRANDING</div>
    <div class="branding-grid">
        <div><b>Technológia</b><br>{st.session_state.branding_data['tech']}</div>
        <div><b>Popis</b><br>{st.session_state.branding_data['popis']}</div>
        <div><b>Dodanie vzorky</b><br>{st.session_state.branding_data['vzorka'].strftime('%d. %m. %Y')}</div>
    </div>

    <div class="graphics-grid">
        <div>
            <div class="section-title">LOGO KLIENTA</div>
            <div class="graphic-box">{"<img src='"+b64_custom_logo+"'>" if b64_custom_logo else ""}</div>
        </div>
        <div>
            <div class="section-title">NÁHĽAD GRAFIKY</div>
            <div class="graphic-box">{"<img src='"+b64_custom_prev+"'>" if b64_custom_prev else ""}</div>
        </div>
    </div>

    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
</div>
"""

# Zobrazenie výsledného HTML
st.markdown(html_content, unsafe_allow_html=True)

# Tlačidlo pre tlač
st.write("")
if st.button("🖨️ Tlačiť ponuku", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)