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
    PR4  resumo para o cabecalho

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import sqlite3
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


_REV_SQL = (
    "SELECT IDRV, IDCP, ReviewDate, Action, Field, SuggestedValue, FromValue, "
    "LinkedAlerts, Rationale, Caveat, Alert, Tag, Spotlight, Accepted, AcceptedDate "
    "FROM P64_ParamRevision")


def _sources(conn: sqlite3.Connection) -> dict[int, tuple]:
    out: dict[int, list] = {}
    for idrv, ref, year in conn.execute(
            "SELECT IDRV, Reference, Year FROM P65_ParamRevisionSource ORDER BY IDRV, Seq"):
        out.setdefault(idrv, []).append((ref, year))
    return {k: tuple(v) for k, v in out.items()}


def _revision(row, sources) -> Revision:
    return Revision(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8],
                    row[9], row[10], row[11], bool(row[12]), bool(row[13]), row[14],
                    sources.get(row[0], ()))


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
def panel_rows(conn: sqlite3.Connection, ida: int, profile: str,
               review: sqlite3.Connection | None = None) -> list[PanelRow]:
    """`review`: conexao de onde vem a revisao (P64, P65); por padrao, a do projeto.

    A revisao e dado de referencia: a tela a le da base de referencia, para que projetos
    criados antes da tabela existir (ou com uma revisao antiga) mostrem a revisao atual.
    """
    eff = cp.effective_values(conn, ida, profile)
    latest = latest_by_param(review or conn)
    meta = {r[0]: r for r in conn.execute(
        "SELECT IDCP, Section, Level, DsCP, utCP, MinValue, MostFrequent, MaxValue, "
        "UsedByModule FROM P30_ControlParam")}
    rows: list[PanelRow] = []
    for idcp, rev in sorted(latest.items(), key=lambda kv: kv[1].idrv):
        _, section, level, name, unit, lo, mf, hi, module = meta[idcp]
        e = eff[idcp]
        rows.append(PanelRow(idcp, section, level, name, unit, lo, mf, hi, e.value, e.text,
                             e.source, module, _note(module), rev,
                             consistency_flags(lo, mf, hi, e.value)))
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
    }
