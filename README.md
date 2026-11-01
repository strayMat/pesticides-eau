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

Jeu data.gouv [Résultats du contrôle sanitaire de l'eau du robinet](https://www.data.gouv.fr/datasets/resultats-du-controle-sanitaire-de-leau-du-robinet) (SISE-Eaux, ministère de la Santé / ARS) :

- archives `eaurob-AAAA.zip` (annuelles) ou `eaurob-AAAAMM.zip` (mensuelles), dont seuls `CAP_PLV_*.txt` (prélèvements aux captages, eau brute) et `CAP_RES_*.txt` (résultats) sont lus ;
- référentiel `eaurob-ref-AAAAMMJJ.zip`, fichier `PAR_*.csv` (paramètres).

Choix :

- **Commune** = `inseecommune` du prélèvement, c'est-à-dire la commune du point de surveillance du captage. Les coordonnées (`coord_x`, `coord_y`) ne sont pas diffusées pour les captages. Le lien captage → communes desservies n'est pas en open data.
- **Pesticides** = paramètres du référentiel PAR dont la famille commence par « PESTICIDES » (substances actives), plus les métabolites `LP` (pertinents), `LN` (non pertinents) et `LC` (pertinence non caractérisée). `PESTOT` (total calculé par le laboratoire) est exclu des sommes et reporté à part.
- **Valeur** = `rsana`, mise à 0 si `rssigne = "<"` (sous la limite de quantification) ; les ng/L sont convertis en µg/L.
- **Doublons** : un prélèvement republié dans plusieurs archives mensuelles n'est compté qu'une fois ; pour un même paramètre analysé plusieurs fois, on garde le maximum.
- **Années** : 2010-2025 ; SISE-Eaux n'est publié qu'à partir de 2016. Avec `--months`, seules les années des mois demandés sont gardées (les archives mensuelles contiennent aussi des prélèvements anciens validés tardivement).

### Colonnes

| colonne | description |
|---|---|
| `inseecommune`, `annee` | clé : code INSEE de la commune du captage et année |
| `n_captages`, `n_captages_eso`, `n_captages_esu` | captages distincts analysés pour les pesticides : total, eau souterraine, eau de surface |
| `n_prelevements`, `n_analyses` | prélèvements et couples prélèvement × paramètre analysés |
| `n_substances_recherchees`, `n_substances_quantifiees` | paramètres distincts recherchés / quantifiés (> 0) |
| `n_substances_actives_quantifiees`, `n_metabolites_quantifies` | répartition des paramètres quantifiés |
| `n_prelevements_quantifies` | prélèvements avec au moins un paramètre quantifié |
| `conc_max_substance` | concentration maximale d'un paramètre (µg/L) |
| `total_pesticides_max`, `total_pesticides_moyen` | somme par prélèvement (métabolites non pertinents inclus) : max et moyenne (µg/L) |
| `pestot_labo_max` | max du total calculé par le laboratoire (`PESTOT`) |
| `n_prel_substance_sup_0_1`, `n_prel_substance_sup_2` | prélèvements avec un paramètre > 0,1 (limite eau distribuée) / > 2 µg/L (limite eaux brutes) |
| `n_prel_total_sup_0_5`, `n_prel_total_sup_5` | prélèvements dont la somme dépasse 0,5 / 5 µg/L |
| `substances_quantifiees` | codes SISE des paramètres quantifiés |
| `codes_bss` | codes BSS (BRGM) des captages souterrains, pour les géolocaliser via ADES / Hub'Eau |

Test sur données réelles (janvier + février 2026) : 1 355 communes, 68 % avec au moins un pesticide quantifié, 65 % avec un code BSS.
