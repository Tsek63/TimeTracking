import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION GOOGLE SHEETS ---
SHEET_ID = "195v8jf2n1jjVQuWlw1s_ka32bu0K13mGrTUnksEp3GU" 
SHEET_NAME = "Data"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    except Exception as e:
        st.error(f"Erreur de configuration Google : {e}")
        return None

def load_data():
    columns = ["date", "intervenante", "tache", "quantite", "nb_ecoles"]
    try:
        client = get_gsheet_client()
        if client:
            data = client.get_all_records()
            df = pd.DataFrame(data)
            
            if df.empty or 'date' not in df.columns:
                return pd.DataFrame(columns=columns)
            
            # Conversion robuste : On transforme ce qui vient du Cloud en vraies dates Python
            df['date'] = pd.to_datetime(df['date'], dayfirst=False).dt.date
            return df
    except Exception as e:
        st.error(f"Erreur de chargement : {e}")
    return pd.DataFrame(columns=columns)

# --- PARAMÈTRES ---
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

st.set_page_config(layout="wide", page_title="Gestion Activité N&M", page_icon="📊")

if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.title("📅 Paramètres")
    date_sel = st.date_input("Choisir une date", date.today())
    # Affichage du format FR pour rassurer l'utilisateur
    st.info(f"Date sélectionnée : **{date_sel.strftime('%d/%m/%Y')}**")
    
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS)

    st.divider()
    if st.button("🔄 Synchroniser les données"):
        st.session_state.df_act = load_data()
        st.rerun()

# --- CORPS DE L'APP : SAISIE ---
col_saisie, col_recap = st.columns([1, 1.2])

with col_saisie:
    st.subheader("📝 Encodage")
    with st.form("form_activite", clear_on_submit=True):
        tache_sel = st.selectbox("Type de tâche", LISTE_TACHES)
        qte = st.number_input("Valeur (Nombre entier)", min_value=0, step=1, value=1)
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles", min_value=0, step=1, value=0)

        if st.form_submit_button("💾 Enregistrer"):
            client = get_gsheet_client()
            if client:
                # On enregistre en format ISO (YYYY-MM-DD) pour la compatibilité Cloud
                new_row = [str(date_sel), choix_inter, tache_sel, int(qte), int(ecoles)]
                client.append_row(new_row)
                st.session_state.df_act = load_data()
                st.success("✅ Enregistré !")
                st.rerun()

with col_recap:
    st.subheader(f"📋 Activités du {date_sel.strftime('%d/%m/%Y')}")
    
    if not st.session_state.df_act.empty:
        # Filtrage
        mask = (st.session_state.df_act['date'] == date_sel)
        view_df = st.session_state.df_act[mask].copy()
        
        if not view_df.empty:
            # FORMATTAGE VISUEL pour le tableau de droite
            view_df['date'] = view_df['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
            st.dataframe(view_df[["date", "intervenante", "tache", "quantite", "nb_ecoles"]], use_container_width=True)
        else:
            st.info("Aucune activité pour ce jour.")

# --- SECTION STATISTIQUES & IMPRESSION ---
st.divider()
st.header("📊 Reporting")

tab_stats, tab_print = st.tabs(["📊 Graphiques", "🖨️ Mode Impression"])

# Calcul des filtres pour les deux onglets
with tab_stats:
    c1, c2 = st.columns(2)
    with c1:
        per = st.date_input("Période", [date.today() - timedelta(days=7), date.today()])
    with c2:
        inter_f = st.multiselect("Filtrer par intervenante", LISTE_REDACTEURS, default=LISTE_REDACTEURS)

df_f = st.session_state.df_act.copy()
if len(per) == 2:
    df_f = df_f[(df_f['date'] >= per[0]) & (df_f['date'] <= per[1])]
if inter_f:
    df_f = df_f[df_f['intervenante'].isin(inter_f)]

with tab_stats:
    if not df_f.empty:
        st.bar_chart(data=df_f.groupby('intervenante')['quantite'].sum().reset_index(), x='intervenante', y='quantite', color='intervenante')
        st.write("**Détail des tâches sur la période :**")
        st.bar_chart(df_f.groupby('tache')['quantite'].sum())

with tab_print:
    if not df_f.empty:
        st.subheader(f"Rapport du {per[0].strftime('%d/%m/%Y')} au {per[1].strftime('%d/%m/%Y')}")
        # On crée une copie pour l'affichage sans modifier les données de calcul
        df_display = df_f.sort_values('date', ascending=False).copy()
        df_display['date'] = df_display['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.table(df_display)
