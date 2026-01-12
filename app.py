# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from fpdf import FPDF
from datetime import datetime, timedelta
import io
import os

# --- 1. KONFIGURÁCIA AI (OPRAVA 404 CHYBY) ---
# Použijeme stabilný názov modelu pre rok 2026
MODEL_NAME = "gemini-1.5-flash" 

API_KEY = st.secrets.get("GEMINI_API_KEY", "")
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception as e:
        st.error(f"Chyba konfigurácie AI: {e}")

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
        # Uistite sa, že DejaVuSans.ttf je v priečinku na GitHube
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVu', '', 11)
    except:
        pdf.set_font('helvetica', '', 11)
    
    # AI Text ponuky
    pdf.multi_cell(0, 7, text)
    pdf.ln(10)
    
    # Tabuľka produktov
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, "Rozpis produktov:", ln=True)
    pdf.set_font('DejaVu', '', 9)
    
    for item in basket_items:
        y_start = pdf.get_y()
        # Obrázok variantu (stĺpec Q) má prednosť v PDF
        img_url = item.get('img_p') if str(item.get('img_p')) != 'nan' else item.get('img_g')
        
        if img_url and str(img_url) != 'nan':
            try:
                pdf.image(img_url, x=10, y=y_start, w=25)
                pdf.set_x(40)
            except:
                pdf.set_x(10)
        
        info = (f"[{item['kod']}] {item['n']}\n"
                f"Farba: {item['f']} | Velkost: {item['v']}\n"
                f"Mnozstvo: {item['ks']} ks | Cena: {item['p']} EUR/ks")
        pdf.multi_cell(0, 6, info)
        pdf.ln(15)
        
    return pdf.output()

# --- 4. WEBOVÉ ROZHRANIE ---
st.set_page_config(page_title="Brandex Creator", layout="wide")

# Inicializácia relácie
if 'basket' not in st.session_state: st.session_state.basket = []
if 'ai_text' not in st.session_state: st.session_state.ai_text = ""

st.title("👕 Brandex Inteligentný Generátor Ponúk")

df = load_excel_data()

if df.empty:
    st.error("❌ Súbor 'produkty.xlsx' nebol nájdený. Nahrajte ho na GitHub.")
    st.stop()

# --- SIDEBAR: KLIENT ---
with st.sidebar:
    st.header("👤 Údaje o klientovi")
    f_firma = st.text_input("Firma / Klient", "Klient s.r.o.")
    f_platnost = st.date_input("Platnosť do", datetime.now() + timedelta(days=14))
    f_jazyk = st.selectbox("Jazyk", ["Slovenčina", "Angličtina"])

# --- HLAVNÁ ČASŤ: VÝBER ---
col_selection, col_basket = st.columns([2, 1])

with col_selection:
    st.subheader("🛒 Výber tovaru")
    
    # 1. Filtrovanie podľa názvu
    prod_names = sorted(df['SKUPINOVY_NAZOV'].unique())
    sel_name = st.selectbox("Vyberte model", prod_names)
    sub_df = df[df['SKUPINOVY_NAZOV'] == sel_name]
    
    c1, c2 = st.columns(2)
    with c1:
        sel_color = st.selectbox("Farba", sorted(sub_df['FARBA'].unique()))
    with c2:
        sel_size = st.selectbox("Veľkosť", sorted(sub_df[sub_df['FARBA'] == sel_color]['SIZE'].unique()))
    
    final_row = sub_df[(sub_df['FARBA'] == sel_color) & (sub_df['SIZE'] == sel_size)].iloc[0]
    
    # --- OBRÁZKY ---
    st.divider()
    img_col1, img_col2 = st.columns(2)
    with img_col1:
        if str(final_row['IMG_GROUP']) != 'nan':
            st.image(final_row['IMG_GROUP'], caption="Skupinový obrázok", use_container_width=True)
    with img_col2:
        if str(final_row['IMG_PRODUCT']) != 'nan':
            st.image(final_row['IMG_PRODUCT'], caption="Obrázok variantu", use_container_width=True)

    # --- VÝPOČET CENY (ZĽAVA Z N) ---
    st.divider()
    v1, v2 = st.columns(2)
    with v1:
        # Cena zo stĺpca N
        retail_price = float(final_row['PRICE']) if not pd.isna(final_row['PRICE']) else 0.0
        st.write(f"Doporučená cena (bez DPH): **{retail_price:.2f} €**")
        zlava = st.number_input("Zľava pre klienta %", min_value=0, max_value=100, value=0)
        ks = st.number_input("Počet kusov (ks)", min_value=1, value=100)
    with v2:
        brand = st.selectbox("Typ brandingu", ["Bez potlače", "Sieťotlač", "Výšivka", "DTF", "Laser"])
        b_c = st.number_input("Cena za branding/ks €", value=1.2 if brand != "Bez potlače" else 0.0)
        
        # Logika: (Cena * (1 - zlava/100)) + branding
        predaj_ks = round((retail_price * (1 - zlava/100)) + b_c, 2)
        st.subheader(f"Výsledná cena: {predaj_ks} €/ks")
        
        if st.button("➕ PRIDAŤ DO PONUKY"):
            st.session_state.basket.append({
                "kod": final_row['KOD_IT'], "n": sel_name, "f": sel_color, "v": sel_size, 
                "ks": ks, "p": predaj_ks, "s": round(predaj_ks*ks, 2), 
                "img_g": final_row['IMG_GROUP'], "img_p": final_row['IMG_PRODUCT']
            })
            st.rerun()

with col_basket:
    st.subheader("📋 Obsah ponuky")
    for i in st.session_state.basket:
        st.write(f"**{i['n']}** ({i['f']})")
        st.caption(f"{i['ks']}ks x {i['p']}€ = {i['s']}€")
    
    if st.session_state.basket:
        total = sum(i['s'] for i in st.session_state.basket)
        st.write(f"### Spolu: {total:.2f} € bez DPH")
        if st.button("🗑️ Vymazať košík"):
            st.session_state.basket = []
            st.rerun()

# --- 5. NÁHĽAD A GENEROVANIE ---
if st.session_state.basket:
    st.divider()
    st.subheader("✨ Generovanie a náhľad ponuky")
    
    if st.button("🧠 Vytvoriť text ponuky pomocou AI"):
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            prods_info = "\n".join([f"- {i['ks']}ks {i['n']} ({i['f']}, {i['v']}), cena {i['p']}€/ks" for i in st.session_state.basket])
            prompt = f"Si obchodník firmy Brandex. Vytvor profesionálnu ponuku pre {f_firma}. Jazyk: {f_jazyk}. Produkty:\n{prods_info}\nCelková suma: {total} EUR bez DPH."
            
            response = model.generate_content(prompt)
            st.session_state.ai_text = response.text
        except Exception as e:
            st.error(f"Chyba AI: {e}. Skúste neskôr.")

    if st.session_state.ai_text:
        # NÁHĽAD PONUKY (PRE PRINT)
        with st.container(border=True):
            st.markdown(f"### NÁHĽAD PONUKY - {f_firma}")
            st.write(f"**Dátum:** {datetime.now().strftime('%d.%m.%Y')}")
            st.write(f"**Platnosť do:** {f_platnost.strftime('%d.%m.%Y')}")
            st.write("---")
            st.write(st.session_state.ai_text)
            st.write("---")
            for item in st.session_state.basket:
                col1, col2 = st.columns([1, 4])
                with col1:
                    img = item['img_p'] if str(item['img_p']) != 'nan' else item['img_g']
                    if img and str(img) != 'nan': st.image(img, width=80)
                with col2:
                    st.write(f"**{item['n']}** (Kód: {item['kod']})")
                    st.write(f"Farba: {item['f']} | Veľkosť: {item['v']} | Množstvo: {item['ks']} ks")
                    st.write(f"Jednotková cena: {item['p']} € | **Spolu: {item['s']} €**")
        
        # TLAČOVÉ MOŽNOSTI
        st.write(" ")
        pdf_data = generate_pdf(st.session_state.ai_text, st.session_state.basket)
        st.download_button("📥 Stiahnuť PDF pre tlač", data=bytes(pdf_data), file_name=f"Ponuka_{f_firma}.pdf", mime="application/pdf")
        st.info("💡 Tip: Pre priamu tlač použite PDF súbor.")