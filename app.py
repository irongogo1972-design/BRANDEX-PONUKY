# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- 1. NASTAVENIA STRÁNKY A CSS PRE TLAČ ---
st.set_page_config(page_title="BRANDEX - Tvorba ponuky", layout="wide")

st.markdown("""
    <style>
    /* Simulácia A4 na obrazovke */
    .reportview-container .main .block-container {
        padding-top: 0rem;
    }
    
    @media screen {
        .paper {
            background: white;
            width: 210mm;
            min-height: 297mm;
            padding: 20mm;
            margin: 10px auto;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
    }

    /* Nastavenia pre tlač */
    @media print {
        header, footer, .stSidebar, .stButton, .no-print {
            display: none !important;
        }
        .paper {
            margin: 0 !important;
            box-shadow: none !important;
            width: 100% !important;
            padding: 0 !important;
        }
        body {
            background-color: white !important;
        }
    }

    .centered { text-align: center; }
    .title-input { font-size: 24px !important; font-weight: bold !important; text-align: center !important; border: none !important; background: transparent !important; }
    .footer-text { font-size: 10px; color: #555; text-align: center; margin-top: 50px; border-top: 1px solid #eee; padding-top: 10px; }
    
    /* Tabuľka položiek */
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 12px; }
    th { background-color: #f8f9fa; }
    .img-cell { width: 80px; text-align: center; vertical-align: middle; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. NAČÍTANIE DÁT ---
@st.cache_data
def load_data():
    if not os.path.exists("produkty.xlsx"):
        return pd.DataFrame()
    df = pd.read_excel("produkty.xlsx", engine="openpyxl")
    # Premenovanie stĺpcov podľa indexov (A=0, F=5, G=6, H=7, N=13, Q=16)
    cols = df.columns
    df = df.rename(columns={
        cols[0]: "KOD_IT", 
        cols[5]: "SKUPINOVY_NAZOV", 
        cols[6]: "FARBA", 
        cols[7]: "SIZE", 
        cols[13]: "PRICE", 
        cols[16]: "IMG_PRODUCT"
    })
    return df

df = load_data()

# Inicializácia košíka a údajov
if 'offer_items' not in st.session_state: st.session_state.offer_items = []
if 'branding_logo' not in st.session_state: st.session_state.branding_logo = None

# --- 3. FORMULÁR PRE ZADÁVANIE (V SIDEBARE - no-print) ---
with st.sidebar:
    st.header("⚙️ Ovládací panel")
    st.write("Tu pridajte položky do ponuky")
    
    if not df.empty:
        model = st.selectbox("Vyberte model", sorted(df['SKUPINOVY_NAZOV'].unique()))
        sub_df = df[df['SKUPINOVY_NAZOV'] == model]
        
        farba = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
        velkosti = st.multiselect("Veľkosti", sorted(sub_df[sub_df['FARBA'] == farba]['SIZE'].unique()))
        
        pocet = st.number_input("Počet kusov", min_value=1, value=10)
        zlava = st.number_input("Zľava v %", min_value=0, max_value=100, value=0)
        
        if st.button("➕ Pridať do ponuky"):
            for v in velkosti:
                row = sub_df[(sub_df['FARBA'] == farba) & (sub_df['SIZE'] == v)].iloc[0]
                item = {
                    "kod": row['KOD_IT'],
                    "n": model,
                    "f": farba,
                    "v": v,
                    "ks": pocet,
                    "p": float(row['PRICE']),
                    "z": zlava,
                    "img": row['IMG_PRODUCT']
                }
                st.session_state.offer_items.append(item)
            st.rerun()

    if st.session_state.offer_items:
        if st.button("🗑️ Vymazať celú ponuku"):
            st.session_state.offer_items = []
            st.rerun()

# --- 4. SAMOTNÁ A4 PONUKA ---
st.markdown('<div class="paper">', unsafe_allow_html=True)

# Logo (Záhlavie)
col_l, col_c, col_r = st.columns([1,2,1])
with col_c:
    if os.path.exists("brandex_logo.png"):
        st.image("brandex_logo.png", use_container_width=True)

# Názov ponuky (editovateľný bez labelu)
offer_name = st.text_input("", placeholder="NÁZOV CENOVEJ PONUKY", key="off_title", help="Zadajte názov ponuky")
st.markdown(f"<h1 style='text-align: center; color: black; margin-top: -20px;'>{offer_name}</h1>", unsafe_allow_html=True)

# Údaje o klientovi
st.markdown("### Pre koho:")
c_firma = st.text_input("Názov firmy", "Firma s.r.o.", label_visibility="collapsed")
c_adresa = st.text_input("Adresa", "Ulica, Mesto", label_visibility="collapsed")
c_meno = st.text_input("Meno zástupcu", "Meno Priezvisko", label_visibility="collapsed")

# POLOŽKY PONUKY (TABUĽKA)
if st.session_state.offer_items:
    html_table = """<table>
        <tr>
            <th>Obrázok</th>
            <th>Kód</th>
            <th>Názov</th>
            <th>Farba</th>
            <th>Veľkosť</th>
            <th>Počet</th>
            <th>Cena/ks</th>
            <th>Zľava %</th>
            <th>Suma bez DPH</th>
        </tr>"""
    
    grand_total = 0
    # Logika zoskupovania obrázkov (zobraziť len raz pre rovnaký model+farbu)
    displayed_imgs = set()

    for idx, item in enumerate(st.session_state.offer_items):
        cena_po_zlave = item['p'] * (1 - item['z']/100)
        suma = item['ks'] * cena_po_zlave
        grand_total += suma
        
        img_key = f"{item['n']}_{item['f']}"
        img_html = ""
        if img_key not in displayed_imgs:
            img_html = f'<td rowspan="1" class="img-cell"><img src="{item["img"]}" width="60"></td>'
            displayed_imgs.add(img_key)
        else:
            img_html = '<td></td>' # Zjednodušené pre Streamlit tabuľku, rowspan v čistom MD/HTML je komplexnejší

        html_table += f"""
        <tr>
            <td class="img-cell"><img src="{item['img']}" width="60"></td>
            <td>{item['kod']}</td>
            <td>{item['n']}</td>
            <td>{item['f']}</td>
            <td>{item['v']}</td>
            <td>{item['ks']}</td>
            <td>{item['p']:.2f} €</td>
            <td>{item['z']}%</td>
            <td>{suma:.2f} €</td>
        </tr>
        """
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)
    st.markdown(f"<h3 style='text-align: right;'>Celkom k úhrade bez DPH: {grand_total:.2f} €</h3>", unsafe_allow_html=True)

# BRANDING
st.divider()
st.subheader("Branding")
b_col1, b_col2, b_col3 = st.columns([2,2,1])
with b_col1:
    b_typ = st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "Subli", "Tampoprint", "DTF", "DTG"])
    b_popis = st.text_area("Popis brandingu")
with b_col2:
    b_loc = st.text_input("Umiestnenie")
    b_cena = st.number_input("Cena za branding €", min_value=0.0, value=0.0)
with b_col3:
    b_logo = st.file_uploader("Nahrať logo", type=['png', 'jpg'])
    if b_logo:
        st.image(b_logo, width=100)

st.markdown(f"**Cena za branding celkom:** {b_cena:.2f} €")

# TERMÍNY
st.divider()
d_col1, d_col2, d_col3 = st.columns(3)
with d_col1: st.date_input("Termín dodania vzorky")
with d_col2: st.date_input("Termín dodania objednávky")
with d_col3: st.date_input("Platnosť ponuky", value=datetime.now() + timedelta(days=7))

# PÄTA
st.markdown(f"""
    <div class="footer-text">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- TLAČIDLO TLAČIŤ (Fixované v rohu) ---
st.markdown("""
    <script>
    function printOffer() {
        window.print();
    }
    </script>
    """, unsafe_allow_html=True)

if st.button("🖨️ Tlačiť ponuku", on_click=None):
    st.components.v1.html("""
        <script>
        window.parent.window.print();
        </script>
    """, height=0)