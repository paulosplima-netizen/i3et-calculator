"""Rodada: congelar, executar e gravar o resultado (Fase A, passo 4).

Congelar grava em D09 um JSON canonico de tudo o que entra no calculo e o seu
SHA-256. Executar calcula cada caso (menos os Pending) com o nucleo e grava R45.
Duas rodadas com o mesmo `InputHash` e o mesmo `ParamBaseHash` dao o mesmo R45
(regra I24).

Blocos:
    RN1  verificacao previa
    RN2  congelar
    RN3  executar
    RN4  gravar R45

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import secrets
import sqlite3

from . import (
    b1_choices,
    calc,
    control_params,
    ef_edit,
    loader,
    power_rule,
    provenance,
    user_assets,
    user_mass_params,
    user_recipes,
)
from . import battery as battery_mod
from .log import Log
from .validate import check_analysis

#: Indicadores calculados pelo nucleo (P51.CalcStatus = Calculated) e de onde
#: vem cada um: IDVP de D03, ou um dos nomes especiais.
_GC_INDICATORS = {"O10": 2, "O11": 3, "O12": 15, "O13": 7, "O14": 8, "O15": 27, "O16": 14,
                  "O17": 31, "O19": 5}


def _rows(conn, sql, args=()):
    cur = conn.execute(sql, args)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


# --------------------------------------------------------------------------
# BLOCO RN1 -- verificacao previa
#   Devolve : lista de problemas (vazia: pode congelar); as regras I16 a I23 e
#             I28 ficam em validate.check_analysis.
# --------------------------------------------------------------------------
def precheck(conn: sqlite3.Connection, ida: int) -> list[str]:
    return check_analysis(conn, ida)


# --------------------------------------------------------------------------
# BLOCO RN2 -- congelar
#   Le      : D06, D07, D02, D03, D12, P30/D08 e a base.
#   Devolve : RunID. Grava M01 e D09 (Status Frozen).
# --------------------------------------------------------------------------
def _snapshot(conn, ida: int, *, calculator_version: str, base_hash: str,
              reference_workbook: str) -> dict:
    d06 = _rows(conn, "SELECT * FROM D06_Analysis WHERE IDA = ?", (ida,))[0]
    defaults, fits = power_rule.load_defaults(conn), power_rule.load_fits(conn)
    overrides = power_rule.load_overrides(conn, ida)
    cases = []
    for c in _rows(conn, "SELECT * FROM D07_AnalysisVehicle WHERE IDA = ? ORDER BY IDCase", (ida,)):
        f = power_rule.effective_factors(
            c["IDVPT"], rule=d06["CombinedPowerRule"], case_key=c["CaseKey"],
            idcase=c["IDCase"], defaults=defaults, fits=fits, overrides=overrides)
        cases.append({
            "case": c,
            "vehicle": _rows(conn, "SELECT * FROM D01_Vehicle WHERE IDV = ?", (c["IDV"],))[0],
            "alternative": _rows(conn, "SELECT * FROM D02_EvaluationAlternative "
                                 "WHERE IDV = ? AND IDEA = ?", (c["IDV"], c["IDEA"]))[0],
            "params": _rows(conn, "SELECT IDVP, GC, GCText, IsCalculated FROM "
                            "D03_VehicleParamValue WHERE IDV = ? ORDER BY IDVP", (c["IDV"],)),
            "power_factors": {"ice": f.ice, "ee": f.ee, "origin": f.origin,
                              "provisional": f.provisional},
        })
    eff = control_params.effective_values(conn, ida, d06["ParamProfile"])
    snap = {"analysis": d06, "cases": cases,
            "control_params": {k: [e.value, e.text, e.source] for k, e in sorted(eff.items())},
            "versions": {"calculator": calculator_version, "param_base_hash": base_hash,
                         "reference_workbook": reference_workbook}}
    usadas = sorted({c["alternative"]["IDVMR"] for c in cases
                     if str(c["alternative"]["IDVMR"]).startswith(user_recipes.PREFIX)})
    if usadas:                      # I30: a rodada guarda o hash das participacoes usadas
        snap["user_recipes"] = {i: user_recipes.shares_hash(conn, i) for i in usadas}
    versoes_ef = sorted({d06["IDEFV"]} | {c["alternative"]["IDEFV"] for c in cases})
    usadas_ef = {i: ef_edit.factors_hash(conn, i) for i in versoes_ef
                 if ef_edit.needs_hash(conn, i)}
    if usadas_ef:                   # I53: hash dos fatores efetivos das listas do usuario/alteradas
        snap["emission_factors"] = usadas_ef
    versoes_u = {}
    for c in cases:                 # I53: montagens (UA-) e parametros de massa (UM-) usados
        a = c["alternative"]
        if str(a["IDAPV"]).startswith("UA-"):
            versoes_u[a["IDAPV"]] = user_assets.assembly_hash(conn, a["IDAPV"])
        if str(a["IDMPV"]).startswith(user_mass_params.PREFIX):
            versoes_u[a["IDMPV"]] = user_mass_params.params_hash(conn, a["IDMPV"])
    if versoes_u:
        snap["user_versions"] = versoes_u
    escolhas = b1_choices.load(conn, ida)
    if escolhas is not None:        # sem escolha, o instantaneo e o mesmo de antes do B1
        snap["b1"] = escolhas
    return snap


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def freeze(conn: sqlite3.Connection, ida: int, *, calculator_version: str,
           reference_workbook: str, project_name: str | None = None) -> str:
    problems = precheck(conn, ida)
    if problems:
        raise ValueError("cannot freeze: " + "; ".join(problems))
    base_hash = conn.execute(
        "SELECT Value FROM M00_BaseInfo WHERE Key = 'ParamBaseHash'").fetchone()[0]
    snap = canonical(_snapshot(conn, ida, calculator_version=calculator_version,
                               base_hash=base_hash, reference_workbook=reference_workbook))
    now = dt.datetime.now().isoformat(timespec="seconds")
    run_id = "RUN-" + dt.datetime.now().strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(2)
    seq = conn.execute("SELECT COALESCE(MAX(RunSeq), 0) + 1 FROM D09_Run WHERE IDA = ?",
                       (ida,)).fetchone()[0]
    conn.execute("INSERT INTO M01_RunMetadata (RunID, RunTimestamp, CalculatorVersion, "
                 "ParamBaseHash, ProjectName, ValidationStatus) VALUES (?,?,?,?,?,'Frozen')",
                 (run_id, now, calculator_version, base_hash, project_name))
    conn.execute(
        "INSERT INTO D09_Run (RunID, IDA, RunSeq, FrozenAt, InputSnapshot, InputHash, "
        "ParamBaseHash, ReferenceWorkbook, CalculatorVersion, Status) "
        "VALUES (?,?,?,?,?,?,?,?,?,'Frozen')",
        (run_id, ida, seq, now, snap, hashlib.sha256(snap.encode("utf-8")).hexdigest(),
         base_hash, reference_workbook, calculator_version))
    conn.commit()
    return run_id


# --------------------------------------------------------------------------
# BLOCO RN3 -- executar
#   Calcula cada caso do instantaneo congelado, nao o estado atual do projeto.
#   `db_path` e o arquivo do projeto (o nucleo le as tabelas de parametros dele).
# --------------------------------------------------------------------------
def execute(conn: sqlite3.Connection, db_path: str, run_id: str) -> dict:
    snap = json.loads(conn.execute("SELECT InputSnapshot FROM D09_Run WHERE RunID = ?",
                                   (run_id,)).fetchone()[0])
    stale = [i for i, h in snap.get("emission_factors", {}).items()
             if ef_edit.factors_hash(conn, i) != h]
    for i, h in snap.get("user_versions", {}).items():
        atual = (user_assets.assembly_hash(conn, i) if i.startswith("UA-")
                 else user_mass_params.params_hash(conn, i))
        if atual != h:
            stale.append(i)
    if stale:                                                          # I53
        raise ValueError("I53: " + ", ".join(stale) + " changed after "
                         "this run was frozen; freeze the analysis again (T41)")
    base = loader.load_sqlite(db_path)
    ef_table = loader.effective_emission_factors(base)
    log = Log()
    results = {}
    cp_values = {k: v[0] for k, v in snap["control_params"].items()}
    try:
        for c in snap["cases"]:
            if c["case"]["SizingOrigin"] == "Pending":
                continue
            alt, pf = c["alternative"], c["power_factors"]
            gc = {p["IDVP"]: float(p["GC"] or 0.0) for p in c["params"]}
            supplied = {p["IDVP"] for p in c["params"] if not p["IsCalculated"]}
            battery = next((p["GCText"] for p in c["params"] if p["IDVP"] == 32), None)
            battery = battery if battery not in (None, "", "ND") else None
            res = calc.calculate_vehicle(
                base, gc, powertrain=c["vehicle"]["IDVPT"], battery_id=battery,
                idmpv=alt["IDMPV"], idvmr=alt["IDVMR"], idefv=alt["IDEFV"], idapv=alt["IDAPV"],
                boundary=alt["Boundary"], ef_table=ef_table, supplied=supplied,
                power_factors=(pf["ice"], pf["ee"]),
                mass_adjustment_kg=float(c["case"].get("MassAdjustmentKg") or 0.0),
                body_share=b1_choices.body_share(c["case"].get("MassBodyShare")),
                generic_battery=battery_mod.generic_model(base.get("P58"), battery, cp_values),
                log=log)
            res["mass_calibration"]["BodyShareReference"] = b1_choices.reference_body_share(
                base, alt["IDVMR"])
            results[c["case"]["CaseKey"]] = (c, res)
    except Exception:
        conn.execute("UPDATE D09_Run SET Status = 'Failed' WHERE RunID = ?", (run_id,))
        conn.commit()
        raise
    write_results(conn, run_id, results, snap)
    write_b1(conn, run_id, base, ef_table, results, cp_values, snap.get("b1"))
    return results


# --------------------------------------------------------------------------
# BLOCO RN3b -- B1 (C15, C16, C34, C35)
#   Com as escolhas padrao (core/b1_results.Options); as escolhas do usuario
#   (D10, D06) entram quando as telas T12-T18 existirem.
# --------------------------------------------------------------------------
def write_b1(conn, run_id, base, ef_table, results, cp_values, choices=None) -> None:
    from . import b1_results
    if "P31" not in base or conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'C35_VehicleLifeStage'"
    ).fetchone() is None:
        return
    base_options = b1_choices.options(choices, cp_values)
    for c, res in results.values():
        case = c["case"]
        options = copy.copy(base_options)
        options.declared_mass_kg = case.get("DeclaredMassKg")
        options.declared_source = case.get("DeclaredSource") or ""
        ef = b1_results.ef_for(ef_table, c["alternative"]["IDEFV"])
        frames = b1_results.compute(res, base, ef, options,
                                    boundary=c["alternative"]["Boundary"])
        b1_results.write_db(conn, run_id, ida=case["IDA"], idcase=case["IDCase"],
                            idv=case["IDV"], idea=case["IDEA"], frames=frames)
    conn.commit()


# --------------------------------------------------------------------------
# BLOCO RN4 -- gravar R45
#   Indicadores calculados: origem Calculated. Indicadores que so existem na
#   planilha: ExcelReference, so para a configuracao gravada (P52).
# --------------------------------------------------------------------------
def write_results(conn: sqlite3.Connection, run_id: str, results: dict, snap: dict) -> None:
    status = dict(conn.execute("SELECT IDInd, CalcStatus FROM P51_OutputIndicator "
                               "WHERE IsHeader = 0"))
    refs = {}
    for case_key, idind, val, txt in conn.execute(
            "SELECT CaseKey, IDInd, Value, ValueText FROM P52_ExcelReferenceValue "
            "WHERE RefSet IN ('CP_OUT_EC','CP_OUT_FC')"):
        refs[(case_key, idind)] = (val, txt)
    conn.execute("DELETE FROM R45_PowertrainSummary WHERE RunID = ?", (run_id,))
    by_case = {c["case"]["CaseKey"]: c for c in snap["cases"]}
    for key, c in by_case.items():
        pt = c["case"]["IDVPT"]
        recorded = c["case"]["SizingOrigin"] == "ExcelReference"
        out = results.get(key)
        for idind, st in status.items():
            val = txt = None
            if st == "Calculated" and out is not None:
                _, res = out
                gc = res["gc"]
                if idind in _GC_INDICATORS:
                    val = float(gc[_GC_INDICATORS[idind]])
                elif idind == "O9":
                    txt = c["vehicle"]["DsV"]
                elif idind == "O18":
                    txt = next((p["GCText"] for p in c["params"] if p["IDVP"] == 32), None)
                elif idind == "O28":
                    txt = c["alternative"]["IDVMR"]
                elif idind == "O20":
                    val = float(res["totals"]["MassIDV"])   # massa calculada, nao a de entrada
                elif idind == "O29":
                    val = float(res["totals"]["GHGCradleToGate"])
                else:
                    continue
            seal = provenance.classify(st, is_recorded_case=recorded,
                                       has_reference=(key, idind) in refs)
            if seal.origin == provenance.EXCEL_REFERENCE:
                val, txt = refs[(key, idind)]
            elif st == "Calculated" and out is not None:
                seal = provenance.Seal(provenance.CALCULATED)
            else:
                continue
            if val is None and txt is None:
                continue
            conn.execute("INSERT INTO R45_PowertrainSummary (RunID, CaseKey, IDVPT, IDInd, "
                         "Value, ValueText, ValueOrigin) VALUES (?,?,?,?,?,?,?)",
                         (run_id, key, pt, idind, val, txt, seal.origin))
    conn.execute("UPDATE D09_Run SET Status = 'Calculated' WHERE RunID = ?", (run_id,))
    conn.execute("UPDATE M01_RunMetadata SET ValidationStatus = 'Calculated' WHERE RunID = ?",
                 (run_id,))
    conn.commit()
