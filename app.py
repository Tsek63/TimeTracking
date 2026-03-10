import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION GOOGLE SHEETS ---
# Remplacez par l'ID de votre feuille (présent dans l'URL de votre Google Sheet)
SHEET_ID = "VOTRE_ID_DE_FEUILLE_ICI"
SHEET_NAME = "Data"

def get_gsheet_client():
    # Connexion via les Secrets de Streamlit (pour le déploiement Cloud)
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

def load_data():
    try:
        client = get_gsheet_client()
        data = client.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    except Exception as e:
        return pd.DataFrame(columns=["date", "intervenante", "tache", "quantite", "nb_ecoles"])

# --- LISTES ET PARAMÈTRES ---
LISTE_REDACTEURS = ["Véronique Maigrié", "Sylvie Nyssen"]
LISTE_TACHES = [
    "DEPANNAGE TELEPHONIQUE", "DEPANNAGE MAIL", "SUIVI DEPLOIEMENT TELEPHONIQUE",
    "SUIVI DEPLOIEMENT MAIL", "VISIO DE PRESENTATION", "VISIO DIVERS",
    "MAIL DIVERS", "MODIFICATIONS FICHIER PO", "JOURNEE DE FORMATION",
    "SUIVI ADMIN FORMATION", "MATINEE D’ACCOMPAGNEMENT", 
    "SUIVI MATINEE D’ACCOMPAGNEMENT", "ENCODAGE TICKET", "SUIVI FICHIER TICKETS",
    "MODIFICATION - CREATION DOC", "MODIFICATION – CREATION VIDEO",
    "NETTOYAGES DES DONNEES CREOS"
]

st.set_page_config(layout="wide", page_title="Suivi Activité Cloud - N&M")

# Initialisation des données
if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.title("📅 Paramètres")
    date_sel = st.date_input("Date de l'activité", date.today())
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS)
    
    if st.button("🔄 Actualiser les données"):
        st.session_state.df_act = load_data()
        st.rerun()

# --- FORMULAIRE D'ENCODAGE ---
col_saisie, col_direct = st.columns([1, 1.2])

with col_saisie:
    st.subheader("📝 Encodage")
    with st.form("form_activite", clear_on_submit=True):
        tache_sel = st.selectbox("Type de tâche", LISTE_TACHES)
        qte = st.number_input("Valeur (Nombre entier)", min_value=0, step=1, value=1)
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles concernées", min_value=0, step=1, value=0)

        if st.form_submit_button("💾 Enregistrer sur Google Sheets"):
            try:
                sheet = get_gsheet_client()
                new_row = [str(date_sel), choix_inter, tache_sel, qte, ecoles]
                sheet.append_row(new_row)
                st.success("✅ Enregistré dans le Cloud !")
                st.session_state.df_act = load_data() # Recharger
                st.rerun()
            except Exception as e:
                st.error(f"Erreur de connexion : {e}")

# --- AFFICHAGE ET STATS ---
# (Reprendre ici la logique de filtrage et de graphiques du code précédent)
# Le reste du code reste identique, utilisant st.session_state.df_act
