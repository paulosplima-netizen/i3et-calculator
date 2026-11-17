"""Modelos genericos de bateria de tracao (P58).

Fase A, passo 5. O i3ET tem, na guia 'GREET Batteries Material List' (colunas ID:IF),
tres modelos `PB-<tipo>-indefinido` cujos fatores sao os parametros do Control
Panel. A tabela guarda so o vinculo; os valores continuam em P30 (e D08).

Blocos:
    GB1  linhas de P58
    GB2  gravacao do CSV
"""

from __future__ import annotations

import sys

from fase_a_common import write_csv

SOURCE = ("i3ET, guia 'GREET Batteries Material List' (colunas ID:IF) e Control Panel "
          "X66:Z72, X83:Z89")
HEADER = ["IDBMd", "IDVPT", "SizingBasis", "IDCPMass", "IDCPCarbon", "SourceGBM", "NotesGBM"]

# --------------------------------------------------------------------------
# BLOCO GB1 -- linhas
#   HEV: bateria de potencia, massa = X72 (kg/kW) x potencia eletrica; carbono X88.
#   PHEV: bateria de energia com fatores proprios, X70 (kg/kWh) e X86.
#   BEV: bateria de energia, X67 (kg/kWh) e X83.
# --------------------------------------------------------------------------
ROWS = [
    ["PB-HEV-indefinido", "HEV", "Power", "X72", "X88", SOURCE,
     "Bateria de potência (HEV, SHEV, FCEV)."],
    ["PB-PHEV-indefinido", "PHEV", "Energy", "X70", "X86", SOURCE,
     "Bateria de energia com fatores próprios do PHEV."],
    ["PB-BEV-indefinido", "BEV", "Energy", "X67", "X83", SOURCE,
     "Bateria de energia (BEV, SPHEV, PHEV). A rodada gravada usa este modelo no PHEV e no SPHEV."],
]


def main() -> int:
    write_csv("P58_GenericBatteryModel", HEADER, [dict(zip(HEADER, r)) for r in ROWS])
    return 0


if __name__ == "__main__":
    sys.exit(main())
