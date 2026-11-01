"""Données SISE-Eaux fictives : deux archives mensuelles (eaurob-202501, eaurob-202502)."""

import csv
from pathlib import Path

import pytest

PLV_COLS = ["cddept", "cdreseau", "nomreseau", "inseecommuneprinc", "nomcommuneprinc", "referenceprel", "dateprel"]
RES_COLS = ["cddept", "referenceprel", "cdparametresiseeaux", "libminparametre", "rqana", "valtraduite", "referenceanl"]

MONTHS = {
    "202501": {
        "CAP_PLV": [
            ["001", "001000001", "Source A", "1001", "Ambérieux", "00100000001", "2025-01-05"],
            ["001", "001000002", "Forage B", "01001", "Ambérieux", "00100000002", "2025-01-20"],
            ["001", "001000001", "Source A", "01001", "Ambérieux", "00100000004", "2024-12-31"],
        ],
        "CAP_RESULT": [
            ["001", "00100000001", "ATRZ", "Atrazine", "0,05", "0,05", "A1"],
            ["001", "00100000001", "GPST", "Glyphosate", "0.3", "0.3", "A1"],
            ["001", "00100000001", "GPST", "Glyphosate", "0.2", "0.2", "A2"],
            ["001", "00100000001", "PESTOT", "Total pesticides", "0.35", "0.35", "A1"],
            ["001", "00100000001", "NO3", "Nitrates", "25", "25", "A1"],
            ["001", "00100000002", "ATRZ", "Atrazine", "<0.02", "0", "A3"],
            ["001", "00100000002", "AMPA", "AMPA", "2,5", "2,5", "A3"],
            ["001", "00100000004", "ATRZ", "Atrazine", "1.0", "1.0", "A4"],
        ],
        # Doit être ignoré : prélèvement sur une unité de distribution
        "UDI_PLV": [["099", "099000001", "UDI X", "99999", "X", "09900000009", "2025-01-10"]],
        "UDI_RESULT": [["099", "09900000009", "ATRZ", "Atrazine", "5", "5", "A9"]],
    },
    "202502": {
        "CAP_PLV": [["02A", "02A000003", "Puits C", "2A004", "Ajaccio", "02A00000003", "03/02/2025"]],
        "CAP_RESULT": [["02A", "02A00000003", "ESAMTC", "ESA métolachlore", "<0.05", "0", "A5"]],
    },
}


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    for month, files in MONTHS.items():
        d = tmp_path / f"eaurob-{month}"
        d.mkdir()
        for kind, rows in files.items():
            cols = PLV_COLS if kind.endswith("PLV") else RES_COLS
            with open(d / f"{kind}_{month}.txt", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(cols)
                w.writerows(rows)
    return tmp_path
