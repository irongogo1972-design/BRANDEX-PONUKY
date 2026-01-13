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

# Inicializácia pamäte
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. NASTAVENIA STRÁNKY A ŠTÝLY ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")

logo_base64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
    <style>
    /* RESET ŠTANDARDNÉHO STREAMLITU */
    [data-testid="stAppViewBlockContainer"] {{ padding-top: 2rem !important; }}

    @media screen {{
        .paper {{
            background: white; width: 210mm; min-height: 297mm;
            padding: 10mm 15mm; margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2); color: black;
        }}
    }}

    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"], .stFileUploadDropzone {{
            display: none !important;
        }}
        html, body {{ height: auto !important; background: white !important; }}
        .paper {{ 
            margin: 0 !important; box-shadow: none !important; width: 100% !important; 
            padding: 0 !important; display: block !important; height: auto !important;
            padding-top: 10px !important; /* Minimálna medzera zhora */
        }}
        
        /* Opakovanie loga na každej strane */
        .print-header {{
            position: relative; top: 0; text-align: center;
            width: 100%; background: white; margin-bottom: 0px;
        }}
        
        /* Päta na každej strane */
        .footer-box {{
            position: fixed; bottom: 0; left: 0; right: 0;
            text-align: center; border-top: 1px solid black;
            padding: 5px 0; background: white; font-size: 9px;
        }}
        @page {{ size: A4; margin: 1.5cm 1cm; }}
    }}

    /* ODSTRÁNENIE ŠEDÝCH BOXOV A CENTROVANIE NÁZVU */
    .stTextInput input, .stTextArea textarea {{
        border: none !important; background-color: transparent !important;
        padding: 0 !important; color: black !important;
    }}

    .centered-title-box {{ 
        text-align: center !important; margin: 0 auto; width: 100%; 
        margin-top: -10px !important; /* Posun názvu bližšie k logu */
    }}
    .centered-title-box input {{
        font-size: 28px !important; font-weight: bold !important;
        text-align: center !important; text-transform: uppercase;
    }}
    
    .client-box {{ font-size: 11px !important; color: black; margin-top: 10px; }}
    .client-box input {{ font-size: 11px !important; height: 16px !important; border: none !important; }}

    /* TABUĽKA */
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; color: black; table-layout: fixed; }}
    th, td {{ border: 1px solid black; padding: 4px; text-align: center; font-size: 10px; }}
    th {{ background-color: #f2f2f2; font-weight: bold; }}
    
    .img-cell {{ width: 100px; vertical-align: middle; }}
    .img-cell img {{ max-width: 100%; height: auto; max-height: 250px; object-fit: contain; }}

    .summary-table {{ border: none !important; margin-top: 5px; float: right; width: 280px; }}
    .summary-table td {{ border: none !important; text-align: right; padding: 1px 5px; font-size: 11px; }}
    
    .processor-text {{ margin-top: 20px; font-size: 11px; text-align: right; font-style: italic; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        df = pd.read_excel(file, engine="openpyxl")
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except: return pd.DataFrame()

df_db = load_excel()

# --- 4. SIDEBAR OVLÁDANIE ---
with st.sidebar:
    st.header("⚙️ Nastavenia")
    processor = st.text_input("Ponuku vypracoval", placeholder="Vaše meno")
    
    if not df_db.empty:
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        sub_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        
        # Zoraďovanie veľkostí
        avail_sizes = sub_df[sub_df['FARBA'] == farba]['SIZE'].unique()
        velkosti = st.multiselect("Veľkosti", sort_sizes(avail_sizes))
        
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        br_unit = st.number_input("Branding / ks €", min_value=0.0, step=0.1, value=0.0)
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in velkosti:
                row = sub_df[(sub_df['FARBA'] == farba) & (sub_df['SIZE'] == s)].iloc[0]
                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc, 
                    "img": str(row['IMG_PRODUCT']), "br": br_unit
                })
            st.rerun()

    st.divider()
    st.header("🗑️ Správa položiek")
    if st.session_state['offer_items']:
        for idx, item in enumerate(st.session_state['offer_items']):
            if st.button(f"Zmazať {item['kod']} ({item['v']})", key=f"d_{idx}"):
                st.session_state['offer_items'].pop(idx)
                st.rerun()

# --- 5. DOKUMENT ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# LOGO (Hlavička)
if logo_base64:
    st.markdown(f'<div class="print-header" style="text-align:center;"><img src="data:image/png;base64,{logo_base64}" width="220"></div>', unsafe_allow_html=True)

# NÁZOV (Minimálna medzera)
st.markdown('<div class="centered-title-box">', unsafe_allow_html=True)
st.text_input("", value="CENOVÁ PONUKA", key="main_title", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# PRE KOHO
st.markdown('<div class="client-box"><b>Pre koho:</b>', unsafe_allow_html=True)
k1, k2 = st.columns([1, 1])
with k1:
    st.text_input("Firma", "Názov firmy", label_visibility="collapsed", key="cf")
    st.text_input("Adresa", "Adresa", label_visibility="collapsed", key="ca")
    st.text_input("Zástupca", "Meno zástupcu", label_visibility="collapsed", key="cm")
st.markdown('</div>', unsafe_allow_html=True)

# TABUĽKA S BRANDINGOM
total_items_net = 0
total_brand_net = 0
if st.session_state['offer_items']:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    html = '<table><thead><tr><th style="width:100px;">Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th></tr></thead><tbody>'
    
    groups = items_df.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state['offer_items'][idx]
            p_after_z = it['p'] * (1 - it['z']/100)
            row_total = it['ks'] * (p_after_z + it['br'])
            
            total_items_net += (it['ks'] * p_after_z)
            total_brand_net += (it['ks'] * it['br'])
            
            html += '<tr>'
            if i == 0:
                img_url = it['img'] if it['img'] not in ['nan', 'None', ''] else ""
                html += f'<td rowspan="{g_size}" class="img-cell"><img src="{img_url}"></td>'
            
            html += f"""
                <td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>
                <td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td>
                <td>{it['br']:.2f} €</td><td>{row_total:.2f} €</td></tr>
            """
            idx += 1
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    # SUMÁR
    suma_zaklad = total_items_net + total_brand_net
    dph_v = suma_zaklad * 0.23
    st.markdown(f"""
    <table class="summary-table">
        <tr><td>Suma položiek bez DPH:</td><td>{total_items_net:.2f} €</td></tr>
        <tr><td>Branding celkom bez DPH:</td><td>{total_brand_net:.2f} €</td></tr>
        <tr><td><b>Základ DPH:</b></td><td><b>{suma_zaklad:.2f} €</b></td></tr>
        <tr><td>DPH (23%):</td><td>{dph_v:.2f} €</td></tr>
        <tr style="background-color:#eee;"><td><b>CELKOM S DPH:</b></td><td><b>{suma_zaklad + dph_v:.2f} €</b></td></tr>
    </table><div style="clear:both;"></div>
    """, unsafe_allow_html=True)

# BRANDING ŠPECIFIKÁCIA
st.divider()
st.subheader("Branding")
b1, b2, b3 = st.columns([2, 1, 1])
with b1:
    st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    st.text_area("Popis a umiestnenie", key="br_desc", height=70)
with b2:
    logo_upl = st.file_uploader("Nahrať logo klienta", type=['png', 'jpg', 'jpeg'])
with b3:
    if logo_upl: st.image(logo_upl, width=120)

# TERMÍNY
st.divider()
d1, d2, d3 = st.columns(3)
with d1: st.date_input("Termín dodania vzorky")
with d2: st.date_input("Termín dodania ponuky")
with d3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

if processor:
    st.markdown(f'<div class="processor-text">Ponuku vypracoval: {processor}</div>', unsafe_allow_html=True)

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
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)