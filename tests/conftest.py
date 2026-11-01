"""Données SISE-Eaux fictives au format réel : deux archives mensuelles (eaurob-202501, eaurob-202502)
et le référentiel PAR (eaurob-ref)."""

import csv
from pathlib import Path

import pytest

PLV_COLS = [
    "cddept", "inseecommune", "nomcommune", "cdreseau", "nomreseau", "codetypeinstallation",
    "inae", "cdpointsurv", "referenceprel", "dateprel", "codebss", "coord_x", "coord_y",
]  # fmt: skip
RES_COLS = [
    "cddept",
    "referenceprel",
    "cdparametre",
    "cdparametresiseeaux",
    "rqana",
    "rssigne",
    "rsana",
    "cdunitereferencesiseeaux",
]
PAR_COLS = [
    "cdparametresiseeaux",
    "cdparametre",
    "libmajparametre",
    "libminparametre",
    "cdfamilleparam",
    "libfamilleparam",
    "casparam",
]

PAR = [
    ["ATRZ", "1107", "ATRAZINE", "Atrazine", "TR", "PESTICIDES TRIAZINES", "1912-24-9"],
    ["GPST", "1506", "GLYPHOSATE", "Glyphosate", "PD", "PESTICIDES DIVERS", "1071-83-6"],
    ["AMPA", "1907", "AMPA", "AMPA", "LC", "MÉTABOLITES DONT LA PERTINENCE N’A PAS ÉTÉ CARACTÉRISÉE",  # noqa: RUF001 (libellé SISE) "1066-51-9"],
    ["ESAMTC", "6854", "ESA METOLACHLORE", "ESA metolachlore", "LP", "MÉTABOLITES PERTINENTS", "171118-09-5"],
    ["PESTOT", "6276", "TOTAL DES PESTICIDES", "Total des pesticides analysés", "PD", "PESTICIDES DIVERS", ""],
    ["NO3", "1340", "NITRATES", "Nitrates", "NP", "PARAMETRES AZOTES ET PHOSPHORES", "14797-55-8"],
]

MONTHS = {
    "202501": {
        "CAP_PLV": [
            [
                "001",
                "1001",
                "Ambérieux",
                "001000001",
                "Source A",
                "CAP",
                "ESO",
                "P1",
                "00100000001",
                "2025-01-05",
                "06754X0071",
                "",
                "",
            ],
            [
                "001",
                "01001",
                "Ambérieux",
                "001000002",
                "Prise B",
                "CAP",
                "ESU",
                "P2",
                "00100000002",
                "2025-01-20",
                "",
                "",
                "",
            ],
            [
                "001",
                "01001",
                "Ambérieux",
                "001000001",
                "Source A",
                "CAP",
                "ESO",
                "P1",
                "00100000004",
                "2024-12-31",
                "06754X0071",
                "",
                "",
            ],
        ],
        "CAP_RES": [
            ["001", "00100000001", "1107", "ATRZ", "0,05", "", "0.050000", "µg/L"],
            ["001", "00100000001", "1506", "GPST", "0,3", "", "0.300000", "µg/L"],
            ["001", "00100000001", "1506", "GPST", "0,2", "", "0.200000", "µg/L"],
            ["001", "00100000001", "6276", "PESTOT", "0,35", "", "0.350000", "µg/L"],
            ["001", "00100000001", "1340", "NO3", "25", "", "25.000000", "mg/L"],
            ["001", "00100000002", "1107", "ATRZ", "<0,02", "<", "0.020000", "µg/L"],
            ["001", "00100000002", "1907", "AMPA", "2500", "", "2500.000000", "ng/L"],
            ["001", "00100000004", "1107", "ATRZ", "1,0", "", "1.000000", "µg/L"],
        ],
        # Doit être ignoré : prélèvement sur une unité de distribution
        "UDI_PLV": [
            ["099", "99999", "X", "099000001", "UDI X", "UDI", "ESO", "P9", "09900000009", "2025-01-10", "", "", ""]
        ],
        "UDI_RES": [["099", "09900000009", "1107", "ATRZ", "5", "", "5.000000", "µg/L"]],
    },
    "202502": {
        # Republie le prélèvement 00100000002 (doublon à dédoublonner)
        "CAP_PLV": [
            [
                "02A",
                "2A004",
                "Ajaccio",
                "02A000003",
                "Puits C",
                "CAP",
                "ESO",
                "P3",
                "02A00000003",
                "2025-02-03",
                "",
                "",
                "",
            ],
            [
                "001",
                "01001",
                "Ambérieux",
                "001000002",
                "Prise B",
                "CAP",
                "ESU",
                "P2",
                "00100000002",
                "2025-01-20",
                "",
                "",
                "",
            ],
        ],
        "CAP_RES": [["02A", "02A00000003", "6854", "ESAMTC", "<0,05", "<", "0.050000", "µg/L"]],
    },
}


def _write(path: Path, cols: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
        w.writerow(cols)
        w.writerows(rows)


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    for month, files in MONTHS.items():
        d = tmp_path / f"eaurob-{month}"
        d.mkdir()
        for kind, rows in files.items():
            _write(d / f"{kind}_{month}.txt", PLV_COLS if kind.endswith("PLV") else RES_COLS, rows)
    ref = tmp_path / "eaurob-ref"
    ref.mkdir()
    _write(ref / "PAR_20260812.csv", PAR_COLS, PAR)
    return tmp_path
