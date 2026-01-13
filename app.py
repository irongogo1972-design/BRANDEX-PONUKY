# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import base64
from datetime import datetime, timedelta

# --- 1. FUNKCIA NA PREVOD OBRÁZKA DO BASE64 (Zabezpečí zobrazenie loga) ---
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

# --- 2. INICIALIZÁCIA PAMÄTE ---
if 'offer_items' not in st.session_state:
    st.session_state['offer_items'] = []

# --- 3. KONFIGURÁCIA STRÁNKY A ŠTÝLY ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")

logo_base64 = get_base64_image("brandex_logo.png")

st.markdown(f"""
    <style>
    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"] {{
            display: none !important;
        }}
        .paper {{ 
            margin: 0 !important; 
            box-shadow: none !important; 
            width: 100% !important; 
            padding: 0 !important; 
        }}
        /* Päta na každej strane */
        .footer-box {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            border-top: 1px solid black;
            padding: 10px 0;
            background: white;
        }}
        @page {{ size: A4; margin: 1.5cm; }}
        .stMarkdown, .element-container {{ margin: 0 !important; padding: 0 !important; }}
    }}
    
    @media screen {{
        .paper {{
            background: white;
            width: 210mm;
            min-height: 297mm;
            padding: 20mm;
            margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            color: black;
            position: relative;
        }}
        .footer-box {{
            margin-top: 50px;
            border-top: 1px solid black;
            padding-top: 10px;
            text-align: center;
        }}
    }}

    /* Vycentrovanie názvu ponuky */
    .centered-title input {{
        font-size: 32px !important;
        font-weight: bold !important;
        text-align: center !important;
        border: none !important;
        background-color: transparent !important;
        width: 100%;
    }}
    
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; color: black; }}
    th, td {{ border: 1px solid black; padding: 6px; text-align: center; font-size: 12px; }}
    th {{ background-color: #f2f2f2; }}
    
    .footer-box {{ font-size: 11px; line-height: 1.4; color: black; }}
    </style>
    """, unsafe_allow_html=True)

# --- 4. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    file = "produkty.xlsx"
    if not os.path.exists(file): return pd.DataFrame()
    try:
        # A=0, F=5, G=6, H=7, N=13, Q=16
        df = pd.read_excel(file, engine="openpyxl")
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except:
        return pd.DataFrame()

df_db = load_excel()

# --- 5. OVLÁDACÍ PANEL (SIDEBAR) ---
with st.sidebar:
    st.header("⚙️ Správa položiek")
    if not df_db.empty:
        model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        temp_df = df_db[df_db['SKUPINOVY_NAZOV'] == model]
        
        farba = st.selectbox("Farba", sorted(temp_df['FARBA'].unique()))
        size_df = temp_df[temp_df['FARBA'] == farba]
        
        velkosti = st.multiselect("Vyberte veľkosti", sorted(size_df['SIZE'].unique()))
        
        qty = st.number_input("Počet kusov", min_value=1, value=1)
        disc = st.number_input("Zľava pre klienta %", min_value=0, max_value=100, value=0)
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in velkosti:
                row = size_df[size_df['SIZE'] == s].iloc[0]
                st.session_state['offer_items'].append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                    "ks": qty, "p": float(row['PRICE']), "z": disc,
                    "img": str(row['IMG_PRODUCT'])
                })
            st.rerun()

    st.divider()
    if st.button("🗑️ Vymazať celú ponuku"):
        st.session_state['offer_items'] = []
        st.rerun()

# --- 6. A4 DOKUMENT ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# LOGO - Centrované pomocou Base64
if logo_base64:
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{logo_base64}" width="300">
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("<h2 style='text-align: center;'>BRANDEX</h2>", unsafe_allow_html=True)

# NÁZOV PONUKY - Vycentrovaný
st.markdown('<div class="centered-title">', unsafe_allow_html=True)
st.text_input("", value="CENOVÁ PONUKA", key="main_title", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# PRE KOHO
st.markdown("### Pre koho:")
k1, k2 = st.columns([1, 1])
with k1:
    st.text_input("Firma", "Názov firmy", label_visibility="collapsed", key="c_firm")
    st.text_input("Adresa", "Adresa", label_visibility="collapsed", key="c_adr")
    st.text_input("Zástupca", "Meno zástupcu", label_visibility="collapsed", key="c_rep")

# TABUĽKA POLOŽIEK
total_qty = 0
total_items_sum = 0
if len(st.session_state['offer_items']) > 0:
    items_df = pd.DataFrame(st.session_state['offer_items'])
    
    html = '<table><thead><tr>'
    html += '<th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava %</th><th>Suma</th>'
    html += '</tr></thead><tbody>'
    
    # Zoskupovanie pre rowspan (rovnaký model + farba = jeden obrázok)
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
                img_url = it['img'] if it['img'] != 'nan' and it['img'] != 'None' else ""
                html += f'<td rowspan="{g_size}"><img src="{img_url}" width="60"></td>'
            
            html += f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td>"
            html += f"<td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{row_sum:.2f} €</td></tr>"
            idx += 1
            
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

# BRANDING
st.divider()
st.subheader("Branding")
b1, b2, b3 = st.columns([2, 2, 1])
with b1:
    st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    st.text_area("Popis a umiestnenie", key="brand_desc")
with b2:
    brand_unit_price = st.number_input("Cena brandingu na 1ks €", min_value=0.0, step=0.1, value=0.0)
    logo_upl = st.file_uploader("Nahrať logo klienta", type=['png', 'jpg'])
with b3:
    if logo_upl: st.image(logo_upl, width=120)

total_brand_price = total_qty * brand_unit_price

# SUMÁR A DPH
st.divider()
suma_zaklad = total_items_sum + total_brand_price
dph_hodnota = suma_zaklad * 0.23
suma_s_dph = suma_zaklad + dph_hodnota

r1, r2 = st.columns([3, 2])
with r2:
    st.markdown(f"""
    | Popis | Suma |
    | :--- | :--- |
    | Suma tovar a branding: | {suma_zaklad:.2f} € |
    | **Základ DPH:** | **{suma_zaklad:.2f} €** |
    | DPH (23%): | {dph_hodnota:.2f} € |
    | **CELKOM S DPH:** | **{suma_s_dph:.2f} €** |
    """, unsafe_allow_html=True)

# TERMÍNY
st.divider()
d1, d2, d3 = st.columns(3)
with d1: st.date_input("Termín dodania vzorky")
with d2: st.date_input("Termín dodania ponuky")
with d3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

# PÄTA (Zobrazená v aplikácii aj pri tlači)
st.markdown("""
    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- FIXNÉ TLAČIDLO TLAČE ---
if st.button("🖨️ Tlačiť ponuku"):
    st.components.v1.html("""
        <script>
        window.parent.window.print();
        </script>
    """, height=0)