"""Formato de exibicao dos numeros (T47, B1; decisao 12 de 19/11/2026).

Sem Streamlit. Este modulo e o unico lugar que decide casas decimais, unidades,
separadores e notacao do que aparece nas telas, no relatorio HTML, no XLSX e no CSV.

Regras que protegem os resultados:

* so a exibicao muda: o calculo e os resultados congelados nunca sao arredondados;
* o CSV so arredonda se a configuracao pedir (`csv_rounded`);
* o relatorio informa o formato usado (`describe`);
* a configuracao fica no arquivo do projeto (D22), para o relatorio ser reproduzivel.

Blocos:
    FM1  configuracao (perfis, validacao, D22)
    FM2  numeros e tabelas (fmt, scale, frame)
    FM3  saidas (XLSX, CSV)
"""

from __future__ import annotations

import dataclasses
import json
import math
import sqlite3
from dataclasses import dataclass, field

import pandas as pd

# --------------------------------------------------------------------------
# BLOCO FM1 -- configuracao
# --------------------------------------------------------------------------
#: classe de grandeza -> (nome na tela de configuracao, unidade base)
CLASSES: dict[str, tuple[str, str]] = {
    "mass": ("Mass", "kg"),
    "ghg": ("GHG emissions", "kg CO₂e"),
    "share": ("Shares", ""),
    "factor": ("Emission factors", "kg CO₂e/unit"),
    "ratio": ("Ratios and coefficients", ""),
    "energy": ("Energy", "MJ"),
    "power": ("Power", "kW"),
    "distance": ("Distance", "km"),
    "money": ("Money", "R$"),
    "generic": ("Other quantities", ""),
}

_DEFAULT_DECIMALS = {"mass": 1, "ghg": 1, "share": 2, "factor": 4, "ratio": 3, "energy": 1,
                     "power": 1, "distance": 0, "money": 2, "generic": 2}
_ARTICLE_DECIMALS = {"mass": 1, "ghg": 1, "share": 1, "factor": 3, "ratio": 2, "energy": 1,
                     "power": 1, "distance": 0, "money": 0, "generic": 1}

PROFILES = ("default", "article", "audit", "custom")


@dataclass(frozen=True)
class Format:
    profile: str = "default"
    #: casas decimais por classe; None = precisao total (perfil de auditoria)
    decimals: dict = field(default_factory=lambda: dict(_DEFAULT_DECIMALS))
    mass_unit: str = "kg"            # kg | t
    ghg_unit: str = "kg"             # kg | t
    share_as: str = "percent"        # percent | fraction
    decimal_sep: str = "."           # . | ,
    thousands_sep: str = ","         # , | . | " " | ""
    csv_sep: str = ","               # , | ;
    sci_below: float = 0.0           # |x| menor que isto vai em notacao cientifica; 0 desliga
    csv_rounded: bool = False        # o CSV so arredonda se for pedido


def profile(name: str) -> Format:
    """Perfis prontos. `custom` parte do padrao."""
    if name == "article":
        return Format("article", dict(_ARTICLE_DECIMALS), sci_below=1e-3)
    if name == "audit":
        return Format("audit", {k: None for k in CLASSES}, thousands_sep="", sci_below=0.0)
    return Format(name if name in PROFILES else "default")


DEFAULT = profile("default")


def validate(f: Format) -> Format:
    """Devolve `f` se for valido; senao ValueError com o motivo."""
    if f.profile not in PROFILES:
        raise ValueError(f"perfil desconhecido: {f.profile}")
    if f.mass_unit not in ("kg", "t") or f.ghg_unit not in ("kg", "t"):
        raise ValueError("a unidade de massa e de GEE e kg ou t")
    if f.share_as not in ("percent", "fraction"):
        raise ValueError("a participacao e em percent ou fraction")
    if f.decimal_sep not in (".", ","):
        raise ValueError("o separador decimal e . ou ,")
    if f.thousands_sep not in (",", ".", " ", ""):
        raise ValueError("o separador de milhar e , . espaco ou vazio")
    if f.thousands_sep == f.decimal_sep:
        raise ValueError("os separadores decimal e de milhar nao podem ser iguais")
    if f.csv_sep not in (",", ";"):
        raise ValueError("o separador de campos do CSV e , ou ;")
    if f.csv_sep == "," and f.decimal_sep == ",":
        raise ValueError("CSV com virgula decimal exige ponto e virgula como separador de campos")
    if f.sci_below < 0:
        raise ValueError("o limite de notacao cientifica nao pode ser negativo")
    for k in CLASSES:
        d = f.decimals.get(k, _DEFAULT_DECIMALS[k])
        if d is not None and not 0 <= int(d) <= 12:
            raise ValueError(f"casas decimais de {k}: de 0 a 12")
    return f


def to_dict(f: Format) -> dict:
    return dataclasses.asdict(f)


def from_dict(d: dict) -> Format:
    base = profile(d.get("profile", "default"))
    campos = {x.name for x in dataclasses.fields(Format)}
    dados = {k: v for k, v in d.items() if k in campos}
    dec = dict(base.decimals)
    dec.update({k: (None if v is None else int(v)) for k, v in (d.get("decimals") or {}).items()
                if k in CLASSES})
    dados["decimals"] = dec
    return validate(dataclasses.replace(base, **dados))


def load(conn: sqlite3.Connection) -> tuple[Format, bool]:
    """(formato do projeto, se ha formato gravado). Sem D22 ou sem linha: o padrao."""
    try:
        row = conn.execute("SELECT SettingValue FROM D22_FormatSetting "
                           "WHERE SettingKey = 'format'").fetchone()
    except sqlite3.OperationalError:
        return DEFAULT, False
    if row is None:
        return DEFAULT, False
    try:
        return from_dict(json.loads(row[0])), True
    except (ValueError, TypeError):
        return DEFAULT, False


def save(conn: sqlite3.Connection, f: Format) -> None:
    validate(f)
    conn.execute("INSERT INTO D22_FormatSetting (SettingKey, SettingValue) VALUES ('format', ?) "
                 "ON CONFLICT (SettingKey) DO UPDATE SET SettingValue = excluded.SettingValue",
                 (json.dumps(to_dict(f), sort_keys=True),))


def describe(f: Format) -> str:
    """Uma linha para o rodape do relatorio."""
    casas = ("precisao total" if all(v is None for v in f.decimals.values()) else
             f"massa {f.decimals['mass']}, GEE {f.decimals['ghg']}, "
             f"fatores {f.decimals['factor']} casas")
    return (f"Formato: perfil {f.profile}; {casas}; massa em {f.mass_unit}, GEE em "
            f"{f.ghg_unit} CO2e; participacoes em "
            f"{'%' if f.share_as == 'percent' else 'fracao'}. "
            "Os calculos usam precisao total; so a exibicao e arredondada.")


# --------------------------------------------------------------------------
# BLOCO FM2 -- numeros e tabelas
#   scale  : converte a unidade (kg -> t; fracao -> %) sem arredondar
#   unit   : rotulo da unidade na configuracao atual
#   fmt    : texto de um numero (None ou NaN viram "—")
#   frame  : copia de uma tabela com as colunas indicadas escaladas e arredondadas
# --------------------------------------------------------------------------
def scale(value, qclass: str, f: Format = DEFAULT):
    if value is None:
        return None
    if qclass == "mass" and f.mass_unit == "t":
        return value / 1000.0
    if qclass == "ghg" and f.ghg_unit == "t":
        return value / 1000.0
    if qclass == "share" and f.share_as == "percent":
        return value * 100.0
    return value


def unit(qclass: str, f: Format = DEFAULT) -> str:
    if qclass == "mass":
        return f.mass_unit
    if qclass == "ghg":
        return f"{f.ghg_unit} CO₂e"
    if qclass == "share":
        return "%" if f.share_as == "percent" else ""
    return CLASSES.get(qclass, ("", ""))[1]


def _decimals(qclass: str, f: Format):
    return f.decimals.get(qclass, f.decimals.get("generic", 2))


def _swap(s: str, f: Format) -> str:
    """Troca os separadores de uma string no formato ingles (1,234.5)."""
    return s.replace(",", "\x00").replace(".", f.decimal_sep).replace("\x00", f.thousands_sep)


def fmt(value, qclass: str = "generic", f: Format = DEFAULT, *, with_unit: bool = False,
        convert: bool = True) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    v = scale(float(value), qclass, f) if convert else float(value)
    d = _decimals(qclass, f)
    if d is None:
        s = _swap(f"{v:.15g}", f)
    elif f.sci_below and v != 0 and abs(v) < f.sci_below:
        s = _swap(f"{v:.{d}e}", f)
    else:
        s = _swap(f"{v:,.{d}f}", f)
    u = unit(qclass, f)
    return f"{s} {u}".strip() if with_unit and u else s


def frame(df: pd.DataFrame, columns: dict[str, str], f: Format = DEFAULT, *,
          rename: bool = False) -> pd.DataFrame:
    """Copia de `df` com as colunas de `columns` ({coluna: classe}) na unidade e nas casas
    do formato. Com `rename`, o nome da coluna ganha a unidade entre parenteses."""
    out = df.copy()
    novos = {}
    for col, qclass in columns.items():
        if col not in out.columns:
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce") * _factor(qclass, f)
        d = _decimals(qclass, f)
        if d is not None:
            out[col] = out[col].round(d)
        u = unit(qclass, f)
        if rename and u:
            novos[col] = f"{col} ({u})"
    return out.rename(columns=novos)


def _factor(qclass: str, f: Format) -> float:
    return scale(1.0, qclass, f)


def column_class(name) -> str | None:
    """Classe de grandeza de uma coluna de resultado pelo nome; None se nao se sabe."""
    n = str(name)
    low = n.lower()
    if "per" in low and low.startswith("ghg"):
        return "ratio"
    if low.startswith("mass") or low.endswith("masskg"):
        return "mass"
    if low.startswith("ghg"):
        return "ghg"
    if "share" in low or low.startswith(("mshare", "bmshare")):
        return "share"
    if low in ("ef", "eflow", "efhigh", "neweef", "originalef"):
        return "factor"
    return None


_UNIT_CLASS = {"kg": "mass", "kg CO2e/v": "ghg", "kg CO2e/kg of v": "ratio", "kW": "power",
               "m": "distance_m"}


def indicator(value, ut, f: Format = DEFAULT) -> tuple[str, str]:
    """Texto e unidade de um indicador de saida (R45/R46), pela unidade da planilha.

    Massa e GHG por veiculo seguem a unidade (kg/t) e as casas do formato; potencia e razao
    seguem as casas; o resto usa as casas genericas. Sem valor, devolve ("", unidade).
    """
    ut = "" if ut is None else str(ut)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "", ut
    qclass = _UNIT_CLASS.get(ut, "generic")
    if qclass == "distance_m":
        qclass = "generic"
    text = fmt(value, qclass, f)
    if qclass == "mass":
        return text, unit("mass", f)
    if qclass == "ghg":
        return text, f"{f.ghg_unit} CO₂e/v"
    return text, ut


def header(name, qclass: str | None, f: Format = DEFAULT) -> str:
    """Nome da coluna com a unidade, quando o formato muda a unidade guardada."""
    changed = (qclass == "mass" and f.mass_unit == "t") or (qclass == "ghg" and f.ghg_unit == "t") \
        or (qclass == "share" and f.share_as == "percent")
    return f"{name} [{unit(qclass, f)}]" if changed and qclass else str(name)


def round_only(df: pd.DataFrame, f: Format = DEFAULT) -> pd.DataFrame:
    """Arredonda as colunas reconhecidas nas casas do formato, na unidade guardada (CSV)."""
    out = df.copy()
    for col in out.columns:
        qclass = column_class(col)
        d = _decimals(qclass, f) if qclass else None
        if qclass and d is not None and pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].round(d)
    return out


def column_format(qclass: str, f: Format = DEFAULT) -> dict:
    """Opcoes para `st.column_config.NumberColumn(**column_format(...))`."""
    d = _decimals(qclass, f)
    return {"format": "%.10g" if d is None else f"%.{d}f"}


# --------------------------------------------------------------------------
# BLOCO FM3 -- saidas
#   excel_number_format : codigo de formato de celula. O valor guardado continua em
#       kg e em fracao: o formato mostra t com a virgula final do Excel (divide por
#       mil) e % com o sinal de porcento.
#   csv_text            : texto CSV na convencao escolhida; arredonda so se pedido.
# --------------------------------------------------------------------------
def excel_number_format(qclass: str, f: Format = DEFAULT) -> str:
    d = _decimals(qclass, f)
    casas = 6 if d is None else d
    corpo = "0" if f.thousands_sep == "" else "#,##0"
    if casas:
        corpo += "." + "0" * casas
    if qclass == "share" and f.share_as == "percent":
        return corpo.replace("#,##0", "0") + "%"
    if f.sci_below and qclass in ("factor", "ratio"):
        return "0." + "0" * casas + "E+00" if casas else "0E+00"
    if (qclass == "mass" and f.mass_unit == "t") or (qclass == "ghg" and f.ghg_unit == "t"):
        return corpo + ","
    return corpo


def csv_text(df: pd.DataFrame, columns: dict[str, str] | None = None, f: Format = DEFAULT) -> str:
    out = df
    if f.csv_rounded and columns:
        out = frame(df, columns, f)
    return out.to_csv(index=False, sep=f.csv_sep, decimal=f.decimal_sep)
