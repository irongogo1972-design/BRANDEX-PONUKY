# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. NASTAVENIA STRÁNKY A CSS ---
st.set_page_config(page_title="BRANDEX Ponuka", layout="wide")

st.markdown("""
    <style>
    @media screen {
        .paper {
            background: white;
            width: 210mm;
            min-height: 297mm;
            padding: 15mm;
            margin: 10px auto;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
    }
    @media print {
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"] {
            display: none !important;
        }
        .paper { margin: 0 !important; box-shadow: none !important; width: 100% !important; padding: 0 !important; }
        .stMarkdown { margin: 0 !important; }
    }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { border: 1px solid #333; padding: 6px; text-align: center; font-size: 11px; }
    th { background-color: #f2f2f2; font-weight: bold; }
    .img-cell { width: 80px; }
    .footer-text { font-size: 9px; text-align: center; margin-top: 30px; border-top: 1px solid #000; padding-top: 5px; line-height: 1.2; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAČÍTANIE DÁT ---
@st.cache_data
def load_data():
    if not os.path.exists("produkty.xlsx"):
        return pd.DataFrame()
    try:
        df = pd.read_excel("produkty.xlsx", engine="openpyxl")
        # Mapovanie stĺpcov: A=0, F=5, G=6, H=7, N=13, Q=16
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except:
        return pd.DataFrame()

df = load_data()

# Inicializácia session state
if 'items' not in st.session_state: st.session_state.items = []

# --- 3. OVLÁDACÍ PANEL (SIDEBAR) ---
with st.sidebar:
    st.header("🛒 Pridať tovar")
    if not df.empty:
        model = st.selectbox("Produkt", sorted(df['SKUPINOVY_NAZOV'].unique()))
        sub_df = df[df['SKUPINOVY_NAZOV'] == model]
        
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        size_df = sub_df[sub_df['FARBA'] == farba]
        
        velkosti = st.multiselect("Veľkosti", sorted(size_df['SIZE'].unique()))
        
        pocet = st.number_input("Počet kusov", min_value=1, value=1, step=1)
        zlava = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for v in velkosti:
                row = size_df[size_df['SIZE'] == v].iloc[0]
                img_url = str(row['IMG_PRODUCT']) if str(row['IMG_PRODUCT']) != 'nan' else ""
                
                new_item = {
                    "kod": row['KOD_IT'],
                    "n": model,
                    "f": farba,
                    "v": v,
                    "ks": pocet,
                    "p": float(row['PRICE']),
                    "z": zlava,
                    "img": img_url
                }
                st.session_state.items.append(new_item)
            st.rerun()
    
    st.divider()
    if st.button("🗑️ Vymazať všetko"):
        st.session_state.items = []
        st.rerun()

# --- 4. TVORBA VIZUÁLU A4 ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# Hlavička s logom
c1, c2, c3 = st.columns([1,2,1])
with c2:
    if os.path.exists("brandex_logo.png"):
        st.image("brandex_logo.png")

# Názov a Klient
st.markdown("<br>", unsafe_allow_html=True)
off_title = st.text_input("", "CENOVÁ PONUKA", key="t", help="Názov", label_visibility="collapsed")
st.markdown(f"<h1 style='text-align: center; margin-top:0;'>{off_title}</h1>", unsafe_allow_html=True)

col_k1, col_k2 = st.columns([1,1])
with col_k1:
    st.markdown("**Pre koho:**")
    c_firma = st.text_input("Firma", "Názov firmy", label_visibility="collapsed")
    c_adr = st.text_input("Adresa", "Adresa", label_visibility="collapsed")
    c_meno = st.text_input("Zástupca", "Meno zástupcu", label_visibility="collapsed")

# TABUĽKA POLOŽIEK
if st.session_state.items:
    # Zoskupenie pre rowspan (Model + Farba)
    items_df = pd.DataFrame(st.session_state.items)
    
    html = """<table><thead><tr>
        <th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Suma</th>
    </tr></thead><tbody>"""
    
    # Logika pre rowspan
    groups = items_df.groupby(['n', 'f'], sort=False).size().tolist()
    curr_idx = 0
    total_sum = 0

    for g_size in groups:
        for i in range(g_size):
            item = st.session_state.items[curr_idx]
            cena_ks = item['p'] * (1 - item['z']/100)
            suma_riadok = item['ks'] * cena_ks
            total_sum += suma_riadok
            
            html += "<tr>"
            # Obrázok len pre prvý riadok v skupine
            if i == 0:
                img_tag = f'<img src="{item["img"]}" width="50">' if item["img"] else ""
                html += f'<td rowspan="{g_size}" class="img-cell">{img_tag}</td>'
            
            html += f"""
                <td>{item['kod']}</td>
                <td>{item['n']}</td>
                <td>{item['f']}</td>
                <td>{item['v']}</td>
                <td>{item['ks']}</td>
                <td>{item['p']:.2f} €</td>
                <td>{item['z']}%</td>
                <td>{suma_riadok:.2f} €</td>
            </tr>"""
            curr_idx += 1
            
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: right;'>Celkom bez DPH: {total_sum:.2f} €</h4>", unsafe_allow_html=True)

# BRANDING SEKCE
st.divider()
st.subheader("Branding")
bc1, bc2, bc3 = st.columns([2,2,1])
with bc1:
    b_typ = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    b_popis = st.text_area("Popis a umiestnenie", placeholder="Napr. Výšivka loga na ľavé prsia, cca 8cm")
with bc2:
    b_cena = st.number_input("Cena za branding celkom €", min_value=0.0, value=0.0)
    b_logo = st.file_uploader("Nahrať logo klienta", type=['png', 'jpg'])
with bc3:
    if b_logo: st.image(b_logo, width=100)

# TERMÍNY
st.divider()
tc1, tc2, tc3 = st.columns(3)
with tc1: st.date_input("Termín vzorky")
with tc2: st.date_input("Termín dodania")
with tc3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

# PÄTA
st.markdown("""
    <div class="footer-text">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- FIXNÉ TLAČIDLO TLAČE ---
st.markdown("""
    <div class="no-print" style="position: fixed; bottom: 20px; right: 20px;">
        <button onclick="window.print()" style="padding: 10px 20px; background: #ff4b4b; color: white; border: none; border-radius: 5px; cursor: pointer;">
            🖨️ TLAČIŤ PONUKU (PDF)
        </button>
    </div>
    """, unsafe_allow_html=True)