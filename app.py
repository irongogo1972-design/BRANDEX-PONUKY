# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA STRÁNKY A ŠTÝLY ---
st.set_page_config(page_title="BRANDEX Ponuka", layout="wide")

# CSS pre simuláciu A4 a centrovanie prvkov
st.markdown("""
    <style>
    /* Skrytie štandardných Streamlit prvkov pri tlači */
    @media print {
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"] {
            display: none !important;
        }
        .paper {
            margin: 0 !important;
            box-shadow: none !important;
            width: 100% !important;
            padding: 0 !important;
        }
        .stMarkdown, .element-container { margin: 0 !important; }
        @page { size: A4; margin: 0; }
    }
    
    /* Vizuál papiera na obrazovke */
    @media screen {
        .paper {
            background: white;
            width: 210mm;
            min-height: 297mm;
            padding: 15mm;
            margin: 10px auto;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
            color: black;
        }
    }

    /* Tabuľka */
    table { width: 100%; border-collapse: collapse; margin-top: 15px; }
    th, td { border: 1px solid black; padding: 5px; text-align: center; font-size: 11px; color: black; }
    th { background-color: #f2f2f2; }
    
    /* Päta */
    .footer-text { 
        font-size: 10px; 
        text-align: center; 
        margin-top: 40px; 
        border-top: 1px solid black; 
        padding-top: 10px; 
        line-height: 1.3; 
        color: black;
    }
    
    /* Vycentrovanie loga */
    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAČÍTANIE DÁT Z EXCELU ---
@st.cache_data
def load_data():
    file_path = "produkty.xlsx"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        # Výber stĺpcov: A(0), F(5), G(6), H(7), N(13), Q(16)
        df = df.iloc[:, [0, 5, 6, 7, 13, 16]]
        df.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        return df
    except:
        return pd.DataFrame()

df = load_data()

# Inicializácia košíka v pamäti
if 'items' not in st.session_state:
    st.session_state.items = []

# --- 3. BOČNÝ PANEL (Vstup dát) ---
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
        
        if st.button("➕ PRIDAŤ"):
            for v in velkosti:
                row = size_df[size_df['SIZE'] == v].iloc[0]
                img_url = str(row['IMG_PRODUCT']) if str(row['IMG_PRODUCT']) != 'nan' else ""
                
                st.session_state.items.append({
                    "kod": row['KOD_IT'], "n": model, "f": farba, "v": v,
                    "ks": pocet, "p": float(row['PRICE']), "z": zlava, "img": img_url
                })
            st.rerun()
    
    st.divider()
    if st.button("🗑️ Vymazať všetko"):
        st.session_state.items = []
        st.rerun()

# --- 4. HLAVNÝ DOKUMENT (A4) ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# LOGO - Úplne hore a vycentrované
logo_path = "brandex_logo.png"
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h1 style='text-align:center;'>BRANDEX</h1>", unsafe_allow_html=True)

# NÁZOV PONUKY
off_title = st.text_input("", "CENOVÁ PONUKA", key="t", label_visibility="collapsed")
st.markdown(f"<h1 style='text-align: center; margin-top:0; font-size: 32px;'>{off_title}</h1>", unsafe_allow_html=True)

# ÚDAJE O KLIENTOVI
col_k1, col_k2 = st.columns([1,1])
with col_k1:
    st.markdown("**Pre koho:**")
    st.text_input("Firma", "Názov firmy", label_visibility="collapsed")
    st.text_input("Adresa", "Adresa", label_visibility="collapsed")
    st.text_input("Zástupca", "Meno zástupcu", label_visibility="collapsed")

# TABUĽKA POLOŽIEK (Ochrana pred ValueError)
if len(st.session_state.items) > 0:
    # DataFrame vytvoríme len vtedy, ak zoznam nie je prázdny
    items_df = pd.DataFrame(st.session_state.items)
    
    html = """<table><thead><tr>
        <th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Suma</th>
    </tr></thead><tbody>"""
    
    # Skupinové zobrazenie (rowspan)
    counts = items_df.groupby(['n', 'f'], sort=False).size().tolist()
    curr_idx = 0
    total_sum = 0

    for g_size in counts:
        for i in range(g_size):
            item = st.session_state.items[curr_idx]
            cena_po_zlave = item['p'] * (1 - item['z']/100)
            riadok_suma = item['ks'] * cena_po_zlave
            total_sum += riadok_suma
            
            html += "<tr>"
            if i == 0:
                img_src = f'<img src="{item["img"]}" width="50">' if item["img"] else ""
                html += f'<td rowspan="{g_size}">{img_src}</td>'
            
            html += f"""
                <td>{item['kod']}</td><td>{item['n']}</td><td>{item['f']}</td>
                <td>{item['v']}</td><td>{item['ks']}</td><td>{item['p']:.2f} €</td>
                <td>{item['z']}%</td><td>{riadok_suma:.2f} €</td>
            </tr>"""
            curr_idx += 1
            
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown(f"<h4 style='text-align: right;'>Celkom bez DPH: {total_sum:.2f} €</h4>", unsafe_allow_html=True)

# BRANDING
st.divider()
st.subheader("Branding")
bc1, bc2, bc3 = st.columns([2,2,1])
with bc1:
    st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    st.text_area("Popis a umiestnenie", placeholder="Zadajte detaily brandingu...")
with bc2:
    st.number_input("Cena za branding celkom €", min_value=0.0, step=0.5)
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

# TLAČIDLO (Len na obrazovke)
st.markdown("""
    <div class="no-print" style="position: fixed; bottom: 20px; right: 20px;">
        <button onclick="window.print()" style="padding: 15px 30px; background: #ff4b4b; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
            🖨️ TLAČIŤ / ULOŽIŤ PDF
        </button>
    </div>
    """, unsafe_allow_html=True)