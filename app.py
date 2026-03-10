import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import streamlit.components.v1 as components

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

# --- STYLE POUR L'IMPRESSION PRO ---
st.markdown("""
    <style>
    @media print {
        header, .stSidebar, .stButtons, [data-testid="stHeader"], .stTabs [role="tablist"] {
            display: none !important;
        }
        .main .block-container {
            padding-top: 0rem !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

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
    tache_sel = st.selectbox("Action effectuée", LISTE_TACHES)
    with st.form("form_activite", clear_on_submit=True):
        qte = st.number_input("Quantité / Valeur", min_value=1, step=1)
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles concernées", min_value=1, step=1)
        if st.form_submit_button("💾 Enregistrer l'activité"):
            client = get_gsheet_client()
            if client:
                new_row = [str(date_sel), choix_inter, tache_sel, int(qte), int(ecoles)]
                client.append_row(new_row)
                st.session_state.df_act = load_data()
                st.success("✅ Enregistré !")
                st.rerun()

with col_recap:
    st.subheader(f"📋 Détails du {date_sel.strftime('%d/%m/%Y')}")
    df_j = st.session_state.df_act[st.session_state.df_act['date'] == date_sel].copy()
    if not df_j.empty:
        for i, row in df_j.iterrows():
            c_txt, c_btn = st.columns([5, 1])
            with c_txt:
                txt = f"**{row['intervenante']}** | {row['tache']} ({row['quantite']})"
                if row['nb_ecoles'] > 0: txt += f" - {row['nb_ecoles']} écoles"
                st.write(txt)
            with c_btn:
                if st.button("🗑️", key=f"del_{i}"):
                    client = get_gsheet_client()
                    client.delete_rows(int(i) + 2)
                    st.session_state.df_act = load_data()
                    st.rerun()
    else:
        st.info("Aucun encodage pour ce jour.")

# --- 5. REPORTING & IMPRESSION ---
st.divider()
st.header("📊 Reporting & Impression")

cf1, cf2, cf3 = st.columns([1, 1, 1.5])
with cf1:
    per = st.date_input("Sélectionnez la période", [date.today() - timedelta(days=30), date.today()])
with cf2:
    f_inter = st.multiselect("Intervenantes", LISTE_REDACTEURS, default=LISTE_REDACTEURS)
with cf3:
    f_tache = st.multiselect("Filtrer par tâches", LISTE_TACHES)

df_f = st.session_state.df_act.copy()
if len(per) == 2:
    df_f = df_f[(df_f['date'] >= per[0]) & (df_f['date'] <= per[1])]
if f_inter:
    df_f = df_f[df_f['intervenante'].isin(f_inter)]
if f_tache:
    df_f = df_f[df_f['tache'].isin(f_tache)]

tab_stats, tab_print = st.tabs(["📊 Statistiques", "🖨️ Mode Impression"])

with tab_stats:
    if not df_f.empty:
        s1, s2 = st.columns(2)
        with s1:
            st.write("**Répartition par Intervenante**")
            fig_p1 = px.pie(df_f, names='intervenante', values='quantite', color='intervenante', color_discrete_map=COULEURS_MAP)
            st.plotly_chart(fig_p1, use_container_width=True, key="p1")
        with s2:
            st.write("**Volume total par Tâche**")
            df_g = df_f.groupby('tache')['quantite'].sum().reset_index()
            fig_b = px.bar(df_g, x='tache', y='quantite', color='tache', color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_b, use_container_width=True, key="pb")
    else:
        st.warning("Aucune donnée.")

with tab_print:
    if not df_f.empty:
        st.markdown(f"### Rapport d'activité du {per[0].strftime('%d/%m/%Y')} au {per[1].strftime('%d/%m/%Y')}")
        
        p1, p2 = st.columns(2)
        with p1:
            st.write("**Actions (Tâches)**")
            fig_t = px.pie(df_f, names='tache', values='quantite', color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_t, use_container_width=True, key="p2")
        with p2:
            st.write("**Intervenantes**")
            fig_i = px.pie(df_f, names='intervenante', values='quantite', color='intervenante', color_discrete_map=COULEURS_MAP)
            st.plotly_chart(fig_i, use_container_width=True, key="p3")
        
        st.write("**Détails des activités :**")
        df_p = df_f.sort_values('date', ascending=False)
        df_p['date'] = df_p['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
        st.table(df_p)
        
        # --- LE BOUTON IMPRIMANTE ---
        st.divider()
        st.write("### 🖨️ Prêt pour l'impression ?")
        if st.button("Lancer l'impression du rapport"):
            components.html("<script>window.print();</script>", height=0)
    else:
        st.info("Rien à imprimer.")
