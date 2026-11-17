"""Exportacao de rodadas e do projeto em JSON (Fase A, passo 6).

Toda exportacao registra `ProjectID`, `RunID`, `InputHash`, `ParamBaseHash` e o
selo de origem de cada valor (docs/06, T08). Previas (`Preview`) nao saem: ficam
so em tela. O JSON e canonico (chaves em ordem alfabetica, sem espacos, UTF-8) e
leva o proprio hash (`ExportHash`, SHA-256 do conteudo sem esse campo), para que
quem receber o arquivo confira que nada mudou.

Blocos:
    RX1  uma rodada
    RX2  o projeto
    RX3  JSON canonico e hash
    RX4  gravar arquivo
    RX5  verificar um arquivo exportado

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3

from . import project, provenance

FORMAT = "i3et-export"
FORMAT_VERSION = "1"

_CONFIG_TABLES = ("D06_Analysis", "D07_AnalysisVehicle", "D08_ControlParamValue",
                  "D12_CombinedPowerOverride")
_VEHICLE_TABLES = ("D01_Vehicle", "D02_EvaluationAlternative", "D03_VehicleParamValue")


def _rows(conn: sqlite3.Connection, sql: str, args=()) -> list[dict]:
    cur = conn.execute(sql, args)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def _identity(conn: sqlite3.Connection) -> dict:
    ident = project.identity(conn)
    if ident is None:
        raise ValueError("this file is not a project (no M03_Project row)")
    return ident


# --------------------------------------------------------------------------
# BLOCO RX1 -- uma rodada
#   Le      : D09, R45, P51 e M03.
#   Devolve : dict com a identidade, os hashes e os resultados com selo.
#             Previas ficam de fora; `omitted_previews` diz quantas.
# --------------------------------------------------------------------------
def export_run(conn: sqlite3.Connection, run_id: str) -> dict:
    ident = _identity(conn)
    runs = _rows(conn, "SELECT * FROM D09_Run WHERE RunID = ?", (run_id,))
    if not runs:
        raise KeyError(f"unknown run: {run_id}")
    run = runs[0]
    snapshot = json.loads(run.pop("InputSnapshot"))
    results = _rows(
        conn,
        "SELECT r.CaseKey, r.IDVPT, r.IDInd, i.DsInd, i.utInd, r.Value, r.ValueText, "
        "r.ValueOrigin FROM R45_PowertrainSummary r "
        "JOIN P51_OutputIndicator i ON i.IDInd = r.IDInd WHERE r.RunID = ? "
        "ORDER BY r.CaseKey, r.IDInd", (run_id,))
    kept, omitted = [], 0
    for row in results:
        seal = provenance.Seal(row["ValueOrigin"])
        if not provenance.allowed_in_report(seal):
            omitted += 1
            continue
        row["Seal"] = provenance.label(seal, run["RunSeq"])
        kept.append(row)
    return _finish({
        "format": FORMAT, "format_version": FORMAT_VERSION, "kind": "run",
        "project": ident,
        "run": run,
        "analysis": snapshot.get("analysis"),
        "inputs": snapshot,
        "results": kept,
        "omitted_previews": omitted,
    })


# --------------------------------------------------------------------------
# BLOCO RX2 -- o projeto
#   Le      : M03, D01 a D03, D06 a D09, D12 e R45.
#   Devolve : dict com a configuracao, os veiculos e todas as rodadas.
# --------------------------------------------------------------------------
def export_project(conn: sqlite3.Connection) -> dict:
    ident = _identity(conn)
    out = {"format": FORMAT, "format_version": FORMAT_VERSION, "kind": "project",
           "project": ident,
           "param_base_hash": conn.execute(
               "SELECT Value FROM M00_BaseInfo WHERE Key = 'ParamBaseHash'").fetchone()[0],
           "configuration": {t: _rows(conn, f"SELECT * FROM {t}") for t in _CONFIG_TABLES},
           "vehicles": {t: _rows(conn, f"SELECT * FROM {t}") for t in _VEHICLE_TABLES},
           "runs": []}
    for (rid,) in conn.execute("SELECT RunID FROM D09_Run ORDER BY IDA, RunSeq").fetchall():
        full = export_run(conn, rid)
        out["runs"].append({"run": full["run"], "results": full["results"],
                            "omitted_previews": full["omitted_previews"]})
    return _finish(out)


# --------------------------------------------------------------------------
# BLOCO RX3 -- JSON canonico e hash
# --------------------------------------------------------------------------
def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "ExportHash"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def _finish(payload: dict) -> dict:
    payload["ExportHash"] = _hash(payload)
    return payload


# --------------------------------------------------------------------------
# BLOCO RX4 -- gravar arquivo
# --------------------------------------------------------------------------
def write(payload: dict, path: str) -> str:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(canonical(payload))
    return path


# --------------------------------------------------------------------------
# BLOCO RX5 -- verificar um arquivo exportado
#   Devolve : lista de problemas; vazia quando o arquivo esta integro.
# --------------------------------------------------------------------------
def verify(payload: dict) -> list[str]:
    problems = []
    if payload.get("format") != FORMAT:
        problems.append("not an i3ET export")
        return problems
    if payload.get("ExportHash") != _hash(payload):
        problems.append("ExportHash does not match the content")
    if not (payload.get("project") or {}).get("ProjectID"):
        problems.append("ProjectID is missing")
    runs = [payload] if payload.get("kind") == "run" else payload.get("runs", [])
    for item in runs:
        run = item.get("run") or {}
        for key in ("RunID", "InputHash", "ParamBaseHash"):
            if not run.get(key):
                problems.append(f"{key} is missing in a run")
        for row in item.get("results", []):
            if row.get("ValueOrigin") not in (provenance.CALCULATED,
                                              provenance.EXCEL_REFERENCE):
                problems.append(f"value without a valid seal: {row.get('CaseKey')} "
                                f"{row.get('IDInd')}")
                break
    return problems
