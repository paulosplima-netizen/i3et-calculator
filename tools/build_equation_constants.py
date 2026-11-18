"""Constantes de equacao como parametros (P59).

Bloco B0 da Fase B (itens 1 e 3). Todo fator e parametro: o que antes estava
embutido no codigo passa a ser linha desta tabela, com valor, unidade e fonte.

Blocos:
    EC1  linhas de P59
    EC2  gravacao do CSV
"""

from __future__ import annotations

import sys

from fase_a_common import write_csv

HEADER = ["IDEC", "ValueEC", "UnitEC", "SourceEC", "NotesEC", "IsProvisional"]

# --------------------------------------------------------------------------
# BLOCO EC1 -- linhas
#   STARTER_PER_KW: IDVP 18 = fator x potencia do motor a combustao (IDVP 2).
#     O M1 aplica 0,04 (doc 01, §7.2), e os doze veiculos BP reproduzem o M1 com ele.
#     O M2 (ET28:EY28) grava 0,03 x P_ICE nas seis motorizacoes da rodada gravada,
#     e a regra 18 da Market Vehicles (P35) tambem usa 0,03. Os dois valores
#     convivem na planilha (D15); a rodada gravada passa o do M2 como informado.
#   HP_PER_KW: reproduz a matriz da Market Vehicles sem divergencia (1,35962
#     deixa 2 veiculos fora no parametro 4).
# --------------------------------------------------------------------------
ROWS = [
    ["STARTER_PER_KW", 0.04, "kW/kW",
     "i3ET, M1, equacao do IDVP 18 (doc 01, §7.2)",
     "IDVP 18 = fator x IDVP 2. O M2 e a regra 18 de P35 usam 0,03; ver 05a (D15).", 0],
    ["HP_PER_KW", 1.34102, "hp/kW",
     "i3ET, Market Vehicles M257:AW299 (faixas de potencia em hp)",
     "Reproduz a matriz sem divergencia; 1,35962 deixa 2 veiculos fora no parametro 4.", 0],
]


def main() -> int:
    write_csv("P59_EquationConstant", HEADER, [dict(zip(HEADER, r)) for r in ROWS])
    return 0


if __name__ == "__main__":
    sys.exit(main())
