"""Catalogo de parametros do painel de controle: valor efetivo (Fase A, passo 4).

P30 e o catalogo (205 parametros, imutavel); D08 guarda so o que o usuario
alterou, por analise e perfil. O valor efetivo e:

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
    """Grava a alteracao. Devolve True quando o valor ficou fora da faixa (aviso)."""
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
    conn.execute(
        "INSERT OR REPLACE INTO D08_ControlParamValue "
        "(IDA, IDCP, Profile, Value, ValueText, ValueSource, UpdatedAt) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (ida, idcp, profile, value, text, source.strip(),
         datetime.now(timezone.utc).isoformat(timespec="seconds")))
    return is_out_of_range(value, row[1], row[2])


def restore(conn: sqlite3.Connection, ida: int, idcp: str, profile: str) -> bool:
    """Apaga a alteracao (Restore default). Devolve True se havia linha."""
    _check_profile(profile)
    cur = conn.execute("DELETE FROM D08_ControlParamValue "
                       "WHERE IDA = ? AND IDCP = ? AND Profile = ?", (ida, idcp, profile))
    return cur.rowcount > 0


def restore_profile(conn: sqlite3.Connection, ida: int, profile: str) -> int:
    """Apaga todas as alteracoes de um perfil da analise. Devolve quantas linhas saíram."""
    _check_profile(profile)
    cur = conn.execute("DELETE FROM D08_ControlParamValue WHERE IDA = ? AND Profile = ?",
                       (ida, profile))
    return cur.rowcount
