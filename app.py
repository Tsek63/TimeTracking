import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION GOOGLE SHEETS ---
SHEET_ID = "VOTRE_ID_DE_FEUILLE_ICI" # À copier depuis l'URL de votre Google Sheet
SHEET_NAME = "Data"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    # Utilise les secrets configurés sur Streamlit Cloud
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

st.set_page_config(layout="wide", page_title="Gestion Activité - N&M")

if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.title("📅 Calendrier & Filtres")
    date_sel = st.date_input("Date de l'encodage", date.today())
    choix_inter = st.selectbox("Intervenante par défaut", LISTE_REDACTEURS)
    
    st.divider()
    if st.button("🔄 Synchroniser Google Sheets"):
        st.session_state.df_act = load_data()
        st.success("Données à jour !")

# --- ZONE D'ENCODAGE ---
col_saisie, col_info = st.columns([1, 1.2])

with col_saisie:
    st.subheader("📝 Nouvel Enregistrement")
    with st.form("form_act", clear_on_submit=True):
        tache_sel = st.selectbox("Tâche effectuée", LISTE_TACHES)
        qte = st.number_input("Valeur (Nombre entier)", min_value=0, step=1, value=1)
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles", min_value=0, step=1)
        
        if st.form_submit_button("💾 Enregistrer dans le Cloud"):
            try:
                sheet = get_gsheet_client()
                sheet.append_row([str(date_sel), choix_inter, tache_sel, qte, ecoles])
                st.session_state.df_act = load_data()
                st.success("Données envoyées avec succès !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

with col_info:
    st.subheader(f"📋 Activité du {date_sel.strftime('%d/%m/%Y')}")
    df_jour = st.session_state.df_act[st.session_state.df_act['date'] == date_sel]
    if not df_jour.empty:
        st.dataframe(df_jour[["intervenante", "tache", "quantite", "nb_ecoles"]], use_container_width=True)
    else:
        st.info("Aucune saisie pour ce jour.")

# --- MODULE DE STATISTIQUES AVANCÉES ---
st.divider()
st.header("📊 Reporting & Analyse")

tab_stats, tab_print = st.tabs(["🔍 Analyse Dynamique", "🖨️ Mode Impression"])

with tab_stats:
    c1, c2, c3 = st.columns(3)
    with c1:
        # Sélection de période
        today = date.today()
        start_date = today - timedelta(days=30)
        per = st.date_input("Période d'analyse", [start_date, today])
    with c2:
        inter_filt = st.multiselect("Intervenante(s)", LISTE_REDACTEURS, default=LISTE_REDACTEURS)
    with c3:
        tache_filt = st.multiselect("Tâche(s)", LISTE_TACHES, default=[])

    # Filtrage du DataFrame
    df_res = st.session_state.df_act.copy()
    if len(per) == 2:
        df_res = df_res[(df_res['date'] >= per[0]) & (df_res['date'] <= per[1])]
    if inter_filt:
        df_res = df_res[df_res['intervenante'].isin(inter_filt)]
    if tache_filt:
        df_res = df_res[df_res['tache'].isin(tache_filt)]

    if not df_res.empty:
        # Graphiques
        st.write(f"**Total cumulé sur la période : {df_res['quantite'].sum()} unités**")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.bar_chart(df_res.groupby('tache')['quantite'].sum())
        with col_g2:
            st.line_chart(df_res.groupby('date')['quantite'].sum())
    else:
        st.warning("Aucune donnée pour ces filtres.")

with tab_print:
    if not df_res.empty:
        st.subheader("📄 Rapport prêt pour impression")
        st.write(f"**Période :** Du {per[0].strftime('%d/%m/%Y')} au {per[1].strftime('%d/%m/%Y')}")
        st.write(f"**Intervenante(s) :** {', '.join(inter_filt)}")
        
        # Tableau formaté pour être propre à l'écran/impression
        df_print = df_res.sort_values(by='date', ascending=False).copy()
        df_print['date'] = df_print['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.table(df_print)
        
        st.info("💡 Astuce : Faites 'Clic droit > Imprimer' ou 'Ctrl+P' pour sauvegarder en PDF.")
    else:
        st.write("Veuillez sélectionner des données dans l'onglet 'Analyse' pour générer un rapport.")
