import streamlit as st
import anthropic
import json
from knowledge_base import MATERIAUX, top3_recommandation

st.set_page_config(page_title="SurgGreen", page_icon="🌱", layout="centered")

st.title("🏥🌱 SurgGreen")
st.caption("Aide au choix de matériaux chirurgicaux — Performance + Impact environnemental")
st.divider()

# ─────────────────────────────────────────
# SAISIE
# ─────────────────────────────────────────

description = st.text_area(
    "Décrivez le besoin chirurgical",
    placeholder='Ex: "plaque tibiale, patient jeune de 22 ans, retrait prévu dans 18 mois"',
    height=100
)

# ─────────────────────────────────────────
# CLAUDE — Extraction contexte
# ─────────────────────────────────────────

def analyser_avec_claude(description: str) -> dict:
    types_disponibles = list(set(
        t for m in MATERIAUX.values() for t in m["types_chirurgie"]
    ))

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Tu es expert en chirurgie orthopédique et biomatériaux.
Extrais les infos clés de cette description chirurgicale.
Types disponibles : {types_disponibles}
Description : "{description}"

Réponds UNIQUEMENT en JSON valide :
{{
  "type_chirurgie": "type parmi la liste",
  "retrait_prevu": true/false,
  "patient_jeune": true/false,
  "irm_necessaire": true/false,
  "contraintes": "résumé 1 phrase",
  "confiance": "haute/moyenne/faible"
}}"""
        }]
    )

    texte = response.content[0].text.replace("```json", "").replace("```", "").strip()
    return json.loads(texte)

# ─────────────────────────────────────────
# BOUTON
# ─────────────────────────────────────────

if st.button("🔍 Analyser et trouver le Top 3", type="primary", use_container_width=True):
    if not description.strip():
        st.warning("Décrivez le besoin chirurgical d'abord.")
    else:
        with st.spinner("Claude analyse votre description..."):
            try:
                ctx = analyser_avec_claude(description)
            except Exception as e:
                st.error(f"Erreur Claude : {e}")
                st.stop()

        # Contexte extrait
        with st.container(border=True):
            st.markdown("**🧠 Contexte extrait par Claude**")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Type détecté", ctx["type_chirurgie"])
            c2.metric("Retrait prévu", "✅" if ctx["retrait_prevu"] else "❌")
            c3.metric("Patient jeune", "✅" if ctx["patient_jeune"] else "❌")
            c4.metric("IRM nécessaire", "✅" if ctx["irm_necessaire"] else "❌")
            if ctx.get("contraintes"):
                st.info(f"💡 {ctx['contraintes']}")

        st.divider()

        # Top 3
        resultats = top3_recommandation(ctx["type_chirurgie"])
        eligibles = [r for r in resultats if r["score_final"] > 0]

        if not eligibles:
            st.error("Aucun matériau ne passe le verrou de sécurité clinique pour cette chirurgie.")
        else:
            st.subheader(f"Top 3 — {ctx['type_chirurgie'].capitalize()}")
            medailles = ["🥇", "🥈", "🥉"]

            for i, m in enumerate(eligibles):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"### {medailles[i]} {m['nom']}")
                        st.progress(m["score_final"] / 10,
                                    text=f"Score global : **{m['score_final']}/10**")
                    col2.metric("⚕️ Clinique", f"{m['score_clinique']}/10")
                    col3.metric("🌍 CO₂", f"{m['co2_kg_par_kg']} kg/kg")

                    c1, c2, c3 = st.columns(3)
                    c1.write(f"✅ Succès : {m['taux_succes_pct']}%")
                    c2.write(f"♻️ Biodégradable : {'✅' if m['biodegradable'] else '❌'}")
                    c3.write(f"🔧 Retrait : {'✅' if m['retrait_possible'] else '❌'}")

                    # Alertes contextuelles
                    if ctx["retrait_prevu"] and not m["retrait_possible"]:
                        st.warning("⚠️ Retrait prévu mais ce matériau ne peut pas être retiré")
                    if ctx["irm_necessaire"] and not m["compatible_irm"]:
                        st.warning("⚠️ Suivi IRM prévu mais ce matériau génère des artéfacts")
                    if ctx["patient_jeune"] and m.get("duree_vie_implant_ans", 99) < 10:
                        st.warning("⚠️ Patient jeune — durée de vie de l'implant courte")

                    st.caption(f"📚 {m['reference']}")