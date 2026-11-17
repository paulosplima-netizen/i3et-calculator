"""Analise: casos e veiculos do projeto (Fase A, passo 4).

Cria a configuracao (D06), os casos (D07) e, para cada caso, o veiculo (D01),
seus parametros (D03) e a alternativa de avaliacao (D02).

    EC  comparacao equalizada: seis casos, um por motorizacao. Para as
        configuracoes gravadas na planilha (SELEÇÃO da categoria) o
        dimensionamento vem do bloco auxiliar (P52, conjunto MV_AUX), com
        SizingOrigin = ExcelReference. Com outro ICEV de referencia, so o caso
        REF e calculavel; os demais ficam Pending ate o M3.
    FC  comparacao livre: de 1 a `max_cases` casos, parametros do catalogo
        (P26/P27), SizingOrigin = Manufacturer.

A receita de materiais e escolha do usuario, entre as da motorizacao e do porte
(SHEV usa as do HEV; SPHEV, as do PHEV, como a planilha).

Blocos:
    AN1  criar EC
    AN2  criar FC
    AN3  gerar casos em D01 a D03
    AN4  receitas oferecidas

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import sqlite3

from core.params import HYBRID_COMBINATION

#: Ordem das motorizacoes em EC.
EC_ORDER = ("ICEV", "HEV", "SHEV", "PHEV", "SPHEV", "BEV")

#: Motorizacao cujas receitas a planilha usa quando a propria nao tem.
RECIPE_SOURCE = {"SHEV": "HEV", "SPHEV": "PHEV"}

#: Parametros de veiculo que o nucleo calcula (P07.ParamClass End ou Res).
_COMPUTED_CLASSES = ("End", "Res")

_VP_MAX = 40       # IDVP 2 a 40 vem da planilha; 41 e 42 sao do nucleo
BATTERY_IDVP = 32


# --------------------------------------------------------------------------
# BLOCO AN4 -- receitas oferecidas
#   Devolve : IDs de P15 da motorizacao do caso (as do HEV para SHEV, as do PHEV
#             para SPHEV), com as da mesma carroceria e porte primeiro.
# --------------------------------------------------------------------------
def recipes_for(conn: sqlite3.Connection, idvpt: str, idvdt: str | None = None,
                idvs: str | None = None) -> list[str]:
    pt = RECIPE_SOURCE.get(idvpt, idvpt)
    rows = conn.execute(
        "SELECT IDVMR, IDVDT, IDVS FROM P15_VehicleMaterialRecipe WHERE IDVPT = ? "
        "ORDER BY IDVMR", (pt,)).fetchall()
    rows.sort(key=lambda r: (r[1] != idvdt, r[2] != idvs, r[0]))
    return [r[0] for r in rows]


# --------------------------------------------------------------------------
# BLOCO AN3 -- gerar casos
#   Cria D01, D03 e D02 de um veiculo. Devolve (IDV, IDEA).
# --------------------------------------------------------------------------
def _computed_idvps(conn: sqlite3.Connection) -> set[int]:
    return {r[0] for r in conn.execute(
        "SELECT IDVP FROM P07_VehicleParam WHERE ParamClass IN (?, ?)", _COMPUTED_CLASSES)}


def _new_vehicle(conn, *, name, idvpt, idvdt, idvs, idlr, params, idvmr, d06) -> tuple[int, int]:
    idv = (conn.execute("SELECT COALESCE(MAX(IDV), 0) FROM D01_Vehicle").fetchone()[0]) + 1
    conn.execute("INSERT INTO D01_Vehicle (IDV, DsV, IDVPT, IDVDT, IDVS, IDLR, IsUserDefined) "
                 "VALUES (?,?,?,?,?,?,0)", (idv, name, idvpt, idvdt, idvs, idlr))
    computed = _computed_idvps(conn)
    for idvp, in conn.execute("SELECT IDVP FROM P07_VehicleParam ORDER BY IDVP"):
        val, txt = params.get(idvp, (0.0, None))
        if idvp == 41 and idvp not in params:
            val = 1.0 if idvpt in HYBRID_COMBINATION else 0.0   # existencia do modulo
        conn.execute("INSERT INTO D03_VehicleParamValue (IDV, IDVP, GC, GCText, IsCalculated) "
                     "VALUES (?,?,?,?,?)",
                     (idv, idvp, float(val or 0.0), txt, int(idvp in computed)))
    conn.execute("INSERT INTO D02_EvaluationAlternative "
                 "(IDV, IDEA, IDMPV, IDVMR, IDEFV, IDAPV, Boundary) VALUES (1*?,1,?,?,?,?,?)",
                 (idv, d06["IDMPV"], idvmr, d06["IDEFV"], d06["IDAPV"], d06["Boundary"]))
    return idv, 1


def _market_params(conn, idmv: int) -> dict[int, tuple]:
    """Parametros de um veiculo de mercado como {IDVP: (valor, texto)}."""
    out = {}
    for idvp, val, txt in conn.execute(
            "SELECT m.IDVP, p.Value, p.ValueText FROM P27_MarketVehicleParam p "
            "JOIN P54_MarketParam m USING (IDMP) WHERE p.IDMV = ? AND m.IDVP IS NOT NULL "
            "AND m.IDVP <= ?", (idmv, _VP_MAX)):
        out[idvp] = (val or 0.0, txt)
    return out


#: Indicadores da tabela de saidas (Control Panel BP:BU, que le o M2 ET:EY) que sao
#: entradas do veiculo: P51.IDInd -> IDVP. A tabela de saidas e a gravacao de
#: referencia da rodada; o bloco auxiliar (MV_AUX) guarda outro estado, com
#: dimensionamento e bateria diferentes (docs/08, passo 5).
_OUTPUT_INPUTS = {"O10": 2, "O11": 3, "O13": 7, "O14": 8, "O15": 27, "O16": 14,
                  "O17": 31, "O19": 5}
_BATTERY_INDICATOR = "O18"


def _recorded_params(conn, case_key: str) -> tuple[dict[int, tuple], str | None]:
    """Parametros gravados do caso e o nome da receita.

    Base: bloco auxiliar (P52, MV_AUX). Por cima, as entradas que o M2 usa de fato
    (M2_IN) e o dimensionamento e a bateria da tabela de saidas (CP_OUT_EC).
    """
    params, recipe = {}, None
    for idmp, val, txt in conn.execute(
            "SELECT IDMP, Value, ValueText FROM P52_ExcelReferenceValue "
            "WHERE RefSet = 'MV_AUX' AND CaseKey = ?", (case_key,)):
        if idmp is None:
            recipe = txt
        elif idmp <= _VP_MAX:
            params[idmp] = (val or 0.0, txt)
    for idmp, val, txt in conn.execute(
            "SELECT IDMP, Value, ValueText FROM P52_ExcelReferenceValue "
            "WHERE RefSet = 'M2_IN' AND CaseKey = ?", (case_key,)):
        if idmp is not None and idmp <= _VP_MAX and (val is not None or txt):
            params[idmp] = (val or 0.0, txt)
    for idind, val, txt in conn.execute(
            "SELECT IDInd, Value, ValueText FROM P52_ExcelReferenceValue "
            "WHERE RefSet = 'CP_OUT_EC' AND CaseKey = ?", (case_key,)):
        if idind in _OUTPUT_INPUTS and val is not None:
            params[_OUTPUT_INPUTS[idind]] = (val, None)
        elif idind == _BATTERY_INDICATOR and txt not in (None, "", "-"):
            params[BATTERY_IDVP] = (0.0, txt)
    return params, recipe


def _pick_recipe(conn, wanted: str | None, idvpt, idvdt, idvs) -> str:
    offered = recipes_for(conn, idvpt, idvdt, idvs)
    if not offered:
        raise ValueError(f"no material recipe for powertrain {idvpt}")
    if wanted and wanted in offered:
        return wanted
    sheet = conn.execute("SELECT 1 FROM P15_VehicleMaterialRecipe WHERE IDVMR = ?",
                         (wanted,)).fetchone() if wanted else None
    return wanted if sheet else offered[0]


def _insert_d06(conn, *, name, mode, idvc, idmv_ref, cfg) -> int:
    ida = conn.execute("SELECT COALESCE(MAX(IDA), 0) FROM D06_Analysis").fetchone()[0] + 1
    conn.execute(
        "INSERT INTO D06_Analysis (IDA, DsA, Mode, AnalysisType, IDVC, IDMVRef, FuelScenario, "
        "TestNorm, DistanceCurve, IDEFV, IDMPV, IDAPV, Boundary, SPHEVEco, LightweightingOn, "
        "ParamProfile, CombinedPowerRule) VALUES (?,?,?,'GHG_LCA_LCC',?,?,?,?,?,?,?,?,?,?,0,?,?)",
        (ida, name, mode, idvc, idmv_ref, cfg["fuel"], cfg["norm"], cfg["curve"], cfg["idefv"],
         cfg["idmpv"], cfg["idapv"], cfg.get("boundary", "MAT_ASM"), int(cfg.get("sphev_eco", 0)),
         cfg.get("profile", "Expert"), cfg.get("power_rule", "Default")))
    return ida


def _d06(conn, ida) -> dict:
    cur = conn.execute("SELECT * FROM D06_Analysis WHERE IDA = ?", (ida,))
    return dict(zip([d[0] for d in cur.description], cur.fetchone()))


# --------------------------------------------------------------------------
# BLOCO AN1 -- criar EC
#   cfg : fuel, norm, curve, idefv, idmpv, idapv [, boundary, profile, power_rule,
#         sphev_eco]; recipes: {CaseKey: IDVMR} opcional (escolha do usuario).
#   Devolve : IDA.
# --------------------------------------------------------------------------
def create_ec(conn: sqlite3.Connection, name: str, idvc: str, cfg: dict, *,
              idmv_ref: int | None = None, recipes: dict[str, str] | None = None) -> int:
    recipes = recipes or {}
    cat = conn.execute("SELECT CaseDigit, IDMVSelecao FROM P29_VehicleCategory WHERE IDVC = ?",
                       (idvc,)).fetchone()
    if cat is None:
        raise KeyError(f"unknown category: {idvc}")
    digit, selecao = cat
    ref = idmv_ref or selecao
    recorded = ref == selecao
    ida = _insert_d06(conn, name=name, mode="EC", idvc=idvc, idmv_ref=ref, cfg=cfg)
    d06 = _d06(conn, ida)
    _, dt, vs, lr = conn.execute(
        "SELECT IDVPT, IDVDT, IDVS, IDLR FROM P26_MarketVehicle WHERE IDMV = ?", (ref,)).fetchone()
    pts = dict(conn.execute("SELECT CaseKey, IDVPT FROM P56_CombinedPowerFit "
                            "WHERE CaseKey LIKE ?", (f"A{digit}_",)).fetchall())
    keys = sorted(pts, key=lambda k: EC_ORDER.index(pts[k]))
    if len(keys) != 6:
        raise ValueError(f"category {idvc} has {len(keys)} recorded configurations, expected 6")
    for n, key in enumerate(keys, start=1):
        pt = pts[key]
        if recorded:
            params, sheet_recipe = _recorded_params(conn, key)
            origin = "ExcelReference"
        else:
            params, sheet_recipe = _market_params(conn, ref), None
            origin = "Manufacturer" if n == 1 else "Pending"
        idvmr = _pick_recipe(conn, recipes.get(key, sheet_recipe), pt, dt, vs)
        idv, idea = _new_vehicle(conn, name=f"{key} {pt}", idvpt=pt, idvdt=dt, idvs=vs, idlr=lr,
                                 params=params, idvmr=idvmr, d06=d06)
        conn.execute(
            "INSERT INTO D07_AnalysisVehicle (IDA, IDCase, CaseKey, CaseRole, IDVPT, IDMV, IDV, "
            "IDEA, SizingOrigin) VALUES (?,?,?,?,?,?,?,?,?)",
            (ida, n, key, "REF" if n == 1 else "EQ", pt, ref if n == 1 else None, idv, idea,
             origin))
    return ida


# --------------------------------------------------------------------------
# BLOCO AN2 -- criar FC
#   cases : lista de dicts {idmv, fuel (opcional), idvmr (opcional)}.
# --------------------------------------------------------------------------
def create_fc(conn: sqlite3.Connection, name: str, cfg: dict, cases: list[dict], *,
              max_cases: int) -> int:
    if not 1 <= len(cases) <= 7:
        raise ValueError("a free comparison has from 1 to 7 cases")
    if len(cases) > max_cases:
        raise ValueError(f"at most {max_cases} cases are accepted in this version")
    ida = _insert_d06(conn, name=name, mode="FC", idvc=None, idmv_ref=None, cfg=cfg)
    d06 = _d06(conn, ida)
    for n, case in enumerate(cases, start=1):
        row = conn.execute("SELECT DsMV, IDVPT, IDVDT, IDVS, IDLR FROM P26_MarketVehicle "
                           "WHERE IDMV = ?", (case["idmv"],)).fetchone()
        if row is None:
            raise KeyError(f"unknown market vehicle: {case['idmv']}")
        dsmv, pt, dt, vs, lr = row
        idvmr = _pick_recipe(conn, case.get("idvmr"), pt, dt, vs)
        idv, idea = _new_vehicle(conn, name=dsmv, idvpt=pt, idvdt=dt, idvs=vs, idlr=lr,
                                 params=_market_params(conn, case["idmv"]), idvmr=idvmr, d06=d06)
        conn.execute(
            "INSERT INTO D07_AnalysisVehicle (IDA, IDCase, CaseKey, CaseRole, IDVPT, IDMV, IDV, "
            "IDEA, FuelBlend, SizingOrigin) VALUES (?,?,?,'FC',?,?,?,?,?,'Manufacturer')",
            (ida, n, f"SV{n}", pt, case["idmv"], idv, idea, case.get("fuel")))
    return ida
