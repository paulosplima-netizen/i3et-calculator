"""Dados de mercado do B2: leitura das tabelas de origem, correspondencia com o catalogo e a
referencia ponderada (C33).

Sem Streamlit. Nada aqui grava na base: as funcoes leem e devolvem estruturas; quem grava e
a ferramenta de importacao ou a tela do master (decisao do autor pendente, docs/11).

Blocos:
    MD1  normalizacao de nomes e chaves
    MD2  informativo da FENABRAVE (texto) -> linhas de licenciamento
    MD3  tabela do PBEV (linhas extraidas do PDF) -> registros e campos
    MD4  correspondencia dos licenciamentos com o catalogo (P26)
    MD5  referencia ponderada por segmento (C33)
    MD6  cobertura contra o total da ANFAVEA (P60)
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# BLOCO MD1 -- nomes e chaves
#   A planilha e os informativos grafam marca e modelo de formas diferentes
#   (M.BENZ, RAM/3500.0, FORD/F-150). A chave de cruzamento e maiuscula, sem
#   acento, com espacos colapsados; os apelidos abaixo cobrem o que a comparacao
#   de 21/11/2026 encontrou.
# --------------------------------------------------------------------------
BRAND_ALIASES = {
    "M.BENZ": "MERCEDES-BENZ", "MERCEDES BENZ": "MERCEDES-BENZ", "GM": "GM",
    "VW TRUCK E BUS": "VW", "VOLKSWAGEN": "VW", "CHEVROLET": "GM",
}
MODEL_ALIASES = {
    "F-150": "F150", "T-LUX": "TLUX", "AUMARK S 315": "AUMARK S315",
}


def norm(texto) -> str:
    """Maiuscula, sem acento, sem '.0' final de numero lido como real, espacos colapsados."""
    if texto is None:
        return ""
    t = unicodedata.normalize("NFKD", str(texto))
    t = "".join(c for c in t if not unicodedata.combining(c)).upper().strip()
    t = re.sub(r"(?<=\d)\.0$", "", t)
    return re.sub(r"\s+", " ", t)


def split_make_model(texto: str) -> tuple[str, str]:
    """'VW/POLO' -> ('VW', 'POLO'). Sem barra, a marca fica vazia."""
    marca, _, modelo = str(texto).partition("/")
    if not modelo:
        return "", norm(marca)
    return norm(marca), norm(modelo)


def match_key(marca: str, modelo: str) -> str:
    """Chave padronizada: marca/modelo, com os apelidos aplicados."""
    m = BRAND_ALIASES.get(norm(marca), norm(marca))
    mo = MODEL_ALIASES.get(norm(modelo), norm(modelo))
    return f"{m}/{mo}"


def fuel_group(combustivel: str | None) -> str:
    """Grupo de combustivel dos segmentos de P70: EG (etanol/gasolina), D (diesel), X (demais)."""
    return {"FLEX": "EG", "GASOLINE": "EG", "DIESEL": "D"}.get(norm(combustivel), "X")


# --------------------------------------------------------------------------
# BLOCO MD2 -- informativo da FENABRAVE
#   Le      : o texto do informativo (pdftotext -layout ou pdfplumber layout=True).
#   Devolve : uma lista de SalesSection, uma por quadro "Ranking dos
#             emplacamentos ...", com as duas colunas (automoveis, comerciais leves).
# --------------------------------------------------------------------------
@dataclass
class SalesRow:
    sales_class: str        # 'V' automovel, 'CL' comercial leve
    ranking: int
    brand: str
    model: str
    units: int

    @property
    def key(self) -> str:
        return match_key(self.brand, self.model)


@dataclass
class SalesSection:
    kind: str               # 'YTD' (acumulado), 'Month'
    period_end: str         # 'AAAA-MM'
    title: str
    rows: list[SalesRow] = field(default_factory=list)


_MONTHS = {m: i for i, m in enumerate(
    ["JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO",
     "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"], start=1)}
_HEADER = re.compile(r"Ranking dos emplacamentos\s+(acumulados at[eé]|em)\s+(\w+)/(\d{4})", re.I)
_ROW = re.compile(r"(\d{1,3})º\s+(.+?)\s{2,}(\d{1,3}(?:\.\d{3})*)(?=\s{2,}|\s*$)")
#: Colunas do quadro: o texto tem duas colunas lado a lado. A primeira ocorrencia de
#: cada linha e de automoveis, a segunda de comerciais leves.
_CLASSES = ("V", "CL")


def parse_fenabrave_text(texto: str) -> list[SalesSection]:
    """Quadros 'Ranking dos emplacamentos ...' do informativo. Linhas sem ranking sao ignoradas."""
    secoes: list[SalesSection] = []
    atual: SalesSection | None = None
    for linha in texto.splitlines():
        h = _HEADER.search(linha)
        if h:
            mes = _MONTHS.get(norm(h.group(2)))
            if mes is None:
                atual = None
                continue
            atual = SalesSection(
                kind="YTD" if h.group(1).lower().startswith("acumulados") else "Month",
                period_end=f"{h.group(3)}-{mes:02d}", title=linha.strip())
            secoes.append(atual)
            continue
        if atual is None:
            continue
        achados = _ROW.findall(linha)
        if not achados and atual.rows and "Ranking" in linha:
            atual = None
            continue
        for i, (rank, nome, un) in enumerate(achados[:2]):
            marca, modelo = split_make_model(nome)
            atual.rows.append(SalesRow(_CLASSES[i], int(rank), marca, modelo,
                                       int(un.replace(".", ""))))
    return [s for s in secoes if s.rows]


def adopted_section(secoes: list[SalesSection]) -> SalesSection | None:
    """Quadro padrao: o acumulado mais recente (decisao 12 do doc de decisoes, pendente)."""
    ytd = [s for s in secoes if s.kind == "YTD"]
    return max(ytd, key=lambda s: s.period_end) if ytd else None


# --------------------------------------------------------------------------
# BLOCO MD3 -- tabela do PBEV
#   Le      : linhas da tabela do PDF (pdfplumber extract_tables), na ordem das
#             colunas da edicao: categoria, marca, modelo, versao, motor, ...
#   Devolve : registros (marca, modelo, versao, campos) como em P28/P55.
# --------------------------------------------------------------------------
#: Ordem dos campos a partir da coluna 'Motor' (indice 4 da linha do PDF). Igual a
#: FIELDS de tools/import_pbev.py (teste de consistencia em tests/test_market_data.py).
PBEV_FIELD_NAMES = [
    "Motor", "TipoPropulsao", "Transmissao", "ArCondicionado", "DirecaoAssistida",
    "Combustivel", "NMOG_NOx_mg_km", "CO_mg_km", "NOx_g_km", "ReducaoRelativaLimite",
    "CO2Fossil_Etanol_g_km", "CO2Fossil_GasolinaDiesel_g_km", "CO2Fossil_VEHP_g_km",
    "Km_l_Etanol_Cidade", "Km_l_Etanol_Estrada", "Km_l_GasolinaDiesel_Cidade",
    "Km_l_GasolinaDiesel_Estrada", "Km_le_Eletrico_Cidade", "Km_le_Eletrico_Estrada",
    "ConsumoEnergetico_MJ_km", "AutonomiaEletrica_km", "ClassificacaoPBE_Relativa",
    "ClassificacaoPBE_Absoluta", "SeloCONPET"]
NOT_APPLICABLE = {"\\", "-", ""}


@dataclass
class PBEVRecord:
    category: str
    brand: str
    model: str
    version: str
    fields: dict[str, float | str]

    @property
    def key(self) -> str:
        return match_key(self.brand, self.model)


def _num(texto: str):
    try:
        return float(texto.replace(",", "."))
    except ValueError:
        return None


def parse_pbev_rows(linhas: list[list[str]]) -> list[PBEVRecord]:
    """Linhas da tabela do PDF. So entram as linhas de dados (mais de 20 celulas e categoria
    preenchida); cabecalhos e totais saem. `\\` (nao se aplica) nao e gravado; `ND` fica texto."""
    out: list[PBEVRecord] = []
    for r in linhas:
        if len(r) < 25 or not r[0].strip() or not r[1].strip() \
                or norm(r[0]) == "CATEGORIA" or norm(r[0]).startswith("TOTAL"):
            continue
        campos: dict[str, float | str] = {}
        for nome, bruto in zip(PBEV_FIELD_NAMES, r[4:], strict=False):
            b = bruto.strip()
            if b in NOT_APPLICABLE:
                continue
            n = _num(b)
            campos[nome] = n if n is not None else b
        out.append(PBEVRecord(r[0].strip(), r[1].strip(), r[2].strip(), r[3].strip(), campos))
    return out


def duplicate_keys(registros: list[PBEVRecord]) -> dict[tuple, int]:
    """Chaves (marca, modelo, versao, motor, transmissao) que se repetem na edicao."""
    cont: dict[tuple, int] = {}
    for r in registros:
        k = (norm(r.brand), norm(r.model), norm(r.version), str(r.fields.get("Motor")),
             str(r.fields.get("Transmissao")))
        cont[k] = cont.get(k, 0) + 1
    return {k: n for k, n in cont.items() if n > 1}


def read_pdf_text(caminho: str) -> str:
    """Texto com layout de um PDF. Exige `pdfplumber` (nao esta em requirements.txt; decisao 4)."""
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise RuntimeError("Leitura de PDF exige a biblioteca pdfplumber "
                           "(pip install pdfplumber)") from exc
    with pdfplumber.open(caminho) as pdf:
        return "\n".join((p.extract_text(layout=True) or "") for p in pdf.pages)


def read_pdf_tables(caminho: str) -> list[list[str]]:
    """Todas as linhas de tabela de um PDF (pdfplumber), com quebras de linha viradas espaco."""
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Leitura de PDF exige a biblioteca pdfplumber "
                           "(pip install pdfplumber)") from exc
    linhas: list[list[str]] = []
    with pdfplumber.open(caminho) as pdf:
        for p in pdf.pages:
            for t in p.extract_tables():
                for r in t:
                    linhas.append([(c or "").replace("\n", " ").strip() for c in r])
    return linhas


# --------------------------------------------------------------------------
# BLOCO MD4 -- correspondencia com o catalogo
#   Um modelo do informativo pode ser um unico veiculo do catalogo ('exact'), ou
#   estar dividido por motorizacao ('split': o catalogo tem 'HR-V' e 'HR-V HEV',
#   e a soma das unidades adotadas fecha com o informativo), ou nao ter par ('none').
#   Quando ha par mas as unidades nao fecham, o status e 'differs' (o master decide).
# --------------------------------------------------------------------------
@dataclass
class CatalogMatch:
    row: SalesRow
    status: str                       # exact | split | differs | none
    idmvs: list[int]
    catalog_units: int | None


_SUFFIX = re.compile(r"^(?:HEV|PHEV|MHEV|SHEV|SPHEV|BEV|FCEV|GL)\b")


def match_to_catalog(conn: sqlite3.Connection, linhas: list[SalesRow]) -> list[CatalogMatch]:
    cat = conn.execute("SELECT IDMV, Brand, Model, COALESCE(SalesUnits,0) FROM P26_MarketVehicle "
                       "WHERE IsSelecao = 0").fetchall()
    porchave: dict[str, tuple[int, int]] = {}
    for idmv, marca, modelo, un in cat:
        porchave[match_key(marca, modelo)] = (idmv, un)
    saida: list[CatalogMatch] = []
    for r in linhas:
        k = r.key
        base = porchave.get(k)
        variantes = [(i, u) for kk, (i, u) in porchave.items()
                     if kk.startswith(k + " ") and _SUFFIX.match(kk[len(k) + 1:])]
        if base is None and not variantes:
            saida.append(CatalogMatch(r, "none", [], None))
            continue
        grupo = ([base] if base else []) + variantes
        total = sum(u for _, u in grupo)
        ids = [i for i, _ in grupo]
        if len(grupo) == 1 and total == r.units:
            status = "exact"
        elif len(grupo) > 1 and total == r.units:
            status = "split"
        else:
            status = "differs"
        saida.append(CatalogMatch(r, status, ids, total))
    return saida


# --------------------------------------------------------------------------
# BLOCO MD5 -- referencia ponderada (C33)
#   Reproduz Control Panel AM9:AR16 / Market Vehicles N228:CZ233: cada veiculo
#   SELECAO recebe a media, ponderada pelas unidades, dos veiculos ICEV dos seus
#   segmentos (P70). Parametros medios = os que hoje tem classe 'Avg' em P27.
#   Area frontal (IDMP 50) = FRONTAL_AREA_FACTOR x largura media (8) x altura media (27).
# --------------------------------------------------------------------------
#: Fator da area frontal da SELECAO (Control Panel AM16:AR16). Constante no codigo ate a
#: decisao 18 (mudar P59 muda o ParamBaseHash).
FRONTAL_AREA_FACTOR = 0.85
IDMP_WIDTH, IDMP_HEIGHT, IDMP_FRONTAL_AREA = 8, 27, 50


def reference_params(conn: sqlite3.Connection, idvc: str,
                     unidades: dict[int, int] | None = None) -> dict[int, float]:
    """Parametros medios do veiculo SELECAO da categoria `idvc`.

    `unidades`: {IDMV: unidades}; se omitido, usa P26.SalesUnits (a edicao da planilha).
    """
    sel = conn.execute("SELECT IDMVSelecao FROM P29_VehicleCategory WHERE IDVC = ?",
                       (idvc,)).fetchone()
    if sel is None:
        raise ValueError(f"categoria desconhecida: {idvc}")
    idsel = sel[0]
    segmentos = conn.execute("SELECT IDVDT, IDVS, FuelGroup, IDVPT FROM P70_ReferenceSegment "
                             "WHERE IDVC = ?", (idvc,)).fetchall()
    veiculos = conn.execute("SELECT IDMV, IDVDT, IDVS, Fuel, IDVPT, COALESCE(SalesUnits,0) "
                            "FROM P26_MarketVehicle WHERE IsSelecao = 0").fetchall()
    membros: list[tuple[int, int]] = []
    for idmv, dt_, sz, fuel, pt, un in veiculos:
        if any(norm(dt_) == norm(d) and norm(sz) == norm(s) and fuel_group(fuel) == g
               and pt == p for d, s, g, p in segmentos):
            membros.append((idmv, (unidades or {}).get(idmv, un) if unidades else un))
    params = [r[0] for r in conn.execute(
        "SELECT DISTINCT IDMP FROM P27_MarketVehicleParam "
        "WHERE IDMV = ? AND ValueClass = 'Avg'", (idsel,))]
    valores = {(i, p): v for i, p, v in conn.execute(
        "SELECT IDMV, IDMP, Value FROM P27_MarketVehicleParam WHERE Value IS NOT NULL")}
    saida: dict[int, float] = {}
    for p in params:
        if p == IDMP_FRONTAL_AREA:
            continue
        num = den = 0.0
        for idmv, un in membros:
            x = valores.get((idmv, p))
            if x is not None and un:
                num += x * un
                den += un
        if den:
            saida[p] = num / den
    if IDMP_WIDTH in saida and IDMP_HEIGHT in saida and IDMP_FRONTAL_AREA in params:
        saida[IDMP_FRONTAL_AREA] = FRONTAL_AREA_FACTOR * saida[IDMP_WIDTH] * saida[IDMP_HEIGHT]
    return saida


def segment_coverage(conn: sqlite3.Connection, total: int) -> dict[str, float]:
    """Unidades dos segmentos de P70 (todos) e a fracao do total informado (P60)."""
    segmentos = conn.execute("SELECT IDVDT, IDVS, FuelGroup, IDVPT FROM P70_ReferenceSegment"
                             ).fetchall()
    soma = 0
    for _idmv, dt_, sz, fuel, pt, un in conn.execute(
            "SELECT IDMV, IDVDT, IDVS, Fuel, IDVPT, COALESCE(SalesUnits,0) FROM P26_MarketVehicle "
            "WHERE IsSelecao = 0"):
        if any(norm(dt_) == norm(d) and norm(sz) == norm(s) and fuel_group(fuel) == g
               and pt == p for d, s, g, p in segmentos):
            soma += un
    return {"units": soma, "total": total, "share": soma / total if total else 0.0}


# --------------------------------------------------------------------------
# BLOCO MD7 -- comparacao de uma edicao do PBEV com a gravada na base
#   Chave do registro: marca, modelo, versao, motor, transmissao (em maiusculas).
#   Devolve contagens e as listas, para a tela do master decidir.
# --------------------------------------------------------------------------
def _pbev_key(brand, model, version, motor, trans) -> tuple:
    return (norm(brand), norm(model), norm(version), norm(motor), norm(trans))


def diff_pbev(conn: sqlite3.Connection, registros: list[PBEVRecord],
              idpbe: str = "PBEV2026") -> dict:
    """Compara registros lidos de um arquivo com a edicao `idpbe` da base (P28/P55)."""
    base: dict[tuple, float | None] = {}
    for idpbr, marca, modelo, versao in conn.execute(
            "SELECT IDPBR, Brand, Model, COALESCE(Version,'') FROM P28_PBEVRecord "
            "WHERE IDPBE = ?", (idpbe,)):
        vals = dict(conn.execute("SELECT FieldName, COALESCE(Value, ValueText) FROM "
                                 "P55_PBEVRecordValue WHERE IDPBR = ? AND FieldName IN "
                                 "('Motor','Transmissao','ConsumoEnergetico_MJ_km')",
                                 (idpbr,)))
        base[_pbev_key(marca, modelo, versao, vals.get("Motor"), vals.get("Transmissao"))] = \
            vals.get("ConsumoEnergetico_MJ_km")
    novo: dict[tuple, float | None] = {}
    for r in registros:
        k = _pbev_key(r.brand, r.model, r.version, r.fields.get("Motor"),
                      r.fields.get("Transmissao"))
        novo[k] = r.fields.get("ConsumoEnergetico_MJ_km")
    adicionados = sorted(set(novo) - set(base))
    removidos = sorted(set(base) - set(novo))
    alterados = sorted(k for k in set(base) & set(novo)
                       if isinstance(base[k], (int, float)) and isinstance(novo[k], (int, float))
                       and abs(base[k] - novo[k]) > 1e-9)
    return {"base": len(base), "file": len(novo), "added": adicionados,
            "removed": removidos, "changed": alterados}
