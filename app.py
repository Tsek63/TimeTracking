import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIGURATION GOOGLE SHEETS ---
# ID nettoyé de tout espace invisible
SHEET_ID = "195v8jf2n1jjVQuWlw1s_ka32bu0K13mGrTUnksEp3GU"
SHEET_NAME = "Data"

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    try:
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    except Exception as e:
        st.error(f"Erreur de connexion Google : {e}")
        return None

def load_data():
    columns = ["date", "intervenante", "tache", "quantite", "nb_ecoles"]
    try:
        client = get_gsheet_client()
        if client:
            # --- TEST DE LECTURE BRUTE ---
            raw_values = client.get_all_values()
            if len(raw_values) > 0:
                st.sidebar.write("✅ Titres trouvés dans Sheet :", raw_values[0])
            else:
                st.sidebar.error("❌ La feuille semble totalement vide !")
            # -----------------------------

            data = client.get_all_records()
            df = pd.DataFrame(data)
            
            if df.empty:
                return pd.DataFrame(columns=columns)
            
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
            return df.dropna(subset=['date'])
    except Exception as e:
        st.sidebar.error(f"Erreur technique : {e}")
        return pd.DataFrame(columns=columns)

# --- 2. PARAMÈTRES ET LISTES ---
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

# --- 3. MISE EN PAGE ---
st.set_page_config(layout="wide", page_title="Suivi Activité N&M", page_icon="📊")

if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("📅 Calendrier")
    date_sel = st.date_input("Date de l'intervention", date.today())
    st.info(f"Format choisi : **{date_sel.strftime('%d/%m/%Y')}**")
    
    st.divider()
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS)
    
    st.divider()
    if st.button("🔄 Actualiser les données Cloud"):
        st.session_state.df_act = load_data()
        st.rerun()

# --- 5. ZONE DE SAISIE ET RÉCAPITULATIF ---
col_saisie, col_recap = st.columns([1, 1.2])

with col_saisie:
    st.subheader("📝 Enregistrement")
    with st.form("form_activite", clear_on_submit=True):
        tache_sel = st.selectbox("Action effectuée", LISTE_TACHES)
        qte = st.number_input("Valeur (Nombre entier)", min_value=0, step=1, value=1)
        
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles", min_value=0, step=1, value=0)

        if st.form_submit_button("💾 Enregistrer l'activité"):
            client = get_gsheet_client()
            if client:
                new_row = [str(date_sel), choix_inter, tache_sel, int(qte), int(ecoles)]
                client.append_row(new_row)
                st.session_state.df_act = load_data()
                st.success("✅ Enregistré avec succès !")
                st.rerun()

with col_recap:
    st.subheader(f"📋 Activités du {date_sel.strftime('%d/%m/%Y')}")
    
    df_local = st.session_state.df_act.copy()
    
    if not df_local.empty:
        # Filtrage
        view_df = df_local[df_local['date'] == date_sel].copy()
        
        if not view_df.empty:
            view_df['date'] = view_df['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
            st.dataframe(view_df[["date", "intervenante", "tache", "quantite", "nb_ecoles"]], use_container_width=True)
        else:
            st.info(f"Pas d'activité enregistrée pour le {date_sel.strftime('%d/%m/%Y')}.")
            # La case à cocher de secours apparaît maintenant TOUJOURS si la date est vide
            if st.checkbox("🔍 Voir les 10 dernières entrées (toutes dates)"):
                st.table(df_local.tail(10))
    else:
        st.warning("⚠️ La base de données est vide ou inaccessible.")

# --- 6. STATISTIQUES ---
st.divider()
st.header("📊 Analyse & Statistiques")
tab1, tab2 = st.tabs(["🔍 Filtres & Graphiques", "🖨️ Mode Impression"])

with tab1:
    c1, c2, c3 = st.columns(3)
    with c1:
        try:
            per = st.date_input("Période", [date.today() - timedelta(days=7), date.today()])
        except:
            per = [date.today(), date.today()]
    with c2:
        f_inter = st.multiselect("Intervenante(s)", LISTE_REDACTEURS, default=LISTE_REDACTEURS)
    with c3:
        f_tache = st.multiselect("Tâche(s)", LISTE_TACHES)

    # Filtrage global
    df_f = st.session_state.df_act.copy()
    if len(per) == 2:
        df_f = df_f[(df_f['date'] >= per[0]) & (df_f['date'] <= per[1])]
    if f_inter:
        df_f = df_f[df_f['intervenante'].isin(f_inter)]
    if f_tache:
        df_f = df_f[df_f['tache'].isin(f_tache)]

    if not df_f.empty:
        g1, g2 = st.columns(2)
        with g1:
            st.write("**Volume par Tâche**")
            st.bar_chart(df_f.groupby('tache')['quantite'].sum())
        with g2:
            st.write("**Répartition par Intervenante**")
            stats_int = df_f.groupby('intervenante')['quantite'].sum().reset_index()
            st.bar_chart(data=stats_int, x='intervenante', y='quantite', color='intervenante')
    else:
        st.write("Aucune donnée sur cette période.")

with tab2:
    if not df_f.empty:
        df_print = df_f.sort_values('date', ascending=False).copy()
        df_print['date'] = df_print['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.table(df_print)
