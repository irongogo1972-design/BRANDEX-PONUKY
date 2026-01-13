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

# Inicializácia pamäte
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. KONFIGURÁCIA STRÁNKY A ŠTÝLY ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")

logo_base64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
    <style>
    /* Štýl pre obrazovku */
    @media screen {{
        .paper {{
            background: white;
            width: 210mm;
            min-height: 297mm;
            padding: 10mm 15mm;
            margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            color: black;
        }}
    }}

    /* Štýl pre TLAČ (A4) */
    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"] {{
            display: none !important;
        }}
        .paper {{ 
            margin: 0 !important; 
            box-shadow: none !important; 
            width: 100% !important; 
            padding: 0 !important;
            padding-top: 100px !important; 
            padding-bottom: 80px !important; 
        }}
        .print-header {{
            position: fixed;
            top: 0; left: 0; right: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 90px;
            background: white;
            z-index: 1000;
        }}
        .footer-box {{
            position: fixed;
            bottom: 0; left: 0; right: 0;
            text-align: center;
            border-top: 1px solid black;
            padding: 10px 0;
            background: white;
            font-size: 10px;
            z-index: 1000;
        }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    /* Centrovaný logo a nadpis */
    .centered-content {{
        text-align: center !important;
        width: 100%;
        margin-bottom: 10px;
    }}
    
    .centered-title-box input {{
        font-size: 26px !important;
        font-weight: bold !important;
        text-align: center !important;
        border: none !important;
        background-color: transparent !important;
        color: black !important;
        width: 100%;
    }}
    
    /* Malé údaje o klientovi */
    .client-box {{ font-size: 12px !important; color: black; line-height: 1.2; }}
    .client-box input {{ font-size: 12px !important; border: none !important; padding: 1px 0 !important; height: 24px !important; }}

    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; color: black; }}
    th, td {{ border: 1px solid black; padding: 4px; text-align: center; font-size: 10px; }}
    th {{ background-color: #f2f2f2; font-weight: bold; }}
    
    .img-cell img {{ max-width: 60px; max-height: 60px; object-fit: contain; }}
    .footer-box {{ font-size: 10px; line-height: 1.3; color: black; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        df = pd.read_excel(file, engine="openpyxl")
        # Stĺpce A, F, G, H, N, Q
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except:
        return pd.DataFrame()

df_db = load_excel()

# --- 4. SIDEBAR (OVLÁDACÍ PANEL) ---
with st.sidebar:
    st.header("📦 Pridať položku")
    if not df_db.empty:
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        temp_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        farba = st.selectbox("Farba", sorted(temp_df['FARBA'].unique()))
        size_df = temp_df[temp_df['FARBA'] == farba]
        velkosti = st.multiselect("Veľkosti", sorted(size_df['SIZE'].unique()))
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        
        st.write("---")
        # Odkaz na obrázok produktu (URL)
        custom_img_url = st.text_input("Link na obrázok produktu (voliteľné)", placeholder="https://...")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in velkosti:
                row = size_df[size_df['SIZE'] == s].iloc[0]
                # Ak je zadaný link, použije sa ten, inak stĺpec Q
                img_to_use = custom_img_url if custom_img_url else str(row['IMG_PRODUCT'])
                
                if img_to_use == 'nan' or not img_to_use.startswith('http'):
                    img_to_use = ""

                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc,
                    "img": img_to_use
                })
            st.rerun()

    st.divider()
    if st.button("🗑️ Vymazať ponuku"):
        st.session_state['offer_items'] = []
        st.rerun()

# --- 5. VIZUÁL PONUKY (A4) ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# HLAVIČKA - Logo v strede
if logo_base64:
    st.markdown(f'<div class="print-header"><img src="data:image/png;base64,{logo_base64}" width="260"></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="print-header"><h2>BRANDEX</h2></div>', unsafe_allow_html=True)

# NÁZOV PONUKY - Vycentrovaný
st.markdown('<div class="centered-title-box">', unsafe_allow_html=True)
st.text_input("", value="CENOVÁ PONUKA", key="main_title", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# PRE KOHO (Menšie písmo)
st.markdown('<div class="client-box"><b>Pre koho:</b>', unsafe_allow_html=True)
k1, k2 = st.columns([1, 1])
with k1:
    st.text_input("Firma", "Názov firmy", label_visibility="collapsed", key="c_firm")
    st.text_input("Adresa", "Adresa", label_visibility="collapsed", key="c_adr")
    st.text_input("Zástupca", "Meno zástupcu", label_visibility="collapsed", key="c_rep")
st.markdown('</div>', unsafe_allow_html=True)

# TABUĽKA POLOŽIEK
total_qty = 0
total_items_sum = 0
if len(st.session_state['offer_items']) > 0:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    html = '<table><thead><tr><th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava %</th><th>Suma</th></tr></thead><tbody>'
    
    # Logika zoskupovania pre Rowspan
    groups = items_df.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state['offer_items'][idx]
            final_p = it['p'] * (1 - it['z']/100)
            row_sum = it['ks'] * final_p
            total_items_sum += row_sum
            total_qty += it['ks']
            
            html += '<tr>'
            if i == 0:
                img_tag = f'<img src="{it["img"]}">' if it["img"] else ""
                html += f'<td rowspan="{g_size}" class="img-cell">{img_tag}</td>'
            
            html += f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td><td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{row_sum:.2f} €</td></tr>"
            idx += 1
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

# BRANDING
st.divider()
st.subheader("Branding")
b1, b2, b3 = st.columns([2, 2, 1])
with b1:
    st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    st.text_area("Popis a umiestnenie", key="brand_desc", height=80)
with b2:
    brand_unit_price = st.number_input("Cena za branding na 1ks €", min_value=0.0, step=0.1, value=0.0)
    logo_upl = st.file_uploader("Nahrať logo pre branding", type=['png', 'jpg', 'jpeg'], key="logo_br")
with b3:
    if logo_upl: st.image(logo_upl, width=120)

total_brand_price = total_qty * brand_unit_price

# SUMÁR A DPH (23%)
st.divider()
suma_zaklad = total_items_sum + total_brand_price
dph_hodnota = suma_zaklad * 0.23
suma_s_dph = suma_zaklad + dph_hodnota

r1, r2 = st.columns([3, 2])
with r2:
    st.markdown(f"""
    <table style="border: none; margin-top: 0;">
        <tr><td style="border:none; text-align:left;">Suma položky:</td><td style="border:none; text-align:right;">{total_items_sum:.2f} €</td></tr>
        <tr><td style="border:none; text-align:left;">Branding ({total_qty} ks):</td><td style="border:none; text-align:right;">{total_brand_price:.2f} €</td></tr>
        <tr><td style="border:none; text-align:left;"><b>Základ DPH:</b></td><td style="border:none; text-align:right;"><b>{suma_zaklad:.2f} €</b></td></tr>
        <tr><td style="border:none; text-align:left;">DPH (23%):</td><td style="border:none; text-align:right;">{dph_hodnota:.2f} €</td></tr>
        <tr style="background-color:#eee;"><td style="border:none; text-align:left;"><b>CELKOM S DPH:</b></td><td style="border:none; text-align:right;"><b>{suma_s_dph:.2f} €</b></td></tr>
    </table>
    """, unsafe_allow_html=True)

# TERMÍNY
st.divider()
d1, d2, d3 = st.columns(3)
with d1: st.date_input("Termín dodania vzorky")
with d2: st.date_input("Termín dodania objednávky")
with d3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

# PÄTA
st.markdown("""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- TLAČIDLO TLAČE ---
if st.button("🖨️ Tlačiť ponuku"):
    st.components.v1.html("<script>window.parent.window.print();</script>", height=0)