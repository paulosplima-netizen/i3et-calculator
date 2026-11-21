"""Painel de parametros: revisoes, fontes e linhas do painel (consulta apenas).

O painel mostra os parametros do bloco Expert com a faixa, o valor efetivo, a
recomendacao da revisao periodica, as fontes e os alertas. Valores e faixas vem
sempre de P30 (e D08, pelo valor efetivo); P64 e P65 trazem so o conteudo
editorial. Nada aqui grava em P30 nem em D08, e nenhum valor sugerido entra no
calculo (a planilha prevalece).

Blocos:
    PR1  revisao vigente e historico (P64, P65)
    PR2  alertas de consistencia, recalculados a partir de P30
    PR3  linhas do painel
    PR4  resumo para o cabecalho (KPIs)
    PR5  alertas de novos desenvolvimentos e notas (P66, P67, P68)
    PR6  formatacao de numeros por familia de unidade
    PR7  busca
    PR8  aceite da sugestao de regua pelo usuario master (P69)

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import hmac
import math
import sqlite3
from datetime import datetime
from dataclasses import dataclass

from core import control_params as cp

#: Modulos do i3ET ja implementados no aplicativo (P30.UsedByModule). Os demais
#: guardam o valor, mas ele so e usado quando o modulo entrar.
IMPLEMENTED_MODULES = ("M1M2", "UI")

BLOCKS = ("UPP", "PET", "LMP", "FEF", "MEF", "AUC", "LWP")
ACTIONS = ("keep", "adjust", "verify")
FIELD_LABEL = {"min": "minimum", "mf": "most frequent", "max": "maximum"}

ALERT_INVERTED = "inverted range (min > max)"
ALERT_TYPICAL = "most frequent value outside the min-max range"
ALERT_ADOPTED = "adopted value outside the min-max range"


@dataclass(frozen=True)
class Revision:
    idrv: int
    idcp: str
    review_date: str
    action: str
    field: str | None
    suggested: float | None
    from_value: float | None
    linked_alerts: int | None
    rationale: str
    caveat: str | None
    alert_text: str | None
    tag: str | None
    spotlight: bool
    accepted: bool
    accepted_date: str | None
    sources: tuple[tuple[str, str | None], ...]
    panel_no: int = 0
    baseline_date: str | None = None
    baseline_min: float | None = None
    baseline_mf: float | None = None
    baseline_max: float | None = None
    baseline_value: float | None = None
    baseline_text: str | None = None


@dataclass(frozen=True)
class Alert:
    idal: int
    review_date: str
    severity: str
    title: str
    context: str | None
    reported: str | None
    adopted: str | None
    body: str | None
    url: str | None
    params: tuple[str, ...]          # IDCP afetados
    panel_nos: tuple[int, ...]       # numeros (#) no painel


@dataclass(frozen=True)
class PanelRow:
    idcp: str
    section: str
    level: str
    name: str
    unit: str | None
    lo: float | None
    mf: float | None
    hi: float | None
    value: float | None
    text: str | None
    source: str                 # 'Default' ou 'User'
    module: str | None
    note: str | None            # "Recorded — not used until M4" ou None
    revision: Revision
    flags: tuple[str, ...]
    default: float | None = None   # valor do catalogo (planilha)
    # Sugestao aceita pelo master: (campo, valor da planilha, valor aceito, data, quem).
    # Nesse caso lo/mf/hi ja trazem o valor aceito no campo.
    accepted_range: tuple | None = None


_REV_SQL = (
    "SELECT IDRV, IDCP, ReviewDate, Action, Field, SuggestedValue, FromValue, "
    "LinkedAlerts, Rationale, Caveat, Alert, Tag, Spotlight, Accepted, AcceptedDate, "
    "PanelNo, BaselineDate, BaselineMin, BaselineMf, BaselineMax, BaselineValue, "
    "BaselineText FROM P64_ParamRevision")


def _sources(conn: sqlite3.Connection) -> dict[int, tuple]:
    out: dict[int, list] = {}
    for idrv, ref, year in conn.execute(
            "SELECT IDRV, Reference, Year FROM P65_ParamRevisionSource ORDER BY IDRV, Seq"):
        out.setdefault(idrv, []).append((ref, year))
    return {k: tuple(v) for k, v in out.items()}


def _revision(row, sources) -> Revision:
    return Revision(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                    row[9], row[10], row[11], bool(row[12]), bool(row[13]), row[14],
                    sources.get(row[0], ()), row[15], row[16], row[17], row[18], row[19],
                    row[20], row[21])


# --------------------------------------------------------------------------
# BLOCO PR1 -- revisao vigente e historico
#   Le      : P64 e P65.
#   Devolve : latest_by_param -> {IDCP: Revision} com a de maior ReviewDate;
#             history -> todas as revisoes do parametro, da mais recente a mais antiga.
# --------------------------------------------------------------------------
def latest_by_param(conn: sqlite3.Connection) -> dict[str, Revision]:
    sources = _sources(conn)
    out: dict[str, Revision] = {}
    for row in conn.execute(_REV_SQL + " ORDER BY IDCP, ReviewDate, IDRV"):
        out[row[1]] = _revision(row, sources)      # a ultima de cada IDCP prevalece
    return out


def history(conn: sqlite3.Connection, idcp: str) -> list[Revision]:
    sources = _sources(conn)
    rows = conn.execute(_REV_SQL + " WHERE IDCP = ? ORDER BY ReviewDate DESC, IDRV DESC",
                        (idcp,)).fetchall()
    return [_revision(r, sources) for r in rows]


# --------------------------------------------------------------------------
# BLOCO PR2 -- alertas de consistencia
#   Recalcula a partir da faixa de P30 e do valor efetivo, sem depender do texto
#   do arquivo de revisao. Faixa ausente nunca acusa.
# --------------------------------------------------------------------------
def consistency_flags(lo: float | None, mf: float | None, hi: float | None,
                      value: float | None) -> tuple[str, ...]:
    flags: list[str] = []
    if lo is None or hi is None:
        return ()
    inverted = lo > hi
    a, b = min(lo, hi), max(lo, hi)
    if inverted:
        flags.append(ALERT_INVERTED)
    if mf is not None and not a <= mf <= b:
        flags.append(ALERT_TYPICAL)
    if value is not None and not a <= value <= b:
        flags.append(ALERT_ADOPTED)
    return tuple(flags)


def _note(module: str | None) -> str | None:
    if module is None or module in IMPLEMENTED_MODULES:
        return None
    return f"Recorded — not used until {module}"


# --------------------------------------------------------------------------
# BLOCO PR3 -- linhas do painel
#   Le      : P30, valor efetivo (D08 da analise e do perfil) e a revisao vigente.
#   Devolve : uma PanelRow por parametro revisado, na ordem do arquivo de revisao.
# --------------------------------------------------------------------------
def user_overrides(project: sqlite3.Connection, ida: int,
                   profile: str) -> dict[str, tuple[float | None, str | None]]:
    """Valores que o usuario alterou na analise (D08), por parametro. So leitura."""
    return {idcp: (v, t) for idcp, v, t in project.execute(
        "SELECT IDCP, Value, ValueText FROM D08_ControlParamValue "
        "WHERE IDA = ? AND Profile = ?", (ida, profile))}


def panel_rows(conn: sqlite3.Connection, ida: int | None = None, profile: str | None = None,
               review: sqlite3.Connection | None = None,
               overrides: dict[str, tuple[float | None, str | None]] | None = None
               ) -> list[PanelRow]:
    """Linhas do painel.

    Sem `ida` nem `overrides`, o valor mostrado e o adotado no catalogo (P30.DefaultValue):
    a consulta independente de projeto. `overrides` (de `user_overrides`) poe por cima os
    valores que o usuario alterou no projeto aberto; faixas, recomendacao e fontes seguem
    sendo as da base de referencia. Com `ida` e `profile`, o valor e o efetivo da analise
    em `conn` (D08). `review`: conexao de onde vem a revisao (P64 a P68); por padrao, a de
    `conn`.
    """
    base = {idcp: cp.Effective(idcp, dv, dt, "Default", cp.is_out_of_range(dv, lo, hi))
            for idcp, dv, dt, lo, hi in conn.execute(
                "SELECT IDCP, DefaultValue, DefaultText, MinValue, MaxValue "
                "FROM P30_ControlParam")}
    if ida is not None:
        eff = cp.effective_values(conn, ida, profile)
    else:
        eff = dict(base)
        for idcp, (v, t) in (overrides or {}).items():
            if idcp in eff:
                eff[idcp] = cp.Effective(idcp, v, t, "User", False)
    latest = latest_by_param(review or conn)
    acc = accepted_ranges(review or conn)
    meta = {r[0]: r for r in conn.execute(
        "SELECT IDCP, Section, Level, DsCP, utCP, MinValue, MostFrequent, MaxValue, "
        "UsedByModule FROM P30_ControlParam")}
    rows: list[PanelRow] = []
    for idcp, rev in sorted(latest.items(), key=lambda kv: (kv[1].panel_no, kv[1].idrv)):
        _, section, level, name, unit, lo, mf, hi, module = meta[idcp]
        e = eff[idcp]
        accepted = None
        a = acc.get(idcp)
        if a and a[0] == rev.idrv:
            _, campo, valor, quando, quem = a
            original = {"min": lo, "mf": mf, "max": hi}[campo]
            accepted = (campo, original, valor, quando, quem)
            lo, mf, hi = (valor if campo == "min" else lo, valor if campo == "mf" else mf,
                          valor if campo == "max" else hi)
        rows.append(PanelRow(idcp, section, level, name, unit, lo, mf, hi, e.value, e.text,
                             e.source, module, _note(module), rev,
                             consistency_flags(lo, mf, hi, e.value), base[idcp].value,
                             accepted))
    return rows


# --------------------------------------------------------------------------
# BLOCO PR4 -- resumo
# --------------------------------------------------------------------------
def summary(rows: list[PanelRow]) -> dict:
    dates = sorted({r.revision.review_date for r in rows})
    return {
        "total": len(rows),
        "by_action": {a: sum(1 for r in rows if r.revision.action == a) for a in ACTIONS},
        "spotlight": sum(1 for r in rows if r.revision.spotlight),
        "accepted": sum(1 for r in rows if r.revision.accepted),
        "alerts": sum(1 for r in rows if r.flags),
        "review_date": dates[-1] if dates else None,
        "battery": sum(1 for r in rows if r.revision.tag == "bat"),
        "ice": sum(1 for r in rows if r.revision.tag == "ice"),
        "sources": len({ref for r in rows for ref, _ in r.revision.sources}),
        "adjustments": (sum(1 for r in rows if r.revision.action in ("adjust", "verify"))),
    }


# --------------------------------------------------------------------------
# BLOCO PR5 -- alertas de novos desenvolvimentos e notas
#   Le      : P66, P67 (alertas e parametros afetados), P68 (notas e historico).
#   Devolve : lista de Alert (mais graves primeiro) e textos de notas/historico.
# --------------------------------------------------------------------------
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def alerts(conn: sqlite3.Connection) -> list[Alert]:
    nos = dict(conn.execute("SELECT IDCP, PanelNo FROM P64_ParamRevision"))
    par: dict[int, list[str]] = {}
    for idal, idcp in conn.execute(
            "SELECT IDAL, IDCP FROM P67_ParamAlertParam ORDER BY IDAL, IDCP"):
        par.setdefault(idal, []).append(idcp)
    out = []
    for r in conn.execute("SELECT IDAL, ReviewDate, Severity, Title, Context, Reported, Adopted, "
                          "Body, Url FROM P66_ParamAlert ORDER BY IDAL"):
        ids = tuple(par.get(r[0], ()))
        out.append(Alert(*r, params=ids,
                         panel_nos=tuple(sorted(nos[i] for i in ids if i in nos))))
    return sorted(out, key=lambda a: (_SEVERITY_ORDER.get(a.severity, 9), a.idal))


def review_texts(conn: sqlite3.Connection, kind: str) -> list[tuple[str, str]]:
    """Textos de P68 (kind 'note' ou 'history'): [(data, texto)], mais recentes primeiro."""
    return [(d, b) for d, b in conn.execute(
        "SELECT ReviewDate, Body FROM P68_ParamReviewNote WHERE Kind = ? "
        "ORDER BY ReviewDate DESC, Seq", (kind,))]


# --------------------------------------------------------------------------
# BLOCO PR6 -- formatacao de numeros por familia de unidade
#   Mesma regra do artefato: unidade com '%' mostra o valor x100 com 1 decimal;
#   as demais familias (mesma unidade) usam as mesmas casas decimais, definidas pela
#   menor amplitude (max-min) nao nula da familia; sem faixas, pelo maximo de casas
#   necessarias, limitado a 2.
# --------------------------------------------------------------------------
def is_pct(unit: str | None) -> bool:
    return bool(unit) and "%" in unit


def _needed_decimals(v: float) -> int:
    for d in range(7):
        if abs(v - round(v, d)) < 1e-9 * max(1.0, abs(v)):
            return d
    return 6


def family_decimals(rows: list[PanelRow]) -> dict[str, int]:
    fam: dict[str, list[PanelRow]] = {}
    for r in rows:
        fam.setdefault(r.unit or "(no unit)", []).append(r)
    out: dict[str, int] = {}
    for unit, grupo in fam.items():
        if is_pct(unit):
            out[unit] = 1
            continue
        amp = [abs(r.hi - r.lo) for r in grupo
               if r.lo is not None and r.hi is not None and abs(r.hi - r.lo) > 0]
        if amp:
            out[unit] = min(3, max(0, math.ceil(-math.log10(min(amp))) + 2))
        else:
            vals = [v for r in grupo for v in (r.value, r.lo, r.mf, r.hi) if v is not None]
            out[unit] = min(2, max((_needed_decimals(v) for v in vals), default=0))
    return out


def fmt(v: float | None, unit: str | None, decimals: dict[str, int]) -> str:
    """Numero formatado (en-US); '—' quando ausente."""
    if v is None:
        return "—"
    if is_pct(unit):
        return f"{v * 100:,.1f}%"
    return f"{v:,.{decimals.get(unit or '(no unit)', 2)}f}"


# --------------------------------------------------------------------------
# BLOCO PR7 -- busca
#   Procura o termo (todas as palavras) no numero (#), id, nome, unidade, bloco
#   (sigla e nome) e referencias das fontes.
# --------------------------------------------------------------------------
BLOCK_NAMES = {
    "UPP": "Usage Preferences Profile", "PET": "Powertrain Efficiencies Technology",
    "LMP": "Lifespan and Maintenance Profile", "FEF": "Fuel Emission Factors",
    "MEF": "Materials Emission Factors", "AUC": "Automotive Unitary Costs",
    "LWP": "Lightweighting Parameters"}


def matches(row: PanelRow, term: str) -> bool:
    palavras = term.casefold().split()
    if not palavras:
        return True
    texto = " ".join([
        row.idcp, row.name, row.unit or "", row.section,
        BLOCK_NAMES.get(row.section, ""),
        " ".join(ref for ref, _ in row.revision.sources)]).casefold()
    for p in palavras:
        if p.startswith("#") and p[1:].isdigit():
            if int(p[1:]) != row.revision.panel_no:
                return False
        elif p not in texto and p != str(row.revision.panel_no):
            return False
    return True


# --------------------------------------------------------------------------
# BLOCO PR8 -- aceite da sugestao de regua (somente usuario master)
#   Aceitar muda so a regua (minimo, mais frequente ou maximo) mostrada no painel, para
#   o campo e o valor da sugestao da revisao vigente. Nunca altera o valor adotado, P30
#   nem o calculo. Desfazer apaga a linha de P69. As conexoes recebidas precisam ser de
#   escrita; o painel as abre so quando o master age.
# --------------------------------------------------------------------------
def accepted_ranges(conn: sqlite3.Connection) -> dict[str, tuple]:
    """{IDCP: (IDRV, campo, valor, data, quem)}; vazio se a tabela nao existe."""
    try:
        return {idcp: (idrv, campo, valor, quando, quem) for idrv, idcp, campo, valor, quando,
                quem in conn.execute("SELECT IDRV, IDCP, Field, Value, AcceptedAt, AcceptedBy "
                                     "FROM P69_ParamRangeAccept")}
    except sqlite3.OperationalError:
        return {}


def can_accept(row: PanelRow) -> bool:
    """Ha sugestao com campo e valor, ainda nao incorporada nem aceita."""
    rev = row.revision
    return (rev.field is not None and rev.suggested is not None and not rev.accepted
            and row.accepted_range is None)


def accept_range(conn: sqlite3.Connection, idcp: str, by: str) -> None:
    rev = latest_by_param(conn).get(idcp)
    if rev is None or rev.field is None or rev.suggested is None:
        raise ValueError("this parameter has no suggested value to accept")
    if rev.accepted:
        raise ValueError("this suggestion is already incorporated in the workbook")
    conn.execute("INSERT OR REPLACE INTO P69_ParamRangeAccept "
                 "(IDRV, IDCP, Field, Value, AcceptedAt, AcceptedBy) VALUES (?,?,?,?,?,?)",
                 (rev.idrv, idcp, rev.field, rev.suggested,
                  datetime.now().isoformat(timespec="seconds"), by or "master"))
    conn.commit()


def revoke_range(conn: sqlite3.Connection, idcp: str) -> None:
    conn.execute("DELETE FROM P69_ParamRangeAccept WHERE IDCP = ?", (idcp,))
    conn.commit()


def verify_master(candidate: str | None, expected: str | None) -> bool:
    """Compara a senha informada com a configurada (tempo constante). Sem senha
    configurada, ninguem e master."""
    if not expected or not candidate:
        return False
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))
