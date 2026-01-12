# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
import xml.etree.ElementTree as ET
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA AI ---
# Skúste "gemini-1.5-flash" (najstabilnejší pre free verzie)
MODEL_NAME = "gemini-1.5-flash" 

API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        st.error(f"Chyba AI konfigurácie: {e}")

FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. POSILNENÝ BRANDEX PARSER ---
@st.cache_data(ttl=3600)
def load_brandex_data():
    try:
        # Pridávame hlavičku (User-Agent), aby nás server Brandexu neblokoval
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(FEED_URL, headers=headers, timeout=45)
        
        # Brandex používa Windows-1250 (stredoeurópske kódovanie)
        content = response.content.decode('windows-1250', errors='replace')
        
        # Skúsime nájsť dáta pomocou ElementTree
        root = ET.fromstring(content)
        data = []
        
        # Hľadáme všetky uzly, ktoré by mohli byť produktom
        for node in root.iter():
            # Skontrolujeme, či tento uzol alebo jeho deti obsahujú KOD_IT
            kod_node = node.find('.//KOD_IT') or node.find('KOD_IT')
            if kod_node is not None:
                row = {}
                for child in node:
                    tag = child.tag.split('}')[-1] # Odstránenie prípadných menných priestorov
                    row[tag.upper()] = child.text.strip() if child.text else ""
                if row:
                    data.append(row)
        
        if not data:
            return pd.DataFrame(), content[:1000] # Vrátime prázdne a kúsok textu pre ladiaci výpis

        df = pd.DataFrame(data)

        # Premenovanie polí
        mapping = {
            'KOD_IT': 'kod',
            'NAZOV': 'n',
            'CENA_EU': 'p',
            'CENA_MO': 'p',
            'PRICE': 'p'
        }
        df = df.rename(columns=mapping)
        
        # Vyčistenie cien (čiarka -> bodka)
        if 'p' in df.columns:
            df['p'] = df['p'].astype(str).str.replace(',', '.')
            df['p'] = pd.to_numeric(df['p'], errors='coerce').fillna(0.0)
        
        return df, ""
    except Exception as e:
        return pd.DataFrame(), str(e)

# --- 3. PDF GENERÁTOR ---
class BrandexPDF(FPDF):
    def header(self):
        try: self.image("brandex_logo.png", 10, 8, 45)
        except: pass
        self.ln(20)

def generate_pdf(text):
    pdf = BrandexPDF()
    pdf.add_page()
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 11)
    except:
        pdf.set_font('helvetica', '', 11)
    pdf.multi_cell(0, 7, text)
    return pdf.output()

# --- 4. WEBOVÉ ROZHRANIE ---
st.set_page_config(page_title="Brandex AI Ponuky", layout="wide")

if 'basket' not in st.session_state: st.session_state.basket = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor")

# Načítanie dát
df, debug_info = load_brandex_data()

# SIDEBAR S ÚDAJMI O KLIENTOVI
with st.sidebar:
    st.header("👤 Klient")
    f_firma = st.text_input("Firma", "Vzorová Firma s.r.o.")
    f_osoba = st.text_input("Kontaktná osoba")
    f_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

# VÝBER PRODUKTU
tab1, tab2 = st.tabs(["🔍 Výber z katalógu", "➕ Pridať manuálne / z webu"])
curr_n, curr_kod, curr_p = "", "", 0.0

with tab1:
    if not df.empty:
        # Vytvorenie vyhľadávacieho poľa [KÓD] Názov
        df['display'] = "[" + df['kod'].astype(str) + "] " + df['n'].astype(str)
        items = sorted(df['display'].unique())
        vyber = st.selectbox("Hľadať produkt v Brandex katalógu", items)
        
        res = df[df['display'] == vyber]
        if not res.empty:
            r = res.iloc[0]
            curr_n, curr_kod, curr_p = r['n'], r['kod'], float(r.get('p', 0.0))
    else:
        st.error("❌ Katalóg je prázdny. Systém v XML nenašiel značku KOD_IT.")
        with st.expander("Ladiace informácie pre technika"):
            st.write("Výsledok spracovania:")
            st.code(debug_info)

with tab2:
    st.write("Tu môžete zadať údaje manuálne, ak ich nevidíte v katalógu.")
    m_kod = st.text_input("Kód tovaru (KOD_IT)", value=curr_kod)
    m_nazov = st.text_input("Názov produktu", value=curr_n)
    m_cena = st.number_input("Nákupná cena € bez DPH", value=curr_p, step=0.1)

final_n = m_nazov if m_nazov else curr_n
final_p = m_cena if m_cena > 0 else curr_p
final_kod = m_kod if m_kod else curr_kod

# NACENENIE
st.divider()
st.subheader(f"Nacenenie položky: {final_n}")
p1, p2, p3, p4 = st.columns(4)
with p1: marza = st.number_input("Vaša marža %", value=35)
with p2: ks = st.number_input("Počet kusov", min_value=1, value=100)
with p3: 
    brand = st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "DTF potlač", "Laser", "UV tlač", "Bez potlače"])
    b_cena = st.number_input("Cena za branding/ks €", value=1.2 if brand != "Bez potlače" else 0.0, step=0.05)
with p4:
    predaj = round((final_p * (1 + marza/100)) + b_cena, 2)
    st.write("Predajná cena:")
    st.subheader(f"{predaj} €/ks")
    if st.button("➕ PRIDAŤ DO PONUKY"):
        st.session_state.basket.append({"kod": final_kod, "n": final_n, "ks": ks, "p": predaj, "s": round(predaj*ks, 2), "b": brand})
        st.rerun()

# KOŠÍK A AI
if st.session_state.basket:
    st.divider()
    st.subheader("📋 Rozpracovaná ponuka")
    for i in st.session_state.basket:
        st.write(f"- **[{i['kod']}] {i['n']}** | {i['ks']}ks | {i['b']} | {i['p']}€/ks -> **{i['s']} €**")
    
    celkom = sum(i['s'] for i in st.session_state.basket)
    st.write(f"### Spolu bez DPH: {celkom:.2f} €")
    
    c_ai1, c_ai2 = st.columns(2)
    with c_ai1:
        if st.button("🗑️ Vymazať košík"):
            st.session_state.basket = []
            st.rerun()
    with c_ai2:
        if st.button("✨ VYGENEROVAŤ PONUKU POMOCOU AI"):
            if not API_KEY:
                st.error("Chýba API kľúč v Streamlit Secrets!")
            else:
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    prods = "\n".join([f"- {i['ks']}ks {i['n']} (kód: {i['kod']}), {i['b']}, {i['p']}€/ks" for i in st.session_state.basket])
                    prompt = f"Si obchodník firmy Brandex. Vytvor profesionálnu ponuku pre {f_firma}. Produkty:\n{prods}\nCelkom: {celkom}€ bez DPH. Jazyk: {f_jazyk}. Platnosť do: {f_platnost}."
                    response = model.generate_content(prompt)
                    st.session_state.ai_text = response.text
                except Exception as e:
                    st.error(f"Chyba AI: {e}")

if st.session_state.ai_text:
    st.divider()
    f_text = st.text_area("Finalizácia textu (môžete upraviť):", value=st.session_state.ai_text, height=300)
    pdf_data = generate_pdf(f_text)
    st.download_button("📥 Stiahnuť PDF ponuku", data=bytes(pdf_data), file_name=f"Ponuka_Brandex_{f_firma}.pdf")