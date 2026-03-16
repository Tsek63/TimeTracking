import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import io

# --- 1. CONFIGURATION ---
SHEET_ID = "195v8jf2n1jjVQuWlw1s_ka32bu0K13mGrTUnksEp3GU"
SHEET_NAME = "Data"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    except Exception as e:
        st.error(f"Erreur de connexion : {e}")
        return None

def load_data():
    columns = ["date", "intervenante", "tache", "quantite", "nb_ecoles"]
    try:
        client = get_gsheet_client()
        if client:
            data = client.get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame(columns=columns)
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
            return df.dropna(subset=['date'])
    except:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- 2. PARAMÈTRES ---
LISTE_REDACTEURS = ["Véronique Maigrié", "Sylvie Nyssen"]
COULEURS_MAP = {
    "Véronique Maigrié": "#FF00FF",  # Rose Fuchsia
    "Sylvie Nyssen": "#008080"       # Bleu Canard
}

LISTE_TACHES = [
    "DEPANNAGE TELEPHONIQUE", "DEPANNAGE MAIL", "SUIVI DEPLOIEMENT TELEPHONIQUE",
    "SUIVI DEPLOIEMENT MAIL", "VISIO DE PRESENTATION", "VISIO DIVERS",
    "MAIL DIVERS", "MODIFICATIONS FICHIER PO", "JOURNEE DE FORMATION",
    "SUIVI ADMIN FORMATION", "MATINEE D'ACCOMPAGNEMENT", 
    "SUIVI MATINEE D'ACCOMPAGNEMENT", "ENCODAGE TICKET", "SUIVI FICHIER TICKETS",
    "MODIFICATION - CREATION DOC", "MODIFICATION – CREATION VIDEO",
    "NETTOYAGES DES DONNEES CREOS"
]

st.set_page_config(layout="wide", page_title="Creos Extrascolaire - Time tracking", page_icon="⏱️")

# --- TITRE GÉNÉRAL avec bouton Utilisateurs ES ---
col_title, col_btn = st.columns([5, 1])
with col_title:
    st.title("⏱️ Creos Extrascolaire - Time tracking")
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    st.link_button("👥 Utilisateurs ES", "https://userscreoses-ej6ntk35eyyz5ttkdd6kzx.streamlit.app/")

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("📅 Menu")
    date_sel = st.date_input("Choisir une date", date.today())
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS)
    st.divider()
    if st.button("🔄 Rafraîchir les données"):
        st.session_state.df_act = load_data()
        st.rerun()

# --- 4. ENCODAGE & RÉCAP DU JOUR ---
c1, c2 = st.columns([1, 1.2])

with c1:
    st.subheader("📝 Encodage")
    t_sel = st.selectbox("Action", LISTE_TACHES)
    with st.form("form_saisie", clear_on_submit=True):
        qte = st.number_input("Quantité", min_value=1, step=1)
        ecoles = 0
        if t_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles", min_value=1, step=1)
        if st.form_submit_button("💾 Enregistrer"):
            client = get_gsheet_client()
            if client:
                client.append_row([str(date_sel), choix_inter, t_sel, int(qte), int(ecoles)])
                st.session_state.df_act = load_data()
                st.success("Donnée ajoutée !")
                st.rerun()

with c2:
    st.subheader(f"📋 Détails du {date_sel.strftime('%d/%m/%Y')}")
    df_j = st.session_state.df_act[st.session_state.df_act['date'] == date_sel].copy()
    if not df_j.empty:
        for i, row in df_j.iterrows():
            ca, cb = st.columns([5, 1])
            ca.write(f"**{row['intervenante']}** | {row['tache']} ({row['quantite']})")
            if cb.button("🗑️", key=f"del_{i}"):
                client = get_gsheet_client()
                client.delete_rows(int(i) + 2)
                st.session_state.df_act = load_data()
                st.rerun()
    else:
        st.info("Aucune donnée pour ce jour.")

# --- 5. REPORTING & EXPORT ---
st.divider()
st.header("📊 Statistiques & Synthèse")

if not st.session_state.df_act.empty:
    f1, f2, f3 = st.columns([1, 1, 1.5])
    with f1:
        per = st.date_input("Sélectionnez la période", [min(st.session_state.df_act['date']), max(st.session_state.df_act['date'])])
    with f2:
        f_int = st.multiselect("Filtrer Intervenantes", LISTE_REDACTEURS, default=LISTE_REDACTEURS)
    with f3:
        f_tac = st.multiselect("Filtrer Tâches", LISTE_TACHES)

    df_f = st.session_state.df_act.copy()
    p_start, p_end = (per[0], per[1]) if len(per) == 2 else (per[0], per[0])
    df_f = df_f[(df_f['date'] >= p_start) & (df_f['date'] <= p_end)]
    
    if f_int: df_f = df_f[df_f['intervenante'].isin(f_int)]
    if f_tac: df_f = df_f[df_f['tache'].isin(f_tac)]

    if not df_f.empty:
        g1, g2 = st.columns(2)
        with g1:
            fig1 = px.pie(df_f, names='intervenante', values='quantite', color='intervenante', color_discrete_map=COULEURS_MAP, title="Répartition par Intervenante")
            st.plotly_chart(fig1, use_container_width=True)
        with g2:
            fig2 = px.pie(df_f, names='tache', values='quantite', title="Répartition par Tâche", color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        df_synth = df_f.groupby('tache').agg({'quantite': 'sum', 'nb_ecoles': 'sum'}).reset_index()
        df_synth.columns = ["Action / Tâche", "Total Quantité", "Total Écoles"]
        
        # --- LOGIQUE EXPORT EXCEL AMÉLIORÉE ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Création d'un petit DataFrame pour l'en-tête du fichier Excel
            header_info = pd.DataFrame([
                ["TITRE :", "Creos Extrascolaire - Time tracking"],
                ["PÉRIODE :", f"Du {p_start} au {p_end}"],
                ["DATE EXPORT :", str(date.today())],
                [] # Ligne vide
            ])
            header_info.to_excel(writer, index=False, header=False, sheet_name='Synthèse', startrow=0)
            df_synth.to_excel(writer, index=False, sheet_name='Synthèse', startrow=5)
            df_f.to_excel(writer, index=False, sheet_name='Données Brutes')
            
            # Ajustement automatique des colonnes Excel
            worksheet = writer.sheets['Synthèse']
            worksheet.set_column('A:C', 25)

        excel_data = output.getvalue()

        col_txt, col_btn = st.columns([3, 1])
        with col_txt: st.subheader("📋 Synthèse par tâche")
        with col_btn:
            st.download_button(
                label="📥 Exporter vers Excel",
                data=excel_data,
                file_name=f"Creos_Tracking_{p_start}_{p_end}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.table(df_synth)
        st.metric(label="TOTAL GÉNÉRAL", value=int(df_synth["Total Quantité"].sum()))
        
    else:
        st.warning("Aucune donnée pour les filtres sélectionnés.")
else:
    st.info("La base est vide.")

# --- COPYRIGHT ---
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: grey; font-size: 0.8em;'>"
    "AJH 2026 - Creos Extrascolaire"
    "</div>", 
    unsafe_allow_html=True
)
