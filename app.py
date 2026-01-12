# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from fpdf import FPDF
from datetime import datetime, timedelta
import io

# --- 1. KONFIGURÁCIA AI ---
MODEL_NAME = "gemini-1.5-flash" 
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- 2. NAČÍTANIE EXCELU (MAPOVANIE A, F, G, H, P) ---
@st.cache_data
def load_excel_data():
    try:
        # Načítame konkrétne stĺpce podľa indexov (0=A, 5=F, 6=G, 7=H, 15=P)
        df = pd.read_excel(
            "produkty.xlsx", 
            usecols=[0, 5, 6, 7, 15], 
            names=["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "IMG_GROUP"],
            engine='openpyxl'
        )
        # Vyčistenie dát
        df = df.dropna(subset=["KOD_IT", "SKUPINOVY_NAZOV"])
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except Exception as e:
        st.error(f"Chyba pri načítaní Excel súboru: {e}")
        return pd.DataFrame()

# --- 3. PDF GENERÁTOR S OBRÁZKOM ---
class BrandexPDF(FPDF):
    def header(self):
        try: self.image("brandex_logo.png", 10, 8, 45)
        except: pass
        self.ln(20)

def generate_pdf(text, basket_items):
    pdf = BrandexPDF()
    pdf.add_page()
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 11)
    except:
        pdf.set_font('helvetica', '', 11)
    
    # Hlavný text od AI
    pdf.multi_cell(0, 7, text)
    
    # Pridanie sekcie s detailmi produktov (vrátane miniatúr obrázkov)
    pdf.ln(10)
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, "Detailný rozpis položiek:", ln=True)
    pdf.set_font('DejaVu', '', 9)
    
    for item in basket_items:
        x_pos = pdf.get_x()
        y_pos = pdf.get_y()
        
        # Ak existuje URL obrázka, skúsime ho vložiť
        if item['img'] and str(item['img']) != 'nan':
            try:
                pdf.image(item['img'], x=x_pos, y=y_pos, w=20)
                pdf.set_x(x_pos + 25) # Posun textu vedľa obrázka
            except:
                pdf.cell(25, 10, "[Bez obrázka]")
        
        info = f"{item['n']} | Farba: {item['f']} | Veľkosť: {item['v']} | Cena: {item['p']} EUR/ks"
        pdf.multi_cell(0, 7, info)
        pdf.ln(15) # Medzera medzi produktmi

    return pdf.output()

# --- 4. WEBOVÉ ROZHRANIE ---
st.set_page_config(page_title="Brandex Pro 2026", layout="wide")

if 'basket' not in st.session_state: st.session_state.basket = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👔 Brandex Inteligentný Generátor (Excel Verzia)")

df = load_excel_data()

# SIDEBAR
with st.sidebar:
    st.header("👤 Klient")
    f_firma = st.text_input("Firma / Klient", "Vzorová Firma s.r.o.")
    f_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

# VÝBER PRODUKTU
if not df.empty:
    st.subheader("🛒 Výber tovaru")
    
    # 1. Výber produktu (Skupinový názov)
    products = sorted(df['SKUPINOVY_NAZOV'].unique())
    selected_prod = st.selectbox("Vyberte produkt", products)
    
    # Filtrovanie pre farby a veľkosti
    filtered = df[df['SKUPINOVY_NAZOV'] == selected_prod]
    
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_color = st.selectbox("Farba", sorted(filtered['FARBA'].unique()))
    with c2:
        # Filtrujeme veľkosti podľa farby
        sizes = sorted(filtered[filtered['FARBA'] == selected_color]['SIZE'].unique())
        selected_size = st.selectbox("Veľkosť", sizes)
    
    # Finálne dáta konkrétneho kusu
    final_row = filtered[(filtered['FARBA'] == selected_color) & (filtered['SIZE'] == selected_size)].iloc[0]
    
    # Zobrazenie náhľadu
    st.divider()
    v1, v2 = st.columns([1, 2])
    with v1:
        if str(final_row['IMG_GROUP']) != 'nan':
            st.image(final_row['IMG_GROUP'], caption=selected_prod, width=250)
    with v2:
        st.write(f"**Kód:** {final_row['KOD_IT']}")
        st.write(f"**Názov:** {selected_prod}")
        st.write(f"**Variant:** {selected_color} / {selected_size}")
        
        # Nacenenie
        n_cena = st.number_input("Nákupná cena bez DPH €", value=5.00, step=0.1) # Excel často nemá nákupnú cenu
        marza = st.number_input("Marža %", value=35)
        ks = st.number_input("Počet kusov", min_value=1, value=100)
        brand_type = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF potlač", "Laser", "Bez potlače"])
        b_cena = st.number_input("Cena za branding/ks €", value=1.20 if brand_type != "Bez potlače" else 0.0)
        
        predaj_ks = round((n_cena * (1 + marza/100)) + b_cena, 2)
        st.subheader(f"Predaj: {predaj_ks} €/ks")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            st.session_state.basket.append({
                "kod": final_row['KOD_IT'], "n": selected_prod, "f": selected_color, 
                "v": selected_size, "ks": ks, "p": predaj_ks, 
                "s": round(predaj_ks * ks, 2), "b": brand_type, "img": final_row['IMG_GROUP']
            })
            st.rerun()

# KOŠÍK A AI
if st.session_state.basket:
    st.divider()
    st.subheader("📋 Rozpracovaná ponuka")
    for i in st.session_state.basket:
        st.write(f"- **{i['n']}** ({i['f']}, {i['v']}) | {i['ks']}ks | {i['p']}€/ks -> **{i['s']} €**")
    
    celkom = sum(i['s'] for i in st.session_state.basket)
    st.write(f"### Spolu bez DPH: {celkom:.2f} €")
    
    if st.button("✨ VYGENEROVAŤ PONUKU"):
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            prods_ai = "\n".join([f"- {i['ks']}ks {i['n']} ({i['f']}, {i['v']}), branding: {i['b']}, cena: {i['p']}€/ks" for i in st.session_state.basket])
            prompt = f"Si obchodník Brandex. Vytvor ponuku pre {f_firma}. Produkty:\n{prods_ai}\nSpolu: {celkom}€ bez DPH. Jazyk: {f_jazyk}."
            st.session_state.ai_text = model.generate_content(prompt).text
        except Exception as e:
            st.error(f"AI Chyba: {e}")

if st.session_state.ai_text:
    st.divider()
    f_text = st.text_area("Finalizácia textu:", value=st.session_state.ai_text, height=300)
    pdf_data = generate_pdf(f_text, st.session_state.basket)
    st.download_button("📥 Stiahnuť PDF s obrázkami", data=bytes(pdf_data), file_name=f"Ponuka_Brandex_{f_firma}.pdf")
else:
    st.error("Excel tabuľka 'produkty.xlsx' nebola nájdená alebo je prázdna.")