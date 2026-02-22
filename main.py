import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from knowledge_base import MATERIAUX, score_clinique, score_environnemental, ORIGINES, get_cout_transport
from material_store import (
    enregistrer_utilisation, get_tous_dossiers,
    get_dossier_materiau, get_stats_materiau, supprimer_dossier_materiau
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# CONFIG & STYLES
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SurgGreen AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.block-container { padding: 2rem 3rem; max-width: 1400px; }

.sg-header {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    border-radius: 16px; padding: 2rem 2.5rem; margin-bottom: 2rem;
}
.sg-header h1 { color: #fff; font-size: 1.9rem; font-weight: 600; margin: 0; }
.sg-header p  { color: #94a3b8; font-size: 0.9rem; margin: 0; }

.metric-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
.metric-card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 1.2rem 1.5rem; transition: box-shadow .2s;
}
.metric-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
.metric-card .label { font-size: 0.72rem; text-transform: uppercase; letter-spacing:.08em; color:#94a3b8; font-weight:600; }
.metric-card .value { font-size: 1.8rem; font-weight: 600; color: #0f172a; font-family:'DM Mono',monospace; margin: 4px 0 2px; }
.metric-card .sub   { font-size: 0.78rem; color: #64748b; }
.metric-card.green  { border-left: 4px solid #22c55e; }
.metric-card.blue   { border-left: 4px solid #3b82f6; }
.metric-card.amber  { border-left: 4px solid #f59e0b; }
.metric-card.purple { border-left: 4px solid #a855f7; }

.sg-card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 1.5rem; margin-bottom: 1.5rem; height: 100%;
}
.sg-card h3 { font-size:.85rem; text-transform:uppercase; letter-spacing:.08em; color:#64748b; font-weight:600; margin-bottom:1rem; }

.reco-badge {
    display:inline-block; background:linear-gradient(90deg,#dcfce7,#bbf7d0);
    color:#15803d; border-radius:8px; padding:6px 14px; font-weight:600; font-size:1rem; margin:6px 0;
}
.tag { display:inline-block; border-radius:6px; padding:2px 10px; font-size:.75rem; font-weight:600; margin:2px; }
.tag-green  { background:#dcfce7; color:#166534; }
.tag-red    { background:#fee2e2; color:#991b1b; }
.tag-amber  { background:#fef9c3; color:#854d0e; }
.tag-blue   { background:#dbeafe; color:#1e40af; }
.tag-purple { background:#f3e8ff; color:#6b21a8; }

.sg-table { width:100%; border-collapse:collapse; font-size:.83rem; }
.sg-table th { background:#f8fafc; color:#64748b; font-weight:600; text-transform:uppercase; font-size:.72rem; letter-spacing:.05em; padding:10px 12px; border-bottom:2px solid #e2e8f0; text-align:left; }
.sg-table td { padding:9px 12px; border-bottom:1px solid #f1f5f9; color:#1e293b; }
.sg-table tr:hover td { background:#f8fafc; }
.sg-table tr.top-row td { font-weight:600; color:#15803d; }

.score-bar-bg   { background:#e2e8f0; border-radius:4px; height:6px; width:100%; margin-top:4px; }
.score-bar-fill { height:6px; border-radius:4px; }

/* Voice recorder */
.voice-box {
    border: 2px dashed #e2e8f0; border-radius: 12px; padding: 1rem 1.5rem;
    background: #f8fafc; margin-bottom: 1rem; text-align: center;
}
.voice-box.active { border-color: #22c55e; background: #f0fdf4; }

/* Sidebar dossier */
.dossier-item {
    background: #f8fafc; border-radius: 8px; padding: 10px 12px;
    margin-bottom: 8px; border-left: 3px solid #3b82f6; font-size: .82rem;
}
.dossier-item .di-mat  { font-weight: 600; color: #1e293b; }
.dossier-item .di-meta { color: #64748b; font-size: .75rem; margin-top: 3px; }

div[data-testid="stTextArea"] textarea {
    border-radius:10px !important; border:1.5px solid #e2e8f0 !important;
    font-family:'DM Sans',sans-serif !important; font-size:.92rem !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color:#3b82f6 !important; box-shadow:0 0 0 3px rgba(59,130,246,.1) !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# NLP ENGINE
# ─────────────────────────────────────────────
from knowledge_base import PATHO_KEYWORDS, score_global

MAT_ALIASES = {
    "titane":     "titane_grade5",
    "acier":      "acier_316L",
    "peek":       "peek",
    "cobalt":     "cobalt_chrome",
    "zircone":    "zircone",
    "plga":       "plga_resorbable",
    "pla":        "pla_bio",
    "magnésium":  "magnesium_bio",
    "tantale":    "tantale_poreux",
    "nitinol":    "nitinol",
    "alumine":    "alumine",
    "silicone":   "silicone_medical",
    "hydroxyapatite": "hydroxyapatite",
    "pmma":       "pmma_neuro",
    "dacron":     "dacron_polyester",
    "ptfe":       "ptfe_expanded",
    "pyrocarbone":"pyrocarbone",
    "chitosane":  "chitosane",
    "collagène":  "collagene_bovin",
    "zinc":       "zinc_biodegradable",
}

def detect_age(text: str) -> int:
    m = re.search(r'(\d+)\s*(ans?|an)', text)
    if m: return int(m.group(1))
    m = re.search(r'(\d+)', text)
    return int(m.group(1)) if m else 35

def detect_pathologie(text: str, age: int) -> str:
    scores = {p: sum(1 for kw in kws if kw in text) for p, kws in PATHO_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "pédiatrie" if age < 18 else "orthopédie"
    if age < 18 and scores.get("pédiatrie", 0) == 0:
        scores["pédiatrie"] = 0.5
        best = max(scores, key=scores.get)
    return best

def detect_materiau_habituel(text: str) -> str:
    for alias, key in MAT_ALIASES.items():
        if alias in text:
            return key
    return "titane_grade5"

# Formes d'implant détectables dans le texte libre
FORMES_IMPLANT = {
    "broche":       ["broche", "broches", "brochage"],
    "vis":          ["vis", "vissage"],
    "plaque":       ["plaque", "plaques", "ostéosynthèse par plaque"],
    "clou":         ["clou", "clous", "enclouage", "centro-médullaire"],
    "prothèse":     ["prothèse", "prothèses", "arthroplastie"],
    "cage":         ["cage", "cages", "espaceur"],
    "ancre":        ["ancre", "ancres", "suture ancre"],
    "filet":        ["filet", "mesh", "treillis"],
    "stent":        ["stent", "stents", "endoprothèse"],
    "agraphe":      ["agraphe", "agrafes", "staple"],
    "cerclage":     ["cerclage", "fil de cerclage"],
    "scaffold":     ["scaffold", "matrice", "substitut osseux", "comblement"],
    "ciment":       ["ciment", "cimentation", "injection"],
    "greffe":       ["greffe", "allogreffe", "autogreffe"],
    "membrane":     ["membrane", "barrière"],
    "ligament":     ["ligament", "ligamentoplastie", "tendon"],
}

def detect_forme_implant(text: str) -> str | None:
    """Retourne la forme standardisée si détectée dans le texte, sinon None."""
    for forme, aliases in FORMES_IMPLANT.items():
        for a in aliases:
            if a in text:
                return forme
    return None

def composer_nom_recommandation(nom_materiau: str, forme: str | None) -> str:
    """
    Compose un nom affiché cohérent avec la forme de l'implant habituel.
    Ex : forme='broche', nom='PLGA 75:25 (...)' → 'Broches en PLGA 75:25'
    """
    if forme is None:
        return nom_materiau
    nom_court = nom_materiau.split("(")[0].strip()
    return f"{forme.capitalize()}s en {nom_court}"


def build_candidats(cible: str, mat_h_key: str, forme: str | None = None) -> pd.DataFrame:
    mat_h_data = MATERIAUX[mat_h_key]
    rows = []
    for k, m in MATERIAUX.items():
        if cible.lower() not in [t.lower() for t in m["types_chirurgie"]]:
            continue
        s_clin = score_clinique(m)
        s_env  = score_environnemental(m)
        gain   = round(mat_h_data["co2_kg_par_kg"] - m["co2_kg_par_kg"], 1)
        rows.append({
            "key": k, "Nom": m["nom"],
            "Nom Affiché": composer_nom_recommandation(m["nom"], forme),
            "Catégorie": m["categorie"],
            "Clinique": s_clin, "Écologie": s_env,
            "Sécurité": round(m["taux_succes_pct"] / 10, 1),
            "Prix":     round(10 - (m["prix_relatif"] * 2), 1),
            "Score Global": score_global(m),
            "Gain CO₂": gain, "Bio": m["biodegradable"],
            "CO₂/kg":   m["co2_kg_par_kg"], "IRM": m["compatible_irm"],
            "Durée (ans)": m["duree_vie_implant_ans"],
            "Référence":   m.get("reference", "—"),
        })
    df = pd.DataFrame(rows)
    return df.sort_values("Score Global", ascending=False).reset_index(drop=True) if not df.empty else df


def build_top3_diversifie(df: pd.DataFrame) -> list[dict]:
    """
    Retourne 3 candidats avec des profils distincts :
    - #1 Meilleur score global
    - #2 Meilleur score écologique (catégorie différente du #1)
    - #3 Meilleur prix (prix_relatif le plus bas, différent des deux premiers)
    """
    if df.empty:
        return []

    top3 = []
    categories_vues = set()

    # #1 — Meilleur score global
    t1 = df.iloc[0].to_dict()
    t1["profil"] = "🏆 Meilleur Score Global"
    t1["profil_color"] = "#15803d"
    top3.append(t1)
    categories_vues.add(t1["Catégorie"])

    # #2 — Meilleur score écologique, catégorie différente si possible
    df_eco = df.sort_values("Écologie", ascending=False)
    for _, row in df_eco.iterrows():
        r = row.to_dict()
        if r["Nom"] != t1["Nom"]:
            r["profil"] = "🌿 Profil Écologique"
            r["profil_color"] = "#0369a1"
            top3.append(r)
            categories_vues.add(r["Catégorie"])
            break

    # #3 — Meilleur prix (score Prix le plus élevé = prix_relatif le plus bas)
    df_prix = df.sort_values("Prix", ascending=False)
    for _, row in df_prix.iterrows():
        r = row.to_dict()
        already = any(r["Nom"] == t["Nom"] for t in top3)
        if not already:
            r["profil"] = "💰 Profil Économique"
            r["profil_color"] = "#b45309"
            top3.append(r)
            break

    return top3


# ─────────────────────────────────────────────
# COMPOSANTS UI
# ─────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="sg-header">
        <div>
            <h1>🛡️ SurgGreen AI</h1>
            <p>Audit Pathologique & Éco-Conception · Analyse multicritère des biomatériaux</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_input_zone() -> str:
    return st.text_area(
        "Décrivez le cas clinique :",
        placeholder="Ex : Tumeur au fémur, patient de 12 ans, actuellement avec du titane",
        height=80, label_visibility="collapsed",
        key="text_input"
    ).strip()

def render_metrics(top, mat_h_data, age, cible, nb_candidats):
    gain     = top["Gain CO₂"]
    gain_pct = round((gain / max(0.1, mat_h_data["co2_kg_par_kg"])) * 100)
    arbres   = round(gain / 25, 1)
    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card green">
            <div class="label">Gain Carbone Net</div>
            <div class="value">{gain:+.1f}</div>
            <div class="sub">kg CO₂ · {gain_pct:+d}% vs habitude</div>
        </div>
        <div class="metric-card blue">
            <div class="label">Score Global</div>
            <div class="value">{top['Score Global']:.1f}</div>
            <div class="sub">/ 10 · Clinique + Éco + Sécu</div>
        </div>
        <div class="metric-card amber">
            <div class="label">Équivalent Arbres</div>
            <div class="value">{arbres}</div>
            <div class="sub">arbres CO₂ économisés</div>
        </div>
        <div class="metric-card purple">
            <div class="label">Alternatives Trouvées</div>
            <div class="value">{nb_candidats}</div>
            <div class="sub">matériaux · cible : {cible.capitalize()}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_top3(top3: list, mat_h_data: dict, age: int):
    """Affiche 3 cartes de recommandation avec profils distincts."""
    cols = st.columns(3)
    colors = ["#15803d", "#0369a1", "#b45309"]
    bg_colors = ["#f0fdf4", "#eff6ff", "#fffbeb"]
    border_colors = ["#22c55e", "#3b82f6", "#f59e0b"]

    for i, (col, cand) in enumerate(zip(cols, top3)):
        with col:
            bio_tag = "✅ Bio" if cand["Bio"] else ""
            irm_tag = "🔵 IRM" if cand["IRM"] else "🔴 IRM"
            gain = cand["Gain CO₂"]
            gain_str = f"{gain:+.1f} kg CO₂"
            gain_color = "#15803d" if gain >= 0 else "#991b1b"

            st.markdown(f"""
            <div style="background:{bg_colors[i]};border:2px solid {border_colors[i]};
                        border-radius:14px;padding:1.2rem 1.3rem;height:100%">
                <div style="font-size:.72rem;font-weight:700;color:{colors[i]};
                            text-transform:uppercase;letter-spacing:.08em;margin-bottom:.6rem">
                    {cand['profil']}
                </div>
                <div style="font-size:1rem;font-weight:700;color:#0f172a;margin-bottom:.3rem">
                    {cand['Nom Affiché']}
                </div>
                <div style="font-size:.75rem;color:#64748b;margin-bottom:.8rem">
                    {cand['Catégorie']} · {cand['Durée (ans)']} ans
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:.4rem;font-size:.78rem;margin-bottom:.8rem">
                    <div><span style="color:#64748b">Score</span><br>
                         <b style="color:{colors[i]}">{cand['Score Global']}/10</b></div>
                    <div><span style="color:#64748b">Clinique</span><br>
                         <b>{cand['Clinique']}/10</b></div>
                    <div><span style="color:#64748b">Écologie</span><br>
                         <b>{cand['Écologie']}/10</b></div>
                    <div><span style="color:#64748b">Succès</span><br>
                         <b>{round(cand['Sécurité']*10)}%</b></div>
                </div>
                <div style="font-size:.82rem;font-weight:700;color:{gain_color};
                            background:white;border-radius:8px;padding:5px 10px;
                            display:inline-block;margin-bottom:.5rem">
                    {gain_str}
                </div>
                <div style="font-size:.72rem;color:#64748b">{bio_tag} &nbsp; {irm_tag}</div>
                <div style="font-size:.68rem;font-style:italic;color:#94a3b8;margin-top:.5rem">
                    {cand['Référence']}
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_radar(top, mat_h_data):
    fig = go.Figure()
    cats = ["Clinique", "Écologie", "Prix", "Sécurité"]
    fig.add_trace(go.Scatterpolar(
        r=[score_clinique(mat_h_data), score_environnemental(mat_h_data),
           10-(mat_h_data["prix_relatif"]*2), mat_h_data["taux_succes_pct"]/10],
        theta=cats, fill="toself",
        name=f"Habitude ({mat_h_data['nom'].split(' ')[0]})",
        line_color="#94a3b8", fillcolor="rgba(148,163,184,0.15)"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[top["Clinique"], top["Écologie"], top["Prix"], top["Sécurité"]],
        theta=cats, fill="toself",
        name=f"Conseillé ({top['Nom Affiché'].split(' ')[0]})",
        line_color="#22c55e", fillcolor="rgba(34,197,94,0.15)"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,10], tickfont=dict(size=9), gridcolor="#e2e8f0")),
        legend=dict(font=dict(size=10)), height=330,
        margin=dict(l=30,r=30,t=20,b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    st.markdown('<div class="sg-card"><h3>🆚 Comparaison Multicritère</h3>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_bar(df):
    fig = px.bar(
        df.head(5), x="Gain CO₂", y="Nom Affiché", orientation="h",
        color="Gain CO₂",
        color_continuous_scale=[[0,"#fef9c3"],[0.5,"#86efac"],[1,"#16a34a"]],
        labels={"Gain CO₂": "Gain Net (kg CO₂)"}, text="Gain CO₂"
    )
    fig.update_traces(texttemplate="%{text:+.1f} kg", textposition="outside")
    fig.update_layout(
        height=280, showlegend=False, coloraxis_showscale=False,
        margin=dict(l=10,r=60,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#f1f5f9"), yaxis=dict(tickfont=dict(size=11))
    )
    st.markdown('<div class="sg-card"><h3>🌿 Potentiel de Gain CO₂ · Top 5</h3>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def render_table(df):
    def score_bar(val, color="#22c55e"):
        pct = min(100, val * 10)
        return f'<div class="score-bar-bg"><div class="score-bar-fill" style="width:{pct}%;background:{color}"></div></div>'

    rows_html = ""
    for i, row in df.iterrows():
        cls      = "top-row" if i == 0 else ""
        crown    = "👑 " if i == 0 else ""
        bio_tag  = '<span class="tag tag-green">Bio</span>'  if row["Bio"] else ""
        irm_tag  = '<span class="tag tag-blue">IRM</span>'  if row["IRM"] else ""
        rows_html += f"""
        <tr class="{cls}">
            <td>{crown}{row['Nom Affiché']}<br><span style='color:#94a3b8;font-size:.72rem'>{row['Catégorie']}</span></td>
            <td>{row['Score Global']}</td>
            <td>{row['Clinique']}{score_bar(row['Clinique'])}</td>
            <td>{row['Écologie']}{score_bar(row['Écologie'],'#3b82f6')}</td>
            <td>{row['Sécurité']}</td>
            <td>{row['CO₂/kg']} kg</td>
            <td>{row['Gain CO₂']:+.1f} kg</td>
            <td>{bio_tag}{irm_tag}</td>
        </tr>"""

    st.markdown(f"""
    <div class="sg-card">
        <h3>📊 Comparatif Complet des Candidats</h3>
        <div style="overflow-x:auto">
        <table class="sg-table">
            <thead>
                <tr>
                    <th>Matériau</th><th>Score Global</th><th>Clinique</th>
                    <th>Écologie</th><th>Sécurité /10</th><th>CO₂/kg</th><th>Gain CO₂</th><th>Tags</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table></div>
    </div>
    """, unsafe_allow_html=True)


def render_historique(nom_materiau: str):
    utilisations = get_dossier_materiau(nom_materiau)
    if not utilisations:
        return
    stats = get_stats_materiau(nom_materiau)

    st.markdown("---")
    st.markdown(f"#### 📁 Dossier · {nom_materiau}")
    st.caption(f"{stats['count']} utilisation(s) · Dernière : {stats['derniere_utilisation']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Utilisations",      stats['count'])
    c2.metric("Âge moyen",         f"{stats['age_moyen']} ans")
    c3.metric("CO₂ moyen",         f"{stats['gain_co2_moyen']:+.1f} kg")
    c4.metric("CO₂ total économisé", f"{stats['gain_co2_total']:+.1f} kg")

    df_hist = pd.DataFrame(reversed(utilisations))
    df_hist.columns = ["Date", "Âge", "Pathologie", "Remplaçait", "Gain CO₂ (kg)"]
    st.dataframe(df_hist, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# ONGLET TRAÇABILITÉ
# ─────────────────────────────────────────────

def render_tracabilite(df_candidats: pd.DataFrame | None = None):
    """
    Onglet Traçabilité & Import :
    - Carte monde avec lignes depuis les pays d'origine vers Paris
    - Tableau détaillé : pays, distance, mode, CO₂ transport, coût financier
    """
    POIDS_IMPLANT_KG = 0.1  # 100 g par défaut

    # Construire le dataset de traçabilité
    rows = []
    keys_a_afficher = list(df_candidats["key"]) if df_candidats is not None else list(ORIGINES.keys())

    for key in keys_a_afficher:
        if key not in ORIGINES or key not in MATERIAUX:
            continue
        orig = ORIGINES[key]
        mat  = MATERIAUX[key]
        transp = get_cout_transport(key, POIDS_IMPLANT_KG)
        rows.append({
            "key": key,
            "Nom": mat["nom"].split("(")[0].strip(),
            "Catégorie": mat["categorie"],
            "Pays / Fabricant": f"{orig['flag']} {orig['pays']}",
            "Ville ref.": orig["ville_ref"],
            "lat": orig["lat"],
            "lon": orig["lon"],
            "Distance (km)": orig["distance_km"],
            "Mode": transp["mode"].capitalize(),
            "CO₂ Fabrication": mat["co2_kg_par_kg"],
            "CO₂ Transport (kg)": transp["co2_transport_kg"],
            "CO₂ Total (kg)": round(mat["co2_kg_par_kg"] * POIDS_IMPLANT_KG + transp["co2_transport_kg"], 4),
            "Coût Transport (€)": transp["cout_transport_eur"],
            "Note origine": orig["note_origine"],
        })

    if not rows:
        st.info("Lance un audit pour voir la traçabilité des candidats.")
        return

    df_trace = pd.DataFrame(rows)

    # ── MÉTRIQUES GLOBALES ──────────────────────────────────────────────────
    nb_france  = sum(1 for r in rows if r["Distance (km)"] < 100)
    nb_europe  = sum(1 for r in rows if 100 <= r["Distance (km)"] < 3000)
    nb_monde   = sum(1 for r in rows if r["Distance (km)"] >= 3000)
    co2_moy    = round(df_trace["CO₂ Transport (kg)"].mean(), 4)
    cout_moy   = round(df_trace["Coût Transport (€)"].mean(), 4)

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card green">
            <div class="label">🇫🇷 Fabrication Locale</div>
            <div class="value">{nb_france}</div>
            <div class="sub">matériaux &lt; 100 km</div>
        </div>
        <div class="metric-card blue">
            <div class="label">🇪🇺 Fabrication Europe</div>
            <div class="value">{nb_europe}</div>
            <div class="sub">matériaux 100–3000 km</div>
        </div>
        <div class="metric-card amber">
            <div class="label">✈️ Import Long Courrier</div>
            <div class="value">{nb_monde}</div>
            <div class="sub">matériaux &gt; 3000 km</div>
        </div>
        <div class="metric-card purple">
            <div class="label">CO₂ Transport Moyen</div>
            <div class="value">{co2_moy}</div>
            <div class="sub">kg CO₂ · implant 100 g · {cout_moy:.4f} €/implant</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CARTE MONDE ─────────────────────────────────────────────────────────
    PARIS_LAT, PARIS_LON = 48.85, 2.35

    # Couleur par mode de transport
    MODE_COLOR = {"aerien": "#ef4444", "maritime": "#3b82f6", "routier": "#22c55e"}
    MODE_LABEL = {"aerien": "✈️ Aérien", "maritime": "🚢 Maritime", "routier": "🚛 Routier"}

    fig_map = go.Figure()

    # Lignes d'origine → Paris
    for r in rows:
        orig = ORIGINES[r["key"]]
        mode = orig["mode_transport"]
        color = MODE_COLOR.get(mode, "#94a3b8")
        dist  = orig["distance_km"]
        opacity = min(0.9, 0.3 + dist / 12000)

        fig_map.add_trace(go.Scattergeo(
            lon=[orig["lon"], PARIS_LON],
            lat=[orig["lat"], PARIS_LAT],
            mode="lines",
            line=dict(width=1.8, color=color),
            opacity=opacity,
            showlegend=False,
            hoverinfo="skip",
        ))

    # Points d'origine
    for r in rows:
        orig  = ORIGINES[r["key"]]
        mode  = orig["mode_transport"]
        transp = get_cout_transport(r["key"], POIDS_IMPLANT_KG)
        color = MODE_COLOR.get(mode, "#94a3b8")
        fig_map.add_trace(go.Scattergeo(
            lon=[orig["lon"]],
            lat=[orig["lat"]],
            mode="markers+text",
            marker=dict(size=10, color=color, line=dict(width=1.5, color="white")),
            text=[r["Nom"]],
            textposition="top center",
            textfont=dict(size=9, color="#1e293b"),
            name=r["Nom"],
            hovertemplate=(
                f"<b>{r['Nom']}</b><br>"
                f"Origine : {orig['flag']} {orig['pays']}<br>"
                f"Distance : {orig['distance_km']:,} km<br>"
                f"Mode : {MODE_LABEL.get(mode, mode)}<br>"
                f"CO₂ transport : {transp['co2_transport_kg']} kg<br>"
                f"Coût transport : {transp['cout_transport_eur']:.4f} €<br>"
                f"<i>{orig['note_origine']}</i><extra></extra>"
            ),
            showlegend=False,
        ))

    # Point Paris (destination)
    fig_map.add_trace(go.Scattergeo(
        lon=[PARIS_LON], lat=[PARIS_LAT],
        mode="markers+text",
        marker=dict(size=14, color="#0f172a", symbol="star", line=dict(width=2, color="white")),
        text=["🏥 Paris"], textposition="bottom right",
        textfont=dict(size=10, color="#0f172a", family="DM Sans"),
        name="Destination · Paris",
        hovertemplate="<b>Destination · Paris, France</b><extra></extra>",
        showlegend=False,
    ))

    # Légende manuelle modes de transport
    for mode, color in MODE_COLOR.items():
        fig_map.add_trace(go.Scattergeo(
            lon=[None], lat=[None], mode="markers",
            marker=dict(size=10, color=color),
            name=MODE_LABEL[mode], showlegend=True,
        ))

    fig_map.update_layout(
        geo=dict(
            showland=True, landcolor="#f1f5f9",
            showocean=True, oceancolor="#dbeafe",
            showcoastlines=True, coastlinecolor="#cbd5e1",
            showcountries=True, countrycolor="#e2e8f0",
            showframe=False,
            projection_type="natural earth",
        ),
        height=520,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h", yanchor="bottom", y=0.02, xanchor="left", x=0.01,
            bgcolor="rgba(255,255,255,0.85)", bordercolor="#e2e8f0", borderwidth=1,
            font=dict(size=11),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    st.markdown('<div class="sg-card"><h3>🗺️ Carte des Origines · Flux d\'Import vers Paris</h3>', unsafe_allow_html=True)
    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── GRAPHIQUE DISTANCES ──────────────────────────────────────────────────
    df_bar = df_trace.sort_values("Distance (km)", ascending=True).copy()
    df_bar["Couleur"] = df_bar["Mode"].map({"Aerien": "#ef4444", "Maritime": "#3b82f6", "Routier": "#22c55e"})

    fig_dist = px.bar(
        df_bar, x="Distance (km)", y="Nom", orientation="h",
        color="Mode",
        color_discrete_map={"Aerien": "#ef4444", "Maritime": "#3b82f6", "Routier": "#22c55e"},
        text="Distance (km)",
        labels={"Distance (km)": "Distance depuis l'usine (km)"},
    )
    fig_dist.update_traces(texttemplate="%{text:,} km", textposition="outside")
    fig_dist.update_layout(
        height=max(280, len(df_bar) * 30),
        showlegend=True,
        margin=dict(l=10, r=80, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="#f1f5f9"),
        yaxis=dict(tickfont=dict(size=10)),
    )

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown('<div class="sg-card"><h3>📏 Distance d\'Import par Matériau</h3>', unsafe_allow_html=True)
        st.plotly_chart(fig_dist, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        # Donut CO₂ transport par mode
        co2_par_mode = df_trace.groupby("Mode")["CO₂ Transport (kg)"].sum().reset_index()
        fig_pie = px.pie(
            co2_par_mode, names="Mode", values="CO₂ Transport (kg)",
            color="Mode",
            color_discrete_map={"Aerien": "#ef4444", "Maritime": "#3b82f6", "Routier": "#22c55e"},
            hole=0.5,
        )
        fig_pie.update_traces(textinfo="percent+label", textfont_size=11)
        fig_pie.update_layout(
            height=300, showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.markdown('<div class="sg-card"><h3>🌫️ Part CO₂ Transport par Mode</h3>', unsafe_allow_html=True)
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── TABLEAU DÉTAILLÉ ────────────────────────────────────────────────────
    rows_html = ""
    for _, r in df_trace.iterrows():
        mode_color = {"Aerien": "#fee2e2", "Maritime": "#dbeafe", "Routier": "#dcfce7"}.get(r["Mode"], "#f1f5f9")
        mode_text  = {"Aerien": "#991b1b", "Maritime": "#1e40af", "Routier": "#166534"}.get(r["Mode"], "#1e293b")
        dist_bar_pct = min(100, int(r["Distance (km)"] / 120))
        rows_html += f"""
        <tr>
            <td><b>{r['Nom']}</b><br>
                <span style='color:#94a3b8;font-size:.72rem'>{r['Catégorie']}</span></td>
            <td>{r['Pays / Fabricant']}<br>
                <span style='color:#94a3b8;font-size:.72rem'>{r['Ville ref.']}</span></td>
            <td>
                {r['Distance (km)']:,} km
                <div class="score-bar-bg"><div class="score-bar-fill"
                    style="width:{dist_bar_pct}%;background:#94a3b8"></div></div>
            </td>
            <td><span style='background:{mode_color};color:{mode_text};
                border-radius:6px;padding:2px 8px;font-size:.75rem;font-weight:600'>
                {r['Mode']}</span></td>
            <td>{r['CO₂ Fabrication']} kg/kg</td>
            <td style='color:#0369a1;font-weight:600'>{r['CO₂ Transport (kg)']} kg</td>
            <td style='color:#0f172a;font-weight:700'>{r['CO₂ Total (kg)']} kg</td>
            <td style='color:#7c3aed;font-weight:600'>{r['Coût Transport (€)']:.4f} €</td>
        </tr>"""

    st.markdown(f"""
    <div class="sg-card">
        <h3>📋 Tableau Détaillé · Traçabilité & Coûts d'Import (implant 100 g)</h3>
        <div style="overflow-x:auto">
        <table class="sg-table">
            <thead><tr>
                <th>Matériau</th><th>Origine</th><th>Distance</th>
                <th>Mode</th><th>CO₂ Fab.</th>
                <th>CO₂ Transport</th><th>CO₂ Total</th><th>Coût Transport</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table></div>
        <div style='font-size:.72rem;color:#94a3b8;margin-top:.8rem'>
            ⚠️ Coûts calculés pour un implant de 100 g · Fret aérien : 0.05 kg CO₂/t·km ·
            Maritime : 0.01 kg CO₂/t·km · Routier : 0.10 kg CO₂/t·km (ADEME / IMO 2023)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── DÉTAIL FABRICANT ────────────────────────────────────────────────────
    with st.expander("🔍 Notes Fabricants & Filières d'Approvisionnement"):
        for r in rows:
            orig = ORIGINES[r["key"]]
            st.markdown(f"**{orig['flag']} {r['Nom']}** · {orig['pays']}  \n"
                        f"_{orig['note_origine']}_")


# ─────────────────────────────────────────────
# APP PRINCIPALE
# ─────────────────────────────────────────────

render_header()

tab_audit, tab_tracabilite, tab_historique = st.tabs(["🔬 Audit Pathologique", "🌍 Traçabilité & Import", "📋 Historique des Matériaux"])

# ── ONGLET 1 : AUDIT ────────────────────────────────────────────────────────
with tab_audit:
    user_input = render_input_zone()

    if user_input:
        ui = user_input.lower()

        age        = detect_age(ui)
        cible      = detect_pathologie(ui, age)
        mat_h_key  = detect_materiau_habituel(ui)
        mat_h_data = MATERIAUX[mat_h_key]
        forme      = detect_forme_implant(ui)

        df = build_candidats(cible, mat_h_key, forme)

        if df.empty:
            st.warning(f"⚠️ Aucun matériau trouvé pour la cible **{cible}**.")
            st.stop()

        top3 = build_top3_diversifie(df)
        top  = df.iloc[0]  # meilleur global pour les métriques et l'historique

        # Sauvegarde session pour l'onglet traçabilité
        st.session_state["df_candidats_session"] = df
        st.session_state["cible_session"] = cible

        enregistrer_utilisation(
            materiau_recommande = top["Nom"],
            age_patient         = age,
            pathologie          = cible,
            materiau_habituel   = mat_h_data["nom"],
            gain_co2            = top["Gain CO₂"],
        )

        render_metrics(top, mat_h_data, age, cible, len(df))

        st.markdown("#### 🎯 Top 3 Recommandations · Profils Différenciés")
        render_top3(top3, mat_h_data, age)

        st.markdown("<br>", unsafe_allow_html=True)

        col_left, col_right = st.columns(2)
        with col_left:
            render_radar(top, mat_h_data)
        with col_right:
            render_bar(df)

        render_table(df)
        render_historique(top["Nom"])

        st.markdown("""
        <div style="margin-top:1rem;padding:12px 16px;background:#fef9c3;border-radius:8px;
                    border-left:4px solid #f59e0b;font-size:.78rem;color:#78350f">
            ⚠️ <b>Usage décisionnel uniquement.</b> Ces recommandations sont des aides à la décision basées sur des
            données ACV publiées. La prescription finale reste sous la responsabilité exclusive du chirurgien.
        </div>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <div style="text-align:center;padding:4rem 2rem;color:#94a3b8">
            <div style="font-size:3rem;margin-bottom:1rem">🩺</div>
            <div style="font-size:1.1rem;font-weight:600;color:#475569">Bienvenue, Docteur.</div>
            <div style="font-size:.9rem;margin-top:.5rem">
                Décrivez votre cas clinique par texte ou par voix pour lancer l'audit écologique.
            </div>
        </div>
        """, unsafe_allow_html=True)


# ── ONGLET 2 : TRAÇABILITÉ ───────────────────────────────────────────────────
with tab_tracabilite:
    # Si un audit a été lancé dans la session, on filtre sur les candidats
    if "df_candidats_session" in st.session_state and not st.session_state["df_candidats_session"].empty:
        df_session = st.session_state["df_candidats_session"]
        st.caption(f"Affichage des {len(df_session)} candidats issus du dernier audit · "
                   f"Pathologie : {st.session_state.get('cible_session', '—')}")
        render_tracabilite(df_session)
    else:
        st.info("💡 Lance un audit dans l'onglet **🔬 Audit Pathologique** pour filtrer la traçabilité "
                "sur les matériaux candidats. En attendant, voici tous les matériaux de la base.")
        render_tracabilite(None)

# ── ONGLET 3 : HISTORIQUE ────────────────────────────────────────────────────
with tab_historique:
    dossiers = get_tous_dossiers()

    if not dossiers:
        st.info("Aucun historique pour l'instant. Lance un audit pour commencer à enregistrer.")
    else:
        choix = st.selectbox("Choisir un matériau :", sorted(dossiers.keys()))

        if choix:
            stats        = get_stats_materiau(choix)
            utilisations = get_dossier_materiau(choix)

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Utilisations",        stats["count"])
            c2.metric("Âge moyen",           f"{stats['age_moyen']} ans")
            c3.metric("CO₂ moyen",           f"{stats['gain_co2_moyen']:+.1f} kg")
            c4.metric("CO₂ total économisé", f"{stats['gain_co2_total']:+.1f} kg")
            c5.metric("Pathologie principale", stats["pathologie_top"])

            st.markdown("---")

            df_hist = pd.DataFrame(list(reversed(utilisations)))
            df_hist.columns = ["Date", "Âge", "Pathologie", "Remplaçait", "Gain CO₂ (kg)"]
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

            st.markdown("")
            if st.button(f"🗑️ Effacer l'historique de {choix}", type="secondary"):
                supprimer_dossier_materiau(choix)
                st.rerun()

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
    
