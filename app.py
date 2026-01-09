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
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)

FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. ŠPECIFICKÝ BRANDEX PARSER ---
@st.cache_data(ttl=3600)
def load_brandex_data():
    try:
        response = requests.get(FEED_URL, timeout=30)
        content = response.content.decode('windows-1250', errors='replace')
        root = ET.fromstring(content)
        
        data = []
        # Hľadáme uzly, ktoré obsahujú KOD_IT (váš kľúčový identifikátor)
        for node in root.findall('.//*'):
            if node.find('KOD_IT') is not None:
                row = {}
                for child in node:
                    tag = child.tag.upper().strip()
                    val = child.text.strip() if child.text else ""
                    row[tag] = val
                data.append(row)
        
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Mapovanie polí podľa vášho zadania
        # KOD_IT -> kod, NAZOV -> n, CENA_EU -> p
        mapping = {
            'KOD_IT': 'kod',
            'NAZOV': 'n',
            'CENA_EU': 'p',
            'CENA': 'p',
            'PRICE': 'p'
        }
        df = df.rename(columns=mapping)
        
        # Ošetrenie cien
        if 'p' in df.columns:
            df['p'] = df['p'].astype(str).str.replace(',', '.')
            df['p'] = pd.to_numeric(df['p'], errors='coerce').fillna(0.0)
        
        return df
    except Exception as e:
        st.error(f"Chyba pri načítaní Brandex feedu: {e}")
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

# Načítanie dát
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

# TABY: VÝBER Z KATALÓGU vs MANUÁLNE ZADANIE
tab1, tab2 = st.tabs(["🔍 Výber z katalógu", "➕ Pridať manuálne / podľa kódu"])

with tab1:
    if not df.empty:
        # Vytvoríme pekný názov: [KÓD] Názov produktu
        df['display_name'] = "[" + df['kod'].astype(str) + "] " + df['n'].astype(str)
        items = sorted(df['display_name'].unique())
        
        vyber_display = st.selectbox("Vyhľadajte produkt (podľa kódu alebo názvu)", items)
        res = df[df['display_name'] == vyber_display]
        
        if not res.empty:
            row = res.iloc[0]
            curr_n = row['n']
            curr_kod = row['kod']
            curr_p = float(row.get('p', 0.0))
        else:
            curr_n, curr_kod, curr_p = "", "", 0.0
    else:
        st.info("Katalóg sa nepodarilo načítať. Použite manuálne zadanie v druhom tabe.")
        curr_n, curr_kod, curr_p = "", "", 0.0

with tab2:
    st.write("Tu môžete zadať produkt priamo z webu produkty.brandex.sk")
    m1, m2, m3 = st.columns([1, 2, 1])
    with m1: m_kod = st.text_input("Kód tovaru (KOD_IT)", value=curr_kod if 'curr_kod' in locals() else "")
    with m2: m_nazov = st.text_input("Názov produktu", value=curr_n if 'curr_n' in locals() else "")
    with m3: m_cena = st.number_input("Nákupná cena bez DPH €", value=curr_p if 'curr_p' in locals() else 0.0, step=0.1)
    
    # Ak sme v tabe 2, prepíšeme hodnoty tými z formulára
    final_n = m_nazov if m_nazov else curr_n
    final_p = m_cena if m_cena > 0 else curr_p
    final_kod = m_kod if m_kod else curr_kod

# VÝPOČET CENY A BRANDINGU (Spoločné pre oba taby)
st.subheader(f"Nacenenie: {final_n} (Kód: {final_kod})")
p1, p2, p3, p4 = st.columns(4)

with p1:
    st.write(f"Nákup: **{final_p:.2f} €**")
    marza = st.number_input("Marža %", value=35)
with p2:
    ks = st.number_input("Počet kusov", min_value=1, value=100)
with p3:
    brand_type = st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "DTF potlač", "Laser", "UV tlač", "Bez potlače"])
    # POŽIADAVKA: Pole pre zadanie ceny brandingu podľa výberu
    def_b_price = 1.20 if brand_type != "Bez potlače" else 0.0
    b_cena = st.number_input("Cena za branding / ks €", value=def_b_price, step=0.05)
with p4:
    predaj_ks = round((final_p * (1 + marza/100)) + b_cena, 2)
    st.write("Predajná cena:")
    st.subheader(f"{predaj_ks} €/ks")
    if st.button("➕ PRIDAŤ DO PONUKY"):
        st.session_state.basket.append({
            "kod": final_kod,
            "n": final_n,
            "ks": ks,
            "p": predaj_ks,
            "s": round(predaj_ks * ks, 2),
            "b": brand_type
        })
        st.toast(f"Pridané: {final_n}")
        st.rerun()

# KOŠÍK A GENERÁTOR
if st.session_state.basket:
    st.divider()
    st.subheader("📋 Položky v rozpracovanej ponuke")
    for idx, i in enumerate(st.session_state.basket):
        st.write(f"{idx+1}. **[{i['kod']}] {i['n']}** - {i['ks']}ks | {i['b']} | {i['p']}€/ks -> **{i['s']} €**")
    
    celkom = sum(i['s'] for i in st.session_state.basket)
    st.write(f"### Spolu bez DPH: {celkom:.2f} €")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🗑️ Vymazať košík"):
            st.session_state.basket = []
            st.rerun()
    with col_btn2:
        if st.button("✨ VYGENEROVAŤ PONUKU POMOCOU AI"):
            if not API_KEY:
                st.error("Chýba AI kľúč.")
            else:
                model = genai.GenerativeModel('gemini-1.5-flash')
                txt_prods = "\n".join([f"- {i['ks']}ks {i['n']} (kód: {i['kod']}), branding: {i['b']}, cena: {i['p']}€/ks" for i in st.session_state.basket])
                prompt = f"Si obchodník Brandex. Vytvor obchodnú ponuku pre {f_firma}. Produkty:\n{txt_prods}\nCelkom: {celkom}€ bez DPH. Platnosť: {f_platnost}. Jazyk: {f_jazyk}."
                st.session_state.ai_text = model.generate_content(prompt).text

if st.session_state.ai_text:
    st.divider()
    f_text = st.text_area("Finalizácia textu:", value=st.session_state.ai_text, height=300)
    pdf_data = generate_pdf(f_text)
    st.download_button("📥 Stiahnuť PDF", data=bytes(pdf_data), file_name=f"Ponuka_Brandex_{f_firma}.pdf")