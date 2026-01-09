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

# --- 2. ROBUSTNÝ PARSER (HĽADÁ PRODUKTY KDEKOĽVEK V XML) ---
@st.cache_data(ttl=3600)
def load_brandex_feed():
    try:
        response = requests.get(FEED_URL, timeout=30)
        # Brandex kódovanie Windows-1250
        content = response.content.decode('windows-1250', errors='replace')
        
        # Odstránenie deklarácií kódovania, ktoré by mýlili parser
        content = content.replace('encoding="windows-1250"', 'encoding="utf-8"')
        
        # SKÚŠAME RÔZNE CESTY (XPATH), ABY SME NAŠLI PRODUKTY
        df = pd.DataFrame()
        test_paths = ['.//ITEM', './/item', './/PRODUCT', './/product', './/ROW', './/row', './*/*']
        
        for path in test_paths:
            try:
                df = pd.read_xml(io.StringIO(content), xpath=path)
                if not df.empty and len(df.columns) > 3: # Ak má aspoň 3 stĺpce, našli sme správny uzol
                    break
            except:
                continue
        
        if df.empty:
            return pd.DataFrame(), content # Vrátime aj surový text pre debug
            
        # Vyčistenie stĺpcov a dát
        df.columns = [str(c).strip() for c in df.columns]
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        
        # Mapovanie stĺpcov (Brandex používa často NAME, PRICE, atď.)
        mapping = {
            'NAME': 'n', 'Name': 'n', 'nazov': 'n', 'NAZOV': 'n', 'Product': 'n',
            'PRICE': 'p', 'Price': 'p', 'cena': 'p', 'CENA': 'p', 'Price_VAT_excl': 'p'
        }
        df = df.rename(columns=mapping)
        
        return df, content
    except Exception as e:
        st.error(f"Chyba pripojenia: {e}")
        return pd.DataFrame(), ""

# --- 3. PDF GENERÁTOR ---
class BrandexPDF(FPDF):
    def header(self):
        try: self.image("brandex_logo.png", 10, 8, 45)
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
st.set_page_config(page_title="Brandex AI", layout="wide")

if 'kosik' not in st.session_state: st.session_state.kosik = []
if 'ai_vystup' not in st.session_state: st.session_state.ai_vystup = ""

st.title("👕 Brandex Inteligentný Generátor")

# NAČÍTANIE DÁT
df, raw_xml = load_brandex_feed()

# --- SEKCIA 1: KLIENT (Pôvodný štýl formulára) ---
with st.container():
    st.subheader("📝 Údaje o klientovi")
    c1, c2, c3, c4 = st.columns(4)
    with c1: f_firma = st.text_input("Firma", "Klient s.r.o.")
    with c2: f_osoba = st.text_input("Kontaktná osoba")
    with c3: f_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
    with c4: f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

st.divider()

# --- SEKCIA 2: PRODUKT (Pôvodný štýl) ---
if not df.empty:
    st.subheader("🛒 Výber a nacenenie produktov")
    
    # Identifikácia stĺpca s názvom
    name_col = 'n' if 'n' in df.columns else df.columns[0]
    zoznam_produktov = sorted(df[name_col].dropna().unique())
    
    vyber = st.selectbox("Vyhľadajte produkt v Brandex katalógu", zoznam_produktov)
    
    # Získanie dát vybraného produktu
    matching = df[df[name_col] == vyber]
    if not matching.empty:
        p_data = matching.iloc[0]
        
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            # Hľadanie ceny
            cena_col = 'p' if 'p' in df.columns else None
            try: n_cena = float(p_data[cena_col]) if cena_col else 0.0
            except: n_cena = 0.0
            st.write(f"Nákupná cena: **{n_cena} €**")
            marza = st.number_input("Marža %", value=35)
        with p2:
            ks = st.number_input("Počet kusov", min_value=1, value=100)
        with p3:
            brand = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF", "Laser", "UV tlač", "Bez potlače"])
            b_cena = st.number_input("Cena brandingu/ks €", value=1.2)
        with p4:
            predaj_ks = round((n_cena * (1 + marza/100)) + b_cena, 2)
            st.write(f"Predajná cena:")
            st.subheader(f"{predaj_ks} €/ks")
            if st.button("➕ Pridať do ponuky"):
                st.session_state.kosik.append({
                    "n": vyber, "ks": ks, "p": predaj_ks, "s": round(predaj_ks * ks, 2), "b": brand
                })
                st.rerun()

    # ZOBRAZENIE KOŠÍKA
    if st.session_state.kosik:
        st.divider()
        st.subheader("📋 Položky v ponuke")
        for idx, i in enumerate(st.session_state.kosik):
            col_k1, col_k2, col_k3 = st.columns([3, 1, 1])
            col_k1.write(f"**{i['n']}** ({i['b']})")
            col_k2.write(f"{i['ks']} ks x {i['p']} €")
            col_k3.write(f"**{i['s']} €**")
        
        celkom = sum(i['s'] for i in st.session_state.kosik)
        st.write(f"### Spolu bez DPH: {celkom:.2f} €")
        if st.button("🗑️ Vymazať košík"):
            st.session_state.kosik = []
            st.rerun()

    # AI A EXPORT
    if st.session_state.kosik:
        st.divider()
        if st.button("✨ VYGENEROVAŤ FINÁLNY TEXT PONUKY"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            produkty_list = "\n".join([f"- {i['ks']}ks {i['n']}, technológia {i['b']}, cena {i['p']}€/ks" for i in st.session_state.kosik])
            prompt = f"Si obchodník Brandex. Vytvor ponuku pre {f_firma}. Produkty:\n{produkty_list}\nCelkom: {celkom}€ bez DPH. Platnosť: {f_platnost}. Jazyk: {f_jazyk}."
            st.session_state.ai_vystup = model.generate_content(prompt).text

        if st.session_state.ai_vystup:
            finalny_text = st.text_area("Upraviť text ponuky:", value=st.session_state.ai_vystup, height=300)
            if st.button("💾 Stiahnuť PDF"):
                pdf_data = generate_pdf(finalny_text)
                st.download_button("Kliknite pre stiahnutie PDF", data=bytes(pdf_data), file_name=f"Ponuka_{f_firma}.pdf")

else:
    st.error("❌ Dáta z katalógu sa nepodarilo načítať.")
    with st.expander("Ladenie (Debug informácie)"):
        st.write("Skúste skontrolovať URL feedu. Surový začiatok XML:")
        st.code(raw_xml[:1000]) # Ukáže nám začiatok XML, aby sme videli štruktúru