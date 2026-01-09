# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA ---
API_KEY = st.secrets.get("GEMINI_API_KEY", "TU_VLOZTE_VAS_API_KLUC")
genai.configure(api_key=API_KEY)

FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. ROBUSTNÉ NAČÍTANIE DÁT ---
@st.cache_data(ttl=3600)
def load_brandex_feed():
    try:
        response = requests.get(FEED_URL, timeout=25)
        # Brandex používa Windows-1250
        content = response.content.decode('windows-1250', errors='replace')
        
        # Skúsime načítať XML s rôznymi cestami (xpath)
        # Brandex zvyčajne balí produkty do <item> alebo <row>
        df = pd.DataFrame()
        for path in ['.//item', './/row', './*', './/product']:
            try:
                df = pd.read_xml(io.StringIO(content), xpath=path)
                if not df.empty and len(df.columns) > 1:
                    break
            except:
                continue
        
        if df.empty:
            # Ak zlyhalo XML, skúsime to ako CSV (niektoré exporty tak fungujú)
            try:
                df = pd.read_csv(io.StringIO(content), sep=';')
            except:
                pass

        if not df.empty:
            # Vyčistíme názvy stĺpcov
            df.columns = [str(c).strip() for c in df.columns]
            # Vyčistíme text v celom dataframe (odstránenie bielych znakov)
            df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Chyba pripojenia k feedu: {e}")
        return pd.DataFrame()

# --- 3. PDF GENERÁTOR ---
class BrandexPDF(FPDF):
    def header(self):
        try:
            self.image("brandex_logo.png", 10, 8, 50)
        except:
            self.set_font('helvetica', 'B', 14)
            self.cell(0, 10, 'BRANDEX PONUKA', ln=True)
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

# --- 4. UI APLIKÁCIE ---
st.set_page_config(page_title="Brandex AI", layout="wide")

if 'kosik' not in st.session_state: st.session_state.kosik = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor")

df = load_brandex_feed()

# DEBUG: Ak chcete vidieť, čo je vo feede, odkomentujte riadok nižšie
# st.write("Stĺpce vo feede:", df.columns.tolist() if not df.empty else "Prázdny feed")

if df.empty:
    st.error("❌ Nepodarilo sa načítať žiadne produkty z feedu. Skontrolujte URL alebo formát dát.")
    st.stop()

# SIDEBAR
with st.sidebar:
    st.header("👤 Klient")
    f_firma = st.text_input("Firma", "Klient s.r.o.")
    f_platnost = st.date_input("Platnosť", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

# HLAVNÁ ČASŤ
col_l, col_r = st.columns([2, 1])

with col_l:
    st.subheader("🔍 Výber produktu")
    
    # Automatická identifikácia stĺpca s názvom
    name_cols = [c for c in df.columns if c.lower() in ['name', 'nazov', 'product', 'titul']]
    name_col = name_cols[0] if name_cols else df.columns[0]
    
    # Odstránenie duplicít a zoradenie
    zoznam_produktov = sorted(df[name_col].dropna().unique())
    vyber = st.selectbox("Hľadajte v katalógu", zoznam_produktov)
    
    # Filtrovanie
    filter_df = df[df[name_col] == vyber]
    
    if not filter_df.empty:
        p_data = filter_df.iloc[0]
        st.success(f"Vybrané: **{vyber}**")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            price_cols = [c for c in df.columns if c.lower() in ['price', 'cena', 'price_vat_excl']]
            price_col = price_cols[0] if price_cols else None
            try:
                nakup = float(p_data[price_col]) if price_col else 0.0
            except:
                nakup = 0.0
            st.metric("Nákup", f"{nakup} €")
            marza = st.slider("Marža %", 0, 100, 30)
        with c2:
            ks = st.number_input("Počet kusov", 1, 10000, 100)
            brand = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF", "Laser"])
        with c3:
            b_cena = st.number_input("Branding/ks €", 0.0, 10.0, 1.0)
            predaj_ks = round((nakup * (1 + marza/100)) + b_cena, 2)
            st.subheader(f"{predaj_ks} €/ks")
        
        if st.button("➕ Pridať do ponuky"):
            st.session_state.kosik.append({
                "n": vyber, "ks": ks, "p": predaj_ks, "s": round(predaj_ks * ks, 2), "b": brand
            })
            st.rerun()

with col_r:
    st.subheader("🛒 Košík")
    for i in st.session_state.kosik:
        st.write(f"- {i['n']} ({i['ks']}ks)")
    
    if st.session_state.kosik:
        total = sum(i['s'] for i in st.session_state.kosik)
        st.write(f"**Spolu bez DPH: {total:.2f} €**")
        if st.button("🗑️ Vymazať"):
            st.session_state.kosik = []
            st.rerun()

# AI ČASŤ
if st.session_state.kosik:
    st.divider()
    if st.button("✨ VYGENEROVAŤ PONUKU"):
        with st.spinner("AI pracuje..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            text_p = "\n".join([f"- {i['ks']}ks {i['n']}, technológia {i['b']}, cena {i['p']}€/ks" for i in st.session_state.kosik])
            prompt = f"Vytvor obchodnú ponuku pre {f_firma}. Produkty:\n{text_p}\nSuma: {total}€ bez DPH. Platnosť: {f_platnost}. Jazyk: {f_jazyk}."
            st.session_state.ai_text = model.generate_content(prompt).text

    if st.session_state.ai_text:
        fin_text = st.text_area("Upraviť text:", value=st.session_state.ai_text, height=300)
        pdf_file = generate_pdf(fin_text)
        st.download_button("📥 Stiahnuť PDF", data=bytes(pdf_file), file_name=f"Ponuka_{f_firma}.pdf")