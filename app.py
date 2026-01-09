# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
import xml.etree.ElementTree as ET
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA ---
# Na Streamlit Cloud nastavte v Settings -> Secrets: GEMINI_API_KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.error("⚠️ Chýba API kľúč! Nastavte ho v Streamlit Secrets.")

FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. EXTRÉMNE ROBUSTNÝ XML PARSER ---
@st.cache_data(ttl=3600)
def load_brandex_data():
    try:
        response = requests.get(FEED_URL, timeout=30)
        # Brandex používa Windows-1250
        raw_content = response.content.decode('windows-1250', errors='replace')
        
        # Manuálne parsovanie XML pomocou ElementTree (odolnejšie ako read_xml)
        root = ET.fromstring(raw_content)
        
        data = []
        # Prejdeme všetky uzly a hľadáme tie, ktoré majú aspoň 3 pod-uzly (pravdepodobne produkt)
        for node in root.iter():
            if len(node) >= 3:
                row = {}
                for child in node:
                    row[child.tag.upper()] = child.text
                if row:
                    data.append(row)
        
        df = pd.DataFrame(data)
        if df.empty:
            return pd.DataFrame()

        # Mapovanie najbežnejších Brandex značiek
        mapping = {
            'NAZOV': 'n', 'PRODUCT': 'n', 'NAME': 'n', 'DESCRIPTION': 'n',
            'CENA_EU': 'p', 'PRICE': 'p', 'CENA': 'p', 'PRICE_VAT_EXCL': 'p',
            'OBRAZOK': 'img', 'IMAGE': 'img', 'IMAGEURL': 'img'
        }
        df = df.rename(columns=mapping)
        
        # Vyčistenie stĺpca s cenou na čísla
        if 'p' in df.columns:
            df['p'] = pd.to_numeric(df['p'].str.replace(',', '.'), errors='coerce').fillna(0.0)
        
        return df
    except Exception as e:
        st.error(f"Chyba pri spracovaní XML: {e}")
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
    st.subheader("🛒 Výber a nacenenie")
    
    # Hľadáme stĺpec s názvom
    col_name = 'n' if 'n' in df.columns else df.columns[0]
    items = sorted(df[col_name].dropna().unique())
    
    vyber = st.selectbox("Vyberte produkt z katalógu", items)
    
    row = df[df[col_name] == vyber].iloc[0]
    
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        n_cena = float(row.get('p', 0.0))
        st.write(f"Nákupná cena: **{n_cena:.2f} €**")
        marza = st.number_input("Marža %", value=35)
    with p2:
        ks = st.number_input("Počet kusov", min_value=1, value=100)
    with p3:
        brand_type = st.selectbox("Typ brandingu", ["Sieťotlač", "Výšivka", "DTF potlač", "Laser", "UV tlač", "Bez potlače"])
        # ODPOVEĎ NA VAŠU POŽIADAVKU: Pole pre zadanie ceny brandingu
        default_b_price = 1.20 if brand_type != "Bez potlače" else 0.0
        b_cena = st.number_input("Cena za branding/ks €", value=default_b_price, step=0.05)
    with p4:
        predaj_ks = round((n_cena * (1 + marza/100)) + b_cena, 2)
        st.write(f"Predajná cena:")
        st.subheader(f"{predaj_ks} €/ks")
        if st.button("➕ Pridať do ponuky"):
            st.session_state.basket.append({
                "n": vyber, "ks": ks, "p": predaj_ks, "s": round(predaj_ks * ks, 2), "b": brand_type
            })
            st.rerun()

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
    if st.session_state.basket:
        st.divider()
        if st.button("✨ VYGENEROVAŤ PONUKU"):
            if not API_KEY:
                st.error("Chýba API Key. Nemôžem generovať AI text.")
            else:
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    txt_prods = "\n".join([f"- {i['ks']}ks {i['n']}, {i['b']}, {i['p']}€/ks" for i in st.session_state.basket])
                    
                    prompt = f"""Si obchodník Brandex. Vytvor obchodnú ponuku pre {f_firma}. 
                    Produkty:\n{txt_prods}\n
                    Celkom: {celkom}€ bez DPH. Platnosť: {f_platnost}. Jazyk: {f_jazyk}.
                    Zameraj sa na kvalitu a profesionálny branding."""
                    
                    # OPRAVA CHYBY InvalidArgument: Uistíme sa, že prompt je reťazec a nie je prázdny
                    if prompt.strip():
                        response = model.generate_content(prompt)
                        st.session_state.ai_text = response.text
                    else:
                        st.error("Chyba: Prompt pre AI je prázdny.")
                except Exception as ai_err:
                    st.error(f"Chyba pri komunikácii s AI: {ai_err}")

        if st.session_state.ai_text:
            f_text = st.text_area("Upraviť text:", value=st.session_state.ai_text, height=300)
            if st.button("💾 Stiahnuť PDF"):
                pdf_data = generate_pdf(f_text)
                st.download_button("Kliknite pre PDF", data=bytes(pdf_data), file_name=f"Ponuka_{f_firma}.pdf")
else:
    st.error("❌ Katalóg je prázdny. Brandex feed sa nepodarilo prečítať.")