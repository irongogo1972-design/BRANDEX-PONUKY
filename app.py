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

# --- 2. ROBUSTNÉ NAČÍTANIE DÁT ---
@st.cache_data(ttl=3600)
def load_brandex_data():
    try:
        # 1. Stiahnutie súboru
        response = requests.get(FEED_URL, timeout=30)
        # Brandex používa Windows-1250 (slovenské kódovanie)
        raw_content = response.content.decode('windows-1250', errors='replace')
        
        # 2. Parsovanie XML
        root = ET.fromstring(raw_content)
        
        data = []
        # Hľadáme produkty (uzly, ktoré majú veľa pod-uzlov, napr. názov, cenu, kód)
        for node in root.iter():
            if len(node) >= 5: # Produkty mávajú aspoň 5-10 údajov
                row = {}
                for child in node:
                    tag = child.tag.upper().strip()
                    val = child.text.strip() if child.text else ""
                    row[tag] = val
                if row:
                    data.append(row)
        
        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # 3. Premenovanie stĺpcov (Brandex mapovanie)
        mapping = {
            'NAZOV': 'n', 'PRODUCT': 'n', 'NAME': 'n', 'PRODUCTNAME': 'n',
            'CENA_EU': 'p', 'PRICE': 'p', 'CENA': 'p', 'PRICE_VAT_EXCL': 'p', 'PRICE_VAT': 'p'
        }
        df = df.rename(columns=mapping)
        
        # 4. Čistenie cien (aby fungovali výpočty)
        if 'p' in df.columns:
            # Nahradíme slovenskú čiarku bodkou a prevedieme na číslo
            df['p'] = df['p'].astype(str).str.replace(',', '.')
            df['p'] = pd.to_numeric(df['p'], errors='coerce').fillna(0.0)
        else:
            df['p'] = 0.0
            
        return df
    except Exception as e:
        st.error(f"Chyba pri spracovaní feedu: {e}")
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

# Kontrola API kľúča
if not API_KEY:
    st.warning("⚠️ V Streamlit Secrets chýba 'GEMINI_API_KEY'. AI nebude fungovať.")

# Načítanie dát
df = load_brandex_data()

# FORMULÁR O KLIENTOVI
with st.container():
    st.subheader("📝 Údaje o klientovi")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_firma = st.text_input("Firma", "Klient s.r.o.")
    with c2: f_osoba = st.text_input("Kontaktná osoba")
    with c3: f_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
    with c4: f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

st.divider()

# VÝBER PRODUKTU
if not df.empty:
    st.subheader("🛒 Výber tovaru")
    
    # Identifikujeme stĺpec s názvom (najčastejšie 'n' po premenovaní)
    col_name = 'n' if 'n' in df.columns else df.columns[0]
    items = sorted(df[col_name].dropna().unique())
    
    vyber = st.selectbox("Hľadajte produkt v katalógu", items)
    
    # FILTROVANIE S POISTKOU PROTI IndexError
    res = df[df[col_name] == vyber]
    
    if not res.empty:
        row = res.iloc[0]
        
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            n_cena = float(row.get('p', 0.0))
            st.write(f"Nákupná cena: **{n_cena:.2f} €**")
            marza = st.number_input("Marža %", value=35)
        with p2:
            ks = st.number_input("Počet kusov", min_value=1, value=100)
        with p3:
            brand_type = st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "DTF potlač", "Laser", "UV tlač", "Bez potlače"])
            # Pole pre zadanie ceny brandingu
            def_b_price = 1.20 if brand_type != "Bez potlače" else 0.0
            b_cena = st.number_input("Cena za branding/ks €", value=def_b_price, step=0.05)
        with p4:
            predaj_ks = round((n_cena * (1 + marza/100)) + b_cena, 2)
            st.write(f"Predajná cena:")
            st.subheader(f"{predaj_ks} €/ks")
            if st.button("➕ Pridať do ponuky"):
                st.session_state.basket.append({
                    "n": vyber, "ks": ks, "p": predaj_ks, "s": round(predaj_ks * ks, 2), "b": brand_type
                })
                st.rerun()
    else:
        st.error("Produkt sa nepodarilo v databáze nájsť.")

    # KOŠÍK
    if st.session_state.basket:
        st.divider()
        st.subheader("📋 Položky v ponuke")
        for i in st.session_state.basket:
            st.write(f"- **{i['n']}** ({i['ks']}ks | {i['b']} | {i['p']}€/ks) -> **{i['s']} €**")
        
        celkom = sum(i['s'] for i in st.session_state.basket)
        st.write(f"### Spolu bez DPH: {celkom:.2f} €")
        if st.button("🗑️ Vymazať košík"):
            st.session_state.basket = []
            st.rerun()

    # AI GENEROVANIE
    if st.session_state.basket and API_KEY:
        st.divider()
        if st.button("✨ VYGENEROVAŤ PONUKU"):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                txt_prods = "\n".join([f"- {i['ks']}ks {i['n']}, {i['b']}, {i['p']}€/ks" for i in st.session_state.basket])
                
                prompt = f"""Si obchodník firmy Brandex. Vytvor obchodnú ponuku pre {f_firma}. 
                Produkty:\n{txt_prods}\n
                Celkom: {celkom}€ bez DPH. Platnosť: {f_platnost}. Jazyk: {f_jazyk}.
                Zameraj sa na kvalitu a profesionálny branding."""
                
                response = model.generate_content(prompt)
                st.session_state.ai_text = response.text
            except Exception as ai_err:
                st.error(f"AI Error: {ai_err}")

        if st.session_state.ai_text:
            f_text = st.text_area("Upraviť text ponuky:", value=st.session_state.ai_text, height=300)
            if st.button("💾 Stiahnuť PDF"):
                pdf_data = generate_pdf(f_text)
                st.download_button("Kliknite sem pre PDF", data=bytes(pdf_data), file_name=f"Ponuka_{f_firma}.pdf")

else:
    st.error("❌ Katalóg tovaru je prázdny. Systém v XML súbore nenašiel žiadne produkty.")
    st.info("Toto sa stáva, ak má XML iné názvy značiek. Tu sú stĺpce, ktoré som v súbore našiel:")
    if not df.empty:
        st.write(df.columns.tolist())