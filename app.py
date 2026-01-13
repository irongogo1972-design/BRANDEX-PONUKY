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
    return None

def sort_sizes(size_list):
    order = ['XXS', 'XS', 'S', 'M', 'L', 'XL', '2XL', '3XL', '4XL', '5XL', '6XL']
    return sorted(size_list, key=lambda x: order.index(x) if x in order else 99)

# Inicializácia pamäte
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. KONFIGURÁCIA A CSS ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")

logo_base64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
    <style>
    /* Reset Streamlit paddingov */
    [data-testid="stAppViewBlockContainer"] {{ padding-top: 1rem !important; }}

    @media screen {{
        .paper {{
            background: white; width: 210mm; min-height: 297mm;
            padding: 5mm 15mm; margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2); color: black;
        }}
    }}

    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"] {{
            display: none !important;
        }}
        .paper {{ 
            margin: 0 !important; box-shadow: none !important; width: 100% !important; 
            padding: 0 !important; padding-top: 10px !important; 
        }}
        .print-header {{
            position: relative; text-align: center; width: 100%;
            background: white; margin-bottom: -20px !important; /* Vytiahne názov hore */
        }}
        .footer-box {{
            position: fixed; bottom: 0; left: 0; right: 0;
            text-align: center; border-top: 1px solid black;
            padding: 5px 0; background: white; font-size: 9px;
        }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    /* Úprava nadpisu - Minimálna medzera */
    .centered-title-box {{ 
        text-align: center !important; margin: 0 auto; width: 100%;
        margin-top: -25px !important; 
    }}
    .centered-title-box input {{
        font-size: 26px !important; font-weight: bold !important;
        text-align: center !important; text-transform: uppercase;
        border: none !important; background: transparent !important; color: black !important;
    }}
    
    /* Extrémne kompaktný Odberateľ */
    .client-box {{ 
        font-size: 10px !important; color: black; 
        line-height: 1.0 !important; margin-top: 5px; 
    }}
    .client-box b {{ font-size: 11px; }}
    .client-box input {{ 
        font-size: 10px !important; height: 16px !important; 
        border: none !important; background: transparent !important;
        padding: 0 !important; margin: 0 !important;
    }}

    /* Tabuľka */
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; color: black; }}
    th, td {{ border: 1px solid black; padding: 3px; text-align: center; font-size: 10px; }}
    th {{ background-color: #f2f2f2; font-weight: bold; }}
    
    .img-cell {{ width: 100px; vertical-align: middle; padding: 2px; }}
    .img-cell img {{ max-width: 100%; height: auto; max-height: 250px; object-fit: contain; }}

    .summary-table {{ border: none !important; margin-top: 5px; float: right; width: 280px; }}
    .summary-table td {{ border: none !important; text-align: right; padding: 1px 5px; font-size: 11px; }}
    
    .processor-text {{ margin-top: 15px; font-size: 10px; text-align: right; font-style: italic; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        df = pd.read_excel(file, engine="openpyxl")
        # A, F, G, H, N, Q
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except: return pd.DataFrame()

df_db = load_excel()

# --- 4. SIDEBAR OVLÁDANIE ---
with st.sidebar:
    st.header("⚙️ Konfigurácia")
    proc = st.text_input("Ponuku vypracoval", placeholder="Meno")
    
    if not df_db.empty:
        st.subheader("📦 Pridať tovar")
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        sub_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        
        # Zoradené veľkosti
        avail_sizes = sub_df[sub_df['FARBA'] == farba]['SIZE'].unique()
        velkosti = st.multiselect("Veľkosti", sort_sizes(avail_sizes))
        
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        br_u = st.number_input("Branding / ks €", min_value=0.0, step=0.1, value=0.0)
        
        # VRÁTENÝ UPLOAD OBRÁZKA PRODUKTU
        st.write("---")
        custom_img = st.file_uploader("Vložiť vlastný obrázok k položke (prepíše Excel)", type=['png', 'jpg', 'jpeg'], key="prod_up")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            # Ak je nahraný obrázok, skonvertujeme ho na base64
            b64_custom = f"data:image/png;base64,{file_to_base64(custom_img)}" if custom_img else None
            
            for s in velkosti:
                row = sub_df[(sub_df['FARBA'] == farba) & (sub_df['SIZE'] == s)].iloc[0]
                # Priorita: 1. Upload, 2. Excel Q
                img_final = b64_custom if b64_custom else str(row['IMG_PRODUCT'])
                if not b64_custom and (img_final == 'nan' or not img_final.startswith('http')):
                    img_final = ""

                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc, 
                    "img": img_final, "br": br_u
                })
            st.rerun()

    st.divider()
    if st.session_state['offer_items']:
        st.subheader("🗑️ Správa")
        for idx, item in enumerate(st.session_state['offer_items']):
            if st.button(f"Zmazať {item['kod']}", key=f"del_{idx}"):
                st.session_state['offer_items'].pop(idx)
                st.rerun()

# --- 5. DOKUMENT ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# LOGO
if logo_base64:
    st.markdown(f'<div class="print-header"><img src="data:image/png;base64,{logo_base64}" width="220"></div>', unsafe_allow_html=True)

# NÁZOV (S negatívnym marginom pre minimálnu medzeru)
st.markdown('<div class="centered-title-box">', unsafe_allow_html=True)
st.text_input("", value="CENOVÁ PONUKA", key="main_title", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# ODBERATEĽ (Zmenšené riadkovanie a písmo)
st.markdown('<div class="client-box"><b>Odberateľ:</b>', unsafe_allow_html=True)
k1, k2 = st.columns([1, 1])
with k1:
    st.text_input("Firma", "Názov firmy", label_visibility="collapsed", key="cf")
    st.text_input("Adresa", "Adresa", label_visibility="collapsed", key="ca")
    st.text_input("Zástupca", "Meno zástupcu", label_visibility="collapsed", key="cm")
st.markdown('</div>', unsafe_allow_html=True)

# TABUĽKA
total_i_net = 0
total_b_net = 0
if st.session_state['offer_items']:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    html = '<table><thead><tr><th style="width:100px;">Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th></tr></thead><tbody>'
    
    groups = items_df.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state['offer_items'][idx]
            p_z = it['p'] * (1 - it['z']/100)
            row_tot = it['ks'] * (p_z + it['br'])
            total_i_net += (it['ks'] * p_z)
            total_b_net += (it['ks'] * it['br'])
            
            html += '<tr>'
            if i == 0:
                img_src = it['img'] if it['img'] else ""
                # Detekcia či ide o base64 alebo URL
                html += f'<td rowspan="{g_size}" class="img-cell"><img src="{img_src}"></td>'
            
            html += f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td><td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{it['br']:.2f} €</td><td>{row_tot:.2f} €</td></tr>"
            idx += 1
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

    # SUMÁR (DPH 23%)
    sum_z = total_i_net + total_b_net
    dph = sum_z * 0.23
    st.markdown(f"""
    <table class="summary-table">
        <tr><td>Suma položiek bez DPH:</td><td>{total_i_net:.2f} €</td></tr>
        <tr><td>Branding celkom bez DPH:</td><td>{total_b_net:.2f} €</td></tr>
        <tr><td><b>Základ DPH:</b></td><td><b>{sum_z:.2f} €</b></td></tr>
        <tr><td>DPH (23%):</td><td>{dph:.2f} €</td></tr>
        <tr style="background-color:#eee;"><td><b>CELKOM S DPH:</b></td><td><b>{sum_z + dph:.2f} €</b></td></tr>
    </table><div style="clear:both;"></div>
    """, unsafe_allow_html=True)

# BRANDING ŠPECIFIKÁCIA (Bottom)
st.divider()
st.subheader("Špecifikácia brandingu")
b1, b2, b3 = st.columns([2, 1, 1])
with b1:
    st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    st.text_area("Popis a umiestnenie loga", key="br_desc", height=70)
with b2:
    logo_br = st.file_uploader("Logo klienta pre branding", type=['png', 'jpg', 'jpeg'], key="br_logo")
with b3:
    if logo_br: st.image(logo_br, width=120)

# TERMÍNY
st.divider()
d1, d2, d3 = st.columns(3)
with d1: st.date_input("Termín vzorky")
with d2: st.date_input("Termín dodania")
with d3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

if proc:
    st.markdown(f'<div class="processor-text">Ponuku vypracoval: {proc}</div>', unsafe_allow_html=True)

# PÄTA
st.markdown("""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# TLAČIDLO TLAČE
st.markdown("""
    <div class="no-print" style="position: fixed; bottom: 20px; right: 20px; z-index: 9999;">
        <button onclick="window.parent.focus(); window.parent.print();" style="
            background-color: #ff4b4b; color: white; border: none;
            padding: 12px 25px; border-radius: 8px; font-weight: bold;
            cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        ">🖨️ TLAČIŤ PONUKU</button>
    </div>
    """, unsafe_allow_html=True)