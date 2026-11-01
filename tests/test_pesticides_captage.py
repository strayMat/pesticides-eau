from pathlib import Path

import ibis
import pandas as pd
import pytest
from click.testing import CliRunner

from pesticides_eau.captage import build_pesticides_captage_commune
from pesticides_eau.cli import cli
from pesticides_eau.download import RESOURCE_PATTERN


def _build(raw_dir: Path, start: int = 2010, end: int = 2025) -> pd.DataFrame:
    con = ibis.duckdb.connect()
    dirs = [raw_dir / "eaurob-202501", raw_dir / "eaurob-202502"]
    return build_pesticides_captage_commune(con, dirs, start, end).to_pandas().set_index(["inseecommune", "annee"])


def test_commune_captage(raw_dir: Path) -> None:
    df = _build(raw_dir)
    # UDI ignorée, code commune complété à 5 caractères, Corse conservée
    assert set(df.index) == {("01001", 2024), ("01001", 2025), ("2A004", 2025)}

    row = df.loc[("01001", 2025)]
    assert row.n_captages == 2
    assert row.n_prelevements == 2
    assert row.n_analyses == 4  # PESTOT et nitrates exclus, doublon GPST dédoublonné
    assert row.n_substances_recherchees == 3
    assert row.n_substances_quantifiees == 3
    assert row.conc_max_substance == pytest.approx(2.5)
    assert row.total_pesticides_max == pytest.approx(2.5)
    assert row.total_pesticides_moyen == pytest.approx((0.35 + 2.5) / 2)
    assert row.pestot_labo_max == pytest.approx(0.35)
    assert row.n_prel_substance_sup_0_1 == 2
    assert row.n_prel_substance_sup_2 == 1
    assert row.n_prel_total_sup_0_5 == 1
    assert row.n_prel_total_sup_5 == 0
    assert list(row.substances_quantifiees) == ["AMPA", "ATRZ", "GPST"]

    corse = df.loc[("2A004", 2025)]
    assert corse.n_substances_quantifiees == 0
    assert corse.n_prelevements_quantifies == 0


def test_year_filter(raw_dir: Path) -> None:
    df = _build(raw_dir, start=2025)
    assert ("01001", 2024) not in df.index


def test_cli_two_months_offline(raw_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out.parquet"
    result = CliRunner().invoke(
        cli,
        [
            "pesticides-captage",
            "--months",
            "202501",
            "--months",
            "202502",
            "--raw-dir",
            str(raw_dir),
            "--offline",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    df = pd.read_parquet(out)
    # Avec --months, seules les années des mois demandés (2025) sont gardées
    assert sorted(df.inseecommune) == ["01001", "2A004"]


def test_resource_pattern() -> None:
    assert RESOURCE_PATTERN.search("eaurob-2024.zip").group(1) == "2024"
    assert RESOURCE_PATTERN.search("eaurob-202601.zip").group(1) == "202601"
    assert RESOURCE_PATTERN.search("eaurob-ref-20260812.zip") is None
