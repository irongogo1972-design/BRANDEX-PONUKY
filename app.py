# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os

# --- 1. KONFIGURÁCIA AI (OPRAVA 404) ---
# V roku 2026 skúsime najprv stabilný názov, ak zlyhá, vypíšeme diagnostiku
MODEL_NAME = "gemini-1.5-flash" 

API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- 2. NAČÍTANIE EXCELU (A, F, G, H, N, P, Q) ---
@st.cache_data
def load_excel_data():
    file_path = "produkty.xlsx"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        # Indexy: A=0, F=5, G=6, H=7, N=13, P=15, Q=16
        df = pd.read_excel(
            file_path, 
            usecols=[0, 5, 6, 7, 13, 15, 16], 
            names=["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_GROUP", "IMG_PRODUCT"],
            engine='openpyxl'
        )
        df = df.dropna(subset=["KOD_IT", "SKUPINOVY_NAZOV"])
        return df
    except Exception as e:
        st.error(f"Chyba pri čítaní Excelu: {e}")
        return pd.DataFrame()

# --- 3. PDF GENERÁTOR (VYLEPŠENÝ O SŤAHOVANIE OBRÁZKOV) ---
class BrandexPDF(FPDF):
    def header(self):
        try: self.image("brandex_logo.png", 10, 8, 40)
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
    
    pdf.multi_cell(0, 7, text)
    pdf.ln(10)
    
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, "Detailny rozpis produktov:", ln=True)
    
    for item in basket_items:
        pdf.set_font('DejaVu', '', 9)
        y_before = pdf.get_y()
        
        # Stiahnutie a vloženie obrázka do PDF
        img_url = item.get('img_p') if str(item.get('img_p')) != 'nan' else item.get('img_g')
        if img_url and str(img_url).startswith('http'):
            try:
                img_res = requests.get(img_url, timeout=5)
                img_bytes = io.BytesIO(img_res.content)
                pdf.image(img_bytes, x=10, y=y_before, w=25)
                pdf.set_x(40)
            except:
                pdf.set_x(10)
        else:
            pdf.set_x(10)

        info = (f"[{item['kod']}] {item['n']}\n"
                f"Farba: {item['f']} | Velkost: {item['v']}\n"
                f"Mnozstvo: {item['ks']} ks | Cena po zlave: {item['p']} EUR/ks")
        pdf.multi_cell(0, 6, info)
        pdf.ln(10)
        
    return pdf.output()

# --- 4. WEBOVÉ ROZHRANIE ---
st.set_page_config(page_title="Brandex Creator v2", layout="wide")

if 'basket' not in st.session_state: st.session_state.basket = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor")

df = load_excel_data()

if df.empty:
    st.error("❌ Súbor 'produkty.xlsx' nenájdený. Nahrajte ho na GitHub.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("👤 Klient")
    f_firma = st.text_input("Firma / Klient", "Klient s.r.o.")
    f_platnost = st.date_input("Platnosť ponuky", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])
    
    if st.button("🔍 Diagnostika AI modelov"):
        try:
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write(models)
        except: st.error("Nepodarilo sa overiť modely.")

# --- HLAVNÁ ČASŤ ---
col_1, col_2 = st.columns([2, 1])

with col_1:
    st.subheader("🛒 Výber tovaru")
    sel_name = st.selectbox("Vyberte model", sorted(df['SKUPINOVY_NAZOV'].unique()))
    sub_df = df[df['SKUPINOVY_NAZOV'] == sel_name]
    
    c1, c2 = st.columns(2)
    with c1:
        sel_color = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
    with c2:
        sel_size = st.selectbox("Veľkosť", sorted(sub_df[sub_df['FARBA'] == sel_color]['SIZE'].unique()))
    
    final_row = sub_df[(sub_df['FARBA'] == sel_color) & (sub_df['SIZE'] == sel_size)].iloc[0]
    
    # Zobrazenie obrázkov (P a Q)
    st.divider()
    i1, i2 = st.columns(2)
    with i1:
        if str(final_row['IMG_GROUP']) != 'nan':
            st.image(final_row['IMG_GROUP'], caption="Skupinový náhľad (P)", width=250)
    with i2:
        if str(final_row['IMG_PRODUCT']) != 'nan':
            st.image(final_row['IMG_PRODUCT'], caption="Detail variantu (Q)", width=250)

    # VÝPOČET CENY
    st.divider()
    v1, v2 = st.columns(2)
    with v1:
        price_n = float(final_row['PRICE']) if not pd.isna(final_row['PRICE']) else 0.0
        st.write(f"Doporučená cena: **{price_n:.2f} €**")
        zlava = st.number_input("Zľava pre klienta %", 0, 100, 0)
        ks = st.number_input("Počet kusov", 1, 10000, 100)
    with v2:
        brand = st.selectbox("Branding", ["Bez potlače", "Sieťotlač", "Výšivka", "DTF", "Laser"])
        b_c = st.number_input("Cena brandingu/ks €", value=1.2 if brand != "Bez potlače" else 0.0)
        
        # Logika: (Cena * (1 - zlava/100)) + branding
        final_unit_price = round((price_n * (1 - zlava/100)) + b_c, 2)
        st.subheader(f"Výsledná cena: {final_unit_price} €/ks")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            st.session_state.basket.append({
                "kod": final_row['KOD_IT'], "n": sel_name, "f": sel_color, "v": sel_size, 
                "ks": ks, "p": final_unit_price, "s": round(final_unit_price*ks, 2),
                "img_g": final_row['IMG_GROUP'], "img_p": final_row['IMG_PRODUCT']
            })
            st.rerun()

with col_2:
    st.subheader("📋 Košík")
    for i in st.session_state.basket:
        st.write(f"**{i['n']}** ({i['f']})")
        st.caption(f"{i['ks']}ks x {i['p']}€ = {i['s']}€")
    
    if st.session_state.basket:
        total = sum(i['s'] for i in st.session_state.basket)
        st.write(f"### Spolu: {total:.2f} € bez DPH")
        if st.button("🗑️ Vymazať košík"):
            st.session_state.basket = []
            st.rerun()

# --- 5. NÁHĽAD A TLAČ ---
if st.session_state.basket:
    st.divider()
    st.subheader("📝 Náhľad a generovanie ponuky")
    
    if st.button("🤖 Vygenerovať sprievodný text (AI)"):
        try:
            # Oprava: Používame priame volanie bez v1beta
            model = genai.GenerativeModel(MODEL_NAME)
            prods = "\n".join([f"- {i['ks']}ks {i['n']} ({i['f']}), cena {i['p']}€/ks" for i in st.session_state.basket])
            prompt = f"Si obchodník Brandex. Vytvor ponuku pre {f_firma}. Jazyk: {f_jazyk}. Produkty:\n{prods}\nCelkom: {total}€ bez DPH."
            
            response = model.generate_content(prompt)
            st.session_state.ai_text = response.text
        except Exception as e:
            st.error(f"AI Chyba: {e}")

    if st.session_state.ai_text:
        # Profesionálny náhľad
        with st.container(border=True):
            st.markdown(f"**Dátum:** {datetime.now().strftime('%d.%m.%Y')} | **Platnosť:** {f_platnost.strftime('%d.%m.%Y')}")
            st.markdown(f"**Odberateľ:** {f_firma}")
            st.write("---")
            st.write(st.session_state.ai_text)
            st.write("---")
            for item in st.session_state.basket:
                c_img, c_txt = st.columns([1, 4])
                with c_img:
                    img = item['img_p'] if str(item['img_p']) != 'nan' else item['img_g']
                    if img and str(img).startswith('http'): st.image(img, width=100)
                with c_txt:
                    st.write(f"**{item['n']}** (Kód: {item['kod']})")
                    st.caption(f"Farba: {item['f']} | Veľkosť: {item['v']} | Cena: {item['p']} €/ks")

        # Tlač do PDF
        pdf_data = generate_pdf(st.session_state.ai_text, st.session_state.basket)
        st.download_button("📥 Stiahnuť PDF (pre tlač)", data=bytes(pdf_data), file_name=f"Ponuka_{f_firma}.pdf", mime="application/pdf")