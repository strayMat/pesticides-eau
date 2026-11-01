import os
from pathlib import Path

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DIR2ROOT = Path(__file__).parent.parent.absolute()
DIR2DATA = DIR2ROOT / "data"
DIR2RAW = DIR2DATA / "raw"
DIR2REFERENCES = Path(__file__).parent / "references"

# Jeu data.gouv « Résultats du contrôle sanitaire de l'eau du robinet » (SISE-Eaux).
# Contient, par type d'installation (CAP = captage, TTP = traitement/production, UDI = distribution),
# un fichier de prélèvements (PLV) et un fichier de résultats (RESULT).
DATAGOUV_DATASET_SLUG = "resultats-du-controle-sanitaire-de-leau-du-robinet"
DATAGOUV_API = "https://www.data.gouv.fr/api/1/datasets"

# Plage d'années demandée pour l'étude. SISE-Eaux n'est publié en open data qu'à partir de 2016.
MIN_YEAR = 2010
MAX_YEAR = 2025
FIRST_PUBLISHED_YEAR = 2016

# Référentiel des paramètres pesticides (extrait du seed `references_generations_futures.csv`
# du projet Data For Good 13_pollution_eau, licence MIT).
PATH2PESTICIDES_REF = DIR2REFERENCES / "parametres_pesticides.csv"
# Paramètre SISE « Total des pesticides analysés » calculé par le laboratoire.
PESTOT_CODE = "PESTOT"

# Seuils (µg/L)
SEUIL_EDCH_SUBSTANCE = 0.1  # limite de qualité eau distribuée, par substance
SEUIL_EDCH_TOTAL = 0.5  # limite de qualité eau distribuée, somme des pesticides
SEUIL_BRUTE_SUBSTANCE = 2.0  # limite de qualité eaux brutes, par substance
SEUIL_BRUTE_TOTAL = 5.0  # limite de qualité eaux brutes, somme des pesticides

DEFAULT_OUTPUT = DIR2DATA / "pesticides_captage_commune.parquet"
