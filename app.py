import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import streamlit.components.v1 as components
import io
import base64
import plotly.express as px


# Helper : détecte si un PO est une Province
def is_province(name):
    return str(name).startswith("Province")

def icon_po(name):
    return "🏛️" if is_province(name) else "🏘️"

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Creos Extrascolaire")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
        #MainMenu, footer, header {visibility: hidden;}
        .main-header {
            background-color: #4169E1;
            padding: 15px 25px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header-title { font-size: 24px; font-weight: bold; margin: 0; }
        .tt-button {
            background-color: white; color: #4169E1; padding: 8px 18px;
            border-radius: 5px; text-decoration: none; font-weight: bold;
        }
    </style>
    <div class="main-header">
        <div class="header-title">Utilisateurs de Creos Extrascolaire</div>
        <a href="https://timetracking-az7ibzngb3zrfbgmrgygn8.streamlit.app" target="_blank" class="tt-button">⏱️ Time Tracking</a>
    </div>
""", unsafe_allow_html=True)

# --- 2. DONNÉES DE RÉFÉRENCE ---
# data_fwb sera construit dynamiquement depuis Google Sheets ci-dessous

# --- FONCTION GÉNÉRATION HTML IMPRESSION (Tab 2) ---
def generate_print_html(df_print, fl_p, fl_m, fl_s):
    date_str = pd.Timestamp.now().strftime("%d/%m/%Y à %H:%M")
    filter_parts = []
    if fl_p: filter_parts.append(f"Province(s) : {', '.join(fl_p)}")
    if fl_m: filter_parts.append(f"Paiement : {', '.join(fl_m)}")
    if fl_s: filter_parts.append(f"Services : {', '.join(fl_s)}")
    filter_text = " &nbsp;|&nbsp; ".join(filter_parts) if filter_parts else "Aucun filtre appliqué — Liste complète par province"
    province_colors = {
        "Bruxelles": "#ffeaa7", "Brabant Wallon": "#81ecec", "Hainaut": "#a29bfe",
        "Liège": "#74b9ff", "Namur": "#fab1a0", "Luxembourg": "#FF43D0",
    }
    rows_html = ""
    total = len(df_print)
    province_order = ["Bruxelles", "Brabant Wallon", "Hainaut", "Liège", "Namur", "Luxembourg"]
    for province in province_order:
        prov_df = df_print[df_print['Province'] == province].sort_values('Commune')
        if not prov_df.empty:
            bg_color = province_colors.get(province, "#e8f0fe")
            count = len(prov_df)
            rows_html += f"""
            <tr class="province-header">
                <td colspan="3" style="background-color:{bg_color}; border-left:4px solid #4169E1;">
                    📍 {province}
                    <span style="margin-left:10px; font-weight:normal; font-size:11px; opacity:0.7;">
                        ({count} commune{"s" if count > 1 else ""})
                    </span>
                </td>
            </tr>"""
            service_colors = {
                "Cantine Jour": "#FFD700", "Cantine Semaine": "#FF8C00",
                "Cantine Mois": "#FF0000", "Garderie": "#38bdf8", "Activités": "#4ade80"
            }
            for i, (_, row) in enumerate(prov_df.iterrows()):
                services_raw = row.get('Services', '') or ''
                services_list = [s.strip() for s in services_raw.split('|') if s.strip()]
                if services_list:
                    services_display = ' '.join([
                        f'<span style="background:{service_colors.get(s,"#ccc")};color:white;padding:2px 7px;'
                        f'border-radius:4px;font-size:10px;font-weight:bold;display:inline-block;margin:1px;'
                        f'-webkit-print-color-adjust:exact;print-color-adjust:exact;">{s}</span>'
                        for s in services_list
                    ])
                else:
                    services_display = '—'
                paiement = row.get('Paiement', '—') or '—'
                paiement_color = "#ec4899" if paiement == "Prépaiement" else "#38bdf8"
                row_bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
                rows_html += f"""
                <tr style="background-color:{row_bg};">
                    <td style="font-weight:600; color:#4169E1;">{row['Commune']}</td>
                    <td>
                        <span style="background:{paiement_color}; color:white; padding:2px 8px;
                                     border-radius:4px; font-size:11px; font-weight:bold;">
                            {paiement}
                        </span>
                    </td>
                    <td style="font-size:11px; color:#475569;">{services_display}</td>
                </tr>"""
    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Creos Extrascolaire — Impression</title>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; padding: 20px; }}
    .header {{ background-color: #4169E1; color: white; padding: 14px 20px; border-radius: 8px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }}
    .header h1 {{ font-size: 18px; margin: 0; }}
    .header .date {{ font-size: 11px; opacity: 0.85; }}
    .filters {{ background: #f0f7ff; border-left: 4px solid #4169E1; padding: 8px 14px; margin-bottom: 12px; border-radius: 0 6px 6px 0; font-size: 11px; color: #334155; }}
    .filters strong {{ color: #4169E1; }}
    .summary {{ background: #008080; color: white; display: inline-block; padding: 6px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; }}
    thead th {{ background-color: #4169E1; color: white; padding: 8px 10px; text-align: left; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    tr.province-header td {{ padding: 7px 10px; font-weight: bold; font-size: 12px; color: #1e293b; border-top: 2px solid #4169E1; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    tr:not(.province-header) td {{ padding: 6px 10px; border-bottom: 1px solid #e2e8f0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .footer {{ margin-top: 20px; text-align: center; font-size: 10px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; }}
    @page {{ margin: 0; size: A4; }}
    @media print {{ body {{ margin: 10mm 12mm; padding: 0; }} .no-print {{ display: none !important; }} thead {{ display: table-header-group; }} tr {{ page-break-inside: avoid; }} }}
</style></head><body>
<div class="header"><h1>🏫 Creos Extrascolaire — Liste des Communes</h1><span class="date">Imprimé le {date_str}</span></div>
<div class="filters"><strong>Filtres appliqués :</strong>&nbsp; {filter_text}</div>
<div class="summary">📍 Total : <strong>{total}</strong> commune{"s" if total > 1 else ""}</div>
<table><thead><tr><th style="width:35%">Commune</th><th style="width:22%">Mode de Paiement</th><th style="width:43%">Services</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<div class="footer">Creos Extrascolaire &mdash; Document généré automatiquement le {date_str}</div>
</body></html>"""
    return html

# --- FONCTION GÉNÉRATION HTML IMPRESSION (Tab 4 - Écoles) ---
def generate_print_html_ecoles(df_print, fl_p, fl_m, fl_s):
    date_str = pd.Timestamp.now().strftime("%d/%m/%Y à %H:%M")
    filter_parts = []
    if fl_p: filter_parts.append(f"Province(s) : {', '.join(fl_p)}")
    if fl_m: filter_parts.append(f"Paiement : {', '.join(fl_m)}")
    if fl_s: filter_parts.append(f"Services : {', '.join(fl_s)}")
    filter_text = " &nbsp;|&nbsp; ".join(filter_parts) if filter_parts else "Aucun filtre appliqué — Liste complète par province"
    province_colors = {
        "Bruxelles": "#ffeaa7", "Brabant Wallon": "#81ecec", "Hainaut": "#a29bfe",
        "Liège": "#74b9ff", "Namur": "#fab1a0", "Luxembourg": "#FF43D0",
    }
    service_colors = {
        "Cantine Jour": "#FFD700", "Cantine Semaine": "#FF8C00",
        "Cantine Mois": "#FF0000", "Garderie": "#38bdf8", "Activités": "#4ade80"
    }
    rows_html = ""
    total = len(df_print)
    province_order = ["Bruxelles", "Brabant Wallon", "Hainaut", "Liège", "Namur", "Luxembourg"]
    for province in province_order:
        prov_df = df_print[df_print['Province'] == province].sort_values(['Commune', 'Ecole']) if 'Ecole' in df_print.columns else df_print[df_print['Province'] == province].sort_values('Commune')
        if not prov_df.empty:
            bg_color = province_colors.get(province, "#e8f0fe")
            count = len(prov_df)
            rows_html += f'''
            <tr class="province-header">
                <td colspan="4" style="background-color:{bg_color}; border-left:4px solid #4169E1;">
                    📍 {province}
                    <span style="margin-left:10px; font-weight:normal; font-size:11px; opacity:0.7;">
                        ({count} école{"s" if count > 1 else ""})
                    </span>
                </td>
            </tr>'''
            for i, (_, row) in enumerate(prov_df.iterrows()):
                services_raw = row.get('Services', '') or ''
                services_list = [s.strip() for s in services_raw.split('|') if s.strip()]
                if services_list:
                    services_display = ' '.join([
                        f'<span style="background:{service_colors.get(s,"#ccc")};color:white;padding:2px 7px;'
                        f'border-radius:4px;font-size:10px;font-weight:bold;display:inline-block;margin:1px;'
                        f'-webkit-print-color-adjust:exact;print-color-adjust:exact;">{s}</span>'
                        for s in services_list
                    ])
                else:
                    services_display = '—'
                paiement = row.get('Paiement', '—') or '—'
                paiement_color = "#ec4899" if paiement == "Prépaiement" else "#38bdf8"
                row_bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
                ecole = row.get('Ecole', '—') or '—'
                commune = row.get('Commune', '—') or '—'
                rows_html += f'''
                <tr style="background-color:{row_bg};">
                    <td style="font-weight:600; color:#334155;">{commune}</td>
                    <td style="color:#4169E1; font-size:11px;">{ecole}</td>
                    <td>
                        <span style="background:{paiement_color}; color:white; padding:2px 8px;
                                     border-radius:4px; font-size:11px; font-weight:bold;">
                            {paiement}
                        </span>
                    </td>
                    <td style="font-size:11px; color:#475569;">{services_display}</td>
                </tr>'''
    html = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Creos Extrascolaire — Écoles Actives</title>
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; padding: 20px; }}
    .header {{ background-color: #008080; color: white; padding: 14px 20px; border-radius: 8px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }}
    .header h1 {{ font-size: 18px; margin: 0; }}
    .header .date {{ font-size: 11px; opacity: 0.85; }}
    .filters {{ background: #f0f7ff; border-left: 4px solid #008080; padding: 8px 14px; margin-bottom: 12px; border-radius: 0 6px 6px 0; font-size: 11px; color: #334155; }}
    .filters strong {{ color: #008080; }}
    .summary {{ background: #008080; color: white; display: inline-block; padding: 6px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11.5px; }}
    thead th {{ background-color: #008080; color: white; padding: 8px 10px; text-align: left; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    tr.province-header td {{ padding: 7px 10px; font-weight: bold; font-size: 12px; color: #1e293b; border-top: 2px solid #008080; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    tr:not(.province-header) td {{ padding: 6px 10px; border-bottom: 1px solid #e2e8f0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    .footer {{ margin-top: 20px; text-align: center; font-size: 10px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; }}
    @page {{ margin: 0; size: A4 landscape; }}
    @media print {{ body {{ margin: 10mm 12mm; padding: 0; }} .no-print {{ display: none !important; }} thead {{ display: table-header-group; }} tr {{ page-break-inside: avoid; }} }}
</style></head><body>
<div class="header"><h1>🏫 Creos Extrascolaire — Liste des Écoles Actives</h1><span class="date">Imprimé le {date_str}</span></div>
<div class="filters"><strong>Filtres appliqués :</strong>&nbsp; {filter_text}</div>
<div class="summary">🏫 Total : <strong>{total}</strong> école{"s" if total > 1 else ""} active{"s" if total > 1 else ""}</div>
<table><thead><tr><th style="width:20%">Commune</th><th style="width:30%">École</th><th style="width:18%">Mode de Paiement</th><th style="width:32%">Services</th></tr></thead>
<tbody>{rows_html}</tbody></table>
<div class="footer">Creos Extrascolaire &mdash; Document généré automatiquement le {date_str}</div>
</body></html>"""
    return html



# --- 3. CONNEXION GSHEETS & CHARGEMENT DES DONNÉES ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Feuille Ecoles (chargée en premier — contient Province depuis la mise à jour)
try:
    df_ecoles = conn.read(worksheet="Ecoles", ttl=600).dropna(how="all")
    for col in ['Fase PO', 'Fase école', 'Code postal']:
        if col in df_ecoles.columns:
            df_ecoles[col] = df_ecoles[col].astype(str).str.replace(r'\.0$', '', regex=True)
except Exception as e:
    df_ecoles = pd.DataFrame()
    st.warning(f"⚠️ Feuille 'Ecoles' introuvable : {e}")

# Construire data_fwb depuis df_ecoles (Province + Commune — source fiable, 268 communes)
_PROV_NORM = {
    "liege": "Liège", "liège": "Liège", "province de liège": "Liège", "province de liege": "Liège",
    "hainaut": "Hainaut", "province du hainaut": "Hainaut",
    "namur": "Namur", "province de namur": "Namur",
    "luxembourg": "Luxembourg", "province de luxembourg": "Luxembourg",
    "brabant wallon": "Brabant Wallon", "province du brabant wallon": "Brabant Wallon",
    "bruxelles": "Bruxelles", "région de bruxelles": "Bruxelles", "région bruxelloise": "Bruxelles",
    "région de bruxelles-capitale": "Bruxelles", "region de bruxelles-capitale": "Bruxelles",
    "bruxelles-capitale": "Bruxelles",
}
data_fwb = {}
if not df_ecoles.empty and 'Province' in df_ecoles.columns and 'Commune' in df_ecoles.columns:
    for _, row in df_ecoles.iterrows():
        raw_p = str(row.get('Province', '')).strip()
        comm  = str(row.get('Commune',  '')).strip()
        if not raw_p or not comm or comm.startswith('Province'):
            continue
        prov = _PROV_NORM.get(raw_p.lower(), raw_p)
        if prov not in data_fwb:
            data_fwb[prov] = set()
        data_fwb[prov].add(comm)
    data_fwb = {k: sorted(v) for k, v in data_fwb.items() if v}
    st.session_state['_data_fwb_cache'] = data_fwb
else:
    data_fwb = st.session_state.get('_data_fwb_cache', {})

# Feuille EcolesConfig (Tab 4)
_config_cols = ["Fase école", "Commune", "Province", "Extrascolaire", "Paiement", "Services"]
try:
    df_config = conn.read(worksheet="EcolesConfig", ttl=0).dropna(how="all")
    if df_config.empty or not all(c in df_config.columns for c in _config_cols):
        df_config = pd.DataFrame(columns=_config_cols)
    else:
        df_config['Fase école'] = df_config['Fase école'].astype(str).str.replace(r'\.0$', '', regex=True)
        df_config = df_config.drop_duplicates(subset=['Fase école'], keep='last').reset_index(drop=True)
except Exception:
    df_config = pd.DataFrame(columns=_config_cols)

# Écoles actives (Extrascolaire = Oui) — source de vérité pour Tab 1
df_active = df_config[df_config['Extrascolaire'] == 'Oui'].copy() if not df_config.empty else pd.DataFrame(columns=_config_cols)
active_communes = set(df_active['Commune'].unique()) if not df_active.empty else set()

# Résumé par commune pour Tab 1 (carte + liste)
if not df_active.empty:
    tab1_rows = []
    df_non = df_config[df_config['Extrascolaire'] == 'Non'].copy() if not df_config.empty else pd.DataFrame(columns=_config_cols)
    for comm, grp in df_active.groupby('Commune'):
        prov = grp['Province'].iloc[0]
        nb_oui = len(grp)
        nb_non = len(df_non[df_non['Commune'] == comm]) if not df_non.empty else 0
        # Écoles dans df_ecoles pour cette commune, non présentes dans df_config
        ecoles_comm = df_ecoles[df_ecoles['Commune'] == comm]['Fase école'].astype(str).tolist() if not df_ecoles.empty else []
        config_comm = df_config[df_config['Commune'] == comm]['Fase école'].astype(str).tolist() if not df_config.empty else []
        nb_sans = len([e for e in ecoles_comm if e not in config_comm])
        tab1_rows.append({
            'Commune': comm, 'Province': prov, 'NbEcoles': nb_oui,
            'NbOui': nb_oui, 'NbNon': nb_non, 'NbSans': nb_sans
        })
    df_tab1 = pd.DataFrame(tab1_rows)
else:
    df_tab1 = pd.DataFrame(columns=['Commune', 'Province', 'NbEcoles', 'NbOui', 'NbNon', 'NbSans'])


# --- 4. TABS ---
tab1, tab3, tab4 = st.tabs([
    "📊 Tableau de bord et Carte",
    "🏫 Écoles par Commune",
    "⚙️ Gestion des Écoles"
])

# ============================================================
# --- TAB 1 : DASHBOARD & CARTE (données depuis EcolesConfig) ---
# ============================================================
with tab1:
    t_dash = df_tab1['Commune'].nunique() if not df_tab1.empty else 0
    p_dash = len(df_active[df_active['Paiement'] == 'Prépaiement']) if not df_active.empty else 0
    po_dash = len(df_active[df_active['Paiement'] == 'Post-paiement']) if not df_active.empty else 0
    s_dash = {
        "Cantine Jour":    (int(df_active['Services'].str.contains("Cantine Jour",    na=False).sum()) if not df_active.empty else 0, "#FFD700"),
        "Cantine Semaine": (int(df_active['Services'].str.contains("Cantine Semaine", na=False).sum()) if not df_active.empty else 0, "#FF8C00"),
        "Cantine Mois":    (int(df_active['Services'].str.contains("Cantine Mois",    na=False).sum()) if not df_active.empty else 0, "#FF0000"),
        "Garderie":        (int(df_active['Services'].str.contains("Garderie",        na=False).sum()) if not df_active.empty else 0, "#38bdf8"),
        "Activités":       (int(df_active['Services'].str.contains("Activités",       na=False).sum()) if not df_active.empty else 0, "#4ade80"),
    }

    json_recs = df_tab1.to_json(orient='records')

    html_map = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>
            :root {{ --dark: #1e293b; --c-bruxelles: #ffeaa7; --c-brabant: #81ecec; --c-hainaut: #a29bfe; --c-liege: #74b9ff; --c-namur: #fab1a0; --c-luxembourg: #FF43D0; }}
            body {{ margin: 0; font-family: sans-serif; display: flex; height: 100vh; overflow: hidden; }}
            #left {{ flex: 4; padding: 10px; display: flex; flex-direction: column; }}
            #right {{ flex: 6; padding: 10px; display: flex; flex-direction: column; background: white; border-left: 1px solid #eee; }}
            #map-box {{ flex: 0 0 300px; background: #262730; border-radius: 8px; margin-bottom: 8px; }}
            svg {{ width: 100%; height: 100%; }}
            .commune {{ stroke: rgba(255,255,255,0.1); stroke-width: 0.5; opacity: 0.3; }}
            .active {{ stroke: #ffffff !important; stroke-width: 1.8px !important; opacity: 1 !important; }}
            #search {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 10px; }}
            #list {{ flex: 1; overflow-y: auto; }}
            .stats-panel {{ background: var(--dark); color: white; padding: 12px; border-radius: 12px; }}
            .panel-header {{ text-align: center; border-bottom: 1px solid #334155; padding-bottom: 5px; margin-bottom: 10px; }}
            .main-count {{ font-size: 40px; font-weight: bold; }}
            .cols-container {{ display: flex; gap: 15px; }}
            .col-half {{ flex: 1; }}
            .v-item {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 11px; }}
            .v-val {{ font-weight: bold; padding: 1px 7px; border-radius: 4px; min-width: 20px; text-align: center; }}
            .item-row {{ display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 12px; align-items: center; }}
            .counts-container {{ display: flex; gap: 5px; align-items: center; }}
            .cnt {{ padding: 2px 8px; border-radius: 4px; color: white; font-size: 11px; font-weight: bold; }}
        </style></head><body onload="init()">
    <div id="left">
        <div id="map-box"><svg id="svg" viewBox="0 0 900 650"></svg></div>
        <div class="stats-panel">
            <div class="panel-header"><div style="font-size:11px; opacity:0.7;">COMMUNES ACTIVES</div><div class="main-count">{t_dash}</div></div>
            <div class="cols-container">
                <div class="col-half">
                    <div style="font-size:10px; opacity:0.5; text-align:center;">PAIEMENT</div>
                    <div class="v-item"><span>Prépaiement</span><span class="v-val" style="background:#ec4899">{p_dash}</span></div>
                    <div class="v-item"><span>Post-paiement</span><span class="v-val" style="background:#38bdf8">{po_dash}</span></div>
                </div>
                <div class="col-half">
                    <div style="font-size:10px; opacity:0.5; text-align:center;">SERVICES</div>
                    { "".join([f'<div class="v-item"><span>{k}</span><span class="v-val" style="background:{v[1]}">{v[0]}</span></div>' for k,v in s_dash.items()]) }
                </div>
            </div>
        </div>
    </div>
    <div id="right"><input type="text" id="search" placeholder="🔍 Rechercher une commune..." onkeyup="doSearch()"><div id="list"></div></div>
    <script>
        const dbData = {json_recs};
        const mapRef = {json.dumps(data_fwb)};
        let db = new Map();
        dbData.forEach(r => db.set(r.Commune, r));
        // Données enrichies par commune (NbOui, NbNon, NbSans)
        function init() {{
            const svg = document.getElementById('svg');
            const anchors = {{ "Bruxelles": [330, 30], "Brabant Wallon": [330, 100], "Hainaut": [40, 180], "Liège": [560, 60], "Namur": [280, 300], "Luxembourg": [530, 400] }};
            Object.entries(mapRef).forEach(([pName, list]) => {{
                const cleanP = pName.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").split(' ')[0];
                list.forEach((name, i) => {{
                    const x = anchors[pName][0] + (i % 8 * 23), y = anchors[pName][1] + (Math.floor(i / 8) * 21);
                    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                    r.setAttribute("x", x); r.setAttribute("y", y); r.setAttribute("width", 20); r.setAttribute("height", 18); r.setAttribute("rx", 3);
                    r.setAttribute("class", "commune" + (db.has(name) ? " active" : ""));
                    r.style.fill = `var(--c-${{cleanP}})`;
                    const t = document.createElementNS("http://www.w3.org/2000/svg", "title"); t.textContent = name; r.appendChild(t); svg.appendChild(r);
                }});
            }}); render();
        }}
        function render() {{
            const listDiv = document.getElementById('list'); listDiv.innerHTML = "";
            ["Bruxelles", "Brabant Wallon", "Hainaut", "Liège", "Namur", "Luxembourg"].forEach(p => {{
                const filtered = Array.from(db.values()).filter(x => x.Province === p).sort((a,b) => a.Commune.localeCompare(b.Commune));
                if(filtered.length > 0) {{
                    const h = document.createElement('div'); h.style.background='#f8fafc'; h.style.padding='6px'; h.style.fontSize='11px'; h.innerText = p; listDiv.appendChild(h);
                    filtered.forEach(x => {{
                        const row = document.createElement('div'); row.className = 'item-row';
                        const counts = `<div class="counts-container"><span class="cnt" style="background:#22c55e" title="Utilisent Creos">✓ ${{x.NbOui}} Écoles utilisant Creos Extrascolaire</span><span class="cnt" style="background:#ef4444" title="N'utilisent pas Creos">✗ ${{x.NbNon}} Écoles qui ne l'utilisent pas</span><span class="cnt" style="background:#94a3b8" title="Sans configuration">? ${{x.NbSans}} Écoles sans choix enregistré</span></div>`;
                        row.innerHTML = `<span><strong style="color:#4169E1;">${{x.Commune}}</strong></span>${{counts}}`;
                        listDiv.appendChild(row);
                    }});
                }}
            }});
        }}
        function doSearch() {{ const v = document.getElementById('search').value.toLowerCase(); document.querySelectorAll('.item-row').forEach(r => {{ r.style.display = r.innerText.toLowerCase().includes(v) ? 'flex' : 'none'; }}); }}
    </script></body></html>"""
    components.html(html_map, height=750)


# ============================================================
# --- TAB 3 : ÉCOLES PAR COMMUNE ---
# ============================================================
with tab3:
    if df_ecoles.empty:
        st.error("⚠️ Impossible de charger la feuille **Ecoles**. Assurez-vous d'avoir créé une feuille nommée **'Ecoles'** dans votre Google Sheets.")
    else:
        all_po = sorted(df_ecoles['Commune'].dropna().unique().tolist())

        total_ecoles_global = len(df_ecoles)
        total_po_global = df_ecoles['Commune'].nunique()
        total_active_with_schools = len([c for c in active_communes if c in df_ecoles['Commune'].values])

        st.markdown(f"""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <div style="display:flex; gap:12px; margin-bottom:16px;">
            <div style="flex:1; background:#4169E1; color:white; padding:14px 18px; border-radius:10px; text-align:center;">
                <div style="font-size:10px; text-transform:uppercase; opacity:0.8; letter-spacing:1px;">Total Écoles</div>
                <div style="font-size:38px; font-weight:bold; line-height:1.1;">{total_ecoles_global}</div>
            </div>
            <div style="flex:1; background:#008080; color:white; padding:14px 18px; border-radius:10px; text-align:center;">
                <div style="font-size:10px; text-transform:uppercase; opacity:0.8; letter-spacing:1px;">PO / Communes</div>
                <div style="font-size:38px; font-weight:bold; line-height:1.1;">{total_po_global}</div>
            </div>
            <div style="flex:1; background:#1e293b; color:white; padding:14px 18px; border-radius:10px; text-align:center;">
                <div style="font-size:10px; text-transform:uppercase; opacity:0.8; letter-spacing:1px;">Actives avec écoles</div>
                <div style="font-size:38px; font-weight:bold; line-height:1.1; color:#4ade80;">{total_active_with_schools}</div>
            </div>
            <div style="flex:3; background:#f8fafc; border:1px solid #e2e8f0; padding:14px 18px; border-radius:10px; display:flex; align-items:center;">
                <div>
                    <div style="font-size:13px; color:#334155; font-weight:600; margin-bottom:4px;">
                        <i class="fa-solid fa-circle-info" style="color:#4169E1;"></i>
                        &nbsp;Comment utiliser cet onglet
                    </div>
                    <div style="font-size:11px; color:#64748b; line-height:1.6;">
                        Sélectionnez une <b>province</b> puis une <b>commune</b> pour afficher ses écoles.<br>
                        <span style="color:#4ade80; font-weight:bold;">✓ Vert</span> = commune active dans Creos &nbsp;|&nbsp;
                        <span style="color:#ef4444; font-weight:bold;">○ Gris</span> = commune non encore active
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if 't3_rc' not in st.session_state:
            st.session_state.t3_rc = 0

        col_p3, col_c3, col_s3, col_btn3 = st.columns([2, 3, 3, 1.5])

        with col_p3:
            prov_tab3 = st.selectbox(
                "🗺️ Province",
                ["Toutes les provinces"] + list(data_fwb.keys()),
                key=f"t3_prov_{st.session_state.t3_rc}"
            )

        if prov_tab3 == "Toutes les provinces":
            communes_dispo = [""] + all_po
        else:
            communes_prov = data_fwb.get(prov_tab3, [])
            base_list = sorted([c for c in communes_prov if c in df_ecoles['Commune'].values])
            # Inclure la Province elle-même si elle est un PO dans les écoles
            if prov_tab3 in df_ecoles['Commune'].values and prov_tab3 not in base_list:
                base_list = sorted(base_list + [prov_tab3])
            communes_dispo = [""] + base_list

        with col_c3:
            commune_tab3 = st.selectbox(
                "🏘️ Commune",
                communes_dispo,
                key=f"t3_comm_{st.session_state.t3_rc}",
                format_func=lambda x: ("— Sélectionnez une commune" if x == "" else f"{'✅' if x in active_communes else '⚪'} {icon_po(x)} {x}")
            )

        with col_s3:
            search_ecole = st.text_input(
                "🔍 Rechercher",
                key=f"t3_search_{st.session_state.t3_rc}",
                placeholder="Nom d'école, directeur, fase..."
            )

        with col_btn3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Effacer les filtres", key="t3_reset", use_container_width=True):
                st.session_state.t3_rc += 1
                st.rerun()

        if not commune_tab3 and not search_ecole:
            st.info("👆 Sélectionnez une commune ou saisissez un terme de recherche.")
        elif not commune_tab3 and search_ecole:
            df_search = df_ecoles[
                df_ecoles['Ecole'].astype(str).str.contains(search_ecole, case=False, na=False) |
                df_ecoles['Fase école'].astype(str).str.contains(search_ecole, case=False, na=False) |
                df_ecoles['Directeur.rice'].astype(str).str.contains(search_ecole, case=False, na=False)
            ]
            if df_search.empty:
                st.warning("Aucun résultat trouvé.")
            else:
                st.markdown(f"**{len(df_search)} résultat(s)** pour *\"{search_ecole}\"* sur toutes les communes")
                for _, row in df_search.iterrows():
                    email_link = f'<a href="mailto:{row["Email"]}" style="color:#4169E1;">{row["Email"]}</a>' if pd.notna(row.get("Email")) and str(row.get("Email","")).strip() else "—"
                    tel_link = f'<a href="tel:{row["Téléphone"]}" style="color:#4169E1;">{row["Téléphone"]}</a>' if pd.notna(row.get("Téléphone")) and str(row.get("Téléphone","")).strip() else "—"
                    st.markdown(
                        f'<div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:4px solid #4169E1; border-radius:8px; padding:10px 16px; margin-bottom:8px;">' +
                        f'<div style="font-weight:700; color:#1e293b; font-size:14px;">{row.get("Ecole","—")}</div>' +
                        f'<div style="font-size:11px; color:#64748b; margin-top:2px;">PO : {row.get("Commune","—")} &nbsp;|&nbsp; Fase école : {row.get("Fase école","—")} &nbsp;|&nbsp; Dir. : {row.get("Directeur.rice","—")}</div>' +
                        f'<div style="font-size:11px; color:#64748b; margin-top:2px;">{email_link} &nbsp;|&nbsp; {tel_link} &nbsp;|&nbsp; {row.get("Adresse","—")}, {row.get("Code postal","—")} {row.get("Localité","—")}</div>' +
                        f'</div>',
                        unsafe_allow_html=True
                    )
        else:
            df_comm = df_ecoles[df_ecoles['Commune'] == commune_tab3].copy()
            fase_po = df_comm['Fase PO'].iloc[0] if not df_comm.empty else '—'
            is_active_t3 = commune_tab3 in active_communes

            paiement_badge_html = ""
            services_badges_html = ""
            if is_active_t3 and not df_active[df_active['Commune'] == commune_tab3].empty:
                active_row = df_active[df_active['Commune'] == commune_tab3].iloc[0]
                paiement_info = active_row.get('Paiement', '—') or '—'
                services_info = active_row.get('Services', '') or ''
                pc = "#ec4899" if paiement_info == "Prépaiement" else "#38bdf8"
                paiement_badge_html = f'<span style="background:{pc}; color:white; padding:4px 12px; border-radius:6px; font-size:11px; font-weight:bold;">{paiement_info}</span>'
                service_colors = {"Cantine Jour": "#FFD700", "Cantine Semaine": "#FF8C00", "Cantine Mois": "#FF0000", "Garderie": "#38bdf8", "Activités": "#4ade80"}
                for s in services_info.split("|"):
                    s = s.strip()
                    if s:
                        sc = service_colors.get(s, "#999")
                        services_badges_html += f'<span style="background:{sc}; color:white; padding:4px 10px; border-radius:6px; font-size:10px; font-weight:bold; margin-left:4px;">{s}</span>'

            active_color = "#4ade80" if is_active_t3 else "#64748b"
            active_text = "&#10003; Active dans Creos Extrascolaire" if is_active_t3 else "&#9675; Non active dans Creos Extrascolaire"
            active_txt_color = "#1e293b" if is_active_t3 else "white"
            active_badge_html = f'<span style="background:{active_color}; color:{active_txt_color}; padding:5px 14px; border-radius:20px; font-size:11px; font-weight:bold;">{active_text}</span>'
            all_badges_html = services_badges_html + paiement_badge_html + active_badge_html

            st.markdown(f'<div style="background:#1e293b; color:white; padding:13px 20px; border-radius:10px; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;"><div style="display:flex; align-items:center; gap:16px;"><span style="font-size:20px; font-weight:bold;">&#127963; {commune_tab3}</span><span style="opacity:0.55; font-size:12px;">Fase PO : <b style="opacity:1;">{fase_po}</b></span><span style="opacity:0.55; font-size:12px;"><b style="opacity:1; color:#f8fafc;">{len(df_comm)}</b> &#233;cole(s)</span></div><div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">{all_badges_html}</div></div>', unsafe_allow_html=True)

            if search_ecole:
                mask = (
                    df_comm['Ecole'].str.contains(search_ecole, case=False, na=False) |
                    df_comm['Directeur.rice'].str.contains(search_ecole, case=False, na=False) |
                    df_comm['Fase école'].astype(str).str.contains(search_ecole, case=False, na=False)
                )
                df_display = df_comm[mask]
            else:
                df_display = df_comm

            if df_display.empty:
                st.warning("Aucune école trouvée pour cette recherche.")
            else:
                st.markdown(f"<div style='font-size:12px; color:#64748b; margin-bottom:10px;'><b style='color:#334155;'>{len(df_display)}</b> école(s) affichée(s)</div>", unsafe_allow_html=True)
                for i in range(0, len(df_display), 2):
                    cols = st.columns(2, gap="medium")
                    for j in range(2):
                        idx = i + j
                        if idx >= len(df_display): break
                        school = df_display.iloc[idx]
                        with cols[j]:
                            email = school.get('Email', None)
                            phone = school.get('Téléphone', None)
                            bte_val = school.get('Bte', None)
                            bte = f" bte {bte_val}" if pd.notna(bte_val) and str(bte_val).strip() not in ['nan', ''] else ""
                            num = school.get('N°', '')
                            rue = school.get('Rue', '')
                            cp = school.get('Code postal', '')
                            loc = school.get('Localité', '')
                            adresse = f"{rue} {num}{bte}, {cp} {loc}".strip()
                            email_html = (f'<a href="mailto:{email}" style="color:#4169E1; text-decoration:none;">{email}</a>' if pd.notna(email) and str(email).strip() not in ['nan', ''] else '<span style="color:#94a3b8;">—</span>')
                            phone_html = (f'<a href="tel:{phone}" style="color:#334155; text-decoration:none;">{phone}</a>' if pd.notna(phone) and str(phone).strip() not in ['nan', ''] else '<span style="color:#94a3b8;">—</span>')

                            fase_e = str(school.get('Fase école', ''))
                            school_conf = df_config[df_config['Fase école'] == fase_e]

                            if not school_conf.empty and school_conf.iloc[0]['Extrascolaire'] == 'Oui':
                                cfg_badge = """<span style="background:#4ade80; color:#1e293b; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:bold;">✓ Utilise l'extrascolaire</span>"""
                            elif not school_conf.empty:
                                # Correction appliquée ici :
                                cfg_badge = """<span style="background:#64748b; color:white; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:bold;">○ Pas d'extrascolaire</span>"""
                            else:
                                cfg_badge = ''

                            _card_html = (
                                f'<div style="background:white;border:1px solid #e2e8f0;border-radius:10px;padding:16px;margin-bottom:12px;border-left:5px solid #4169E1;box-shadow:0 2px 6px rgba(65,105,225,0.08);">' +
                                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:3px;">' +
                                f'<div style="font-size:14px;font-weight:bold;color:#4169E1;line-height:1.3;">&#127963; {school["Ecole"]}</div>' +
                                f'{cfg_badge}' +
                                f'</div>' +
                                f'<div style="font-size:10px;color:#94a3b8;margin-bottom:10px;letter-spacing:0.5px;">' +
                                f'N&#176; FASE &#201;COLE : <b style="color:#475569;font-size:11px;">{school["Fase école"]}</b>' +
                                f'</div>' +
                                f'<div style="border-top:1px solid #f1f5f9;padding-top:10px;font-size:12px;color:#334155;line-height:2;">' +
                                f'<div><b style="color:#4169E1;">&#128100;</b>&nbsp;<b>{school["Directeur.rice"]}</b></div>' +
                                f'<div><b style="color:#4169E1;">&#9993;</b>&nbsp;{email_html}</div>' +
                                f'<div><b style="color:#4169E1;">&#128222;</b>&nbsp;{phone_html}</div>' +
                                f'<div style="font-size:11px;color:#64748b;margin-top:4px;">&#128205;&nbsp;{adresse}</div>' +
                                f'</div>' +
                                f'</div>'
                            )
                            st.markdown(_card_html, unsafe_allow_html=True)

            st.divider()
            col_exp1, col_exp2, col_exp3 = st.columns([3, 2, 3])
            with col_exp2:
                buffer_e = io.BytesIO()
                export_df = df_display.drop(columns=['Rue', 'N°', 'Bte', 'Adresse'], errors='ignore')
                with pd.ExcelWriter(buffer_e, engine='xlsxwriter') as writer:
                    export_df.to_excel(writer, index=False, sheet_name='Ecoles')
                st.download_button(
                    label="📥 Exporter les écoles",
                    data=buffer_e.getvalue(),
                    file_name=f"ecoles_{commune_tab3.lower().replace(' ', '_').replace('/', '-')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True,
                    key="dl_ecoles"
                )


# ============================================================
# --- TAB 4 : CONFIGURATION DES ÉCOLES ---
# ============================================================
with tab4:
    if 't4_frc' not in st.session_state:
        st.session_state.t4_frc = 0

    st.header("⚙️ Gestion des Écoles par Commune")

    # --- Calcul stats ---
    n_active4 = len(df_active)
    n_comm4   = df_active['Commune'].nunique() if not df_active.empty else 0
    n_prep4   = len(df_active[df_active['Paiement'] == 'Prépaiement'])  if not df_active.empty else 0
    n_post4   = len(df_active[df_active['Paiement'] == 'Post-paiement']) if not df_active.empty else 0
    svc_list4 = ["Cantine Jour", "Cantine Semaine", "Cantine Mois", "Garderie", "Activités"]
    svc_cnt4  = {s: int(df_active['Services'].str.contains(s, na=False).sum()) if not df_active.empty else 0 for s in svc_list4}

    # --- Mise en page HAUT : 2/3 formulaire | 1/3 bloc teal ---
    col_left4, col_right4 = st.columns([2, 1])

    # ============================================================
    # COLONNE GAUCHE : Configurer une École
    # ============================================================
    with col_left4:
        st.subheader("📝 Configurer une École")

        # Sélecteurs en cascade
        s1, s2, s3, s4 = st.columns([2, 2, 3, 1])

        with s1:
            # Valider que la valeur en session_state est toujours une clé valide
            if st.session_state.get("t4_prov") not in list(data_fwb.keys()) and data_fwb:
                st.session_state["t4_prov"] = list(data_fwb.keys())[0]
            p_sel4 = st.selectbox(
                "1. Province / Région",
                list(data_fwb.keys()) if data_fwb else ["— Aucune donnée —"],
                key="t4_prov"
            )

        with s2:
            if not df_ecoles.empty:
                base_p4 = sorted([c for c in data_fwb.get(p_sel4, []) if c in df_ecoles['Commune'].values]) if p_sel4 in data_fwb else []
                # Inclure les PO "Province de X" qui correspondent à la province sélectionnée
                province_pos = [c for c in df_ecoles['Commune'].dropna().unique()
                                if is_province(c) and p_sel4.lower() in c.lower()]
                for pp in province_pos:
                    if pp not in base_p4:
                        base_p4 = sorted(base_p4 + [pp])
                communes_p4 = base_p4
            else:
                communes_p4 = []
            com_options4 = ["— Sélectionnez —"] + communes_p4
            if st.session_state.get("t4_comm") not in com_options4:
                st.session_state["t4_comm"] = com_options4[0]
                st.session_state.pop("t4_ecole", None)
            com_sel4 = st.selectbox(
                "2. Commune / PO",
                com_options4,
                key="t4_comm",
                format_func=lambda x: x if x == "— Sélectionnez —" else f"{icon_po(x)} {x}"
            )

        with s3:
            commune_valide4 = com_sel4 != "— Sélectionnez —" and not df_ecoles.empty
            if commune_valide4:
                df_comm4 = df_ecoles[df_ecoles['Commune'] == com_sel4].copy()
                df_comm4['Fase école'] = df_comm4['Fase école'].astype(str).str.replace(r'\.0$', '', regex=True)
                school_opts4 = []
                for _, row4 in df_comm4.iterrows():
                    fase4 = str(row4['Fase école'])
                    match4 = df_config[df_config['Fase école'] == fase4]
                    if not match4.empty:
                        icon4 = " ✅" if match4.iloc[0]['Extrascolaire'] == 'Oui' else " ⭕"
                    else:
                        icon4 = ""
                    school_opts4.append((f"{row4['Ecole']}{icon4} — Fase {fase4}", fase4, row4['Ecole']))
                fase_map4     = {opt[0]: (opt[1], opt[2]) for opt in school_opts4}
                ecole_labels4 = [opt[0] for opt in school_opts4]
                if st.session_state.get("t4_ecole") not in ecole_labels4:
                    st.session_state["t4_ecole"] = ecole_labels4[0] if ecole_labels4 else None
                ecole_label_sel4 = st.selectbox(
                    "3. École",
                    ecole_labels4,
                    key="t4_ecole"
                )
                ecole_fase_sel4, ecole_name_sel4 = fase_map4.get(ecole_label_sel4, ("", ""))
            else:
                ecole_fase_sel4, ecole_name_sel4 = "", ""
                st.session_state.pop("t4_ecole", None)
                st.selectbox(
                    "3. École",
                    ["— Choisissez d'abord une commune —"],
                    disabled=True
                )

        with s4:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Effacer", key="t4_reset", use_container_width=True):
                for k in ["t4_comm", "t4_comm_val", "t4_ecole", "t4_ecole_val"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()

        # Préchargement config actuelle
        if ecole_fase_sel4:
            cur4          = df_config[df_config['Fase école'] == ecole_fase_sel4]
            cur_extra4    = cur4.iloc[0]['Extrascolaire'] if not cur4.empty else 'Non'
            cur_pay4_raw  = cur4.iloc[0]['Paiement']      if not cur4.empty else ''
            cur_pay4      = cur_pay4_raw if cur_pay4_raw in ['Prépaiement', 'Post-paiement'] else 'Prépaiement'
            cur_serv4_raw = str(cur4.iloc[0].get('Services', '')) if not cur4.empty else ''
            cur_serv4     = [s.strip() for s in cur_serv4_raw.split('|') if s.strip() and s.strip() != 'nan']
        else:
            cur_extra4, cur_pay4, cur_serv4 = 'Non', 'Prépaiement', []

        # Formulaire
        with st.form("form_ecole4"):
            if ecole_fase_sel4:
                _fhdr = f'<div style="background:#f0f7ff; border-left:4px solid #4169E1; padding:10px 16px; border-radius:0 8px 8px 0; margin-bottom:12px;">'
                _fhdr += f'<span style="font-weight:700; color:#1e293b; font-size:15px;">🏫 {ecole_name_sel4}</span>'
                _fhdr += f'&nbsp;&nbsp;<span style="color:#64748b; font-size:12px;">Fase {ecole_fase_sel4} &nbsp;|&nbsp; {com_sel4}</span></div>'
                st.markdown(_fhdr, unsafe_allow_html=True)
                fc1, fc2 = st.columns(2)
                with fc1:
                    extra_v4 = st.radio(
                        "Utilise l'Extrascolaire Creos ?",
                        ["Oui", "Non"],
                        horizontal=True,
                        index=0 if cur_extra4 == 'Oui' else 1
                    )
                with fc2:
                    pay_v4 = st.radio(
                        "Mode de paiement",
                        ["Prépaiement", "Post-paiement"],
                        horizontal=True,
                        index=0 if cur_pay4 == 'Prépaiement' else 1,
                        help="Applicable uniquement si Extrascolaire = Oui"
                    )
                serv_v4 = st.multiselect(
                    "Services utilisés",
                    ["Cantine Jour", "Cantine Semaine", "Cantine Mois", "Garderie", "Activités"],
                    default=cur_serv4,
                    help="Applicable uniquement si Extrascolaire = Oui"
                )
                fbs1, fbs2 = st.columns(2)
                with fbs1:
                    saved4 = st.form_submit_button("💾 ENREGISTRER / MODIFIER", use_container_width=True)
                with fbs2:
                    deleted4 = st.form_submit_button("🗑️ SUPPRIMER", use_container_width=True)

                if saved4:
                    new_row4 = pd.DataFrame([{
                        "Fase école":    ecole_fase_sel4,
                        "Commune":       com_sel4,
                        "Province":      p_sel4,
                        "Extrascolaire": extra_v4,
                        "Paiement":      pay_v4 if extra_v4 == "Oui" else "",
                        "Services":      "|".join(serv_v4) if extra_v4 == "Oui" else ""
                    }])
                    df_upd4 = pd.concat(
                        [df_config[df_config['Fase école'] != ecole_fase_sel4], new_row4],
                        ignore_index=True
                    )
                    try:
                        conn.update(worksheet="EcolesConfig", data=df_upd4)
                        st.success("✅ Enregistré !")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e_save:
                        st.error(f"❌ Impossible d'enregistrer : {e_save}")

                if deleted4:
                    df_upd4 = df_config[df_config['Fase école'] != ecole_fase_sel4]
                    try:
                        conn.update(worksheet="EcolesConfig", data=df_upd4)
                        st.success("🗑️ Supprimé !")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e_del:
                        st.error(f"❌ Impossible de supprimer : {e_del}")
            else:
                st.info("👆 Sélectionnez une Province, une Commune et une École pour configurer.")
                st.form_submit_button("💾 ENREGISTRER / MODIFIER", disabled=True, use_container_width=True)

    # ============================================================
    # COLONNE DROITE : Bloc teal uniquement
    # ============================================================
    with col_right4:
        _svc_j4 = svc_cnt4["Cantine Jour"]
        _svc_s4 = svc_cnt4["Cantine Semaine"]
        _svc_m4 = svc_cnt4["Cantine Mois"]
        _svc_g4 = svc_cnt4["Garderie"]
        _svc_a4 = svc_cnt4["Activités"]
        _html4  = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
        _html4 += '<div style="background-color:#008080; padding:20px; border-radius:15px; color:white; text-align:center;">'
        _html4 += '<div style="font-size:11px; text-transform:uppercase; opacity:0.8; margin-bottom:4px;">Total des écoles actives</div>'
        _html4 += f'<div style="font-size:52px; font-weight:bold; margin-bottom:12px; line-height:1;">{n_active4}</div>'
        _html4 += '<div style="display:flex; justify-content:space-around; border-top:1px solid rgba(255,255,255,0.2); border-bottom:1px solid rgba(255,255,255,0.2); padding:12px 0; margin-bottom:12px;">'
        _html4 += f'<div style="text-align:center;"><span style="display:block; font-size:16px; font-weight:bold; color:#ec4899;">{n_prep4}</span><span style="font-size:10px; opacity:0.9;">Prépaiement</span></div>'
        _html4 += f'<div style="text-align:center;"><span style="display:block; font-size:16px; font-weight:bold; color:#38bdf8;">{n_post4}</span><span style="font-size:10px; opacity:0.9;">Post-paiement</span></div>'
        _html4 += f'<div style="text-align:center;"><span style="display:block; font-size:16px; font-weight:bold; color:#a78bfa;">{n_comm4}</span><span style="font-size:10px; opacity:0.9;">Communes</span></div>'
        _html4 += '</div>'
        _html4 += '<div style="text-align:left; font-size:10px; display:grid; grid-template-columns: 1fr 1fr; gap:6px;">'
        _html4 += f'<div style="background:rgba(255,255,255,0.1); padding:6px; border-radius:6px; border-left:4px solid #FFD700;"><i class="fa-solid fa-utensils"></i> Cant. Jour : <b>{_svc_j4}</b></div>'
        _html4 += f'<div style="background:rgba(255,255,255,0.1); padding:6px; border-radius:6px; border-left:4px solid #FF8C00;"><i class="fa-solid fa-calendar-day"></i> Cant. Sem. : <b>{_svc_s4}</b></div>'
        _html4 += f'<div style="background:rgba(255,255,255,0.1); padding:6px; border-radius:6px; border-left:4px solid #FF0000;"><i class="fa-solid fa-calendar-days"></i> Cant. Mois : <b>{_svc_m4}</b></div>'
        _html4 += f'<div style="background:rgba(255,255,255,0.1); padding:6px; border-radius:6px; border-left:4px solid #38bdf8;"><i class="fa-solid fa-clock"></i> Garderie : <b>{_svc_g4}</b></div>'
        _html4 += f'<div style="background:rgba(255,255,255,0.1); padding:6px; border-radius:6px; border-left:4px solid #4ade80; grid-column: span 2;"><i class="fa-solid fa-volleyball"></i> Activités : <b>{_svc_a4}</b></div>'
        _html4 += '</div></div>'
        st.markdown(_html4, unsafe_allow_html=True)

    # ============================================================
    # BAS PLEINE LARGEUR : Filtres, Liste & Graphiques
    # ============================================================
    st.divider()

    col_filt_title, col_filt_reset = st.columns([6, 2])
    with col_filt_title:
        st.subheader("🔍 Filtres & Liste des écoles utilisant l'Extrascolaire")
    with col_filt_reset:
        st.write("")
        if st.button("❌ Effacer filtres", key="t4_filt_reset", use_container_width=True):
            st.session_state.t4_frc += 1
            st.rerun()

    ff1, ff2, ff3 = st.columns(3)
    with ff1:
        fl4_p = st.multiselect(
            "Province",
            sorted(df_active['Province'].unique()) if not df_active.empty else [],
            placeholder="Choisir la province ou la Région",
            key=f"t4_fp_{st.session_state.t4_frc}"
        )
    with ff2:
        fl4_m = st.multiselect(
            "Paiement",
            ["Prépaiement", "Post-paiement"],
            placeholder="Type de paiement",
            key=f"t4_fm_{st.session_state.t4_frc}"
        )
    with ff3:
        fl4_s = st.multiselect(
            "Services",
            ["Cantine Jour", "Cantine Semaine", "Cantine Mois", "Garderie", "Activités"],
            placeholder="Choix des services",
            key=f"t4_fs_{st.session_state.t4_frc}"
        )

    df_r4 = df_active.copy()
    if not df_r4.empty:
        if fl4_p: df_r4 = df_r4[df_r4['Province'].isin(fl4_p)]
        if fl4_m: df_r4 = df_r4[df_r4['Paiement'].isin(fl4_m)]
        for sv4 in fl4_s:
            df_r4 = df_r4[df_r4['Services'].str.contains(sv4, na=False)]

    if not df_r4.empty:
        if not df_ecoles.empty:
            ecoles_info4 = df_ecoles[['Fase école', 'Ecole']].copy()
            ecoles_info4['Fase école'] = ecoles_info4['Fase école'].astype(str).str.replace(r'\.0$', '', regex=True)
            df_sorted4 = df_r4.merge(ecoles_info4, on='Fase école', how='left')
        else:
            df_sorted4 = df_r4.copy()
        df_sorted4 = df_sorted4.sort_values(['Province', 'Commune'])
        disp_cols4  = [c for c in ['Province', 'Commune', 'Ecole', 'Fase école', 'Paiement', 'Services'] if c in df_sorted4.columns]
        df_display4 = df_sorted4[disp_cols4]

        buf4 = io.BytesIO()
        with pd.ExcelWriter(buf4, engine='xlsxwriter') as wr4:
            df_display4.to_excel(wr4, index=False, sheet_name='EcolesActives')

        print_html4 = generate_print_html_ecoles(df_display4, fl4_p, fl4_m, fl4_s)
        b64_print4 = base64.b64encode(print_html4.encode('utf-8')).decode('ascii')

        # --- Ligne 1: Boutons (Export + Impression) à 1 niveau de colonnes ---
        btn_xl4, btn_pr4, _sp4 = st.columns([3, 3, 4])
        with btn_xl4:
            st.download_button(
                label="📥 Exporter vers Excel",
                data=buf4.getvalue(),
                file_name="ecoles_actives.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True,
                key="dl_ecoles4"
            )
        with btn_pr4:
            _js_fn4  = "function b64ToUtf8_4(s){return decodeURIComponent(atob(s).split('').map(function(c){return '%'+('00'+c.charCodeAt(0).toString(16)).slice(-2);}).join(''));}"
            _js_fn4 += f"function openPrint4(){{var h=b64ToUtf8_4('{b64_print4}');var w=window.open('','_blank');w.document.open();w.document.write(h);w.document.close();setTimeout(function(){{w.focus();w.print();}},600);}}"
            _btn_html4  = '<style>*{box-sizing:border-box;margin:0;padding:0;}body{margin:0;padding:0;}'
            _btn_html4 += 'button{background:#008080;color:white;border:none;padding:0 16px;border-radius:5px;cursor:pointer;width:100%;height:38px;font-size:14px;font-weight:bold;font-family:sans-serif;display:flex;align-items:center;justify-content:center;gap:6px;margin-top:2px;}'
            _btn_html4 += 'button:hover{background:#006666;}</style>'
            _btn_html4 += '<button onclick="openPrint4()">🖨️ IMPRESSION</button>'
            _btn_html4 += f'<script>{_js_fn4}</script>'
            components.html(_btn_html4, height=50)

        # --- Ligne 2: Tableau + Graphiques ---
        col_list4, col_viz4 = st.columns([6, 4], gap="medium")
        with col_list4:
            st.dataframe(df_display4, use_container_width=True, hide_index=True, height=450)
        with col_viz4:
            p_c4 = df_display4['Paiement'].value_counts().reset_index()
            fig_p4 = px.pie(p_c4, values='count', names='Paiement', hole=0.4, title="Modes de Paiement",
                            color='Paiement', color_discrete_map={'Prépaiement':'#ec4899', 'Post-paiement':'#38bdf8'})
            fig_p4.update_layout(height=250, margin=dict(l=0,r=0,t=40,b=0), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_p4, use_container_width=True, config={'displayModeBar': False})
            sl4 = ["Cantine Jour", "Cantine Semaine", "Cantine Mois", "Garderie", "Activités"]
            ct4 = [df_display4['Services'].str.contains(s, na=False).sum() for s in sl4]
            df_s4 = pd.DataFrame({'Service': sl4, 'Nombre': ct4})
            fig_s4 = px.bar(df_s4, x='Nombre', y='Service', orientation='h', title="Popularité des Services",
                            color='Service', color_discrete_map={"Cantine Jour": "#FFD700", "Cantine Semaine": "#FF8C00", "Cantine Mois": "#FF0000", "Garderie": "#38bdf8", "Activités": "#4ade80"})
            fig_s4.update_layout(height=250, showlegend=False, margin=dict(l=0,r=0,t=40,b=0), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_s4, use_container_width=True, config={'displayModeBar': False})
    else:
        if df_active.empty:
            st.info("ℹ️ Aucune école configurée pour l'instant.")
        else:
            st.warning("Aucun résultat pour ces filtres.")



# --- FOOTER ---
st.markdown("""
    <div style="position: fixed; bottom: 0; left: 0; right: 0; background-color: #1e293b;
        color: rgba(255,255,255,0.45); text-align: center; font-size: 11px;
        padding: 5px 0; letter-spacing: 1px; z-index: 9999;">
        © AJH 2026 — Creos Extrascolaire
    </div>
""", unsafe_allow_html=True)
