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
        st.error(f"Erreur de connexion Google : {e}")
        return None

def load_data():
    columns = ["date", "intervenante", "tache", "quantite", "nb_ecoles"]
    try:
        client = get_gsheet_client()
        if client:
            data = client.get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame(columns=columns)
            # Conversion forcée en format date
            df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.date
            return df.dropna(subset=['date'])
    except:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

# --- INITIALISATION ÉTAT ---
if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

# --- 2. PARAMÈTRES & STYLE ---
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

# CSS spécial Impression (masque les menus inutiles)
st.markdown("""
    <style>
    @media print {
        div[data-testid="stSidebar"], div[data-testid="stHeader"], .stButtons, .stTabs [role="tablist"] {
            display: none !important;
        }
        .main .block-container { padding: 0 !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("📅 Menu")
    date_sel = st.date_input("Date de l'intervention", date.today())
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS)
    st.divider()
    if st.button("🔄 Actualiser les données"):
        st.session_state.df_act = load_data()
        st.rerun()

# --- 4. FORMULAIRE ET RÉCAP ---
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📝 Encodage")
    tache_sel = st.selectbox("Action", LISTE_TACHES)
    with st.form("f_add", clear_on_submit=True):
        qte = st.number_input("Quantité", min_value=1, step=1)
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles", min_value=1, step=1)
        
        if st.form_submit_button("💾 Enregistrer"):
            client = get_gsheet_client()
            if client:
                client.append_row([str(date_sel), choix_inter, tache_sel, int(qte), int(ecoles)])
                st.session_state.df_act = load_data()
                st.success("C'est dans la boîte !")
                st.rerun()

with col2:
    st.subheader(f"📋 Aujourd'hui ({date_sel.strftime('%d/%m/%Y')})")
    df_temp = st.session_state.df_act.copy()
    df_jour = df_temp[df_temp['date'] == date_sel]
    
    if not df_jour.empty:
        for i, row in df_jour.iterrows():
            c_a, c_b = st.columns([5, 1])
            c_a.write(f"**{row['intervenante']}** : {row['tache']} ({row['quantite']})")
            if c_b.button("🗑️", key=f"d_{i}"):
                client = get_gsheet_client()
                client.delete_rows(int(i) + 2)
                st.session_state.df_act = load_data()
                st.rerun()
    else:
        st.info("Rien à signaler pour cette date.")

# --- 5. REPORTING & IMPRESSION ---
st.divider()
st.header("📊 Reporting & Historique")

if not st.session_state.df_act.empty:
    # FILTRES TOUJOURS VISIBLES
    f1, f2, f3 = st.columns([1, 1, 1.5])
    with f1:
        d_range = st.date_input("Période", [min(st.session_state.df_act['date']), max(st.session_state.df_act['date'])], key="filter_date")
    with f2:
        f_int = st.multiselect("Personnes", LISTE_REDACTEURS, default=LISTE_REDACTEURS, key="filter_int")
    with f3:
        f_tac = st.multiselect("Tâches", LISTE_TACHES, key="filter_tac")

    # FILTRAGE
    df_f = st.session_state.df_act.copy()
    if len(d_range) == 2:
        df_f = df_f[(df_f['date'] >= d_range[0]) & (df_f['date'] <= d_range[1])]
    if f_int:
        df_f = df_f[df_f['intervenante'].isin(f_int)]
    if f_tac:
        df_f = df_f[df_f['tache'].isin(f_tac)]

    # AFFICHAGE DIRECT (SANS ONGLETS POUR ÉVITER LE BLANC)
    if not df_f.empty:
        st.markdown("---")
        # CETTE SECTION EST CELLE QUI SERA IMPRIMÉE
        container_print = st.container()
        with container_print:
            st.markdown(f"## 📋 RAPPORT D'ACTIVITÉ N&M")
            st.write(f"Extraction du **{d_range[0]}** au **{d_range[1]}**")
            
            p1, p2 = st.columns(2)
            with p1:
                fig_actions = px.pie(df_f, names='tache', values='quantite', title="Répartition des Actions")
                st.plotly_chart(fig_actions, use_container_width=True, key="print_pie_1")
            with p2:
                fig_pers = px.pie(df_f, names='intervenante', values='quantite', color='intervenante', color_discrete_map=COULEURS_MAP, title="Répartition par Personne")
                st.plotly_chart(fig_pers, use_container_width=True, key="print_pie_2")
            
            st.write("### Tableau récapitulatif")
            # On affiche un tableau statique (st.table) qui s'imprime mieux qu'un dataframe interactif
            df_print = df_f.sort_values('date', ascending=False).copy()
            df_print['date'] = df_print['date'].apply(lambda x: x.strftime('%d/%m/%Y'))
            st.table(df_print[["date", "intervenante", "tache", "quantite", "nb_ecoles"]])

        # BOUTON D'IMPRESSION
        st.write("---")
        if st.button("🖨️ LANCER L'IMPRESSION DU RAPPORT CI-DESSUS"):
            components.html("<script>window.print();</script>", height=0)
    else:
        st.warning("Aucune donnée pour ces filtres.")
else:
    st.info("La base de données est vide.")

    # FILTRAGE DU DF
    df_f = st.session_state.df_act.copy()
    if len(d_range) == 2:
        df_f = df_f[(df_f['date'] >= d_range[0]) & (df_f['date'] <= d_range[1])]
    if f_int:
        df_f = df_f[df_f['intervenante'].isin(f_int)]
    if f_tac:
        df_f = df_f[df_f['tache'].isin(f_tac)]

    t1, t2 = st.tabs(["Graphiques", "Rapport d'impression"])

    with t1:
        if not df_f.empty:
            g1, g2 = st.columns(2)
            with g1:
                st.plotly_chart(px.pie(df_f, names='intervenante', values='quantite', color='intervenante', color_discrete_map=COULEURS_MAP, title="Par Intervenante"), use_container_width=True, key="c1")
            with g2:
                df_bar = df_f.groupby('tache')['quantite'].sum().reset_index()
                st.plotly_chart(px.bar(df_bar, x='tache', y='quantite', color='tache', title="Par Tâche"), use_container_width=True, key="c2")

    with t2:
        if not df_f.empty:
            st.markdown(f"## RAPPORT D'ACTIVITÉ")
            st.write(f"Période du {d_range[0]} au {d_range[1]}")
            
            p1, p2 = st.columns(2)
            p1.plotly_chart(px.pie(df_f, names='tache', values='quantite', title="Répartition Actions"), use_container_width=True, key="c3")
            p2.plotly_chart(px.pie(df_f, names='intervenante', values='quantite', color='intervenante', color_discrete_map=COULEURS_MAP, title="Répartition Personnes"), use_container_width=True, key="c4")
            
            st.table(df_f.sort_values('date', ascending=False))
            
            if st.button("🖨️ LANCER L'IMPRESSION"):
                components.html("<script>window.print();</script>", height=0)
else:
    st.warning("Base de données vide.")
