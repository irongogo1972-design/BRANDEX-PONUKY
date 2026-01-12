# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os

# --- 1. KONFIGURÁCIA AI (NAJNOVŠÍ STABILNÝ MODEL) ---
# Používame Gemini 2.0 Flash - je najnovší a najrýchlejší pre rok 2026
MODEL_NAME = "gemini-2.0-flash" 

API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        # Test, či model existuje
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        st.error(f"Chyba AI konfigurácie: {e}")
else:
    st.error("⚠️ Do Streamlit Secrets vložte nový GEMINI_API_KEY z nového projektu!")

# --- 2. NAČÍTANIE EXCELU (A, F, G, H, N, P, Q) ---
@st.cache_data
def load_excel_data():
    file_path = "produkty.xlsx"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    try:
        df = pd.read_excel(
            file_path, 
            usecols=[0, 5, 6, 7, 13, 15, 16], 
            names=["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "PRICE", "IMG_GROUP", "IMG_PRODUCT"],
            engine='openpyxl'
        )
        return df.dropna(subset=["KOD_IT", "SKUPINOVY_NAZOV"])
    except Exception as e:
        st.error(f"Chyba pri čítaní Excelu: {e}")
        return pd.DataFrame()

# --- 3. PDF GENERÁTOR ---
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
    
    pdf.multi_cell(0, 7, text)
    pdf.ln(10)
    
    for item in basket_items:
        y_curr = pdf.get_y()
        # Ak je Q prázdne, použije P
        img = item['img_p'] if str(item['img_p']) != 'nan' else item['img_g']
        if img and str(img).startswith('http'):
            try:
                res = requests.get(img, timeout=5)
                pdf.image(io.BytesIO(res.content), x=10, y=y_curr, w=25)
                pdf.set_x(40)
            except: pdf.set_x(10)
        
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(0, 5, f"{item['n']} (Kód: {item['kod']})", ln=True)
        pdf.set_font('DejaVu', '', 9)
        pdf.cell(0, 5, f"Variant: {item['f']} | Velkost: {item['v']} | Cena: {item['p']} EUR/ks", ln=True)
        pdf.ln(10)
    return pdf.output()

# --- 4. WEBOVÉ ROZHRANIE ---
st.set_page_config(page_title="Brandex Creator", layout="wide")

if 'basket' not in st.session_state: st.session_state.basket = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor")

df = load_excel_data()
if df.empty:
    st.error("❌ Nahrajte 'produkty.xlsx' na GitHub.")
    st.stop()

# SIDEBAR
with st.sidebar:
    st.header("👤 Klient")
    f_firma = st.text_input("Firma / Klient", "Meno firmy")
    f_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

# VÝBER
col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("🛒 Výber tovaru")
    sel_name = st.selectbox("Vyberte model", sorted(df['SKUPINOVY_NAZOV'].unique()))
    sub_df = df[df['SKUPINOVY_NAZOV'] == sel_name]
    
    c1, c2 = st.columns(2)
    with c1: sel_color = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
    with c2: sel_size = st.selectbox("Veľkosť", sorted(sub_df[sub_df['FARBA'] == sel_color]['SIZE'].unique()))
    
    final_row = sub_df[(sub_df['FARBA'] == sel_color) & (sub_df['SIZE'] == sel_size)].iloc[0]
    
    # Náhľady obrázkov
    i1, i2 = st.columns(2)
    with i1: 
        if str(final_row['IMG_GROUP']) != 'nan': st.image(final_row['IMG_GROUP'], caption="Skupinový (P)", width=200)
    with i2:
        if str(final_row['IMG_PRODUCT']) != 'nan': st.image(final_row['IMG_PRODUCT'], caption="Variant (Q)", width=200)

    # Cena: Načítame z N, zadávame zľavu
    st.divider()
    v1, v2 = st.columns(2)
    with v1:
        price_n = float(final_row['PRICE']) if not pd.isna(final_row['PRICE']) else 0.0
        st.write(f"Doporučená cena (N): **{price_n:.2f} €**")
        zlava = st.number_input("Zľava %", 0, 100, 0)
        ks = st.number_input("Množstvo ks", 1, 10000, 100)
    with v2:
        brand = st.selectbox("Branding", ["Bez potlače", "Sieťotlač", "Výšivka", "DTF", "Laser"])
        b_c = st.number_input("Cena za branding/ks €", value=1.2 if brand != "Bez potlače" else 0.0)
        # Výpočet: (N * (1 - zľava/100)) + branding
        p_ks = round((price_n * (1 - zlava/100)) + b_c, 2)
        st.subheader(f"Cena: {p_ks} €/ks")
        if st.button("➕ PRIDAŤ DO PONUKY"):
            st.session_state.basket.append({
                "kod": final_row['KOD_IT'], "n": sel_name, "f": sel_color, "v": sel_size, 
                "ks": ks, "p": p_ks, "s": round(p_ks*ks, 2), "img_g": final_row['IMG_GROUP'], "img_p": final_row['IMG_PRODUCT']
            })
            st.rerun()

with col2:
    st.subheader("📋 Obsah")
    for i in st.session_state.basket:
        st.write(f"**{i['n']}** ({i['f']})")
        st.caption(f"{i['ks']}ks x {i['p']}€ = {i['s']}€")
    if st.session_state.basket:
        total = sum(i['s'] for i in st.session_state.basket)
        st.write(f"### Spolu: {total:.2f} € bez DPH")
        if st.button("🗑️ Vymazať"):
            st.session_state.basket = []
            st.rerun()

# --- NÁHĽAD A GENERATOR ---
if st.session_state.basket:
    st.divider()
    if st.button("✨ Vygenerovať text ponuky (AI)"):
        try:
            gen_model = genai.GenerativeModel(MODEL_NAME)
            prods = "\n".join([f"- {i['ks']}ks {i['n']} ({i['f']}), cena {i['p']}€" for i in st.session_state.basket])
            prompt = f"Si obchodník Brandex. Napíš profi ponuku pre {f_firma}. Jazyk: {f_jazyk}. Produkty:\n{prods}\nCelkom: {total}€ bez DPH."
            response = gen_model.generate_content(prompt)
            st.session_state.ai_text = response.text
        except Exception as e:
            st.error(f"AI Chyba: {e}. Skontrolujte nový API kľúč.")

    if st.session_state.ai_text:
        # VIZUÁLNY NÁHĽAD
        with st.container(border=True):
            st.image("brandex_logo.png", width=150)
            st.write(f"**Dátum:** {datetime.now().strftime('%d.%m.%Y')} | **Platnosť:** {f_platnost.strftime('%d.%m.%Y')}")
            st.write(f"**Odberateľ:** {f_firma}")
            st.write("---")
            st.write(st.session_state.ai_text)
            st.write("---")
            for item in st.session_state.basket:
                c_img, c_desc = st.columns([1, 3])
                with c_img:
                    img = item['img_p'] if str(item['img_p']) != 'nan' else item['img_g']
                    if img and str(img).startswith('http'): st.image(img, width=100)
                with c_desc:
                    st.write(f"**{item['n']}** (Kód: {item['kod']})")
                    st.write(f"Variant: {item['f']} | Veľkosť: {item['v']}")
                    st.write(f"Množstvo: {item['ks']} ks | Cena: **{item['p']} €/ks**")
            st.write(f"### CELKOVÁ SUMA: {total:.2f} € bez DPH")

        pdf_data = generate_pdf(st.session_state.ai_text, st.session_state.basket)
        st.download_button("📥 Stiahnuť PDF", data=bytes(pdf_data), file_name=f"Ponuka_{f_firma}.pdf")