# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA AI ---
# Na Streamlit Cloud vložte kľúč do Settings -> Secrets pod názvom GEMINI_API_KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "TU_VLOZTE_VAS_API_KLUC")
genai.configure(api_key=API_KEY)

FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. ROBUSTNÉ NAČÍTANIE DÁT ---
@st.cache_data(ttl=3600)
def load_brandex_feed():
    try:
        response = requests.get(FEED_URL, timeout=30)
        # Brandex používa Windows-1250, dekódujeme so záchranou znakov
        content = response.content.decode('windows-1250', errors='replace')
        
        # Ošetrenie XML štruktúry pre pandas
        content = content.replace('encoding="windows-1250"', 'encoding="utf-8"')
        
        df = pd.DataFrame()
        # Skúsime rôzne cesty v XML, kde môžu byť produkty
        for xpath_try in ['.//item', './/row', './/*']:
            try:
                df = pd.read_xml(io.StringIO(content), xpath=xpath_try)
                if not df.empty and len(df.columns) > 2:
                    break
            except:
                continue
        
        if df.empty:
            return pd.DataFrame()

        # Vyčistenie názvov stĺpcov
        df.columns = [str(c).strip() for c in df.columns]
        
        # Mapovanie stĺpcov na jednotné názvy (Brandex verzia)
        mapping = {
            'Name': 'prod_name', 'NAME': 'prod_name', 'nazov': 'prod_name', 'NAZOV': 'prod_name',
            'Price': 'prod_price', 'PRICE': 'prod_price', 'cena': 'prod_price', 'CENA': 'prod_price'
        }
        df = df.rename(columns=mapping)
        
        # Vyčistenie samotných dát (odstránenie bielych znakov v názvoch)
        if 'prod_name' in df.columns:
            df['prod_name'] = df['prod_name'].astype(str).str.strip()
        
        return df
    except Exception as e:
        st.error(f"Chyba pripojenia k Brandex feedu: {e}")
        return pd.DataFrame()

# --- 3. PDF GENERÁTOR ---
class BrandexPDF(FPDF):
    def header(self):
        try:
            self.image("brandex_logo.png", 10, 8, 45)
        except:
            self.set_font('Helvetica', 'B', 15)
            self.cell(0, 10, 'BRANDEX', ln=True)
        self.ln(20)

def create_pdf(text):
    pdf = BrandexPDF()
    pdf.add_page()
    try:
        # Registrácia fontu (DejaVuSans.ttf musí byť v priečinku)
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 11)
    except:
        pdf.set_font('Helvetica', '', 11)
    
    pdf.multi_cell(0, 7, text)
    return pdf.output()

# --- 4. WEBOVÉ ROZHRANIE ---
st.set_page_config(page_title="Brandex Ponuky", layout="wide")

if 'kosik' not in st.session_state: st.session_state.kosik = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor")

df = load_brandex_feed()

if df.empty:
    st.warning("Načítavam katalóg produktov... Prosím čakajte.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Klient")
    c_firma = st.text_input("Názov firmy", "Klient s.r.o.")
    c_osoba = st.text_input("Kontaktná osoba", "")
    c_platnost = st.date_input("Platnosť ponuky", datetime.now() + timedelta(days=14))
    c_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

# --- HLAVNÁ PLOCHA ---
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("🔍 Výber produktu")
    
    # Identifikácia stĺpca s názvom
    name_col = 'prod_name' if 'prod_name' in df.columns else df.columns[0]
    zoznam_produktov = sorted(df[name_col].unique())
    
    vyber = st.selectbox("Vyhľadajte produkt v zozname", zoznam_produktov)
    
    # FILTROVANIE DÁT S POISTKOU (Tu bola predtým chyba)
    matching_rows = df[df[name_col] == vyber]
    
    if not matching_rows.empty:
        p_data = matching_rows.iloc[0]
        
        st.info(f"**Vybrané:** {vyber}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            price_col = 'prod_price' if 'prod_price' in df.columns else None
            try:
                n_cena = float(p_data[price_col]) if price_col else 0.0
            except:
                n_cena = 0.0
            st.write(f"Nákupná cena: **{n_cena} €**")
            marza = st.slider("Marža %", 0, 150, 30)
            
        with c2:
            ks = st.number_input("Počet kusov", 1, 10000, 100)
            brand = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF", "Laser", "UV tlač", "Bez brandingu"])
            
        with c3:
            b_cena = st.number_input("Branding cena/ks", 0.0, 10.0, 1.2)
            p_cena = round((n_cena * (1 + marza/100)) + b_cena, 2)
            st.metric("Predajná cena", f"{p_cena} €/ks")
            
        if st.button("➕ Pridať do ponuky"):
            st.session_state.kosik.append({
                "n": vyber, "ks": ks, "p": p_cena, "s": round(p_cena * ks, 2), "b": brand
            })
            st.rerun()
    else:
        st.error("Chyba: Vybraný produkt sa nepodarilo v databáze nájsť. Skúste iný.")

with col_right:
    st.subheader("🛒 Aktuálna ponuka")
    if not st.session_state.kosik:
        st.write("Váš košík je prázdny.")
    else:
        for idx, i in enumerate(st.session_state.kosik):
            st.write(f"**{i['n']}**")
            st.caption(f"{i['ks']}ks | {i['b']} | {i['p']}€/ks")
        
        celkom = sum(i['s'] for i in st.session_state.kosik)
        st.divider()
        st.write(f"**SPOLU BEZ DPH: {celkom:.2f} €**")
        
        if st.button("🗑️ Vymazať košík"):
            st.session_state.kosik = []
            st.rerun()

# --- AI GENEROVANIE ---
if st.session_state.kosik:
    st.divider()
    if st.button("✨ VYGENEROVAŤ TEXT PONUKY"):
        with st.spinner("Gemini vytvára profesionálny text..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            text_produkty = ""
            for i in st.session_state.kosik:
                text_produkty += f"- {i['ks']}ks {i['n']}, technológia: {i['b']}, cena: {i['p']}€/ks\n"
            
            prompt = f"""Si obchodník firmy Brandex. Vytvor cenovú ponuku pre firmu {c_firma}.
            Produkty:
            {text_produkty}
            Spolu bez DPH: {celkom} €. Platnosť do: {c_platnost}. Jazyk: {c_jazyk}.
            Uveď, že ceny sú bez DPH. Poďakuj za dopyt a spomeň kvalitu Brandex produktov."""
            
            vysledok = model.generate_content(prompt)
            st.session_state.ai_text = vysledok.text

    if st.session_state.ai_text:
        upraveny_text = st.text_area("Finalizácia textu (môžete upraviť):", value=st.session_state.ai_text, height=350)
        
        pdf_file = create_pdf(upraveny_text)
        st.download_button(
            "📥 Stiahnuť PDF ponuku",
            data=bytes(pdf_file),
            file_name=f"Ponuka_Brandex_{c_firma}.pdf",
            mime="application/pdf"
        )