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

st.set_page_config(layout="wide", page_title="Suivi Activité N&M", page_icon="📊")

if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("📅 Menu")
    date_sel = st.date_input("Date de l'intervention", date.today())
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS)
    st.divider()
    if st.button("🔄 Synchroniser les données"):
        st.session_state.df_act = load_data()
        st.rerun()

# --- 4. ENCODAGE (GAUCHE) & RÉCAPITULATIF (DROITE) ---
col_saisie, col_recap = st.columns([1, 1.3])

with col_saisie:
    st.subheader("📝 Nouvel encodage")
    # Note : On ne met pas le selectbox de la tâche DANS le form pour qu'il soit interactif
    tache_sel = st.selectbox("Action effectuée", LISTE_TACHES)
    
    with st.form("form_activite", clear_on_submit=True):
        qte = st.number_input("Quantité / Valeur", min_value=1, step=1)
        
        # Le champ école s'affiche DIRECTEMENT si la tâche est sélectionnée au-dessus
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles concernées", min_value=1, step=1)

        submit = st.form_submit_button("💾 Enregistrer l'activité")
        
        if submit:
            client = get_gsheet_client()
            if client:
                new_row = [str(date_sel), choix_inter, tache_sel, int(qte), int(ecoles)]
                client.append_row(new_row)
                st.session_state.df_act = load_data()
                st.success("✅ Données envoyées au Cloud !")
                st.rerun()

with col_recap:
    st.subheader(f"📋 Détails du {date_sel.strftime('%d/%m/%Y')}")
    df_j = st.session_state.df_act[st.session_state.df_act['date'] == date_sel].copy()
    
    if not df_j.empty:
        # Tableau unique avec bouton de suppression
        for i, row in df_j.iterrows():
            c_txt, c_btn = st.columns([5, 1])
            with c_txt:
                txt = f"**{row['intervenante']}** | {row['tache']} ({row['quantite']})"
                if row['nb_ecoles'] > 0: txt += f" - {row['nb_ecoles']} écoles"
                st.write(txt)
            with c_btn:
                if st.button("🗑️", key=f"del_{i}"):
                    client = get_gsheet_client()
                    client.delete_rows(i + 2) # +2 car Excel commence à 1 et ligne 1=titres
                    st.session_state.df_act = load_data()
                    st.rerun()
    else:
        st.info("Aucun encodage pour ce jour.")

# --- 5. ANALYSE & IMPRESSION ---
st.divider()
st.header("📊 Reporting & Impression")

tab_stats, tab_print = st.tabs(["📊 Statistiques", "🖨️ Mode Impression"])

# ZONE DES FILTRES (communs aux deux onglets)
st.write("--- Filtres globaux ---")
cf1, cf2 = st.columns(2)
with cf1:
    per = st.date_input("Sélectionnez la période", [date.today() - timedelta(days=30), date.today()])
with cf2:
    f_inter = st.multiselect("Filtrer par intervenante", LISTE_REDACTEURS, default=LISTE_REDACTEURS)

# Filtrage du DataFrame
df_f = st.session_state.df_act.copy()
if len(per) == 2:
    df_f = df_f[(df_f['date'] >= per[0]) & (df_f['date'] <= per[1])]
if f_inter:
    df_f = df_f[df_f['intervenante'].isin(f_inter)]

with tab_stats:
    if not df_f.empty:
        s1, s2 = st.columns(2)
        with s1:
            st.write("**Répartition du temps (Camembert)**")
            fig_pie = px.pie(df_f, names='intervenante', values='quantite', 
                             color='intervenante', color_discrete_map=COULEURS_MAP)
            st.plotly_chart(fig_pie)
        with s2:
            st.write("**Volume par Tâche**")
            st.bar_chart(df_f.groupby('tache')['quantite'].sum())
    else:
        st.warning("Aucune donnée pour les filtres sélectionnés.")

with tab_print:
    if not df_f.empty:
        st.markdown(f"### Rapport d'activité du {per[0].strftime('%d/%m/%Y')} au {per[1].strftime('%d/%m/%Y')}")
        
        # Graphique camembert des tâches pour le rapport
        fig_taches = px.pie(df_f, names='tache', values='quantite', title="Répartition des actions")
        st.plotly_chart(fig_taches)
        
        # Tableau final
        df_p = df_f.sort_values('date', ascending=False)
        df_p['date'] = df_p['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.table(df_p)
        
        st.info("💡 Pour imprimer : Cliquez n'importe où sur la page puis faites Ctrl + P")
    else:
        st.info("Rien à afficher pour l'impression.")
