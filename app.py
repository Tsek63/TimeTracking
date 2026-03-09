import streamlit as st
import pandas as pd
import os
from datetime import date, datetime

# --- CONFIGURATION ---
DB_FILE = "activite_data.csv"
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

def load_data():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=["date", "intervenante", "tache", "quantite", "nb_ecoles"])

def save_data(df):
    df_to_save = df.copy()
    df_to_save.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# Initialisation
if 'df_act' not in st.session_state:
    st.session_state.df_act = load_data()

st.set_page_config(layout="wide", page_title="Suivi Activité - N&M")

# --- SIDEBAR (GAUCHE) ---
with st.sidebar:
    st.title("📅 Paramètres")
    date_sel = st.date_input("Date de l'activité", date.today())
    st.write(f"Jour choisi : **{date_sel.strftime('%d/%m/%Y')}**")
    
    st.divider()
    
    if 'last_inter' not in st.session_state:
        st.session_state.last_inter = LISTE_REDACTEURS[0]
        
    choix_inter = st.selectbox("Intervenante", LISTE_REDACTEURS, 
                               index=LISTE_REDACTEURS.index(st.session_state.last_inter))
    st.session_state.last_inter = choix_inter

    st.divider()
    # Export
    csv = st.session_state.df_act.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Export complet (CSV)", data=csv, file_name="export_activites.csv", mime="text/csv")

# --- CORPS DE L'APPLICATION ---
col_saisie, col_direct = st.columns([1, 1.2])

with col_saisie:
    st.subheader("📝 Encodage")
    with st.form("form_activite", clear_on_submit=True):
        tache_sel = st.selectbox("Type de tâche", LISTE_TACHES)
        
        qte = st.number_input("Valeur (Nombre entier)", min_value=0, step=1, value=1)
        
        # Champ spécial pour le nettoyage
        ecoles = 0
        if tache_sel == "NETTOYAGES DES DONNEES CREOS":
            ecoles = st.number_input("Nombre d'écoles concernées", min_value=0, step=1, value=0)
            st.caption("Note: Pour cette tâche, la valeur et le nombre d'écoles sont enregistrés.")

        if st.form_submit_button("💾 Enregistrer l'activité"):
            new_row = {
                "date": date_sel,
                "intervenante": choix_inter,
                "tache": tache_sel,
                "quantite": qte,
                "nb_ecoles": ecoles if tache_sel == "NETTOYAGES DES DONNEES CREOS" else 0
            }
            st.session_state.df_act = pd.concat([st.session_state.df_act, pd.DataFrame([new_row])], ignore_index=True)
            save_data(st.session_state.df_act)
            st.success("Activité enregistrée !")
            st.rerun()

with col_direct:
    st.subheader(f"📋 Récapitulatif du {date_sel.strftime('%d/%m/%Y')}")
    mask = (st.session_state.df_act['date'] == date_sel)
    view_df = st.session_state.df_act[mask]
    
    if not view_df.empty:
        for i, row in view_df.iterrows():
            txt = f"**{row['tache']}** : {row['quantite']}"
            if row['tache'] == "NETTOYAGES DES DONNEES CREOS":
                txt += f" (Ecoles: {row['nb_ecoles']})"
            
            with st.expander(f"{row['intervenante']} | {txt}"):
                if st.button("Supprimer", key=f"del_{i}"):
                    st.session_state.df_act = st.session_state.df_act.drop(i).reset_index(drop=True)
                    save_data(st.session_state.df_act)
                    st.rerun()
    else:
        st.info("Rien à cette date.")

# --- SECTION STATISTIQUES ET FILTRES ---
st.divider()
st.header("📊 Analyse & Statistiques")

# Filtres de recherche
c1, c2, c3 = st.columns(3)
with c1:
    periode = st.date_input("Choisir une période", [date.today(), date.today()])
with c2:
    filter_inter = st.multiselect("Filtrer par intervenante", LISTE_REDACTEURS, default=LISTE_REDACTEURS)
with c3:
    filter_taches = st.multiselect("Filtrer par tâches", LISTE_TACHES, default=[])

# Application des filtres
df_filt = st.session_state.df_act.copy()
df_filt['date'] = pd.to_datetime(df_filt['date']).dt.date

if len(periode) == 2:
    df_filt = df_filt[(df_filt['date'] >= periode[0]) & (df_filt['date'] <= periode[1])]

if filter_inter:
    df_filt = df_filt[df_filt['intervenante'].isin(filter_inter)]

if filter_taches:
    df_filt = df_filt[df_filt['tache'].isin(filter_taches)]

# Affichage des résultats
if not df_filt.empty:
    st.subheader("📈 Résultats de la sélection")
    
    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Valeurs", int(df_filt['quantite'].sum()))
    k2.metric("Total Ecoles (Nettoyage)", int(df_filt['nb_ecoles'].sum()))
    k3.metric("Nombre d'entrées", len(df_filt))

    # Tableau détaillé
    st.dataframe(df_filt.sort_values('date', ascending=False), use_container_width=True)

    # Graphiques
    g1, g2 = st.columns(2)
    with g1:
        st.write("**Répartition par Tâche (Valeur cumulée)**")
        # Groupement pour le graphique
        chart_data = df_filt.groupby('tache')['quantite'].sum()
        st.bar_chart(chart_data)
    
    with g2:
        st.write("**Evolution temporelle**")
        df_filt['date_str'] = df_filt['date'].apply(lambda x: x.strftime('%d/%m'))
        time_data = df_filt.groupby('date_str')['quantite'].sum()
        st.line_chart(time_data)

    # Bouton Impression (Simulé par une mise en page propre pour le navigateur)
    if st.button("🖨️ Préparer pour l'impression"):
        st.write("---")
        st.write(f"### RAPPORT D'ACTIVITÉ")
        st.write(f"Période : Du {periode[0]} au {periode[1]}")
        st.write(f"Intervenantes : {', '.join(filter_inter)}")
        st.table(df_filt)
        st.info("Utilisez Ctrl+P (Windows) ou Cmd+P (Mac) pour imprimer cette zone.")

else:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés.")
