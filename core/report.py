"""The R tables: results in the form other people receive them.

Documento 4, capitulo 5. The C tables are what the calculation produces; the R
tables are what leaves the program. Three things separate them:

* every R row repeats the scenario it belongs to (`IDMPV`, `IDVMR`, `IDEFV`,
  `IDAPV`, `Boundary`), so a sheet pulled out of the file still says what it
  is;
* the detailed tables carry their own inputs -- `Beta`, `GCR`, `MR`, `GC`,
  `MshareGG`, `EF` -- so whoever opens the file can redo the arithmetic;
* the parameter tables travel along (R20 to R44), reduced to the rows the
  exported scenarios actually used. The result is self-contained: results plus
  exactly the parameters that produced them.

This module builds tables and nothing else. Writing files is `core/export.py`.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd

from . import __version__
from .log import Log

#: Repeated on every result row. Documento 4, secao 5.1, item 2.
SCENARIO_KEYS = ["IDMPV", "IDVMR", "IDEFV", "IDAPV", "Boundary"]

#: R table -> parameter table it is a snapshot of. Documento 4, secao 5.3.
PARAM_SNAPSHOTS = {
    "R20": "P05", "R21": "P06", "R22": "P03", "R23": "P08", "R24": "P04",
    "R25": "P07", "R26": "P09", "R27": "P10", "R28": "P11", "R29": "P12",
    "R30": "P13", "R31": "P14", "R32": "P15", "R33": "P16", "R34": "P17",
    "R35": "P18", "R36": "P19", "R37": "P20", "R38": "P02", "R39": "P21",
    "R40": "P22", "R41": "P23", "R42": "P24", "R43": "P25", "R44": "P01",
}

#: What each R table is, for the index sheet and for the report headings.
TITLES = {
    "R00": "Metadados da execucao",
    "R01": "Veiculos e cenarios",
    "R02": "Parametros do veiculo",
    "R03": "Massa por subgrupo",
    "R04": "Massa por grupo GREET",
    "R05": "Massa e GEE por material e grupo",
    "R06": "Massa e GEE da bateria por material",
    "R07": "Massa e GEE por grupo GREET",
    "R08": "Massa e GEE por material",
    "R09": "GEE da montagem por processo",
    "R10": "Total do berco ao portao",
    "R11": "Log de validacao",
}
TITLES.update({r: f"Parametros: {p}" for r, p in PARAM_SNAPSHOTS.items()})


def _scenario_columns(cen) -> dict:
    return {k: cen[k] for k in SCENARIO_KEYS}


def _stack(frames: list[pd.DataFrame], columns: list[str]) -> pd.DataFrame:
    """Concatenate, or return an empty frame with the right columns.

    An empty result table still has to have its columns: a sheet with no header
    is a sheet nobody can read.
    """
    frames = [f for f in frames if len(f)]
    if not frames:
        return pd.DataFrame(columns=columns)
    out = pd.concat(frames, ignore_index=True)
    return out[[c for c in columns if c in out.columns]]


def _identify(df: pd.DataFrame, idv, idea, cen) -> pd.DataFrame:
    out = df.copy()
    out.insert(0, "IDEA", idea)
    out.insert(0, "IDV", idv)
    for i, (k, v) in enumerate(_scenario_columns(cen).items()):
        out.insert(2 + i, k, v)
    return out


def build(base, results: dict, *, log: Log | None = None,
          generated_at: dt.datetime | None = None) -> dict[str, pd.DataFrame]:
    """Every R table, for the scenarios in `results`.

    `results` is what `calc.calculate` returns: {(IDV, IDEA): result}.
    """
    log = log if log is not None else Log()
    generated_at = generated_at or dt.datetime.now()

    d01 = base["D01"].set_index("IDV")
    d02 = base["D02"].set_index(["IDV", "IDEA"])
    p02 = base["P02"][["IDSG", "DsSG"]]
    p04 = base["P04"][["IDGG", "DsGG"]]
    p07 = base["P07"]
    p09 = base["P09"][["IDM", "DsM", "Mspec", "EFBasis", "ShareRole"]]

    r03, r04, r05, r06, r07, r08, r09, r10, r01, r02 = ([] for _ in range(10))

    for (idv, idea), res in sorted(results.items()):
        cen = d02.loc[(idv, idea)]
        veh = d01.loc[idv]
        t = res["totals"]

        r01.append(pd.DataFrame([{
            "IDV": idv, "IDEA": idea, "DsV": veh["DsV"], "IDVPT": veh["IDVPT"],
            "IDVDT": veh["IDVDT"], "IDVS": veh["IDVS"], "IDLR": veh["IDLR"],
            "IsUserDefined": veh["IsUserDefined"],
            **_scenario_columns(cen), "NotesIDEA": cen.get("NotesIDEA"),
        }]))

        gc = pd.DataFrame([{"IDVP": k, "GC": v} for k, v in sorted(res["gc"].items())])
        gc = gc.merge(p07, on="IDVP", how="left")
        r02.append(_identify(gc, idv, idea, cen))

        c01 = res["C01"].merge(p02, on="IDSG", how="left")
        c01 = c01[["IDSG", "DsSG", "IDGG", "IDVP", "GC", "Beta", "GCR", "MR", "fLM", "ME"]]
        r03.append(_identify(c01, idv, idea, cen))

        r04.append(_identify(res["C02"].merge(p04, on="IDGG", how="left"), idv, idea, cen))

        c03 = res["C03"].merge(p04, on="IDGG", how="left")
        r05.append(_identify(c03, idv, idea, cen))

        if len(res["C07"]):
            c07 = res["C07"].merge(p04, on="IDGG", how="left")
            r06.append(_identify(c07, idv, idea, cen))

        r07.append(_identify(res["C10"].merge(p04, on="IDGG", how="left"), idv, idea, cen))
        r08.append(_identify(res["C11"], idv, idea, cen))
        if len(res["C13"]):
            r09.append(_identify(res["C13"], idv, idea, cen))

        r10.append(pd.DataFrame([{
            "IDV": idv, "IDEA": idea, "DsV": veh["DsV"], "IDVPT": veh["IDVPT"],
            **_scenario_columns(cen),
            "MassIDV": t["MassIDV"], "GHGMaterials": t["GHGMaterials"],
            "GHGAssembly": t["GHGAssembly"],
            "GHGCradleToGate": t["GHGCradleToGate"], "GHGperKg": t["GHGperKg"],
            "MassNoFactor": t["MassNoFactor"], "ShareNoFactor": t["ShareNoFactor"],
        }]))

    R = {
        "R01": _stack(r01, ["IDV", "IDEA", "DsV", "IDVPT", "IDVDT", "IDVS", "IDLR",
                            "IsUserDefined", *SCENARIO_KEYS, "NotesIDEA"]),
        "R02": _stack(r02, ["IDV", "IDEA", *SCENARIO_KEYS, "IDVP", "DsVP", "utVP",
                            "ParamClass", "GCEquation", "GC"]),
        "R03": _stack(r03, ["IDV", "IDEA", *SCENARIO_KEYS, "IDSG", "DsSG", "IDGG",
                            "IDVP", "GC", "Beta", "GCR", "MR", "fLM", "ME"]),
        "R04": _stack(r04, ["IDV", "IDEA", *SCENARIO_KEYS, "IDGG", "DsGG", "MassIDGG"]),
        "R05": _stack(r05, ["IDV", "IDEA", *SCENARIO_KEYS, "IDGG", "DsGG", "IDM", "DsM",
                            "ShareRole", "MshareGG", "MassIDMpGG", "Quantity", "EF",
                            "GHGIDMpGG", "HasFactor", "CountsAsMass"]),
        "R06": _stack(r06, ["IDV", "IDEA", *SCENARIO_KEYS, "IDBMd", "IDGG", "DsGG",
                            "IDM", "DsM", "BMshareGG", "MassIDMpGGB", "Quantity", "EF",
                            "GHGIDMpGGB", "HasFactor", "CountsAsMass"]),
        "R07": _stack(r07, ["IDV", "IDEA", *SCENARIO_KEYS, "IDGG", "DsGG",
                            "MassIDGG", "GHGIDGG"]),
        "R08": _stack(r08, ["IDV", "IDEA", *SCENARIO_KEYS, "IDM", "DsM",
                            "MassIDM", "GHGIDM"]),
        "R09": _stack(r09, ["IDV", "IDEA", *SCENARIO_KEYS, "IDAP", "DsAP",
                            "EnergyPerVehicle", "GHGAssembly"]),
        "R10": _stack(r10, ["IDV", "IDEA", "DsV", "IDVPT", *SCENARIO_KEYS, "MassIDV",
                            "GHGMaterials", "GHGAssembly", "GHGCradleToGate",
                            "GHGperKg", "MassNoFactor", "ShareNoFactor"]),
        "R11": pd.DataFrame(log.to_records(),
                            columns=["Severity", "RuleID", "Message", "Context"]),
    }
    R.update(_snapshots(base, results, p09))
    R["R00"] = _metadata(base, results, log, generated_at)
    return {k: R[k] for k in sorted(R)}


def _metadata(base, results, log: Log, generated_at) -> pd.DataFrame:
    """R00 -- what this file is, and whether it may be trusted."""
    erros, avisos = len(log.of("ERRO")), len(log.of("AVISO"))
    linhas = [
        ("GeneratedAt", generated_at.strftime("%Y-%m-%d %H:%M:%S")),
        ("ProgramVersion", __version__),
        ("ParamBaseHash", base.param_hash or ""),
        ("Vehicles", len({idv for idv, _ in results})),
        ("Scenarios", len(results)),
        ("ValidationStatus", "REPROVADO" if erros else "APROVADO"),
        ("ValidationErrors", erros),
        ("ValidationWarnings", avisos),
        ("Metric", "kg CO2e, GWP-100, IPCC AR6"),
        ("Boundary", ", ".join(sorted({r["totals"]["Boundary"] for r in results.values()}))),
    ]
    return pd.DataFrame(linhas, columns=["Key", "Value"])


def _snapshots(base, results, p09) -> dict[str, pd.DataFrame]:
    """R20 to R44 -- the parameters the exported scenarios used, and no others.

    Filtering is by the keys the scenarios name. The dimension tables that
    carry no such key (the data dictionary, the material list, the group lists)
    travel whole: they are small, and cutting them would leave dangling
    descriptions.
    """
    d02 = base["D02"]
    exportados = set(results)
    cen = d02[[(int(v), int(e)) in exportados
               for v, e in zip(d02["IDV"], d02["IDEA"])]]

    idmpv = set(cen["IDMPV"])
    idvmr = set(cen["IDVMR"])
    idefv = set(cen["IDEFV"])
    idapv = set(cen["IDAPV"])
    baterias = {r["gc"].get(32) for r in results.values()}
    baterias |= {b for b in base["D03"].loc[base["D03"]["IDVP"] == 32, "GCText"].dropna()}
    baterias = {str(b).strip() for b in baterias if b not in (None, "", "-", "NA")}

    def cut(tabela, coluna=None, valores=None):
        df = base[tabela]
        if coluna is None or coluna not in df.columns:
            return df.copy()
        return df[df[coluna].isin(valores)].copy()

    snap = {
        "R20": cut("P05", "IDMPV", idmpv),
        "R21": cut("P06", "IDMPV", idmpv),
        "R22": cut("P03"),
        "R23": cut("P08"),
        "R24": cut("P04"),
        "R25": cut("P07"),
        "R26": cut("P09"),
        "R28": cut("P11", "IDEFV", idefv),
        "R29": cut("P12"),
        "R30": cut("P13"),
        "R31": cut("P14"),
        "R32": cut("P15", "IDVMR", idvmr),
        "R33": cut("P16", "IDVMR", idvmr),
        "R34": cut("P17"),
        "R35": cut("P18"),
        "R36": cut("P19", "IDBMd", baterias),
        "R37": cut("P20", "IDBMd", baterias),
        "R38": cut("P02"),
        "R39": cut("P21"),
        "R40": cut("P22", "IDAPV", idapv),
        "R41": cut("P23", "IDAPV", idapv),
        "R42": cut("P24"),
        "R43": cut("P25", "IDEFV", idefv),
        "R44": cut("P01"),
    }

    # R27 -- versoes de fatores da base e do usuario na mesma tabela, para que
    # quem recebe o arquivo veja de imediato o que veio de onde.
    p10 = base["P10"][base["P10"]["IDEFV"].isin(idefv)].copy()
    p10["IsUserDefined"] = 0
    partes = [p10]
    d04 = base.get("D04")
    if d04 is not None and len(d04):
        propria = d04[d04["IDEFV"].isin(idefv)].copy()
        if len(propria):
            propria["IsUserDefined"] = 1
            partes.append(propria)
    snap["R27"] = pd.concat(partes, ignore_index=True)

    # As versoes proprias do usuario entram em R28 junto com as da base.
    d05 = base.get("D05")
    if d05 is not None and len(d05):
        propria = d05[d05["IDEFV"].isin(idefv)].copy()
        if len(propria):
            snap["R28"] = pd.concat([snap["R28"], propria], ignore_index=True)

    return snap
