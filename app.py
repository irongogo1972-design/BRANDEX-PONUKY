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
# Skúste "gemini-1.5-flash" (stabilný) alebo "gemini-2.0-flash" (najnovší)
MODEL_NAME = "gemini-1.5-flash" 

API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        st.error(f"Chyba pripojenia: {e}")
else:
    st.error("⚠️ Chýba API kľúč v Streamlit Secrets!")

FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. BRANDEX PARSER ---
@st.cache_data(ttl=3600)
def load_brandex_data():
    try:
        response = requests.get(FEED_URL, timeout=30)
        content = response.content.decode('windows-1250', errors='replace')
        root = ET.fromstring(content)
        data = []
        for node in root.findall('.//*'):
            if node.find('KOD_IT') is not None:
                row = {}
                for child in node:
                    tag = child.tag.upper().strip()
                    val = child.text.strip() if child.text else ""
                    row[tag] = val
                data.append(row)
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)
        mapping = {'KOD_IT': 'kod', 'NAZOV': 'n', 'CENA_EU': 'p'}
        df = df.rename(columns=mapping)
        if 'p' in df.columns:
            df['p'] = df['p'].astype(str).str.replace(',', '.')
            df['p'] = pd.to_numeric(df['p'], errors='coerce').fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Chyba feedu: {e}")
        return pd.DataFrame()

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

df = load_brandex_data()

# ÚDAJE O KLIENTOVI
with st.container():
    st.subheader("📝 Údaje o klientovi")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_firma = st.text_input("Firma / Klient", "Vzorová Firma s.r.o.")
    with c2: f_osoba = st.text_input("Kontaktná osoba")
    with c3: f_platnost = st.date_input("Platnosť ponuky do", datetime.now() + timedelta(days=14))
    with c4: f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

st.divider()

# VÝBER PRODUKTU
tab1, tab2 = st.tabs(["🔍 Výber z katalógu", "➕ Pridať manuálne"])

curr_n, curr_kod, curr_p = "", "", 0.0

with tab1:
    if not df.empty:
        df['display'] = "[" + df['kod'].astype(str) + "] " + df['n'].astype(str)
        vyber_display = st.selectbox("Vyhľadajte produkt", sorted(df['display'].unique()))
        res = df[df['display'] == vyber_display]
        if not res.empty:
            r = res.iloc[0]
            curr_n, curr_kod, curr_p = r['n'], r['kod'], float(r.get('p', 0.0))
    else:
        st.info("Katalóg prázdny, použite manuálne zadanie.")

with tab2:
    m1, m2, m3 = st.columns([1, 2, 1])
    with m1: m_kod = st.text_input("Kód tovaru", value=curr_kod)
    with m2: m_nazov = st.text_input("Názov produktu", value=curr_n)
    with m3: m_cena = st.number_input("Nákupná cena €", value=curr_p, step=0.1)

# Nacenenie
final_n = m_nazov if m_nazov else curr_n
final_p = m_cena if m_cena > 0 else curr_p
final_kod = m_kod if m_kod else curr_kod

st.subheader(f"Nacenenie: {final_n}")
p1, p2, p3, p4 = st.columns(4)
with p1: marza = st.number_input("Marža %", value=35)
with p2: ks = st.number_input("Počet kusov", min_value=1, value=100)
with p3: 
    brand_type = st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "DTF potlač", "Laser", "UV tlač", "Bez potlače"])
    b_cena = st.number_input("Cena za branding/ks €", value=1.20 if brand_type != "Bez potlače" else 0.0, step=0.05)
with p4:
    predaj_ks = round((final_p * (1 + marza/100)) + b_cena, 2)
    st.write("Predajná cena:")
    st.subheader(f"{predaj_ks} €/ks")
    if st.button("➕ PRIDAŤ DO PONUKY"):
        st.session_state.basket.append({"kod": final_kod, "n": final_n, "ks": ks, "p": predaj_ks, "s": round(predaj_ks * ks, 2), "b": brand_type})
        st.rerun()

# KOŠÍK A AI GENERÁTOR
if st.session_state.basket:
    st.divider()
    st.subheader("📋 Položky v ponuke")
    for i in st.session_state.basket:
        st.write(f"- **[{i['kod']}] {i['n']}** | {i['ks']}ks | {i['b']} | {i['p']}€/ks -> **{i['s']} €**")
    
    celkom = sum(i['s'] for i in st.session_state.basket)
    st.write(f"### Spolu bez DPH: {celkom:.2f} €")
    
    col_ai1, col_ai2 = st.columns(2)
    with col_ai1:
        if st.button("🗑️ Vymazať košík"):
            st.session_state.basket = []
            st.rerun()
    with col_ai2:
        if st.button("✨ VYGENEROVAŤ PONUKU POMOCOU AI"):
            if not API_KEY:
                st.error("Chýba API kľúč.")
            else:
                try:
                    model = genai.GenerativeModel(MODEL_NAME)
                    txt_prods = "\n".join([f"- {i['ks']}ks {i['n']} (kód: {i['kod']}), {i['b']}, {i['p']}€/ks" for i in st.session_state.basket])
                    prompt = f"Si obchodník Brandex. Vytvor ponuku pre {f_firma}. Produkty:\n{txt_prods}\nCelkom: {celkom}€ bez DPH. Platnosť: {f_platnost}. Jazyk: {f_jazyk}."
                    
                    response = model.generate_content(prompt)
                    st.session_state.ai_text = response.text
                except Exception as e:
                    if "429" in str(e):
                        st.error("⚠️ Limit vyčerpaný (429). Počkajte 60 sekúnd a skúste to znova.")
                    else:
                        st.error(f"Chyba AI: {e}")

if st.session_state.ai_text:
    st.divider()
    f_text = st.text_area("Upraviť text ponuky:", value=st.session_state.ai_text, height=300)
    pdf_data = generate_pdf(f_text)
    st.download_button("📥 Stiahnuť PDF", data=bytes(pdf_data), file_name=f"Ponuka_Brandex_{f_firma}.pdf")