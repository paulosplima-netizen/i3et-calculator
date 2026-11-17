"""Equivalencia entre materiais de versoes diferentes do GREET (alumínio).

Fase A, passo 4. Ate o GREET 2022 (G22) havia um so tipo de aluminio, o
'Wrought Aluminum' (IDM 4). A partir do GREET 2023 (G23, G24) o GREET separa o
alocado em 'Aluminum Sheet (Automotive)' (4a) e 'Aluminum Extrusion
(Automotive)' (4b), e as receitas seguem a mesma divisao. Fatores de emissao e
receitas sao escolhidos de forma independente; esta tabela diz como converter
um no outro quando as versoes nao combinam.

Blocos:
    ME1  fatores de G22 para os tres aluminios, lidos da planilha  -> P11 (correcao)
    ME2  pesos de chapa e extrudado, das receitas da familia GREET 2024
    ME3  gravacao dos CSV

Correcao de P11 (divergencia D2): a base da 0.9.0 trazia, em G22, os valores de
G23 (11,94; 11,94; 4,77). A planilha traz 15,74 para o IDM 4 e 'ND' para 4a e 4b.

Uso:
    python tools/build_material_equivalence.py [caminho/para/LCA_LV_i3ET_20261101.xlsx]
"""

from __future__ import annotations

import csv
import os
import sys

from fase_a_common import CSV_DIR, WORKBOOK_NAME, num, open_workbook, text, write_csv
from xlsx_cells import col2n as C

SHEET = "Emission Factors GREET and BR"
PARENT, CHILDREN = "4", ("4a", "4b")
COL_ID, COL_G22 = C("AC"), C("AE")
FIRST_ROW, LAST_ROW = 6, 148


# --------------------------------------------------------------------------
# BLOCO ME1 -- fatores de G22
#   Le      : coluna AE (G22) da guia, linhas dos materiais 4, 4a e 4b
#   Devolve : linhas de P11 a atualizar. 'ND' vira NULL: sem fator, nao zero.
# --------------------------------------------------------------------------
def g22_factors(g) -> list[dict]:
    linhas = []
    for r in range(FIRST_ROW, LAST_ROW + 1):
        idm = text(g.get((r, COL_ID)))
        if idm not in (PARENT, *CHILDREN):
            continue
        valor = num(g.get((r, COL_G22)))
        nota = (f"Valor da guia '{SHEET}' do {WORKBOOK_NAME}, celula AE{r}. "
                + ("Corrige a 0.9.0, que trazia aqui o valor do G23." if valor is not None
                   else "ND na planilha: o G22 nao separa chapa e extrudado; "
                        "ver P57 e o alerta I28."))
        linhas.append({"IDM": idm, "IDEFV": "G22", "EF": valor, "EFnotes": nota})
    return linhas


# --------------------------------------------------------------------------
# BLOCO ME2 -- pesos
#   Le      : P16 (participacao de cada material no grupo) das receitas da
#             familia GREET 2024, em data/csv/fase_a
#   Devolve : peso de chapa e de extrudado = soma das participacoes de cada um
#             sobre a soma das duas. A razao e quase igual em todos os grupos
#             (0,61 a 0,62), de modo que ponderar pela massa do grupo muda pouco.
# --------------------------------------------------------------------------
def _read(nome):
    with open(os.path.join(CSV_DIR, nome), encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def weights() -> tuple[dict[str, float], int]:
    # So as receitas do GREET 2024 cuja motorizacao a base calcula (sem FCEV):
    # as 30 que originaram os pesos. As edicoes de 2022 e 2023 e as de FCEV
    # entraram na base depois e nao alteram a equivalencia.
    receitas = {r["IDVMR"] for r in _read("P15_VehicleMaterialRecipe.add.csv")
                if "GREET 2024" in r["DsVMR"] and r["IDVPT"] != "FCEV"}
    soma = dict.fromkeys(CHILDREN, 0.0)
    for r in _read("P16_MaterialShare.add.csv"):
        if r["IDVMR"] in receitas and r["IDM"] in soma:
            soma[r["IDM"]] += float(r["MshareGG"] or 0.0)
    total = sum(soma.values())
    return {k: v / total for k, v in soma.items()}, len(receitas)


def main(argv) -> int:
    g = open_workbook(argv).grid(SHEET)
    fatores = g22_factors(g)
    pesos, n = weights()
    origem = (f"Media das {n} receitas da familia GREET 2024 (P15, P16): soma das "
              "participacoes de cada tipo sobre a soma dos dois. Provisorio.")
    equivalencias = [
        {"IDMParent": PARENT, "IDMChild": filho, "Weight": pesos[filho],
         "WeightSource": origem,
         "NotesME": "Alumínio único (até o G22) = chapa + extrudado (do G23 em diante)."}
        for filho in CHILDREN]
    print("Fatores de G22:", [(f["IDM"], f["EF"]) for f in fatores])
    print("Pesos:", {k: round(v, 4) for k, v in pesos.items()}, f"({n} receitas)")
    write_csv("P11_EmissionFactor.aluminio.add",
              ["IDM", "IDEFV", "EF", "EFnotes"], fatores)
    write_csv("P57_MaterialEquivalence",
              ["IDMParent", "IDMChild", "Weight", "WeightSource", "NotesME"], equivalencias)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
