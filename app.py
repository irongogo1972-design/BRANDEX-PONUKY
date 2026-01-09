# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA ---
# Na Streamlit Cloud nastavte v Settings -> Secrets: GEMINI_API_KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "TU_VLOZTE_VAS_API_KLUC")
genai.configure(api_key=API_KEY)

FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. NAČÍTANIE DÁT ---
@st.cache_data(ttl=3600)
def load_brandex_feed():
    try:
        response = requests.get(FEED_URL, timeout=20)
        # Brandex používa Windows-1250 kódovanie
        content = response.content.decode('windows-1250', errors='replace')
        
        # Vyčistenie problematických deklarácií v XML
        content = content.replace('encoding="windows-1250"', 'encoding="utf-8"')
        content = content.replace('encoding="ISO-8859-2"', 'encoding="utf-8"')
        
        df = pd.read_xml(io.StringIO(content))
        
        # Vyčistenie názvov stĺpcov (odstránenie medzier a prevod na malé písmená pre ľahšie hľadanie)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Chyba pri načítaní feedu: {e}")
        return pd.DataFrame()

# --- 3. PDF GENERÁTOR ---
class BrandexPDF(FPDF):
    def header(self):
        try:
            self.image("brandex_logo.png", 10, 8, 50)
        except:
            self.set_font('helvetica', 'B', 16)
            self.cell(0, 10, 'BRANDEX - Cenová ponuka', ln=True)
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

if 'kosik' not in st.session_state:
    st.session_state.kosik = []
if 'ai_text' not in st.session_state:
    st.session_state.ai_text = ""

st.title("🚀 Brandex Inteligentný Generátor")

# SIDEBAR
with st.sidebar:
    st.header("👤 Klient")
    f_firma = st.text_input("Názov firmy", "Klient s.r.o.")
    f_osoba = st.text_input("Kontaktná osoba")
    f_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])
    f_styl = st.selectbox("Tón", ["Profesionálny", "Priateľský"])

# HLAVNÁ ČASŤ
df = load_brandex_feed()

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("🔍 Výber z katalógu")
    if not df.empty:
        # Hľadanie správneho stĺpca pre názov (skúsime bežné varianty)
        mozne_stlpce = ['Name', 'NAME', 'Product', 'Product_Name', 'Nazov', 'NAZOV']
        search_col = next((c for c in mozne_stlpce if c in df.columns), df.columns[0])
        
        vyber_mena = st.selectbox("Vyberte produkt", df[search_col].unique())
        
        # Filtrovanie dát pre vybraný produkt
        filtered_df = df[df[search_col] == vyber_mena]
        
        if not filtered_df.empty:
            prod_data = filtered_df.iloc[0]
            
            c1, c2, c3 = st.columns(3)
            with c1:
                # Hľadanie ceny
                cena_col = next((c for c in ['Price', 'PRICE', 'Cena', 'CENA'] if c in df.columns), None)
                try:
                    n_cena = float(prod_data[cena_col]) if cena_col else 0.0
                except:
                    n_cena = 0.0
                st.metric("Nákupná cena", f"{n_cena} €")
                marza = st.slider("Marža %", 0, 150, 30)
            with c2:
                mnozstvo = st.number_input("Počet kusov", min_value=1, value=100)
                branding = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF", "Laser", "UV Tlač"])
            with c3:
                b_cena = st.number_input("Branding/ks €", value=1.0)
                p_cena = round((n_cena * (1 + marza/100)) + b_cena, 2)
                st.subheader(f"{p_cena} €/ks")
            
            if st.button("➕ Pridať do ponuky"):
                st.session_state.kosik.append({
                    "nazov": vyber_mena,
                    "ks": mnozstvo,
                    "cena_ks": p_cena,
                    "spolu": round(p_cena * mnozstvo, 2),
                    "branding": branding
                })
                st.toast(f"Pridané: {vyber_mena}")
                st.rerun()
    else:
        st.warning("Čakám na načítanie produktov z feedu...")

with col_right:
    st.subheader("🛒 Aktuálny košík")
    if st.session_state.kosik:
        for idx, item in enumerate(st.session_state.kosik):
            st.write(f"**{item['nazov']}**")
            st.caption(f"{item['ks']}ks x {item['cena_ks']}€ ({item['branding']})")
        
        celkom = sum(i['spolu'] for i in st.session_state.kosik)
        st.write(f"--- \n**Celkom bez DPH: {celkom:.2f} €**")
        
        if st.button("🗑️ Vymazať košík"):
            st.session_state.kosik = []
            st.rerun()
    else:
        st.write("Váš košík je zatiaľ prázdny.")

# --- AI A PDF ---
if st.session_state.kosik:
    st.divider()
    if st.button("✨ VYGENEROVAŤ TEXT PONUKY POMOCOU AI"):
        with st.spinner("AI pracuje..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            txt_produkty = ""
            for p in st.session_state.kosik:
                txt_produkty += f"- {p['ks']}ks {p['nazov']}, branding: {p['branding']}, cena: {p['cena_ks']}€/ks\n"
            
            prompt = f"""Vytvor profesionálnu cenovú ponuku pre firmu {f_firma}. 
            Produkty:\n{txt_produkty}\n
            Suma spolu: {sum(i['spolu'] for i in st.session_state.kosik)} € bez DPH.
            Platnosť: {f_platnost}. Jazyk: {f_jazyk}. Štýl: {f_styl}.
            Zahrň poďakovanie a informáciu o kvalite Brandex."""
            
            st.session_state.ai_text = model.generate_content(prompt).text

    if st.session_state.ai_text:
        upraveny_text = st.text_area("Finalizácia textu:", value=st.session_state.ai_text, height=300)
        
        col_down1, col_down2 = st.columns(2)
        with col_down1:
            pdf_data = generate_pdf(upraveny_text)
            st.download_button(
                "📥 Stiahnuť PDF ponuku", 
                data=bytes(pdf_data), 
                file_name=f"Ponuka_Brandex_{f_firma}.pdf",
                mime="application/pdf"
            )