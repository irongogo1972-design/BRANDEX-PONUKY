# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
import xml.etree.ElementTree as ET
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA AI (AKTUALIZOVANÉ PRE ROK 2026) ---
# Skúste gemini-2.0-flash alebo gemini-2.5-flash
MODEL_NAME = "gemini-2.0-flash" 

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

# --- 3. PDF ---
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

# --- 4. UI ---
st.set_page_config(page_title="Brandex AI 2026", layout="wide")

if 'basket' not in st.session_state: st.session_state.basket = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor (v2026)")

df = load_brandex_data()

with st.sidebar:
    st.header("👤 Nastavenia")
    f_firma = st.text_input("Firma", "Klient s.r.o.")
    f_platnost = st.date_input("Platnosť", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])
    if st.button("🔍 Dostupné AI Modely"):
        try:
            ms = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write(ms)
        except: st.error("Nepodarilo sa overiť modely.")

# --- VÝBER PRODUKTU ---
tab1, tab2 = st.tabs(["🔍 Katalóg", "➕ Manuálne"])
with tab1:
    if not df.empty:
        df['display'] = "[" + df['kod'].astype(str) + "] " + df['n'].astype(str)
        vyber = st.selectbox("Hľadať produkt", sorted(df['display'].unique()))
        res = df[df['display'] == vyber].iloc[0]
        c_n, c_k, c_p = res['n'], res['kod'], float(res.get('p', 0.0))
    else: c_n, c_k, c_p = "", "", 0.0

with tab2:
    m_kod = st.text_input("Kód", value=c_k if 'c_k' in locals() else "")
    m_nazov = st.text_input("Názov", value=c_n if 'c_n' in locals() else "")
    m_cena = st.number_input("Cena €", value=c_p if 'c_p' in locals() else 0.0)

# Nacenenie
st.divider()
p1, p2, p3, p4 = st.columns(4)
with p1: marza = st.number_input("Marža %", value=35)
with p2: ks = st.number_input("Ks", min_value=1, value=100)
with p3: 
    brand = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Bez potlače"])
    b_cena = st.number_input("Cena brandingu/ks €", value=1.2 if brand != "Bez potlače" else 0.0)
with p4:
    predaj = round(( (m_cena if m_cena > 0 else c_p) * (1 + marza/100)) + b_cena, 2)
    st.subheader(f"{predaj} €/ks")
    if st.button("➕ PRIDAŤ"):
        st.session_state.basket.append({"n": m_nazov or c_n, "ks": ks, "p": predaj, "s": round(predaj*ks, 2), "b": brand})
        st.rerun()

# Košík a Generovanie
if st.session_state.basket:
    st.divider()
    for i in st.session_state.basket:
        st.write(f"- {i['ks']}ks **{i['n']}** ({i['b']}) -> {i['s']}€")
    
    total = sum(i['s'] for i in st.session_state.basket)
    st.write(f"### Spolu: {total:.2f} € bez DPH")
    
    if st.button("✨ GENEROVAŤ PONUKU"):
        try:
            # POUŽITIE NOVÉHO MODELU
            model = genai.GenerativeModel(MODEL_NAME)
            prods = "\n".join([f"- {i['ks']}ks {i['n']}, {i['b']}, {i['p']}€/ks" for i in st.session_state.basket])
            prompt = f"Si obchodník Brandex. Vytvor ponuku pre {f_firma}. Produkty:\n{prods}\nCelkom: {total}€ bez DPH. Jazyk: {f_jazyk}."
            response = model.generate_content(prompt)
            st.session_state.ai_text = response.text
        except Exception as e:
            st.error(f"Chyba: {e}")

if st.session_state.ai_text:
    final_txt = st.text_area("Upraviť:", value=st.session_state.ai_text, height=300)
    pdf_file = generate_pdf(final_txt)
    st.download_button("📥 PDF", data=bytes(pdf_file), file_name=f"Ponuka_{f_firma}.pdf")