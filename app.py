# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. KONFIGURÁCIA AI (GEMINI) ---
# Na Streamlit Cloud vložte kľúč do Settings -> Secrets pod názvom GEMINI_API_KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", "TU_VLOZTE_VAS_API_KLUC")
genai.configure(api_key=API_KEY)

# URL Brandex Feedu
FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. FUNKCIA PRE NAČÍTANIE PRODUKTOV ---
@st.cache_data(ttl=3600)
def load_brandex_feed():
    try:
        response = requests.get(FEED_URL, timeout=30)
        # Brandex používa Windows-1250 kódovanie
        content = response.content.decode('windows-1250', errors='replace')
        
        # Ošetrenie XML štruktúry
        content = content.replace('encoding="windows-1250"', 'encoding="utf-8"')
        
        # Pokus o načítanie XML (Brandex máva štruktúru pod <item>)
        df = pd.DataFrame()
        for path in ['.//item', './/row', './/*']:
            try:
                df = pd.read_xml(io.StringIO(content), xpath=path)
                if not df.empty and len(df.columns) > 2:
                    break
            except:
                continue
        
        if df.empty:
            st.error("Nepodarilo sa rozpoznať štruktúru XML feedu.")
            return pd.DataFrame()

        # Normalizácia názvov stĺpcov (odstránenie medzier, malé písmená)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Automatické premenovanie kľúčových stĺpcov pre stabilitu aplikácie
        mapping = {
            'Name': 'nazov_prod', 'NAME': 'nazov_prod', 'nazov': 'nazov_prod', 'NAZOV': 'nazov_prod',
            'Price': 'cena_prod', 'PRICE': 'cena_prod', 'cena': 'cena_prod', 'CENA': 'cena_prod',
            'ImageURL': 'foto_prod', 'IMG': 'foto_prod'
        }
        df = df.rename(columns=mapping)
        
        # Ak chýba cena, nastavíme 0
        if 'cena_prod' not in df.columns: df['cena_prod'] = 0.0
        
        return df
    except Exception as e:
        st.error(f"Chyba pripojenia k dátam: {e}")
        return pd.DataFrame()

# --- 3. GENERÁTOR PDF (SO SLOVENSKOU DIAKRITIKOU) ---
class BrandexPDF(FPDF):
    def header(self):
        try:
            self.image("brandex_logo.png", 10, 8, 50)
        except:
            self.set_font('Helvetica', 'B', 16)
            self.cell(0, 10, 'BRANDEX - Cenová ponuka', ln=True)
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Strana {self.page_no()}', 0, 0, 'C')

def create_pdf(text_ponuky):
    pdf = BrandexPDF()
    pdf.add_page()
    
    # Pridanie fontu DejaVu (nutné mať súbor DejaVuSans.ttf v priečinku)
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 11)
    except Exception as e:
        st.warning("Font DejaVuSans.ttf nebol nájdený. PDF nemusí zobraziť diakritiku správne.")
        pdf.set_font('Helvetica', '', 11)
    
    # Spracovanie textu do PDF
    pdf.multi_cell(0, 7, text_ponuky)
    return pdf.output()

# --- 4. HLAVNÁ APLIKÁCIA (UI) ---
st.set_page_config(page_title="Brandex Ponuky", layout="wide", page_icon="📝")

# Inicializácia session state (pamäť košíka a AI)
if 'kosik' not in st.session_state: st.session_state.kosik = []
if 'ai_vystup' not in st.session_state: st.session_state.ai_vystup = ""

st.title("👔 Brandex Inteligentný Generátor Ponúk")

# --- SIDEBAR: ÚDAJE O KLIENTOVI ---
with st.sidebar:
    st.header("👤 Klient a nastavenia")
    c_firma = st.text_input("Názov firmy / Klient", "Vzorová Firma s.r.o.")
    c_osoba = st.text_input("Kontaktná osoba", "Meno Priezvisko")
    c_platnost = st.date_input("Platnosť ponuky do", datetime.now() + timedelta(days=14))
    c_jazyk = st.selectbox("Jazyk ponuky", ["Slovenčina", "Angličtina"])
    c_styl = st.selectbox("Tón komunikácie", ["Profesionálny", "Priateľský", "Technický"])

# --- HLAVNÁ ČASŤ: VÝBER PRODUKTOV ---
df = load_brandex_feed()

if df.empty:
    st.warning("Načítavam dáta z Brandexu... Ak to trvá dlho, skontrolujte pripojenie.")
    st.stop()

col_vlavo, col_vpravo = st.columns([2, 1])

with col_vlavo:
    st.subheader("🔎 Výber produktov z katalógu")
    
    # Hľadanie stĺpca s názvom
    name_col = 'nazov_prod' if 'nazov_prod' in df.columns else df.columns[0]
    zoznam_mien = sorted(df[name_col].dropna().unique())
    
    vybrany_produkt = st.selectbox("Vyhľadajte produkt podľa názvu", zoznam_mien)
    
    # Získanie dát vybraného produktu
    p_data = df[df[name_col] == vybrany_produkt].iloc[0]
    
    st.info(f"**Aktuálny výber:** {vybrany_produkt}")
    
    col_1, col_2, col_3 = st.columns(3)
    with col_1:
        # Cena
        try:
            n_cena = float(p_data['cena_prod'])
        except:
            n_cena = 0.0
        st.metric("Nákupná cena", f"{n_cena:.2f} €")
        marza = st.slider("Vaša marža (%)", 0, 150, 35)
    
    with col_2:
        mnozstvo = st.number_input("Počet kusov", min_value=1, value=100, step=1)
        branding = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Tampónová potlač", "Bez brandingu"])
    
    with col_3:
        branding_cena = st.number_input("Cena za branding/ks (€)", min_value=0.0, value=1.0, step=0.1)
        predajna_cena = round((n_cena * (1 + marza/100)) + branding_cena, 2)
        st.subheader(f"Predaj: {predajna_cena} €/ks")
    
    if st.button("➕ PRIDAŤ DO PONUKY"):
        polozka = {
            "nazov": vybrany_produkt,
            "ks": mnozstvo,
            "cena_ks": predajna_cena,
            "branding": branding,
            "spolu": round(predajna_cena * mnozstvo, 2)
        }
        st.session_state.kosik.append(polozka)
        st.success(f"Produkt {vybrany_produkt} pridaný.")
        st.rerun()

with col_vpravo:
    st.subheader("🛒 Položky v ponuke")
    if not st.session_state.kosik:
        st.write("Košík je prázdny.")
    else:
        for idx, i in enumerate(st.session_state.kosik):
            st.write(f"**{i['nazov']}**")
            st.caption(f"{i['ks']}ks | {i['branding']} | {i['cena_ks']}€/ks")
        
        celkom_bez_dph = sum(i['spolu'] for i in st.session_state.kosik)
        st.divider()
        st.write(f"**CELKOM BEZ DPH: {celkom_bez_dph:.2f} €**")
        
        if st.button("🗑️ Vymazať košík"):
            st.session_state.kosik = []
            st.rerun()

# --- 5. AI GENEROVANIE A EXPORT ---
if st.session_state.kosik:
    st.divider()
    if st.button("✨ VYGENEROVAŤ PONUKU POMOCOU AI"):
        with st.spinner("Gemini vytvára ponuku..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Príprava zoznamu pre AI
            produkty_pre_ai = "\n".join([f"- {i['ks']}ks {i['nazov']}, branding: {i['branding']}, cena: {i['cena_ks']}€/ks" for i in st.session_state.kosik])
            
            prompt = f"""
            Si obchodný manažér spoločnosti Brandex. Vytvor oficiálnu cenovú ponuku.
            Klient: {c_firma}, Kontaktná osoba: {c_osoba}.
            Tón: {c_styl}, Jazyk: {c_jazyk}.
            Platnosť do: {c_platnost}.
            
            Zoznam produktov:
            {produkty_pre_ai}
            
            Celková cena bez DPH: {celkom_bez_dph} €.
            Uveď, že ceny sú bez DPH. Zameraj sa na kvalitu textilu a trvácnosť potlače. 
            Pridaj poďakovanie za dopyt.
            """
            
            vysledok = model.generate_content(prompt)
            st.session_state.ai_vystup = vysledok.text

    if st.session_state.ai_vystup:
        st.subheader("📝 Náhľad textu ponuky")
        # Textové pole na prípadnú manuálnu úpravu
        final_text = st.text_area("Text môžete pred stiahnutím upraviť:", value=st.session_state.ai_vystup, height=400)
        
        # Generovanie a stiahnutie PDF
        pdf_subor = create_pdf(final_text)
        
        st.download_button(
            label="📥 Stiahnuť ponuku v PDF",
            data=bytes(pdf_subor),
            file_name=f"Cenova_ponuka_Brandex_{c_firma}.pdf",
            mime="application/pdf"
        )