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

if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 2. NASTAVENIA STRÁNKY A CSS PRE LAYOUT ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")
logo_base64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
    <style>
    [data-testid="stAppViewBlockContainer"] {{ padding-top: 1rem !important; }}
    
    @media screen {{
        .paper {{
            background: white; width: 210mm; min-height: 297mm;
            padding: 10mm 15mm; margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2); color: black;
            font-family: 'Arial', sans-serif;
        }}
    }}

    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"], .stFileUploader {{
            display: none !important;
        }}
        .paper {{ 
            margin: 0 !important; box-shadow: none !important; width: 100% !important; 
            padding: 0 !important; padding-top: 0 !important;
        }}
        .footer-box {{
            position: fixed; bottom: 0; left: 0; right: 0;
            text-align: center; border-top: 3px solid #ff9933;
            padding: 10px 0; background: white; font-size: 10px;
        }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    /* HLAVIČKA */
    .header-box {{ text-align: center; margin-bottom: 0px; }}
    .main-title {{ font-size: 34px; font-weight: bold; margin-top: -10px; margin-bottom: 30px; text-align: center; }}

    /* INFO SEKCOA (PRE / PLATNOSŤ) */
    .info-row {{ display: flex; justify-content: space-between; margin-bottom: 20px; font-size: 13px; }}
    .client-data {{ line-height: 1.2; }}
    
    /* TABUĽKA */
    .orange-line {{ border-top: 3px solid #ff9933; margin-top: 5px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; color: black; }}
    th {{ background-color: #f2f2f2; font-weight: bold; border: 1px solid #ddd; padding: 6px; font-size: 11px; }}
    td {{ border: 1px solid #ddd; padding: 6px; text-align: center; font-size: 11px; }}
    .img-cell img {{ max-width: 60px; max-height: 60px; object-fit: contain; }}

    /* SUMÁR */
    .summary-box {{ float: right; width: 300px; margin-top: 10px; border-collapse: collapse; }}
    .summary-box td {{ border: none; text-align: right; padding: 3px; font-size: 13px; }}
    .total-row {{ font-weight: bold; font-size: 18px !important; border-top: 2px solid black !important; }}

    /* BOXY PRE LOGO A NÁHĽAD */
    .graphic-box {{ border: 1px dashed #ccc; height: 100px; width: 100%; display: flex; justify-content: center; align-items: center; overflow: hidden; }}
    .graphic-box img {{ max-height: 90px; max-width: 100%; }}
    
    /* POZNÁMKY */
    .notes-box {{ border: 1px solid #ddd; border-radius: 5px; padding: 10px; background-color: #f9f9f9; margin-top: 20px; min-height: 60px; }}
    
    .stTextInput input {{ border: none !important; background: transparent !important; padding: 0 !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAČÍTANIE DÁT ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        df = pd.read_excel(file, engine="openpyxl")
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]] # A, F, G, H, N, Q
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except: return pd.DataFrame()

df_db = load_excel()

# --- 4. SIDEBAR OVLÁDANIE ---
with st.sidebar:
    st.header("⚙️ Správa položiek")
    proc_name = st.text_input("Vypracoval", placeholder="Vaše meno")
    
    if not df_db.empty:
        st.subheader("➕ Pridať tovar")
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        sub_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        velkosti = st.multiselect("Veľkosti", sort_sizes(sub_df[sub_df['FARBA'] == farba]['SIZE'].unique()))
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        br_u = st.number_input("Branding / ks €", min_value=0.0, step=0.1, value=0.0)
        img_l = st.text_input("Vlastný link na obrázok", placeholder="https://...")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in velkosti:
                row = sub_df[(sub_df['FARBA'] == farba) & (sub_df['SIZE'] == s)].iloc[0]
                img_f = img_l if img_l else str(row['IMG_PRODUCT'])
                if img_f == 'nan' or not img_f.startswith('http'): img_f = ""
                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc, "br": br_u, "img": img_f
                })
            st.rerun()

    if st.session_state['offer_items']:
        st.divider()
        if st.button("🗑️ VYMAZAŤ CELÚ PONUKU"):
            st.session_state['offer_items'] = []
            st.rerun()

# --- 5. VIZUÁL A4 ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# LOGO A NÁZOV
if logo_base64:
    st.markdown(f'<div class="header-box"><img src="data:image/png;base64,{logo_base64}" width="280"></div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">PONUKA</div>', unsafe_allow_html=True)

# PRE / PLATNOSŤ
c_l, c_r = st.columns([2, 1])
with c_l:
    st.markdown("<b>PRE :</b>", unsafe_allow_html=True)
    st.text_input("Firma", "Názov firmy", key="f1", label_visibility="collapsed")
    st.text_input("Meno", "Meno kontaktnej osoby", key="f2", label_visibility="collapsed")
    st.text_input("Email", "email@klient.sk", key="f3", label_visibility="collapsed")
with c_r:
    st.markdown("<div style='text-align:right;'><b>Platnosť ponuky do</b></div>", unsafe_allow_html=True)
    st.date_input("Dátum", value=datetime.now() + timedelta(days=14), label_visibility="collapsed")

# POLOŽKY
st.markdown("<div class='orange-line'></div>", unsafe_allow_html=True)
st.markdown("<b>POLOŽKY</b>", unsafe_allow_html=True)

total_net = 0
total_br = 0
if st.session_state['offer_items']:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    html = """<table><thead><tr>
        <th>Obrázok</th><th>Poř.</th><th>Názov</th><th>Kód</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Celkom</th><th>Branding</th>
    </tr></thead><tbody>"""
    
    for idx, it in enumerate(st.session_state['offer_items']):
        price_disc = it['p'] * (1 - it['z']/100)
        row_total = it['ks'] * price_disc
        total_net += row_total
        total_br += (it['ks'] * it['br'])
        
        img_tag = f'<img src="{it["img"]}">' if it["img"] else ""
        html += f"""<tr>
            <td class="img-cell">{img_tag}</td>
            <td>{idx+1}</td>
            <td>{it['n']}</td>
            <td>{it['kod']}</td>
            <td>{it['f']}</td>
            <td>{it['v']}</td>
            <td>{it['ks']}</td>
            <td>{price_disc:.2f} €</td>
            <td>{row_total:.2f}</td>
            <td>{it['br']:.2f} €</td>
        </tr>"""
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

    # SUMÁR
    subtotal = total_net + total_br
    tax = subtotal * 0.23
    grand_total = subtotal + tax
    
    st.markdown(f"""
    <table class="summary-box">
        <tr><td>Medzisúčet:</td><td><b>{subtotal:.2f} €</b></td></tr>
        <tr><td>DPH (23%):</td><td>{tax:.2f} €</td></tr>
        <tr class="total-row"><td>CELKOM:</td><td>{grand_total:.2f} €</td></tr>
    </table><div style="clear:both;"></div>
    """, unsafe_allow_html=True)

# BRANDING
st.markdown("<div class='orange-line'></div>", unsafe_allow_html=True)
st.markdown("<b>BRANDING</b>", unsafe_allow_html=True)
b_c1, b_c2, b_c3 = st.columns([1, 2, 1])
with b_c1:
    st.markdown("<small>Technológia</small>", unsafe_allow_html=True)
    st.selectbox("T", ["Sieťotlač", "Výšivka", "Subli", "DTF", "Tampoprint"], label_visibility="collapsed")
with b_c2:
    st.markdown("<small>Popis</small>", unsafe_allow_html=True)
    st.text_area("P", placeholder="Umiestnenie, farby...", label_visibility="collapsed", height=65)
with b_c3:
    st.markdown("<small>Dodanie vzorky</small>", unsafe_allow_html=True)
    st.date_input("V", label_visibility="collapsed")

# LOGO / NÁHĽAD
st.write("")
g_c1, g_c2 = st.columns(2)
with g_c1:
    st.markdown("<b>LOGO</b>", unsafe_allow_html=True)
    l_up = st.file_uploader("L", accept_multiple_files=True, label_visibility="collapsed")
    st.markdown('<div class="graphic-box">', unsafe_allow_html=True)
    if l_up: st.image(l_up[0], width=150)
    st.markdown('</div>', unsafe_allow_html=True)
with g_c2:
    st.markdown("<b>NÁHĽAD</b>", unsafe_allow_html=True)
    n_up = st.file_uploader("N", accept_multiple_files=True, label_visibility="collapsed")
    st.markdown('<div class="graphic-box">', unsafe_allow_html=True)
    if n_up: st.image(n_up[0], width=150)
    st.markdown('</div>', unsafe_allow_html=True)

# POZNÁMKY
st.write("")
st.markdown("<b>Poznámky:</b>", unsafe_allow_html=True)
st.markdown('<div class="notes-box">', unsafe_allow_html=True)
st.text_area("Pozn", value="Termín dodania do 30 dní", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# VYPRACCOVAL
st.write("")
v1, v2 = st.columns([2, 1])
with v2:
    st.markdown("<div style='text-align:right;'><b>Vypracoval</b><br><br>__________________________</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:right; font-size:12px;'>{proc_name}</div>", unsafe_allow_html=True)

# PÄTA
st.markdown(f"""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# TLAČIDLO TLAČE
if st.button("🖨️ Tlačiť ponuku"):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)