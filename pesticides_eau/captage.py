"""Table des pesticides mesurés aux captages (eaux brutes), agrégée par commune du captage et par année.

Source : SISE-Eaux, fichiers CAP_PLV / CAP_RES du jeu data.gouv « Résultats du contrôle sanitaire de
l'eau du robinet ». La commune retenue est `inseecommune` du prélèvement, c'est-à-dire la commune du
point de surveillance du captage. Les pesticides sont identifiés via le référentiel officiel PAR_*.csv
(archive eaurob-ref), par famille de paramètres.
"""

import logging
from collections.abc import Iterable
from pathlib import Path

import ibis
import ibis.expr.types as ir
from ibis import _

from pesticides_eau.constants import (
    PESTOT_CODE,
    SEUIL_BRUTE_SUBSTANCE,
    SEUIL_BRUTE_TOTAL,
    SEUIL_EDCH_SUBSTANCE,
    SEUIL_EDCH_TOTAL,
)

logger = logging.getLogger(__name__)

# Familles PAR (`cdfamilleparam`) des métabolites ; les substances actives sont les familles « PESTICIDES ... ».
FAMILLES_METABOLITES = {
    "LP": "metabolite_pertinent",
    "LN": "metabolite_non_pertinent",
    "LC": "metabolite_non_caracterise",
}


def find_cap_files(dirs: Iterable[Path], kind: str) -> list[Path]:
    """Fichiers CAP_PLV_* ou CAP_RES_* dans les dossiers extraits."""
    dirs = list(dirs)
    files = [f for d in dirs for f in sorted(Path(d).rglob(f"CAP_{kind}_*.txt"))]
    if not files:
        msg = f"Aucun fichier CAP_{kind}_*.txt trouvé dans {dirs}"
        raise FileNotFoundError(msg)
    return files


def find_par_file(ref_dir: Path) -> Path:
    """Référentiel des paramètres le plus récent (PAR_AAAAMMJJ.csv)."""
    files = sorted(Path(ref_dir).rglob("PAR_*.csv"))
    if not files:
        msg = f"Aucun référentiel PAR_*.csv dans {ref_dir}"
        raise FileNotFoundError(msg)
    return files[-1]


def _read(con: ibis.BaseBackend, files: list[Path]) -> ir.Table:
    return con.read_csv([str(f) for f in files], all_varchar=True, union_by_name=True, header=True)


def read_pesticides_ref(con: ibis.BaseBackend, par_path: Path) -> ir.Table:
    """Substances actives et métabolites de pesticides du référentiel PAR (hors total PESTOT)."""
    par = _read(con, [par_path])
    fam = par.cdfamilleparam
    categorie = fam.substitute(FAMILLES_METABOLITES, else_="substance_active")
    return par.filter(
        par.libfamilleparam.startswith("PESTICIDES") | fam.isin(list(FAMILLES_METABOLITES)),
        par.cdparametresiseeaux != PESTOT_CODE,
    ).select(
        "cdparametresiseeaux",
        "libminparametre",
        "casparam",
        "cdfamilleparam",
        "libfamilleparam",
        categorie=categorie,
    )


def _valeur_ug_l(res: ir.Table) -> ir.FloatingValue:
    """Valeur numérique en µg/L ; 0 si inférieure à la limite de quantification (rssigne '<')."""
    if "rsana" in res.columns:
        brute = res.rsana.replace(",", ".").try_cast("float64")
        brute = ibis.ifelse(res.rssigne.strip() == "<", 0.0, brute)
    else:  # format « commune par commune » (DIS_RESULT)
        brute = res.valtraduite.replace(",", ".").try_cast("float64")
    unite = res.cdunitereferencesiseeaux.strip()
    return ibis.ifelse(unite == "ng/L", brute / 1000, brute)


def build_pesticides_captage_commune(
    con: ibis.BaseBackend,
    data_dirs: Iterable[Path],
    par_path: Path,
    start_year: int,
    end_year: int,
) -> ir.Table:
    """Construit l'expression ibis de la table commune du captage x année."""
    data_dirs = list(data_dirs)
    plv_raw = _read(con, find_cap_files(data_dirs, "PLV"))
    res_raw = _read(con, find_cap_files(data_dirs, "RES"))

    plv = (
        plv_raw
        .select(
            "referenceprel",
            code_captage=_.cdreseau,
            inseecommune=_.inseecommune.strip().lpad(5, "0"),
            nature_eau=_.inae.strip(),
            codebss=_.codebss.strip().nullif(""),
            annee=_.dateprel.re_extract(r"(\d{4})", 1).try_cast("int32"),
        )
        .filter(_.annee.between(start_year, end_year), _.inseecommune.notnull())
        # les fichiers mensuels peuvent republier un même prélèvement
        .distinct(on="referenceprel", keep="first")
    )

    res = res_raw.select("referenceprel", "cdparametresiseeaux", valeur=_valeur_ug_l(res_raw))

    ref = read_pesticides_ref(con, par_path)
    # Un paramètre peut être analysé plusieurs fois sur un prélèvement (terrain / labos) : on garde le max.
    mesures = (
        res
        .join(ref.select("cdparametresiseeaux", "categorie"), "cdparametresiseeaux")
        .group_by(["referenceprel", "cdparametresiseeaux", "categorie"])
        .aggregate(valeur=_.valeur.max())
        .join(plv, "referenceprel")
    )

    par_prel = mesures.group_by(["referenceprel", "inseecommune", "annee"]).aggregate(
        n_parametres=_.count(),
        n_quantifies=(_.valeur > 0).sum(),
        conc_max=_.valeur.max(),
        total=_.valeur.fill_null(0).sum(),
    )
    pestot = (
        res.filter(_.cdparametresiseeaux == PESTOT_CODE).group_by("referenceprel").aggregate(pestot_labo=_.valeur.max())
    )
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

    quantifie = _.valeur > 0
    agg_param = mesures.group_by(["inseecommune", "annee"]).aggregate(
        n_captages=_.code_captage.nunique(),
        n_captages_eso=_.code_captage.nunique(where=_.nature_eau == "ESO"),
        n_captages_esu=_.code_captage.nunique(where=_.nature_eau == "ESU"),
        n_substances_recherchees=_.cdparametresiseeaux.nunique(),
        n_substances_quantifiees=_.cdparametresiseeaux.nunique(where=quantifie),
        n_substances_actives_quantifiees=_.cdparametresiseeaux.nunique(
            where=quantifie & (_.categorie == "substance_active")
        ),
        n_metabolites_quantifies=_.cdparametresiseeaux.nunique(where=quantifie & (_.categorie != "substance_active")),
        substances_quantifiees=_.cdparametresiseeaux.collect(
            where=quantifie, distinct=True, order_by=_.cdparametresiseeaux
        ),
        codes_bss=_.codebss.collect(where=_.codebss.notnull(), distinct=True, order_by=_.codebss),
    )

    out = agg_param.join(agg_prel, ["inseecommune", "annee"])
    return out.select(
        "inseecommune",
        "annee",
        "n_captages",
        "n_captages_eso",
        "n_captages_esu",
        "n_prelevements",
        "n_analyses",
        "n_substances_recherchees",
        "n_substances_quantifiees",
        "n_substances_actives_quantifiees",
        "n_metabolites_quantifies",
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
        "codes_bss",
    ).order_by(["inseecommune", "annee"])
