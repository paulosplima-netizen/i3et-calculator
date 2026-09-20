"""Extract validation fixtures from the i3ET spreadsheet.

The i3ET is the reference this calculator must reproduce. Rather than compare
against its twelve Brazilian-profile vehicles -- which would need a mapping that
does not exist -- we use the i3ET's own configurations (G01, G02, ...) as test
cases: their input parameters, the emission factors actually selected in the
model, and the results it produces.

The fixture is therefore self-contained: it carries inputs AND factors AND
expected outputs. A test built on it checks the calculation engine, not the
data, and keeps working even if the reference base later changes.

Run it once whenever the i3ET spreadsheet changes; the fixture it writes is
versioned with the tests.

Usage:
    python tools/extract_i3et.py [caminho/para/LCA_LV_i3ET_AAAAMMDDx.xlsx]
"""

from __future__ import annotations

import json
import os
import re
import sys

import openpyxl

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "tests", "fixtures", "i3et_reference.json")

DEFAULT_SOURCES = [
    os.path.expanduser("~/mnt/_Calculadora da Pegada de Carbono do Berço ao Portão/"
                       "Documentação/LCA_LV_i3ET_20260919a.xlsx"),
    os.path.expanduser("~/OneDrive/Documents/_Unicamp/_Calculadora da Pegada de Carbono "
                       "do Berço ao Portão/Documentação/LCA_LV_i3ET_20260919a.xlsx"),
]

# A configuration code looks like G01, GL21, S22, P23, A04 -- letters then digits.
CONFIG_RE = re.compile(r"^[A-Z]{1,2}\d{1,2}$")

# Where each quantity lives. Row numbers are 1-based, as in the spreadsheet.
M2_GC_FIRST_ROW = 11          # row 10 + IDVP
M2_GC_LAST_IDVP = 40          # rows 11..50; row 51 is Battery Carbon Intensity, not an IDVP
M2_ROW_VEHICLE_MASS = 69      # WEIGHT (without driver and liquid fuel)
M2_ROWS_GROUP_MASS = range(70, 82)   # the twelve GREET groups, in P04 order
M2_ROW_POWERTRAIN = 10
M2_ROW_ASSEMBLY = 510         # A - Assembling
M2_ROW_MATERIALS = 516        # GHG car without batteries and fluids
M2_ROW_AUX_BATTERY = 560
M2_ROW_PE_BATTERY = 571
M2_ROW_FLUIDS = 617
M2_ROW_TOTAL_I3ET = 511       # includes replacements and end-of-life: NOT cradle-to-gate
M2_ROW_EF_VERSION_INDEX = 67  # column P holds the index into the EF table
M2_COL_EF_VERSION_INDEX = 16

GROUP_ORDER = ["A", "B", "C", "D", "E", "F", "G", "H", "Iaux", "Iprinc", "J", "K"]

M1_ROW_CONFIG_CODE = 6
M1_ROWS_SUBGROUPS = range(8, 60)
M1_COL_SUBGROUP_ID = 16       # "IDS"
M1_OFFSET_MASS = 1            # block is: Tamanho, Peso Calc., Peso GREET, fator LM
M1_OFFSET_FLM = 3             # the lightweighting factor of module M5

EF_SHEET = "Emission Factors GREET and BR"
EF_COL_ID = 29                # AC
EF_ROW_HEADER = 5
EF_FIRST_ROW, EF_LAST_ROW = 6, 201


def find_source(argv):
    if len(argv) > 1:
        return argv[1]
    for p in DEFAULT_SOURCES:
        if os.path.exists(p):
            return p
    raise SystemExit("i3ET spreadsheet not found. Pass the path as an argument.")


def grid(ws, last_row, last_col):
    """Read a sheet into a dict {(row, col): value} in a single pass.

    openpyxl's read-only mode has no usable random access, so we sweep once.
    """
    out = {}
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=last_row,
                                         max_col=last_col, values_only=True), 1):
        for j, v in enumerate(row, 1):
            if v is not None:
                out[(i, j)] = v
    return out


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def sidm(v):
    if v is None:
        return None
    if isinstance(v, float) and v == int(v):
        v = int(v)
    return str(v).strip()


def main() -> int:
    src = find_source(sys.argv)
    print("fonte:", src)
    wb = openpyxl.load_workbook(src, data_only=True, read_only=True)

    m2 = grid(wb["M2 GHG Mfg Module"], 620, 210)
    m1 = grid(wb["M1 Mass Module"], 80, 480)
    efs = grid(wb[EF_SHEET], EF_LAST_ROW, 45)

    # --- which emission factor column the model is currently set to ----------
    ef_index = int(m2[(M2_ROW_EF_VERSION_INDEX, M2_COL_EF_VERSION_INDEX)])
    ef_col = EF_COL_ID + ef_index - 1
    ef_version = str(efs.get((EF_ROW_HEADER, ef_col)))
    ef_values = {}
    for r in range(EF_FIRST_ROW, EF_LAST_ROW + 1):
        idm = sidm(efs.get((r, EF_COL_ID)))
        if idm is None:
            continue
        ef_values[idm] = num(efs.get((r, ef_col)))
    print(f"versao de fatores selecionada no i3ET: {ef_version} "
          f"(indice {ef_index}); {len(ef_values)} materiais, "
          f"{sum(1 for v in ef_values.values() if v is None)} sem valor")

    # --- configuration columns ----------------------------------------------
    m2_cols = {str(v).strip(): c for (r, c), v in m2.items()
               if r == M2_GC_FIRST_ROW and CONFIG_RE.match(str(v).strip())}
    m1_cols = {str(v).strip(): c for (r, c), v in m1.items()
               if r == M1_ROW_CONFIG_CODE and CONFIG_RE.match(str(v).strip())}
    codes = sorted(set(m2_cols) & set(m1_cols))
    print(f"configuracoes: {len(m2_cols)} em M2, {len(m1_cols)} em M1, "
          f"{len(codes)} em ambas")

    # --- subgroup rows in M1 -------------------------------------------------
    # In M1 the subgroup identifier is merged across two rows in one case: the
    # gearbox and the hybrid combination module share IDS 23. The base keeps
    # them apart, so the second occurrence is mapped to its own subgroup.
    SECOND_ROW_IDSG = {23: 43}
    subgroup_rows, seen = [], set()
    for r in M1_ROWS_SUBGROUPS:
        raw = m1.get((r, M1_COL_SUBGROUP_ID))
        if not isinstance(raw, int):
            continue
        idsg = SECOND_ROW_IDSG.get(raw, raw) if raw in seen else raw
        seen.add(raw)
        subgroup_rows.append((r, idsg))

    configs = {}
    for code in codes:
        c2, c1 = m2_cols[code], m1_cols[code]
        gc = {}
        for idvp in range(1, M2_GC_LAST_IDVP + 1):
            v = m2.get((10 + idvp, c2))
            if v is not None:
                gc[idvp] = v if isinstance(v, (int, float)) else str(v).strip()
        me = {}
        for r, idsg in subgroup_rows:
            v = num(m1.get((r, c1 + M1_OFFSET_MASS)))
            if v is not None:
                me[idsg] = v
        groups = {g: num(m2.get((r, c2)))
                  for g, r in zip(GROUP_ORDER, M2_ROWS_GROUP_MASS)}
        expected = {
            "vehicle_mass_kg": num(m2.get((M2_ROW_VEHICLE_MASS, c2))),
            "mass_by_group_kg": groups,
            "me_by_subgroup_kg": me,
            "ghg_materials_kgCO2e": num(m2.get((M2_ROW_MATERIALS, c2))),
            "ghg_aux_battery_kgCO2e": num(m2.get((M2_ROW_AUX_BATTERY, c2))),
            "ghg_pe_battery_kgCO2e": num(m2.get((M2_ROW_PE_BATTERY, c2))),
            "ghg_fluids_kgCO2e": num(m2.get((M2_ROW_FLUIDS, c2))),
            "ghg_assembly_kgCO2e": num(m2.get((M2_ROW_ASSEMBLY, c2))),
            "ghg_total_i3et_kgCO2e": num(m2.get((M2_ROW_TOTAL_I3ET, c2))),
        }
        # Cradle to gate is the i3ET total minus lifetime replacements and
        # end-of-life -- see Documento 1, secao 15.2.
        parts = [expected["ghg_materials_kgCO2e"], expected["ghg_aux_battery_kgCO2e"],
                 expected["ghg_pe_battery_kgCO2e"], expected["ghg_fluids_kgCO2e"],
                 expected["ghg_assembly_kgCO2e"]]
        expected["ghg_cradle_to_gate_kgCO2e"] = (
            sum(p for p in parts if p is not None) if all(p is not None for p in parts) else None)
        configs[code] = {
            "label": str(m2.get((8, c2)) or code),
            "powertrain": str(m2.get((M2_ROW_POWERTRAIN, c2)) or "").strip(),
            "gc": gc,
            "expected": expected,
        }

    fixture = {
        "source_workbook": os.path.basename(src),
        "ef_version_in_model": ef_version,
        "ef_by_material": ef_values,
        "group_order": GROUP_ORDER,
        "configs": configs,
        "note": ("Fixture de validacao extraida do i3ET. Os fatores de emissao sao os "
                 "efetivamente selecionados na planilha no momento da extracao, de modo "
                 "que o teste compara o motor de calculo, nao a base de dados."),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(fixture, fh, ensure_ascii=False, indent=1, sort_keys=True)

    usable = [c for c, d in configs.items()
              if d["expected"]["vehicle_mass_kg"] is not None
              and d["expected"]["ghg_cradle_to_gate_kgCO2e"] is not None]
    print(f"\n{len(configs)} configuracoes extraidas, {len(usable)} completas "
          f"(massa e emissoes), {len(configs) - len(usable)} incompletas e portanto "
          f"inadequadas como caso de teste")
    for c in usable[:8]:
        e = configs[c]["expected"]
        print(f"   {c:6s} {configs[c]['powertrain']:6s} "
              f"massa={e['vehicle_mass_kg']:10.3f} kg  "
              f"berco-portao={e['ghg_cradle_to_gate_kgCO2e']:9.1f} kg CO2e  "
              f"({len(e['me_by_subgroup_kg'])} subgrupos)")
    fixture["usable_configs"] = usable
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(fixture, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"\ngravado: {OUT}  ({os.path.getsize(OUT)/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
