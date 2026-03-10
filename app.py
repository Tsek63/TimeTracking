import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURATION GOOGLE SHEETS ---
# REMPLACEZ par l'ID de votre feuille (trouvé dans l'URL de votre Google Sheet)
SHEET_ID = "VOTRE_ID_DE_FEUILLE_ICI" 
SHEET_NAME = "Data"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    # Utilise les secrets configurés en TOML sur Streamlit Cloud
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    except Exception as e:
        st.error(f"Erreur de configuration Google : {e}")
        return None

def load_data():
    try:
        client = get_gsheet_client()
        if client:
            data = client.get_all_records()
            df = pd.DataFrame(data)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.date
            return df
    except:
        pass
    return pd.DataFrame(columns=["date", "intervenante", "tache", "quantite", "nb_ecoles"])

# --- PARAMÈTRES ---
LISTE_REDACTEURS = ["Véronique Maigrié", "Sylvie Nyssen"]
COULEURS_INTER = {"Véronique Maigrié": "#e67e22", "Sylvie Nyssen": "#3498db"} # Orange et Bleu

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

# Initialisation session
if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.title("📅 Paramètres")
    date_sel = st.date_input("Date de l'activité", date.today())
    
    if 'last_inter' not in st.session_state:
        st.session_state.last_inter = LISTE_REDACTEURS[0]
        
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS, 
                               index=LISTE_REDACTEURS.index(st.session_state.last_inter))
    st.session_state.last_inter = choix_inter

    st.divider()
    if st.button("🔄 Actualiser les données Cloud"):
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
            ecoles = st.number_input("Nombre d'écoles concernées", min_value=0, step=1, value=0)

        if st.form_submit_button("💾 Enregistrer sur Google Sheets"):
            client = get_gsheet_client()
            if client:
                new_row = [str(date_sel), choix_inter, tache_sel, qte, ecoles if tache_sel == "NETTOYAGES DES DONNEES CREOS" else 0]
                client.append_row(new_row)
                st.success("✅ Données synchronisées !")
                st.session_state.df_act = load_data()
                st.rerun()

with col_recap:
    st.subheader(f"📋 Activités du {date_sel.strftime('%d/%m/%Y')}")
    mask = (st.session_state.df_act['date'] == date_sel)
    view_df = st.session_state.df_act[mask]
    
    if not view_df.empty:
        st.dataframe(view_df[["intervenante", "tache", "quantite", "nb_ecoles"]], use_container_width=True)
    else:
        st.info("Aucun encodage pour cette date.")

# --- SECTION STATISTIQUES ---
st.divider()
st.header("📊 Analyse & Reporting")

tab_analyse, tab_print = st.tabs(["🔍 Filtres & Graphiques", "🖨️ Format Impression"])

# Logique de filtrage commune
with tab_analyse:
    c1, c2, c3 = st.columns(3)
    with c1:
        periode = st.date_input("Période", [date.today() - timedelta(days=30), date.today()])
    with c2:
        f_inter = st.multiselect("Intervenante(s)", LISTE_REDACTEURS, default=LISTE_REDACTEURS)
    with c3:
        f_tache = st.multiselect("Tâche(s)", LISTE_TACHES)

# Application des filtres
df_filt = st.session_state.df_act.copy()
if len(periode) == 2:
    df_filt = df_filt[(df_filt['date'] >= periode[0]) & (df_filt['date'] <= periode[1])]
if f_inter:
    df_filt = df_filt[df_filt['intervenante'].isin(f_inter)]
if f_tache:
    df_filt = df_filt[df_filt['tache'].isin(f_tache)]

with tab_analyse:
    if not df_filt.empty:
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Valeurs", int(df_filt['quantite'].sum()))
        k2.metric("Total Écoles", int(df_filt['nb_ecoles'].sum()))
        k3.metric("Nb d'entrées", len(df_filt))

        g1, g2 = st.columns(2)
        with g1:
            st.write("**Répartition par Tâche**")
            st.bar_chart(df_filt.groupby('tache')['quantite'].sum())
        
        with g2:
            st.write("**Répartition par Intervenante**")
            # Graphique avec couleurs personnalisées
            inter_data = df_filt.groupby('intervenante')['quantite'].sum().reset_index()
            st.bar_chart(data=inter_data, x='intervenante', y='quantite', color='intervenante')
            
        st.write("**Évolution sur la période**")
        evol_data = df_filt.groupby(['date', 'intervenante'])['quantite'].sum().unstack().fillna(0)
        st.line_chart(evol_data)
    else:
        st.warning("Aucune donnée à afficher avec ces filtres.")

with tab_print:
    if not df_filt.empty:
        st.subheader("Rapport d'activité")
        st.write(f"Période : Du {periode[0].strftime('%d/%m/%Y')} au {periode[1].strftime('%d/%m/%Y')}")
        
        # Formatage pour l'impression
        df_p = df_filt.sort_values('date', ascending=False).copy()
        df_p['date'] = df_p['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.table(df_p)
        st.caption("Faites Ctrl+P pour imprimer ce tableau.")
    else:
        st.info("Sélectionnez des données dans l'onglet Analyse.")
