import os
import json
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from knowledge_base import MATERIAUX, score_clinique, score_environnemental, score_global
from material_store import (
    enregistrer_utilisation, get_tous_dossiers,
    get_dossier_materiau, get_stats_materiau, supprimer_dossier_materiau
)

# ─────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

app = FastAPI(title="SurgGreen API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    description: str

class RecordRequest(BaseModel):
    materiau_recommande: str
    age_patient: int
    pathologie: str
    materiau_habituel: str
    gain_co2: float

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def top3_recommandation(type_chirurgie: str) -> list:
    candidats = []
    for k, m in MATERIAUX.items():
        if type_chirurgie.lower() not in [t.lower() for t in m["types_chirurgie"]]:
            continue
        candidats.append({
            "key": k,
            "nom": m["nom"],
            "score_final": score_global(m),
            "score_clinique": score_clinique(m),
            "score_environnemental": score_environnemental(m),
            "co2_kg_par_kg": m["co2_kg_par_kg"],
            "taux_succes_pct": m["taux_succes_pct"],
            "biodegradable": m["biodegradable"],
            "retrait_possible": m.get("retrait_possible", False),
            "compatible_irm": m["compatible_irm"],
            "duree_vie_implant_ans": m["duree_vie_implant_ans"],
            "reference": m.get("reference", "—"),
        })
    candidats.sort(key=lambda x: x["score_final"], reverse=True)
    return candidats[:3]

# ─────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "SurgGreen API"}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    types_disponibles = list(set(
        t for m in MATERIAUX.values() for t in m["types_chirurgie"]
    ))

    prompt = f"""Tu es expert en chirurgie orthopédique et biomatériaux.
Extrais les infos clés de cette description chirurgicale.
Types disponibles : {types_disponibles}
Description : "{req.description}"

Réponds UNIQUEMENT en JSON valide, sans backticks, sans texte avant ou après :
{{
  "type_chirurgie": "type parmi la liste",
  "retrait_prevu": true,
  "patient_jeune": true,
  "irm_necessaire": false,
  "contraintes": "résumé 1 phrase",
  "confiance": "haute"
}}"""

    try:
        response = model.generate_content(prompt)
        texte = response.text.replace("```json", "").replace("```", "").strip()
        ctx = json.loads(texte)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur Gemini : {str(e)}")

    recommandations = top3_recommandation(ctx["type_chirurgie"])

    return {
        "contexte": ctx,
        "recommandations": recommandations
    }


@app.post("/record")
def record(req: RecordRequest):
    try:
        enregistrer_utilisation(
            materiau_recommande=req.materiau_recommande,
            age_patient=req.age_patient,
            pathologie=req.pathologie,
            materiau_habituel=req.materiau_habituel,
            gain_co2=req.gain_co2,
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
def history_all():
    return get_tous_dossiers()


@app.get("/history/{materiau_name}")
def history_one(materiau_name: str):
    return get_dossier_materiau(materiau_name)


@app.get("/stats/{materiau_name}")
def stats(materiau_name: str):
    return get_stats_materiau(materiau_name)


@app.delete("/history/{materiau_name}")
def delete_history(materiau_name: str):
    deleted = supprimer_dossier_materiau(materiau_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Matériau non trouvé")
    return {"status": "deleted"}


# ─────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
