# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os

# --- 1. KONFIGURÁCIA AI ---
MODEL_NAME = "gemini-1.5-flash" 
API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    genai.configure(api_key=API_KEY)

# --- 2. NAČÍTANIE EXCELU ---
@st.cache_data
def load_excel_data():
    file_path = "produkty.xlsx"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    
    try:
        # Načítame stĺpce A, F, G, H, P (indexy 0, 5, 6, 7, 15)
        df = pd.read_excel(
            file_path, 
            usecols=[0, 5, 6, 7, 15], 
            names=["KOD_IT", "SKUPINOVY_NAZOV", "FARBA", "SIZE", "IMG_GROUP"],
            engine='openpyxl'
        )
        # Vyčistenie
        df = df.dropna(subset=["KOD_IT", "SKUPINOVY_NAZOV"])
        return df
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
        # Ochrana pred chýbajúcimi kľúčmi v starých reláciách
        n = item.get('n', 'Produkt')
        f = item.get('f', '-')
        v = item.get('v', '-')
        p = item.get('p', 0)
        img = item.get('img', None)
        
        y_pred = pdf.get_y()
        if img and str(img) != 'nan':
            try:
                pdf.image(img, x=10, y=y_pred, w=20)
                pdf.set_x(35)
            except:
                pdf.set_x(10)
        
        pdf.multi_cell(0, 6, f"{n}\nFarba: {f}, Velkost: {v}\nCena: {p} EUR/ks")
        pdf.ln(5)
    return pdf.output()

# --- 4. WEBOVÉ ROZHRANIE ---
st.set_page_config(page_title="Brandex Pro", layout="wide")

# POISTKA: Ak sa zmenila štruktúra košíka, vymažeme starý
if 'basket' in st.session_state:
    if len(st.session_state.basket) > 0 and 'f' not in st.session_state.basket[0]:
        st.session_state.basket = []

if 'basket' not in st.session_state: st.session_state.basket = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor")

df = load_excel_data()

if df.empty:
    st.error("❌ Súbor 'produkty.xlsx' nebol nájdený alebo ho nebolo možné načítať.")
    st.stop()

# SIDEBAR
with st.sidebar:
    st.header("👤 Klient")
    f_firma = st.text_input("Firma", "Klient s.r.o.")
    f_platnost = st.date_input("Platnosť", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

# VÝBER
col_sel1, col_sel2 = st.columns([2, 1])

with col_sel1:
    st.subheader("🛒 Výber tovaru")
    prod_list = sorted(df['SKUPINOVY_NAZOV'].unique())
    selected_prod = st.selectbox("Produkt", prod_list)
    
    sub_df = df[df['SKUPINOVY_NAZOV'] == selected_prod]
    
    c1, c2 = st.columns(2)
    with c1:
        color_list = sorted(sub_df['FARBA'].unique())
        sel_color = st.selectbox("Farba", color_list)
    with c2:
        size_list = sorted(sub_df[sub_df['FARBA'] == sel_color]['SIZE'].unique())
        sel_size = st.selectbox("Veľkosť", size_list)
    
    final_item = sub_df[(sub_df['FARBA'] == sel_color) & (sub_df['SIZE'] == sel_size)].iloc[0]
    
    st.divider()
    v1, v2 = st.columns([1, 2])
    with v1:
        if str(final_item['IMG_GROUP']) != 'nan':
            st.image(final_item['IMG_GROUP'], width=200)
    with v2:
        st.write(f"**Kód:** {final_item['KOD_IT']}")
        n_cena = st.number_input("Nákupná cena €", value=2.0, step=0.1)
        marza = st.number_input("Marža %", value=35)
        ks = st.number_input("Množstvo ks", min_value=1, value=100)
        brand = st.selectbox("Branding", ["Sieťotlač", "Výšivka", "DTF", "Laser", "Bez potlače"])
        b_c = st.number_input("Cena brandingu/ks €", value=1.0)
        
        p_ks = round((n_cena * (1 + marza/100)) + b_c, 2)
        st.subheader(f"Cena: {p_ks} €/ks")
        
        if st.button("➕ PRIDAŤ"):
            st.session_state.basket.append({
                "kod": final_item['KOD_IT'], "n": selected_prod, "f": sel_color, 
                "v": sel_size, "ks": ks, "p": p_ks, "s": round(p_ks*ks, 2),
                "img": final_item['IMG_GROUP']
            })
            st.rerun()

with col_sel2:
    st.subheader("📋 Košík")
    for i in st.session_state.basket:
        # Ochrana pred chýbajúcimi kľúčmi v starých reláciách pri zobrazení
        st.write(f"**{i.get('n', 'Item')}** ({i.get('f', '-')})")
        st.caption(f"{i.get('ks', 0)}ks x {i.get('p', 0)}€")
    
    if st.session_state.basket:
        total = sum(i.get('s', 0) for i in st.session_state.basket)
        st.write(f"**Spolu: {total:.2f} €**")
        if st.button("🗑️ Vymazať"):
            st.session_state.basket = []
            st.rerun()

# AI
if st.session_state.basket:
    st.divider()
    if st.button("✨ GENEROVAŤ PONUKU"):
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            txt = "\n".join([f"- {i['ks']}ks {i['n']} ({i['f']}), cena {i['p']}€/ks" for i in st.session_state.basket])
            prompt = f"Si obchodník Brandex. Vytvor ponuku pre {f_firma}. Produkty:\n{txt}\nJazyk: {f_jazyk}."
            st.session_state.ai_text = model.generate_content(prompt).text
        except Exception as e:
            st.error(f"AI Chyba: {e}")

if st.session_state.ai_text:
    final_txt = st.text_area("Upraviť text:", value=st.session_state.ai_text, height=200)
    pdf_gen = generate_pdf(final_txt, st.session_state.basket)
    st.download_button("📥 Stiahnuť PDF", data=bytes(pdf_gen), file_name=f"Ponuka_{f_firma}.pdf")