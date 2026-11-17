"""Fixtures do PBEV/INMETRO: P36, P28, P55 e P50.

Fase A, passo 3. Le a guia 'PBEV - INMETRO - 2026' como uma edicao.

Blocos:
    PB1  edicao                                   -> P36
    PB2  registros e seus campos                  -> P28 e P55
    PB3  vinculo com os veiculos de mercado       -> P50
    PB4  gravacao dos CSV

Uso:
    python tools/import_pbev.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import sys

from fase_a_common import WORKBOOK_NAME, num, open_workbook, text, write_csv
from xlsx_cells import col2n

SHEET = "PBEV - INMETRO - 2026"
EDITION = "PBEV2026"
C = col2n
FIRST_ROW, LAST_ROW = 22, 864

#: Coluna -> nome do campo. O cabecalho da guia ocupa quatro linhas (18 a 21)
#: com celulas mescladas; os nomes abaixo condensam esse cabecalho.
FIELDS = {
    "C": "Categoria", "G": "Motor", "H": "TipoPropulsao", "I": "Transmissao",
    "J": "ArCondicionado", "K": "DirecaoAssistida", "L": "Combustivel",
    "M": "NMOG_NOx_mg_km", "N": "CO_mg_km", "O": "NOx_g_km",
    "P": "ReducaoRelativaLimite", "Q": "CO2Fossil_Etanol_g_km",
    "R": "CO2Fossil_GasolinaDiesel_g_km", "S": "CO2Fossil_VEHP_g_km",
    "T": "Km_l_Etanol_Cidade", "U": "Km_l_Etanol_Estrada",
    "V": "Km_l_GasolinaDiesel_Cidade", "W": "Km_l_GasolinaDiesel_Estrada",
    "X": "Km_le_Eletrico_Cidade", "Y": "Km_le_Eletrico_Estrada",
    "Z": "ConsumoEnergetico_MJ_km", "AA": "AutonomiaEletrica_km",
    "AB": "ClassificacaoPBE_Relativa", "AC": "ClassificacaoPBE_Absoluta",
    "AD": "SeloCONPET",
}
#: Marca de "nao se aplica" na tabela do INMETRO: o campo nao e gravado.
NOT_APPLICABLE = {"\\", "-"}

P36_COLS = ["IDPBE", "EditionYear", "EditionVersion", "SourcePBE", "PublishedAt",
            "ImportedAt", "RecordCount", "NotesPBE"]
P28_COLS = ["IDPBR", "IDPBE", "MatchKey", "Brand", "Model", "Version", "SheetRow"]
P55_COLS = ["IDPBR", "FieldName", "Value", "ValueText"]
P50_COLS = ["IDMV", "IDPBR", "IDPBE", "IsFirstMatch"]


# --------------------------------------------------------------------------
# BLOCO PB2 -- registros (P28) e campos (P55)
#   Le      : linhas 22 a 864. IDPBR e a linha do registro na planilha.
#   Devolve : (registros, campos). A chave de cruzamento e a coluna B da
#             guia: marca, espaco, modelo.
# --------------------------------------------------------------------------
def records(g) -> tuple[list[dict], list[dict]]:
    regs, campos = [], []
    for r in range(FIRST_ROW, LAST_ROW + 1):
        marca, modelo = text(g.get((r, C("D")))), text(g.get((r, C("E"))))
        if marca is None or modelo is None:
            continue
        regs.append({"IDPBR": r, "IDPBE": EDITION,
                     "MatchKey": text(g.get((r, C("B")))) or f"{marca} {modelo}",
                     "Brand": marca, "Model": modelo,
                     "Version": text(g.get((r, C("F")))), "SheetRow": r})
        for col, campo in FIELDS.items():
            bruto = g.get((r, C(col)))
            if bruto is None or (isinstance(bruto, str) and bruto.strip() in NOT_APPLICABLE):
                continue
            valor = num(bruto)
            campos.append({"IDPBR": r, "FieldName": campo, "Value": valor,
                           "ValueText": None if valor is not None else str(bruto).strip()})
    return regs, campos


# --------------------------------------------------------------------------
# BLOCO PB3 -- vinculo veiculo-registro (P50)
#   Le      : os nomes dos veiculos da Market Vehicles (coluna N) e as chaves
#             dos registros
#   Devolve : todos os registros de cada veiculo; o primeiro, na ordem da
#             guia, e o que a busca da planilha devolve.
# --------------------------------------------------------------------------
def links(mv, regs) -> list[dict]:
    por_chave: dict[str, list[int]] = {}
    for reg in regs:
        por_chave.setdefault(reg["MatchKey"], []).append(reg["IDPBR"])
    out = []
    for r in range(7, 162):
        nome = text(mv.get((r, C("N"))))
        if nome is None or mv.get((r, C("M"))) == "X":
            continue
        for i, idpbr in enumerate(sorted(por_chave.get(nome, []))):
            out.append({"IDMV": r, "IDPBR": idpbr, "IDPBE": EDITION,
                        "IsFirstMatch": int(i == 0)})
    return out


# --------------------------------------------------------------------------
# BLOCOS PB1 e PB4 -- edicao e gravacao
# --------------------------------------------------------------------------
def main(argv) -> int:
    wb = open_workbook(argv)
    g = wb.grid(SHEET)
    mv = wb.grid("Market Vehicles")
    regs, campos = records(g)
    print("PBEV ->", "data/csv/fase_a")
    write_csv("P36_PBEVEdition", P36_COLS, [{
        "IDPBE": EDITION, "EditionYear": 2026, "EditionVersion": None,
        "SourcePBE": f"{WORKBOOK_NAME}, guia '{SHEET}', B22:AD864",
        "RecordCount": len(regs),
        "NotesPBE": "Copia da tabela do INMETRO guardada na planilha do i3ET."}])
    write_csv("P28_PBEVRecord", P28_COLS, regs)
    write_csv("P55_PBEVRecordValue", P55_COLS, campos)
    write_csv("P50_MarketVehiclePBEV", P50_COLS, links(mv, regs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
