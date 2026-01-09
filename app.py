import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
import io
from fpdf import FPDF
from datetime import datetime, timedelta

# --- 1. NASTAVENIA A BEZPE»NOSç ---
# Odpor˙Ëame v Streamlit Cloud pouûiù st.secrets["GEMINI_API_KEY"]
# Pre lok·lne testovanie mÙûete kæ˙Ë vloûiù priamo sem:
API_KEY = st.secrets.get("GEMINI_API_KEY", "TU_VLOZTE_SVOJ_API_KLUC")
genai.configure(api_key=API_KEY)

# URL Feed (Brandex)
FEED_URL = "https://produkty.brandex.sk/index.cfm?module=Brandex&page=DownloadFile&File=DataExport"

# --- 2. FUNKCIE PRE D¡TA A LOGIKU ---
@st.cache_data(ttl=3600)
def load_brandex_feed():
    try:
        response = requests.get(FEED_URL, timeout=10)
        # NaËÌtanie XML d·t z Brandexu
        df = pd.read_xml(io.BytesIO(response.content))
        # Premenovanie stÂpcov podæa beûnej ötrukt˙ry (upravte podæa re·lneho XML)
        # Predpoklad·me: Name, Price, ImageURL, Description
        return df
    except Exception as e:
        st.error(f"Nepodarilo sa naËÌtaù feed: {e}")
        return pd.DataFrame()

def generate_ai_text(klient, polozky, styl, jazyk, platnost):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    items_list = ""
    for p in polozky:
        items_list += f"- {p['mnozstvo']}ks {p['nazov']}, branding: {p['branding']}, cena: {p['predajna_cena']} Ä/ks bez DPH\n"

    system_prompt = "Si obchodn˝ z·stupca firmy Brandex. TvorÌö profesion·lne cenovÈ ponuky na reklamn˝ textil a predmety."
    
    user_prompt = f"""
    Vytvor text ponuky pre klienta {klient['firma']}.
    Kontaktn· osoba: {klient['osoba']}.
    Jazyk: {jazyk}. ät˝l: {styl}.
    
    Poloûky:
    {items_list}
    
    Platnosù ponuky: do {platnost}
    ZahrÚ inform·ciu, ûe ceny s˙ uvedenÈ bez DPH 20%. 
    SpomeÚ, ûe Brandex si zaklad· na kvalite brandingu a r˝chlom dodanÌ.
    """
    
    response = model.generate_content([system_prompt, user_prompt])
    return response.text

# --- 3. PDF GENER¡TOR (SlovenËina) ---
class BrandexPDF(FPDF):
    def header(self):
        try:
            self.image("brandex_logo.png", 10, 8, 45)
        except:
            self.set_font('helvetica', 'B', 16)
            self.cell(0, 10, 'BRANDEX', ln=True)
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Strana {self.page_no()}', align='C')

def create_pdf(text, klient_firma):
    pdf = BrandexPDF()
    pdf.add_page()
    
    # REGISTR¡CIA FONTU (S˙bor DejaVuSans.ttf musÌ byù v prieËinku)
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 11)
    except:
        pdf.set_font('helvetica', '', 11) # Z·loûn˝ font bez diakritiky
        
    pdf.multi_cell(0, 7, text)
    return pdf.output()

# --- 4. WEBOV… ROZHRANIE ---
st.set_page_config(page_title="Brandex AI Ponuky", layout="wide", page_icon="??")

# CSS pre krajöÌ vzhæad
st.markdown("""<style> .stButton>button { width: 100%; border-radius: 5px; height: 3em; } </style>""", unsafe_allow_html=True)

if 'kosik' not in st.session_state:
    st.session_state.kosik = []

st.title("?? Brandex Inteligentn· Ponuka")

# SIDEBAR: ⁄DAJE O KLIENTOVI
with st.sidebar:
    st.image("brandex_logo.png", width=200)
    st.header("?? ⁄daje o klientovi")
    k_firma = st.text_input("Firma / N·zov")
    k_osoba = st.text_input("Kontaktn· osoba")
    k_email = st.text_input("Email")
    platnost_ponuky = st.date_input("Platnosù do", datetime.now() + timedelta(days=14))
    jazyk_volba = st.selectbox("Jazyk", ["SlovenËina", "AngliËtina"])
    styl_volba = st.selectbox("TÛn ponuky", ["Profesion·lny", "Priateæsk˝", "Technick˝"])

# HLAVN¡ »ASç: V›BER PRODUKTOV
df = load_brandex_feed()

col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("?? V˝ber produktu z Brandex katalÛgu")
    if not df.empty:
        # Predpoklad·me stÂpec 'Name' v XML. Ak sa vol· inak, zmeÚte ho tu.
        search_col = 'Name' if 'Name' in df.columns else df.columns[0]
        vsetky_produkty = df[search_col].unique()
        vybrany_prod_meno = st.selectbox("Vyhæadajte produkt", vsetky_produkty)
        
        prod_info = df[df[search_col] == vybrany_prod_meno].iloc[0]
        
        st.info(f"**VybranÈ:** {vybrany_prod_meno}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            nakup_cena = float(prod_info.get('Price', 0))
            st.metric("N·kupn· cena", f"{nakup_cena} Ä")
            marza = st.slider("Marûa %", 0, 200, 35)
        with c2:
            mnozstvo = st.number_input("PoËet kusov", min_value=1, value=50)
            branding_typ = st.selectbox("TechnolÛgia", ["Bez brandingu", "SieùotlaË", "V˝öivka", "DTF", "Laser", "UV tlaË"])
        with c3:
            branding_cena = st.number_input("Cena za branding/ks (Ä)", min_value=0.0, value=1.0, step=0.1)
            predajna = round((nakup_cena * (1 + marza/100)) + branding_cena, 2)
            st.metric("Predajn· cena / ks", f"{predajna} Ä")

        if st.button("? Pridaù do ponuky"):
            st.session_state.kosik.append({
                "nazov": vybrany_prod_meno,
                "mnozstvo": mnozstvo,
                "predajna_cena": predajna,
                "branding": branding_typ,
                "spolu": round(predajna * mnozstvo, 2)
            })
            st.toast("Produkt pridan˝!")

with col_b:
    st.subheader("?? Aktu·lna ponuka")
    if st.session_state.kosik:
        for idx, item in enumerate(st.session_state.kosik):
            st.write(f"**{item['nazov']}** ({item['mnozstvo']} ks)")
            st.caption(f"{item['branding']} | {item['predajna_cena']} Ä/ks | Spolu: {item['spolu']} Ä")
        
        celkom_bez_dph = sum(i['spolu'] for i in st.session_state.kosik)
        st.divider()
        st.write(f"**Celkom bez DPH: {celkom_bez_dph:.2f} Ä**")
        
        if st.button("??? Vymazaù vöetko"):
            st.session_state.kosik = []
            st.rerun()
    else:
        st.write("Ponuka je pr·zdna.")

# GENER¡TOR
if st.session_state.kosik:
    st.divider()
    if st.button("? VYGENEROVAç PONUKU POMOCOU AI"):
        klient_data = {"firma": k_firma, "osoba": k_osoba, "email": k_email}
        ai_vysledok = generate_ai_text(klient_data, st.session_state.kosik, styl_volba, jazyk_volba, platnost_ponuky)
        st.session_state.final_text = ai_vysledok
        
    if 'final_text' in st.session_state:
        st.subheader("?? N·hæad textu")
        st.text_area("Text mÙûete manu·lne upraviù", value=st.session_state.final_text, height=300, key="edit_text")
        
        pdf_data = create_pdf(st.session_state.edit_text, k_firma)
        st.download_button(
            label="?? Stiahnuù PDF ponuku",
            data=bytes(pdf_data),
            file_name=f"Cenova_ponuka_Brandex_{k_firma}.pdf",
            mime="application/pdf"
        )