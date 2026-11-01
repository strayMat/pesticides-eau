"""Téléchargement des archives SISE-Eaux « eau du robinet » depuis data.gouv.fr."""

import logging
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

from pesticides_eau.constants import DATAGOUV_API, DATAGOUV_DATASET_SLUG, DIR2RAW

logger = logging.getLogger(__name__)

# eaurob-2024.zip (annuel) ou eaurob-202601.zip (mensuel)
RESOURCE_PATTERN = re.compile(r"eaurob-(\d{4}|\d{6})\.zip$")
# Référentiels (PAR = paramètres) : eaurob-ref-AAAAMMJJ.zip
REF_PATTERN = re.compile(r"eaurob-ref-(\d{8})\.zip$")
REF_PERIOD = "ref"


def _get_json(url: str) -> dict:
    import json

    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        data: dict = json.load(resp)
        return data


def list_resources() -> dict[str, str]:
    """Retourne {période: url} pour les archives eaurob-AAAA.zip / eaurob-AAAAMM.zip, et {"ref": url} du référentiel."""
    meta = _get_json(f"{DATAGOUV_API}/{DATAGOUV_DATASET_SLUG}/")
    resources = {}
    refs = {}
    for res in meta["resources"]:
        name = res.get("title") or res["url"].rsplit("/", 1)[-1]
        if match := RESOURCE_PATTERN.search(name):
            resources[match.group(1)] = res["url"]
        elif match := REF_PATTERN.search(name):
            refs[match.group(1)] = res["url"]
    if refs:  # référentiel le plus récent
        resources[REF_PERIOD] = refs[max(refs)]
    return resources


def download_period(period: str, raw_dir: Path = DIR2RAW, resources: dict[str, str] | None = None) -> Path:
    """Télécharge et décompresse l'archive d'une période (« 2024 », « 202601 » ou « ref »).

    Retourne le dossier d'extraction. Ne retélécharge pas si le dossier existe déjà.
    """
    extract_dir = raw_dir / f"eaurob-{period}"
    if extract_dir.exists() and any(extract_dir.iterdir()):
        logger.info("Archive %s déjà présente dans %s", period, extract_dir)
        return extract_dir
    resources = resources if resources is not None else list_resources()
    if period not in resources:
        msg = f"Période {period} absente du jeu data.gouv (disponibles : {sorted(resources)})"
        raise KeyError(msg)
    raw_dir.mkdir(parents=True, exist_ok=True)
    zip_path = raw_dir / f"eaurob-{period}.zip"
    logger.info("Téléchargement %s", resources[period])
    with urllib.request.urlopen(resources[period], timeout=600) as resp, open(zip_path, "wb") as f:  # noqa: S310
        shutil.copyfileobj(resp, f)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    zip_path.unlink()
    return extract_dir
