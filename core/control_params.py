"""Catalogo de parametros do painel de controle: valor efetivo (Fase A, passo 4).

P30 e o catalogo (205 parametros, imutavel); D08 guarda so o que o usuario
alterou, por analise. Os tres perfis (Basic, Expert, Expanded) sao interligados
(decisao de 21/11/2026): alterar um parametro grava o mesmo valor nos tres, e
restaurar apaga nos tres. O valor efetivo e:

    1. o valor de D08 para o perfil ativo, se existir;
    2. senao, P30.DefaultValue (ou DefaultText), igual nos tres perfis.
       P30.BasicValue fica gravado como na planilha e nao e usado
       (decisao de 17/11/2026).

Valor fora da faixa gera aviso e nunca bloqueia. Parametro calculado nao
aceita valor do usuario (regra I20).

Blocos:
    CT1  valor efetivo
    CT2  faixa
    CT3  alterar e restaurar

Este modulo nao importa streamlit.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

PROFILES = ("Basic", "Expert", "Expanded")

#: Parametros que a T03 define (modo, combustivel, norma, curva, lista de fatores): nao se
#: editam como valor de usuario na T04 nem na T48.
CONFIG_LINKED = {"Fuel considered in Graphs", "Test Cycle", "Daily Distance CDF",
                 "Emission Factors List"}


@dataclass(frozen=True)
class Effective:
    idcp: str
    value: float | None
    text: str | None
    source: str            # 'Default' ou 'User'
    out_of_range: bool


def _check_profile(profile: str) -> None:
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile!r}")


# --------------------------------------------------------------------------
# BLOCO CT2 -- faixa
#   Devolve : True quando o valor esta fora de [Min, Max]. Faixa invertida ou
#             ausente (ha tres no catalogo) nunca acusa: o valor e gravado
#             como esta e o relatorio de divergencias lista a faixa.
# --------------------------------------------------------------------------
def is_out_of_range(value: float | None, lo: float | None, hi: float | None) -> bool:
    if value is None or lo is None or hi is None or lo > hi:
        return False
    return value < lo or value > hi


# --------------------------------------------------------------------------
# BLOCO CT1 -- valor efetivo
#   Le      : P30 e D08 (analise e perfil).
#   Devolve : {IDCP: Effective} para os 205 parametros.
# --------------------------------------------------------------------------
def effective_values(conn: sqlite3.Connection, ida: int, profile: str) -> dict[str, Effective]:
    _check_profile(profile)
    user = {idcp: (v, t) for idcp, v, t in conn.execute(
        "SELECT IDCP, Value, ValueText FROM D08_ControlParamValue "
        "WHERE IDA = ? AND Profile = ?", (ida, profile))}
    out: dict[str, Effective] = {}
    for idcp, dv, dt, lo, hi in conn.execute(
            "SELECT IDCP, DefaultValue, DefaultText, MinValue, MaxValue FROM P30_ControlParam"):
        if idcp in user:
            v, t = user[idcp]
            out[idcp] = Effective(idcp, v, t, "User", is_out_of_range(v, lo, hi))
        else:
            out[idcp] = Effective(idcp, dv, dt, "Default", is_out_of_range(dv, lo, hi))
    return out


# --------------------------------------------------------------------------
# BLOCO CT3 -- alterar e restaurar
#   set_value grava ou substitui a linha de D08; restore a apaga.
#   Parametro calculado e recusado (I20); a origem do valor e obrigatoria (I27).
# --------------------------------------------------------------------------
def set_value(conn: sqlite3.Connection, ida: int, idcp: str, profile: str, *,
              value: float | None = None, text: str | None = None, source: str) -> bool:
    """Grava a alteracao nos tres perfis (interligados). Devolve True quando o valor
    ficou fora da faixa (aviso). `profile` e o perfil de onde veio a edicao."""
    _check_profile(profile)
    if not source or not source.strip():
        raise ValueError("ValueSource must not be empty")
    if (value is None) == (text is None):
        raise ValueError("exactly one of value and text must be given")
    row = conn.execute("SELECT IsCalculated, MinValue, MaxValue FROM P30_ControlParam "
                       "WHERE IDCP = ?", (idcp,)).fetchone()
    if row is None:
        raise KeyError(f"unknown parameter: {idcp}")
    if row[0]:
        raise ValueError(f"{idcp} is calculated and takes no user value")
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for perfil in PROFILES:
        conn.execute(
            "INSERT OR REPLACE INTO D08_ControlParamValue "
            "(IDA, IDCP, Profile, Value, ValueText, ValueSource, UpdatedAt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ida, idcp, perfil, value, text, source.strip(), agora))
    return is_out_of_range(value, row[1], row[2])


def restore(conn: sqlite3.Connection, ida: int, idcp: str, profile: str) -> bool:
    """Apaga a alteracao (Restore default) nos tres perfis. Devolve True se havia linha."""
    _check_profile(profile)
    cur = conn.execute("DELETE FROM D08_ControlParamValue WHERE IDA = ? AND IDCP = ?",
                       (ida, idcp))
    return cur.rowcount > 0


@dataclass(frozen=True)
class EditPreview:
    """O que uma alteracao faria, para mostrar antes de confirmar."""
    idcp: str
    name: str
    unit: str | None
    ida: int
    profile: str
    current_value: float | None
    current_text: str | None
    current_source: str            # 'Default' ou 'User'
    catalog_value: float | None
    catalog_text: str | None
    new_value: float | None
    new_text: str | None
    lo: float | None
    hi: float | None
    out_of_range: bool
    changed: bool
    profiles: tuple[str, ...]


def edit_preview(conn: sqlite3.Connection, ida: int, idcp: str, profile: str, *,
                 value: float | None = None, text: str | None = None) -> EditPreview:
    """Compara o valor efetivo da analise com o novo valor, sem gravar."""
    _check_profile(profile)
    row = conn.execute("SELECT DsCP, utCP, DefaultValue, DefaultText, MinValue, MaxValue "
                       "FROM P30_ControlParam WHERE IDCP = ?", (idcp,)).fetchone()
    if row is None:
        raise KeyError(f"unknown parameter: {idcp}")
    cur = effective_values(conn, ida, profile)[idcp]
    changed = (value is not None and (cur.value is None or abs(value - cur.value) > 1e-12)) \
        or (text is not None and text != cur.text)
    return EditPreview(idcp, row[0], row[1], ida, profile, cur.value, cur.text, cur.source,
                       row[2], row[3], value, text, row[4], row[5],
                       is_out_of_range(value, row[4], row[5]), bool(changed), PROFILES)


def restore_all(conn: sqlite3.Connection, ida: int) -> int:
    """Apaga todas as alteracoes da analise (os tres perfis). Devolve quantos parametros
    voltaram ao valor da planilha."""
    cur = conn.execute("SELECT COUNT(DISTINCT IDCP) FROM D08_ControlParamValue WHERE IDA = ?",
                       (ida,))
    n = cur.fetchone()[0]
    conn.execute("DELETE FROM D08_ControlParamValue WHERE IDA = ?", (ida,))
    return n


def restore_profile(conn: sqlite3.Connection, ida: int, profile: str) -> int:
    """Compatibilidade: com os perfis interligados, equivale a `restore_all`."""
    _check_profile(profile)
    return restore_all(conn, ida)
