import logging
from pathlib import Path

import click
import ibis

from pesticides_eau.constants import (
    DEFAULT_OUTPUT,
    DIR2RAW,
    FIRST_PUBLISHED_YEAR,
    LOG_LEVEL,
    MAX_YEAR,
    MIN_YEAR,
)

logging.basicConfig(
    level=logging.getLevelName(LOG_LEVEL),
    format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(package_name="pesticides_eau")
def cli() -> None:
    pass


@cli.command("pesticides-captage")
@click.option("--start-year", type=click.IntRange(MIN_YEAR, MAX_YEAR), default=MIN_YEAR, show_default=True)
@click.option("--end-year", type=click.IntRange(MIN_YEAR, MAX_YEAR), default=MAX_YEAR, show_default=True)
@click.option(
    "--months",
    multiple=True,
    help="Périodes mensuelles AAAAMM (test), à la place des archives annuelles et sans borne d'années (ex. --months 202601 --months 202602).",
)
@click.option(
    "--raw-dir",
    type=click.Path(path_type=Path),
    default=DIR2RAW,
    show_default=True,
    help="Dossier des archives extraites.",
)
@click.option("--offline", is_flag=True, help="Ne rien télécharger, utiliser uniquement --raw-dir.")
@click.option("--output", type=click.Path(path_type=Path), default=DEFAULT_OUTPUT, show_default=True)
def pesticides_captage(
    start_year: int, end_year: int, months: tuple[str, ...], raw_dir: Path, offline: bool, output: Path
) -> None:
    """Pesticides mesurés aux captages (eaux brutes), par commune du captage et par année."""
    from pesticides_eau.captage import build_pesticides_captage_commune
    from pesticides_eau.download import download_period, list_resources

    if months:
        periods = list(months)
        # Mode test : les archives mensuelles ne couvrent que l'année en cours, on ne borne pas.
        start_year = min(int(m[:4]) for m in months)
        end_year = max(int(m[:4]) for m in months)
    else:
        if start_year < FIRST_PUBLISHED_YEAR:
            logger.warning(
                "SISE-Eaux n'est publié qu'à partir de %s : les années %s-%s seront absentes.",
                FIRST_PUBLISHED_YEAR,
                start_year,
                FIRST_PUBLISHED_YEAR - 1,
            )
        periods = [str(y) for y in range(max(start_year, FIRST_PUBLISHED_YEAR), end_year + 1)]

    if offline:
        data_dirs = [raw_dir / f"eaurob-{p}" for p in periods if (raw_dir / f"eaurob-{p}").exists()]
    else:
        resources = list_resources()
        data_dirs = [download_period(p, raw_dir, resources) for p in periods]
    if not data_dirs:
        msg = f"Aucune donnée pour les périodes {periods} dans {raw_dir}"
        raise click.ClickException(msg)

    con = ibis.duckdb.connect()
    table = build_pesticides_captage_commune(con, data_dirs, start_year, end_year)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(output)
    n = con.read_parquet(output).count().execute()
    click.secho(f"{n} lignes (commune x année) écrites dans {output}", fg="green")


if __name__ == "__main__":
    cli()
