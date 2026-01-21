# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import base64
import google.generativeai as genai
import json
from datetime import datetime, timedelta

# --- 1. POMOCNÉ FUNKCIE ---
@st.cache_data
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

# --- 2. AI EXTRAKCIA Z GARIS PDF (OPRAVENÁ VERZIA) ---
def extract_data_from_garis(uploaded_file):
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("Chýba API kľúč v Secrets!")
        return None
    
    try:
        genai.configure(api_key=api_key)
        # Používame model 1.5 Flash - najstabilnejší pre Free Tier
        # Voláme ho priamo názvom, aby sme sa vyhli 404 chybám
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        file_data = uploaded_file.getvalue()
        content = [{"mime_type": uploaded_file.type, "data": file_data}]
        
        prompt = """
        Analyzuj túto PDF ponuku zo systému GARIS. Vytiahni dáta a vráť ich v čistom JSON formáte.
        Polia:
        - firma (názov odberateľa)
        - adresa (kompletná adresa)
        - osoba (kontaktná osoba)
        - vypracoval (meno spracovateľa)
        - polozky (zoznam, kde každá má: kod, nazov, mnozstvo, cena_bez_dph)
        Kód identifikuj napr. ako 'B02E' alebo 'O82'.
        Vráť IBA čistý JSON bez markdown značiek (bez ```json).
        """
        
        response = model.generate_content([prompt, content[0]])
        text_response = response.text.strip()
        
        # Očistenie od markdown obalov pre istotu
        if text_response.startswith("```"):
            text_response = "\n".join(text_response.splitlines()[1:-1])
            
        return json.loads(text_response.strip())
    except Exception as e:
        st.error(f"AI Import zlyhal: {e}")
        return None

# Inicializácia pamäte (Session State)
if 'offer_items' not in st.session_state: st.session_state['offer_items'] = []
if 'client' not in st.session_state: 
    st.session_state['client'] = {"f": "", "a": "", "o": "", "p": datetime.now() + timedelta(days=14), "v": "", "d": "10-14 pracovných dní"}

# --- 3. NASTAVENIA STRÁNKY A CSS (WYSIWYG) ---
st.set_page_config(page_title="Brandex Creator PRO", layout="wide", initial_sidebar_state="expanded")

logo_main_b64 = get_base64_image("brandex_logo.PNG")

st.markdown(f"""
<style>
    [data-testid="stAppViewBlockContainer"] {{ padding: 0 !important; }}
    [data-testid="stHeader"] {{ display: none !important; }}
    
    .paper {{
        background: white; width: 210mm; min-height: 290mm;
        padding: 12mm 15mm; margin: 0 auto;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
        color: black; font-family: "Arial", sans-serif;
    }}

    @media print {{
        header, footer, .stSidebar, .stButton, .no-print, [data-testid="stSidebarNav"], .stFileUploader, .stDownloadButton {{
            display: none !important;
        }}
        .paper {{ margin: 0 !important; box-shadow: none !important; width: 100% !important; padding: 0 !important; }}
        .footer-box {{
            position: fixed; bottom: 0; left: 0; right: 0;
            text-align: center; border-top: 2px solid #FF8C00;
            padding: 5px 0; background: white; font-size: 8px;
        }}
        @page {{ size: A4; margin: 1cm; }}
    }}

    .header-logo {{ text-align: center; margin-bottom: 0px; }}
    .header-logo img {{ width: 220px; }}
    .main-title {{ font-size: 32px; font-weight: bold; text-align: center; text-transform: uppercase; margin: -10px 0 15px 0; }}
    .orange-line {{ border-top: 2px solid #FF8C00; margin: 8px 0; }}

    .info-grid {{ display: flex; justify-content: space-between; margin-top: 15px; font-size: 11px; }}
    .info-left {{ width: 55%; text-align: left; line-height: 1.2; }}
    .info-right {{ width: 40%; text-align: right; line-height: 1.2; }}
    .delivery-note {{ font-size: 9px; font-style: italic; color: #555; }}

    table.items-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; color: black; }}
    table.items-table th {{ background: #f2f2f2; border: 1px solid #ccc; padding: 5px; font-size: 9px; text-transform: uppercase; }}
    table.items-table td {{ border: 1px solid #ccc; padding: 4px; text-align: center; font-size: 10px; vertical-align: middle; }}
    .img-cell img {{ max-width: 80px; max-height: 110px; object-fit: contain; }}

    .summary-wrapper {{ display: flex; justify-content: flex-end; margin-top: 10px; }}
    .summary-table {{ width: 280px; border-collapse: collapse; border: none !important; }}
    .summary-table td {{ border: none !important; border-bottom: 1px solid #eee !important; padding: 3px 8px; text-align: right; font-size: 11px; }}
    .total-row {{ font-weight: bold; background: #fdf2e9; font-size: 13px !important; border-bottom: 2px solid #FF8C00 !important; }}

    .section-header {{ font-weight: bold; font-size: 13px; margin-top: 20px; text-transform: uppercase; }}
    .graphics-container {{ display: flex; justify-content: space-between; gap: 20px; margin-top: 10px; }}
    .graphic-col {{ width: 48%; border: 1px dashed #ccc; padding: 5px; text-align: center; min-height: 110px; display: flex; flex-direction: column; gap: 5px; align-items: center; }}
    .graphic-col img {{ max-width: 100%; max-height: 120px; }}

    .footer-box {{ font-size: 10px; text-align: center; border-top: 2px solid #FF8C00; margin-top: 30px; padding-top: 5px; line-height: 1.4; }}
</style>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR OVLÁDANIE ---
with st.sidebar:
    st.title("👔 Brandex Editor")
    
    # 1. IMPORT Z GARIS
    st.subheader("📄 Import z GARIS (PDF)")
    erp_file = st.file_uploader("Nahrajte PDF ponuku", type=['pdf'])
    if erp_file and st.button("🚀 IMPORTOVAŤ DÁTA"):
        with st.spinner("AI analyzuje GARIS dokument..."):
            extracted = extract_data_from_garis(erp_file)
            if extracted:
                st.session_state.client['f'] = extracted.get('firma', "")
                st.session_state.client['a'] = extracted.get('adresa', "")
                st.session_state.client['o'] = extracted.get('osoba', "")
                st.session_state.client['v'] = extracted.get('vypracoval', "")
                
                if os.path.exists("produkty.xlsx"):
                    df_db_full = pd.read_excel("produkty.xlsx", engine="openpyxl")
                    for p in extracted.get('polozky', []):
                        match = df_db_full[df_db_full.iloc[:, 0].astype(str).str.contains(str(p['kod']), na=False, case=False)]
                        img_url = str(match.iloc[0, 16]) if not match.empty else ""
                        st.session_state.offer_items.append({
                            "kod": p['kod'], "n": p['nazov'], "f": "", "v": "",
                            "ks": int(p['mnozstvo']), "p": float(p['cena_bez_dph']), "z": 0, "br": 0, "img": img_url
                        })
                st.success("Import úspešný!")
                st.rerun()

    st.divider()
    with st.expander("👤 Odberateľ a Termíny", expanded=False):
        c_firma = st.text_input("Firma", st.session_state.client['f'])
        c_adresa = st.text_area("Adresa", st.session_state.client['a'])
        c_osoba = st.text_input("Kontakt", st.session_state.client['o'])
        c_platnost = st.date_input("Platnosť", st.session_state.client['p'])
        c_dodanie = st.text_input("Doba dodania", st.session_state.client['d'])
        c_vypracoval = st.text_input("Vypracoval", st.session_state.client['v'])

    # 3. PRIDÁVANIE TOVARU
    if os.path.exists("produkty.xlsx"):
        df_db = pd.read_excel("produkty.xlsx", engine="openpyxl").iloc[:, [0, 5, 6, 7, 13, 16]]
        df_db.columns = ["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_PRODUCT"]
        
        with st.expander("➕ Pridať položky", expanded=True):
            model = st.selectbox("Produkt", sorted(df_db['SKUPINOVY_NAZOV'].unique()))
            sub = df_db[df_db['SKUPINOVY_NAZOV'] == model]
            farba = st.selectbox("Farba", sorted(sub['FARBA'].unique()))
            
            color_sub = sub[sub['FARBA'] == farba]
            suggested_img = str(color_sub['IMG_PRODUCT'].dropna().iloc[0]) if not color_sub['IMG_PRODUCT'].dropna().empty else ""

            velkosti = st.multiselect("Veľkosti", sort_sizes(color_sub['SIZE'].unique()))
            qty = st.number_input("Počet ks", 1, 5000, 1)
            disc = st.number_input("Zľava %", 0, 100, 0)
            br_u = st.number_input("Branding/ks €", 0.0, 50.0, 0.0)
            link_img = st.text_input("Link na obrázok", value=suggested_img)
            
            if st.button("PRIDAŤ DO TABUĽKY"):
                for s in velkosti:
                    row = color_sub[color_sub['SIZE'] == s].iloc[0]
                    st.session_state.offer_items.append({
                        "kod": row['KOD_IT'], "n": model, "f": farba, "v": s,
                        "ks": qty, "p": float(row['PRICE']), "z": disc, "br": br_u, "img": link_img
                    })
                st.rerun()

    with st.expander("🎨 Branding a Grafika", expanded=False):
        b_tech = st.selectbox("Technológia", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Subli", "Tampoprint"])
        b_desc = st.text_area("Popis")
        b_date = st.date_input("Dodanie vzorky", datetime.now())
        upl_logos = st.file_uploader("LOGÁ", type=['png','jpg','jpeg','pdf'], accept_multiple_files=True)
        upl_previews = st.file_uploader("NÁHĽADY", type=['png','jpg','jpeg','pdf'], accept_multiple_files=True)

    if st.session_state.offer_items:
        st.divider()
        if st.button("🗑️ VYMAZAŤ CELÚ PONUKU"):
            st.session_state.offer_items = []
            st.rerun()
        for idx, item in enumerate(st.session_state.offer_items):
            if st.button(f"Zmazať {item['kod']} ({item['v']})", key=f"del_{idx}"):
                st.session_state.offer_items.pop(idx)
                st.rerun()

# --- 5. ZOSTAVENIE HTML VÝSTUPU ---
def render_files(files):
    h = ""
    for f in files:
        if f.type == "application/pdf": h += f'<div style="font-size:10px">📄 {f.name} (PDF)</div>'
        else: h += f'<img src="data:image/png;base64,{base64.b64encode(f.getvalue()).decode()}">'
    return h

table_body = ""
t_items = 0
t_brand = 0
if st.session_state.offer_items:
    df_items = pd.DataFrame(st.session_state.offer_items)
    groups = df_items.groupby(['n', 'f'], sort=False).size().tolist()
    idx = 0
    for g_size in groups:
        for i in range(g_size):
            it = st.session_state.offer_items[idx]
            pz = it['p'] * (1 - it['z']/100)
            r_sum = it['ks'] * (pz + it['br'])
            t_items += (it['ks'] * pz)
            t_brand += (it['ks'] * it['br'])
            row = "<tr>"
            if i == 0:
                img = it['img'] if it['img'] != 'nan' else ""
                row += f'<td rowspan="{g_size}" class="img-cell"><img src="{img}"></td>'
            row += f"<td>{it['kod']}</td><td>{it['n']}</td><td>{it['f']}</td><td>{it['v']}</td><td>{it['ks']}</td><td>{it['p']:.2f} €</td><td>{it['z']}%</td><td>{it['br']:.2f} €</td><td>{r_sum:.2f} €</td></tr>"
            table_body += row
            idx += 1

sum_base = t_items + t_brand

# KONŠTRUKCIA FINÁLNEHO HTML
doc_html = f"""
<div class="paper">
    <div class="header-logo"><img src="data:image/png;base64,{logo_main_b64 if logo_main_b64 else ''}"></div>
    <div class="main-title">PONUKA</div>

    <div class="info-grid">
        <div class="info-left"><b>ODBERATEĽ :</b><br>{c_firma if c_firma else "................"}<br>{c_adresa if c_adresa else ""}<br>{c_osoba if c_osoba else ""}</div>
        <div class="info-right">
            <b>PLATNOSŤ PONUKY DO :</b><br>{c_platnost.strftime('%d. %m. %Y')}<br><br>
            <b>PREDPOKLADANÁ DOBA DODANIA :</b><br>{c_dodanie}<br>
            <span style="font-size:9px; font-style:italic; color:#555;">od schválenia vzoriek</span><br><br>
            <b>VYPRACOVAL :</b><br>{c_vypracoval if c_vypracoval else "................"}
        </div>
    </div>

    <div class="orange-line"></div>
    <div class="section-header">POLOŽKY</div>
    <table class="items-table">
        <thead><tr><th>Obrázok</th><th>Kód</th><th>Názov</th><th>Farba</th><th>Veľkosť</th><th>Počet</th><th>Cena/ks</th><th>Zľava</th><th>Branding</th><th>Suma bez DPH</th></tr></thead>
        <tbody>{table_body if table_body else "<tr><td colspan='10' style='text-align:center; padding:20px;'>Žiadne položky</td></tr>"}</tbody>
    </table>

    <div class="summary-wrapper">
        <table class="summary-table">
            <tr><td>Suma položiek bez DPH:</td><td>{t_items:.2f} €</td></tr>
            <tr><td>Branding celkom bez DPH:</td><td>{t_brand:.2f} €</td></tr>
            <tr style="font-weight:bold;"><td>Základ DPH:</td><td>{sum_base:.2f} €</td></tr>
            <tr><td>DPH (23%):</td><td>{sum_base * 0.23:.2f} €</td></tr>
            <tr class="total-row"><td>CELKOM S DPH:</td><td>{sum_base * 1.23:.2f} €</td></tr>
        </table>
    </div>

    <div class="orange-line"></div>
    <div class="section-header">BRANDING</div>
    <div style="display:flex; justify-content:space-between; font-size:11px; margin-top:5px;">
        <div style="flex:1"><b>Technológia</b><br>{b_tech}</div>
        <div style="flex:2"><b>Popis</b><br>{b_desc}</div>
        <div style="flex:1; text-align:right;"><b>Dodanie vzorky</b><br>{b_date.strftime('%d. %m. %Y')}</div>
    </div>

    <div class="graphics-row" style="display:flex; justify-content:space-between; gap:20px;">
        <div class="graphic-col"><div class="section-title">LOGO KLIENTA</div><div class="graphic-box" style="border:1px dashed #ccc; padding:5px; text-align:center; min-height:100px;">{render_files(upl_logos)}</div></div>
        <div class="graphic-col"><div class="section-title">NÁHĽAD GRAFIKY</div><div class="graphic-box" style="border:1px dashed #ccc; padding:5px; text-align:center; min-height:100px;">{render_files(upl_previews)}</div></div>
    </div>

    <div class="footer-box">
        BRANDEX, s.r.o., Narcisova 1, 821 01 Bratislava | Prevádzka: Stará vajnorská 37, 831 04 Bratislava<br>
        tel.: +421 2 55 42 12 47 | email: brandex@brandex.sk | www.brandex.sk
    </div>
</div>
"""

st.html(doc_html)

# TLAČIDLO TLAČE
st.write("")
if st.button("🖨️ Tlačiť ponuku", use_container_width=True):
    st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)