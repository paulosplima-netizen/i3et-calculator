"""Recomposicao dos fatores de emissao da lista BR23 a partir das rotas.

Bloco B1 (T17). Sem Streamlit. Reproduz, para aco, ferro fundido e aluminio, o
que a guia 'Emission Factors BR' da planilha faz com os parametros X91 a X101
do painel:

    F   = (M.Q + N.R + O.S + P.T) . (1 - J) / (1 - I)    FE nacional recomposto
    E   = L . (1 - H) / (1 - G)                          FE global ajustado
    FE  = U . E + (1 - U) . F                            por tipo de veiculo

M a P sao os FE por rota (P61), Q a T as participacoes das rotas (P62), U a
fracao importada do tipo de veiculo (P62, linhas IMP_*), G a J as perdas (P61).

Blocos:
    RT1  avaliador de expressoes de P62 (aritmetica, X9n, [IDM:ROTA])
    RT2  participacoes e perdas dado o conjunto de parametros
    RT3  FE recomposto por material e tipo de veiculo
"""

from __future__ import annotations

import ast
import operator
import re

ROUTES = ("RECYCLED", "VIRGIN_MAIN", "VIRGIN_ALT", "GREEN")
#: tipo de veiculo -> linha de fracao importada em P62 -> lista BR23 equivalente
VEHICLE_TYPES = {"ICEV": ("IMP_ICEV", "BR23"), "ICEV_SUV": ("IMP_ICEV_SUV", "BR23_ICEV_SUV"),
                 "HEV": ("IMP_HEV", "BR23_HEV"), "PHEV": ("IMP_PHEV", "BR23_PHEV"),
                 "BEV": ("IMP_BEV", "BR23_BEV")}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv}
_TOKEN = re.compile(r"\[([^\]:]+):([A-Z_]+)\]")


# --------------------------------------------------------------------------
# BLOCO RT1 -- avaliador de expressoes
#   Aceita so numeros, + - * / e parenteses. Qualquer outra coisa e recusada.
# --------------------------------------------------------------------------
def _eval(no):
    if isinstance(no, ast.Expression):
        return _eval(no.body)
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return float(no.value)
    if isinstance(no, ast.BinOp) and type(no.op) in _OPS:
        return _OPS[type(no.op)](_eval(no.left), _eval(no.right))
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.USub, ast.UAdd)):
        v = _eval(no.operand)
        return -v if isinstance(no.op, ast.USub) else v
    raise ValueError("expressao nao permitida")


def evaluate(expr: str, values: dict[str, float]) -> float:
    """Calcula `expr` com os valores `values` (X92, ...); [IDM:ROTA] ja vem trocado."""
    texto = re.sub(r"\bX\d+\b",
                   lambda m: repr(float(values[m.group(0)])), expr)
    return _eval(ast.parse(texto, mode="eval"))


# --------------------------------------------------------------------------
# BLOCO RT2 -- participacoes
#   Le      : linhas de P62 como dicts, parametros {X91: valor}.
#   Devolve : {(IDM, rota_ou_IMP): participacao}
# --------------------------------------------------------------------------
def shares(p62: list[dict], params: dict[str, float]) -> dict[tuple[str, str], float]:
    regras = {(r["IDM"], r["Route"]): r for r in p62}
    pronto: dict[tuple[str, str], float] = {}

    def resolve(idm: str, rota: str, pilha: tuple = ()) -> float:
        chave = (idm, rota)
        if chave in pronto:
            return pronto[chave]
        if chave in pilha:
            raise ValueError(f"referencia circular em P62: {chave}")
        r = regras[chave]
        if r["ShareRule"] == "CONSTANT":
            v = float(r["ShareValue"])
        elif r["ShareRule"] == "PARAM":
            v = float(params[r["IDCP"]])
        else:
            expr = _TOKEN.sub(
                lambda m: repr(resolve(m.group(1), m.group(2), pilha + (chave,))),
                r["RuleExpr"])
            v = evaluate(expr, params)
        pronto[chave] = v
        return v

    for idm, rota in regras:
        resolve(idm, rota)
    return pronto


def check_params(params: dict[str, float]) -> list[str]:
    """I37: X91 a X101 (menos X96, o FE do aco, que nao e percentual) em [0, 1]."""
    erros = []
    for k, v in params.items():
        if re.fullmatch(r"X(9[1-57-9]|10[01])", k) and not 0 <= v <= 1:
            erros.append(f"{k} = {v} fora de [0, 1]")
    return erros


# --------------------------------------------------------------------------
# BLOCO RT3 -- fatores recompostos
#   Devolve : {IDM: {"NATIONAL": F, "ICEV": ..., "ICEV_SUV": ..., "HEV": ...,
#                    "PHEV": ..., "BEV": ...}}
#   "NATIONAL" e a lista BR23_100 (100% nacional, sem importacao).
# --------------------------------------------------------------------------
def recompose(p61: list[dict], p62: list[dict],
              params: dict[str, float]) -> dict[str, dict[str, float]]:
    erros = check_params(params)
    if erros:
        raise ValueError("; ".join(erros))
    part = shares(p62, params)
    saida: dict[str, dict[str, float]] = {}
    for idm in sorted({r["IDM"] for r in p61}):
        linhas = {r["Route"]: r for r in p61 if r["IDM"] == idm}
        ref = linhas["RECYCLED"]
        ef_rota = sum(linhas[rt]["EFRoute"] * part[(idm, rt)] for rt in ROUTES)
        perda_nac = (params[ref["LossNationalAdjIDCP"]] if ref["LossNationalAdjIDCP"]
                     else ref["LossNationalAdjusted"])
        f = ef_rota * (1 - ref["LossNationalAdopted"]) / (1 - perda_nac)
        e = ref["EFGlobal"] * (1 - ref["LossGlobalAdopted"]) / (1 - ref["LossGlobalAdjusted"])
        res = {"NATIONAL": f}
        for tipo, (imp, _lista) in VEHICLE_TYPES.items():
            u = part[(idm, imp)]
            res[tipo] = u * e + (1 - u) * f
        saida[idm] = res
    return saida


def load_tables(conn) -> tuple[list[dict], list[dict], dict[str, float]]:
    """Le P61, P62 e os valores padrao de X91 a X101 (P30) de uma conexao."""
    def linhas(sql):
        cur = conn.execute(sql)
        nomes = [d[0] for d in cur.description]
        return [dict(zip(nomes, r)) for r in cur]
    p61 = linhas("SELECT * FROM P61_BRRouteFactor")
    p62 = linhas("SELECT * FROM P62_BRRouteShare")
    params = {r[0]: r[1] for r in conn.execute(
        "SELECT IDCP, DefaultValue FROM P30_ControlParam WHERE IDCP IN "
        "('X91','X92','X93','X94','X95','X97','X98','X99','X100','X101')")}
    return p61, p62, params
