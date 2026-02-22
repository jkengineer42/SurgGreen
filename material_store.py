"""
SurgGreen — Dossier Matériaux
Historique JSON des utilisations par matériau recommandé
"""

import json
import os
from datetime import datetime
from pathlib import Path

STORE_PATH = Path("data/materiaux_dossier.json")


def _load() -> dict:
    """Charge le JSON ou retourne un dict vide."""
    if STORE_PATH.exists():
        try:
            with open(STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save(data: dict) -> None:
    """Sauvegarde le dict dans le JSON."""
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def enregistrer_utilisation(
    materiau_recommande: str,
    age_patient: int,
    pathologie: str,
    materiau_habituel: str,
    gain_co2: float,
) -> None:
    """Ajoute une entrée dans le dossier du matériau recommandé."""
    data = _load()

    entree = {
        "date":               datetime.now().strftime("%Y-%m-%d %H:%M"),
        "age_patient":        age_patient,
        "pathologie":         pathologie,
        "materiau_habituel":  materiau_habituel,
        "gain_co2_kg":        gain_co2,
    }

    if materiau_recommande not in data:
        data[materiau_recommande] = []

    data[materiau_recommande].append(entree)
    _save(data)


def get_dossier_materiau(nom_materiau: str) -> list:
    """Retourne toutes les utilisations enregistrées pour un matériau."""
    data = _load()
    return data.get(nom_materiau, [])


def get_tous_dossiers() -> dict:
    """Retourne l'intégralité du store."""
    return _load()


def get_stats_materiau(nom_materiau: str) -> dict:
    """Calcule des stats agrégées pour un matériau."""
    utilisations = get_dossier_materiau(nom_materiau)
    if not utilisations:
        return {"count": 0}

    ages       = [u["age_patient"] for u in utilisations]
    gains      = [u["gain_co2_kg"] for u in utilisations]
    pathos     = [u["pathologie"] for u in utilisations]
    habituels  = [u["materiau_habituel"] for u in utilisations]

    patho_counts   = {p: pathos.count(p) for p in set(pathos)}
    habituel_counts = {h: habituels.count(h) for h in set(habituels)}

    return {
        "count":            len(utilisations),
        "age_moyen":        round(sum(ages) / len(ages), 1),
        "gain_co2_total":   round(sum(gains), 1),
        "gain_co2_moyen":   round(sum(gains) / len(gains), 1),
        "pathologie_top":   max(patho_counts, key=patho_counts.get),
        "habituel_top":     max(habituel_counts, key=habituel_counts.get),
        "pathologies":      patho_counts,
        "habituels":        habituel_counts,
        "derniere_utilisation": utilisations[-1]["date"],
    }


def supprimer_dossier_materiau(nom_materiau: str) -> bool:
    """Supprime toutes les entrées d'un matériau. Retourne True si supprimé."""
    data = _load()
    if nom_materiau in data:
        del data[nom_materiau]
        _save(data)
        return True
    return False
