# pesticides-eau

Étude des effets des pesticides sur la santé des nouveau-nés en milieu rural : construction des données d'exposition.

## Installation

```bash
make install
```

## `pesticides-captage`

Construit la table des pesticides mesurés **aux captages** (eaux brutes), agrégée par **commune du captage** et par **année**.

```bash
make pesticides-captage
# ou
uv run pesticides-eau pesticides-captage --start-year 2016 --end-year 2025
# test rapide sur deux archives mensuelles
uv run pesticides-eau pesticides-captage --months 202601 --months 202602
```

Sortie : `data/pesticides_captage_commune.parquet`.

### Source

Jeu data.gouv [Résultats du contrôle sanitaire de l'eau du robinet](https://www.data.gouv.fr/datasets/resultats-du-controle-sanitaire-de-leau-du-robinet) (SISE-Eaux, ministère de la Santé / ARS), archives `eaurob-AAAA.zip` (annuelles) ou `eaurob-AAAAMM.zip` (mensuelles). Seuls les fichiers des installations de type **CAP** (captages) sont lus, en `PLV` (prélèvements) et en `RESULT` (résultats).

- Commune = `inseecommuneprinc` du prélèvement, c'est-à-dire la commune du point de surveillance du captage.
- Pesticides = substances actives et métabolites du référentiel `pesticides_eau/references/parametres_pesticides.csv`, extrait du seed `references_generations_futures.csv` de [Data For Good 13_pollution_eau](https://github.com/dataforgoodfr/13_pollution_eau) (MIT). Les lignes totaux (`PESTOT`) sont exclues des sommes.
- Plage d'années : 2010-2025. SISE-Eaux n'est publié qu'à partir de 2016.

### Colonnes

| colonne | description |
|---|---|
| `inseecommune`, `annee` | clé : code INSEE de la commune du captage et année |
| `n_captages` | captages distincts avec au moins une analyse de pesticide |
| `n_prelevements`, `n_analyses` | prélèvements et couples prélèvement × substance analysés |
| `n_substances_recherchees`, `n_substances_quantifiees` | substances distinctes recherchées / quantifiées (> 0) |
| `n_prelevements_quantifies` | prélèvements avec au moins une substance quantifiée |
| `conc_max_substance` | concentration maximale d'une substance (µg/L) |
| `total_pesticides_max`, `total_pesticides_moyen` | somme des substances par prélèvement : max et moyenne (µg/L) |
| `pestot_labo_max` | max du total calculé par le laboratoire (`PESTOT`) |
| `n_prel_substance_sup_0_1`, `n_prel_substance_sup_2` | prélèvements avec une substance > 0,1 (limite eau distribuée) / > 2 µg/L (limite eaux brutes) |
| `n_prel_total_sup_0_5`, `n_prel_total_sup_5` | prélèvements dont le total dépasse 0,5 / 5 µg/L |
| `substances_quantifiees` | liste des codes SISE des substances quantifiées |

### À vérifier sur les vraies données

Le code a été écrit sans accès aux fichiers réels : les noms de fichiers CAP (`*CAP*PLV*`, `*CAP*RESULT*`) et les colonnes (`cdreseau`, `inseecommuneprinc`, `dateprel`, `referenceprel`, `cdparametresiseeaux`, `valtraduite`) reprennent la structure des fichiers `DIS_*`. Ils sont centralisés en tête de `pesticides_eau/captage.py`.
