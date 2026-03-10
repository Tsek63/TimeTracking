import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

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
COULEURS_MAP = {"Véronique Maigrié": "#E67E22", "Sylvie Nyssen": "#3498DB"}
LISTE_TACHES = [
    "DEPANNAGE TELEPHONIQUE", "DEPANNAGE MAIL", "SUIVI DEPLOIEMENT TELEPHONIQUE",
    "SUIVI DEPLOIEMENT MAIL", "VISIO DE PRESENTATION", "VISIO DIVERS",
    "MAIL DIVERS", "MODIFICATIONS FICHIER PO", "JOURNEE DE FORMATION",
    "SUIVI ADMIN FORMATION", "MATINEE D’ACCOMPAGNEMENT", 
    "SUIVI MATINEE D’ACCOMPAGNEMENT", "ENCODAGE TICKET", "SUIVI FICHIER TICKETS",
    "MODIFICATION - CREATION DOC", "MODIFICATION – CREATION VIDEO",
    "NETTOYAGES DES DONNEES CREOS"
]

st.set_page_config(layout="wide", page_title="Suivi Activité N&M")

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
    st.subheader(f"📋 Historique du {date_sel.strftime('%d/%m/%Y')}")
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

# --- 5. REPORTING ---
st.divider()
st.header("📊 Statistiques & Export")

if not st.session_state.df_act.empty:
    f1, f2, f3 = st.columns([1, 1, 1.5])
    with f1:
        per = st.date_input("Période", [min(st.session_state.df_act['date']), max(st.session_state.df_act['date'])])
    with f2:
        f_int = st.multiselect("Filtrer Intervenantes", LISTE_REDACTEURS, default=LISTE_REDACTEURS)
    with f3:
        f_tac = st.multiselect("Filtrer Tâches", LISTE_TACHES)

    df_f = st.session_state.df_act.copy()
    if len(per) == 2:
        df_f = df_f[(df_f['date'] >= per[0]) & (df_f['date'] <= per[1])]
    if f_int:
        df_f = df_f[df_f['intervenante'].isin(f_int)]
    if f_tac:
        df_f = df_f[df_f['tache'].isin(f_tac)]

    t1, t2 = st.tabs(["📊 Graphiques", "📥 Export pour Impression"])

    with t1:
        if not df_f.empty:
            g1, g2 = st.columns(2)
            with g1:
                fig1 = px.pie(df_f, names='intervenante', values='quantite', color='intervenante', color_discrete_map=COULEURS_MAP, title="Répartition par Personne")
                st.plotly_chart(fig1, use_container_width=True, key="g1")
            with g2:
                df_bar = df_f.groupby('tache')['quantite'].sum().reset_index()
                fig2 = px.bar(df_bar, x='tache', y='quantite', color='tache', title="Volume par Action")
                st.plotly_chart(fig2, use_container_width=True, key="g2")
        else:
            st.warning("Aucune donnée correspondante.")

    with t2:
        if not df_f.empty:
            st.subheader("📥 Préparer l'impression")
            st.write("Le format web est capricieux à l'impression. Téléchargez le tableau ci-dessous pour l'imprimer proprement via Excel ou Numbers.")
            
            df_export = df_f.sort_values('date', ascending=False).copy()
            df_export['date'] = df_export['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
            
            # Bouton de téléchargement CSV
            csv = df_export.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Télécharger le tableau (CSV pour Excel)",
                data=csv,
                file_name=f"rapport_activite_{per[0]}_{per[1]}.csv",
                mime='text/csv',
            )
            
            st.write("### Aperçu des données à exporter :")
            st.table(df_export)
        else:
            st.info("Rien à exporter.")
else:
    st.info("La base est vide.")
