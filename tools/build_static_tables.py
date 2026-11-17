"""Tabelas da Fase A que sao decisao de projeto, e nao leitura da planilha.

Fase A, passo 3. Escritas aqui para que a origem de cada linha fique num so
lugar, auditavel e repetivel.

Blocos:
    ST1  motorizacoes: descricoes e as que entram so no catalogo   -> P12
    ST2  carrocerias que entram so no catalogo                     -> P13
    ST3  fatores de uso combinado (padrao por motorizacao)         -> P53
    ST4  gravacao dos CSV

Uso:
    python tools/build_static_tables.py
"""

from __future__ import annotations

import sys

from fase_a_common import write_csv

# --------------------------------------------------------------------------
# BLOCO ST1 -- motorizacoes (P12)
#   As seis primeiras ja existem, com um marcador provisorio na descricao.
#   MHEV e FCEV aparecem na Market Vehicles; entram no catalogo sem calculo.
#   As descricoes sao redacao desta etapa, a revisar pelo autor.
# --------------------------------------------------------------------------
POWERTRAINS = [
    ("ICEV", 1, "Internal combustion engine vehicle: the engine alone drives the wheels."),
    ("HEV", 1, "Hybrid electric vehicle (parallel): engine and electric motor drive the "
               "wheels; the battery is charged on board only."),
    ("SHEV", 1, "Series hybrid electric vehicle: the electric motor drives the wheels; "
                "the engine runs a generator."),
    ("PHEV", 1, "Plug-in hybrid electric vehicle (parallel): as the HEV, with a larger "
                "battery charged from the grid."),
    ("SPHEV", 1, "Series plug-in hybrid electric vehicle: as the SHEV, with a larger "
                 "battery charged from the grid."),
    ("BEV", 1, "Battery electric vehicle: the electric motor alone drives the wheels."),
    ("MHEV", 0, "Mild hybrid electric vehicle. Listed in the market catalogue; not "
                "calculated."),
    ("FCEV", 0, "Fuel cell electric vehicle. Listed in the market catalogue; enters the "
                "calculation in the final stage."),
]

# --------------------------------------------------------------------------
# BLOCO ST2 -- carrocerias (P13)
#   Van e Chassis estao na Market Vehicles (25 veiculos) e nao tem parametros
#   de massa. So as linhas novas sao gravadas; as quatro da 0.9.0 nao mudam.
# --------------------------------------------------------------------------
DESIGNS = [
    ("Van", 0, "Van. Listed in the market catalogue; not calculated."),
    ("Chassis", 0, "Chassis cab. Listed in the market catalogue; not calculated."),
]

# --------------------------------------------------------------------------
# BLOCO ST3 -- fatores de uso combinado (P53)
#   Decisao de 17/11/2026 (docs/06, secao 6). A potencia combinada e
#       P = FatorICE * P_ICE + FatorEE * P_EE
#   ICEV usa so o motor a combustao; BEV, SHEV e SPHEV (e FCEV) so o eletrico.
#   HEV e PHEV: valores provisorios (1; 1), a soma decidida em 16/11, ate o
#   fim da validacao contra o Excel; depois serao arbitrados entre 0 e 1.
#   Os pares arbitrados para igualar a planilha ficam em P56 (CF).
# --------------------------------------------------------------------------
ORDER = ["ICEV", "HEV", "SHEV", "PHEV", "SPHEV", "BEV"]
FACTORS = {                # IDVPT -> (FatorICE, FatorEE, provisorio)
    "ICEV": (1.0, 0.0, 0), "SHEV": (0.0, 1.0, 0), "SPHEV": (0.0, 1.0, 0),
    "BEV": (0.0, 1.0, 0), "HEV": (1.0, 1.0, 1), "PHEV": (1.0, 1.0, 1),
}
NOTES = {
    "ICEV": "Only the combustion engine drives the wheels.",
    "SHEV": "Series hybrid: only the electric motor drives the wheels.",
    "SPHEV": "Series hybrid: only the electric motor drives the wheels.",
    "BEV": "Only the electric motor drives the wheels.",
    "HEV": "Provisional default (sum) until validation against the Excel model ends.",
    "PHEV": "Provisional default (sum) until validation against the Excel model ends.",
}


def power_factors() -> list[dict]:
    return [{"IDVPT": pt, "FactorICE": FACTORS[pt][0], "FactorEE": FACTORS[pt][1],
             "IsProvisional": FACTORS[pt][2], "NotesCPR": NOTES[pt]} for pt in ORDER]


# --------------------------------------------------------------------------
# BLOCO ST4 -- gravacao
# --------------------------------------------------------------------------
def main() -> int:
    print("Tabelas estaticas ->", "data/csv/fase_a")
    write_csv("P12_Powertrain.add", ["IDVPT", "DsVPT", "IsCalculable"],
              [{"IDVPT": i, "DsVPT": d, "IsCalculable": c} for i, c, d in POWERTRAINS])
    write_csv("P13_DesignType.add", ["IDVDT", "DsVDT", "IsCalculable"],
              [{"IDVDT": i, "DsVDT": d, "IsCalculable": c} for i, c, d in DESIGNS])
    write_csv("P53_CombinedPowerRule",
              ["IDVPT", "FactorICE", "FactorEE", "IsProvisional", "NotesCPR"],
              power_factors())
    return 0


if __name__ == "__main__":
    sys.exit(main())
