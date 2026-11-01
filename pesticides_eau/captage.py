"""Table des pesticides mesurés aux captages (eaux brutes), agrégée par commune du captage et par année.

Source : SISE-Eaux, fichiers CAP (installations de type captage) du jeu data.gouv
« Résultats du contrôle sanitaire de l'eau du robinet ». La commune retenue est celle du point de
surveillance du prélèvement (`inseecommuneprinc`), c'est-à-dire la localisation du captage.
"""

import logging
from collections.abc import Iterable
from pathlib import Path

import ibis
import ibis.expr.types as ir
from ibis import _

from pesticides_eau.constants import (
    PATH2PESTICIDES_REF,
    PESTOT_CODE,
    SEUIL_BRUTE_SUBSTANCE,
    SEUIL_BRUTE_TOTAL,
    SEUIL_EDCH_SUBSTANCE,
    SEUIL_EDCH_TOTAL,
)

logger = logging.getLogger(__name__)

# Colonnes SISE-Eaux utilisées (mêmes noms que dans les fichiers DIS_PLV / DIS_RESULT).
COL_PRELEVEMENT = "referenceprel"
COL_INSTALLATION = "cdreseau"
# `inseecommune` dans les fichiers eaurob (CAP/TTP/UDI_PLV), `inseecommuneprinc` dans DIS_PLV.
COL_COMMUNE_CANDIDATES = ("inseecommune", "inseecommuneprinc")
COL_DATE = "dateprel"
COL_PARAMETRE = "cdparametresiseeaux"
COL_VALEUR = "valtraduite"


def find_cap_files(dirs: Iterable[Path], kind: str) -> list[Path]:
    """Fichiers texte des captages (`CAP`) de type `PLV` ou `RES` (CAP_RES_* / CAP_RESULT_*) dans les dossiers extraits."""
    files = []
    for d in dirs:
        for f in sorted(Path(d).rglob("*")):
            name = f.name.upper()
            if f.is_file() and f.suffix.lower() in {".txt", ".csv"} and "CAP" in name and kind in name:
                files.append(f)
    if not files:
        msg = f"Aucun fichier CAP {kind} trouvé dans {list(dirs)}"
        raise FileNotFoundError(msg)
    return files


def _read(con: ibis.BaseBackend, files: list[Path]) -> ir.Table:
    return con.read_csv(
        [str(f) for f in files],
        all_varchar=True,
        union_by_name=True,
        header=True,
    )


def read_pesticides_ref(con: ibis.BaseBackend, path: Path = PATH2PESTICIDES_REF) -> ir.Table:
    """Référentiel des substances actives et métabolites (hors totaux)."""
    ref = con.read_csv(str(path), all_varchar=True, header=True)
    return ref.filter(_.categorie_2.notnull() & (_.categorie_2 != "")).select(
        COL_PARAMETRE, "libminparametre", "categorie_2", "categorie_3"
    )


def _to_float(col: ir.StringValue) -> ir.FloatingValue:
    return col.replace(",", ".").try_cast("float64")


def build_pesticides_captage_commune(
    con: ibis.BaseBackend,
    data_dirs: Iterable[Path],
    start_year: int,
    end_year: int,
) -> ir.Table:
    """Construit l'expression ibis de la table commune du captage x année."""
    data_dirs = list(data_dirs)
    plv_raw = _read(con, find_cap_files(data_dirs, "PLV"))
    res_raw = _read(con, find_cap_files(data_dirs, "RES"))
    col_commune = next((c for c in COL_COMMUNE_CANDIDATES if c in plv_raw.columns), None)
    if col_commune is None:
        msg = f"Aucune colonne commune parmi {COL_COMMUNE_CANDIDATES} : {plv_raw.columns}"
        raise KeyError(msg)

    plv = (
        plv_raw
        .select(
            referenceprel=_[COL_PRELEVEMENT],
            code_captage=_[COL_INSTALLATION],
            inseecommune=_[col_commune].strip().lpad(5, "0"),
            annee=_[COL_DATE].re_extract(r"(\d{4})", 1).try_cast("int32"),
        )
        .filter(_.annee.between(start_year, end_year), _.inseecommune.notnull())
        .distinct(on="referenceprel", keep="first")
    )

    res = res_raw.select(
        referenceprel=_[COL_PRELEVEMENT],
        cdparametresiseeaux=_[COL_PARAMETRE].strip(),
        valeur=_to_float(_[COL_VALEUR]),
    )

    # Un paramètre peut être analysé plusieurs fois sur un prélèvement (terrain / labos) : on garde le max.
    ref = read_pesticides_ref(con)
    mesures = (
        res
        .join(ref, COL_PARAMETRE)
        .group_by(["referenceprel", COL_PARAMETRE])
        .aggregate(valeur=_.valeur.max())
        .join(plv, "referenceprel")
    )

    # Niveau prélèvement
    par_prel = mesures.group_by(["referenceprel", "inseecommune", "annee"]).aggregate(
        n_parametres=_.count(),
        n_quantifies=(_.valeur > 0).sum(),
        conc_max=_.valeur.max(),
        total=_.valeur.fill_null(0).sum(),
    )
    pestot = res.filter(_[COL_PARAMETRE] == PESTOT_CODE).group_by("referenceprel").aggregate(pestot_labo=_.valeur.max())
    par_prel = par_prel.left_join(pestot, "referenceprel").drop("referenceprel_right")

    agg_prel = par_prel.group_by(["inseecommune", "annee"]).aggregate(
        n_prelevements=_.count(),
        n_analyses=_.n_parametres.sum(),
        n_prelevements_quantifies=(_.n_quantifies > 0).sum(),
        conc_max_substance=_.conc_max.max(),
        total_pesticides_max=_.total.max(),
        total_pesticides_moyen=_.total.mean(),
        pestot_labo_max=_.pestot_labo.max(),
        n_prel_substance_sup_0_1=(_.conc_max > SEUIL_EDCH_SUBSTANCE).sum(),
        n_prel_substance_sup_2=(_.conc_max > SEUIL_BRUTE_SUBSTANCE).sum(),
        n_prel_total_sup_0_5=(_.total > SEUIL_EDCH_TOTAL).sum(),
        n_prel_total_sup_5=(_.total > SEUIL_BRUTE_TOTAL).sum(),
    )

    agg_param = mesures.group_by(["inseecommune", "annee"]).aggregate(
        n_captages=_.code_captage.nunique(),
        n_substances_recherchees=_[COL_PARAMETRE].nunique(),
        n_substances_quantifiees=_[COL_PARAMETRE].nunique(where=_.valeur > 0),
        substances_quantifiees=_[COL_PARAMETRE].collect(where=_.valeur > 0, distinct=True, order_by=_[COL_PARAMETRE]),
    )

    out = agg_param.join(agg_prel, ["inseecommune", "annee"])
    return out.select(
        "inseecommune",
        "annee",
        "n_captages",
        "n_prelevements",
        "n_analyses",
        "n_substances_recherchees",
        "n_substances_quantifiees",
        "n_prelevements_quantifies",
        "conc_max_substance",
        "total_pesticides_max",
        "total_pesticides_moyen",
        "pestot_labo_max",
        "n_prel_substance_sup_0_1",
        "n_prel_substance_sup_2",
        "n_prel_total_sup_0_5",
        "n_prel_total_sup_5",
        "substances_quantifiees",
    ).order_by(["inseecommune", "annee"])
