# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. INICIALIZÁCIA PAMÄTE (Hneď na začiatku) ---
if 'items' not in st.session_state:
    st.session_state.items = []

# --- 2. NASTAVENIA STRÁNKY A ŠTÝLY ---
st.set_page_config(page_title="BRANDEX Creator", layout="wide")

st.markdown("""
    <style>
    /* Skrytie prvkov pri tlači */
    @media print {
        header, footer, .stSidebar, .stButton, .no-print, 
        [data-testid="stSidebarNav"], .stChatInput, .stChatMessage {
            display: none !important;
        }
        .paper {
            margin: 0 !important;
            box-shadow: none !important;
            width: 100% !important;
            padding: 0 !important;
        }
        .stMarkdown, .element-container, .stHorizontalBlock { margin: 0 !important; padding: 0 !important; }
        @page { size: A4; margin: 1cm; }
    }
    
    /* Vizuál papiera na obrazovke */
    @media screen {
        .paper {
            background: white;
            width: 210mm;
            min-height: 297mm;
            padding: 20mm;
            margin: 10px auto;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            color: black;
        }
    }

    .centered { text-align: center; }
    .title-text { font-size: 32px; font-weight: bold; text-align: center; margin-bottom: 20px; text-transform: uppercase; }
    
    /* Tabuľka ponuky */
    .quote-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    .quote-table th, .quote-table td { border: 1px solid black; padding: 6px; text-align: center; font-size: 12px; color: black; }
    .quote-table th { background-color: #f2f2f2; }
    .img-cell img { max-width: 60px; height: auto; }

    /* Päta */
    .footer-box { 
        font-size: 11px; 
        text-align: center; 
        margin-top: 50px; 
        border-top: 1px solid black; 
        padding-top: 10px; 
        line-height: 1.4;
        color: black;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel():
    if not os.path.exists("produkty.xlsx"):
        return pd.DataFrame()
    try:
        # A(0), F(5), G(6), H(7), N(13), Q(16)
        df = pd.read_excel("produkty.xlsx", engine="openpyxl")
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except:
        return pd.DataFrame()

df_db = load_excel()

# --- 4. OVLÁDACÍ PANEL (SIDEBAR - SKRYTÝ PRI TLAČI) ---
with st.sidebar:
    st.header("📦 Pridať tovar")
    if not df_db.empty:
        sel_model = st.selectbox("Model", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
        temp_df = df_db[df_db['SKUPINOVY_NAZOV'] == sel_model]
        
        sel_color = st.selectbox("Farba", sorted(temp_df['FARBA'].unique()))
        size_df = temp_df[temp_df['FARBA'] == sel_color]
        
        sel_sizes = st.multiselect("Veľkosti", sorted(size_df['SIZE'].unique()))
        
        sel_qty = st.number_input("Počet kusov", min_value=1, value=1)
        sel_discount = st.number_input("Zľava %", min_value=0, max_value=100, value=0)
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            for s in sel_sizes:
                row = size_df[size_df['SIZE'] == s].iloc[0]
                st.session_state.items.append({
                    "id": row['KOD_IT'], "name": sel_model, "color": sel_color, "size": s,
                    "qty": sel_qty, "price": float(row['PRICE']), "disc": sel_discount,
                    "img": str(row['IMG_PRODUCT'])
                })
            st.rerun()

    st.divider()
    if st.button("🗑️ Vymazať všetko"):
        st.session_state.items = []
        st.rerun()

# --- 5. A4 DOKUMENT ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# LOGO (Záhlavie)
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    if os.path.exists("brandex_logo.png"):
        st.image("brandex_logo.png", use_container_width=True)

# NÁZOV PONUKY
st.write("")
quote_title = st.text_input("Názov ponuky", "CENOVÁ PONUKA", label_visibility="collapsed")
st.markdown(f'<div class="title-text">{quote_title}</div>', unsafe_allow_html=True)

# PRE KOHO
st.markdown("**Pre koho:**")
k_col1, k_col2 = st.columns([1, 1])
with k_col1:
    f_firma = st.text_input("Názov firmy", "Firma s.r.o.", label_visibility="collapsed")
    f_adr = st.text_input("Adresa", "Adresa firmy", label_visibility="collapsed")
    f_meno = st.text_input("Meno zástupcu", "Meno a Priezvisko", label_visibility="collapsed")

# TABUĽKA POLOŽIEK
if st.session_state.items:
    df_items = pd.DataFrame(st.session_state.items)
    
    # HTML tabuľka s rowspan logikou
    html = '<table class="quote-table"><thead><tr>'
    html += '<th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Suma</th>'
    html += '</tr></thead><tbody>'
    
    # Zoskupovanie pre obrázok
    groups = df_items.groupby(['name', 'color'], sort=False).size().tolist()
    idx = 0
    total_quote = 0

    for g_size in groups:
        for i in range(g_size):
            it = st.session_state.items[idx]
            price_final = it['price'] * (1 - it['disc']/100)
            row_sum = it['qty'] * price_final
            total_quote += row_sum
            
            html += '<tr>'
            if i == 0:
                img_src = it['img'] if it['img'] != 'nan' else ''
                html += f'<td rowspan="{g_size}" class="img-cell"><img src="{img_src}"></td>'
            
            html += f"<td>{it['id']}</td><td>{it['name']}</td><td>{it['color']}</td><td>{it['size']}</td>"
            html += f"<td>{it['qty']}</td><td>{it['price']:.2f} €</td><td>{it['disc']}%</td><td>{row_sum:.2f} €</td></tr>"
            idx += 1
            
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: right;'>Celkom bez DPH: {total_quote:.2f} €</h3>", unsafe_allow_html=True)

# BRANDING
st.divider()
st.subheader("Branding")
b1, b2, b3 = st.columns([2, 2, 1])
with b1:
    b_type = st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    b_desc = st.text_area("Popis brandingu", placeholder="Popis technológie...")
with b_col2: # Oprava premennej z b2 na b_col2
    b_loc = st.text_input("Umiestnenie", placeholder="Umiestnenie loga")
    b_price = st.number_input("Cena za branding €", min_value=0.0, step=0.5)
with b3:
    b_logo = st.file_uploader("Nahrať logo klienta", type=['png', 'jpg'])
    if b_logo: st.image(b_logo, width=120)

st.markdown(f"**Cena za branding celkom:** {b_price:.2f} €")

# TERMÍNY
st.divider()
d1, d2, d3 = st.columns(3)
with d1: st.date_input("Termín vzorky")
with d2: st.date_input("Termín dodania")
with d3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

# PÄTA
st.markdown("""
    <div class="footer-text">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# TLAČIDLO TLAČE (Fixované)
st.markdown("""
    <div class="no-print" style="position: fixed; bottom: 20px; right: 20px;">
        <button onclick="window.print()" style="padding: 15px 30px; background: #ff4b4b; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
            🖨️ TLAČIŤ PONUKU / ULOŽIŤ PDF
        </button>
    </div>
    """, unsafe_allow_html=True)