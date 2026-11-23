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
    """Texto com layout de um PDF. Exige `pdfplumber` (requirements.txt, decisao 4)."""
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
#: Fator da area frontal da SELECAO (Control Panel AM16:AR16): parametro P59 (decisao 18, 23/11).
FRONTAL_AREA_KEY = "FRONTAL_AREA_FACTOR"
IDMP_WIDTH, IDMP_HEIGHT, IDMP_FRONTAL_AREA = 8, 27, 50


def reference_params(conn: sqlite3.Connection, idvc: str,
                     unidades: dict[int, int] | None = None,
                     powertrain: str | None = None) -> dict[int, float]:
    """Parametros medios do veiculo SELECAO da categoria `idvc`.

    `unidades`: {IDMV: unidades}; se omitido, usa P26.SalesUnits (a edicao da planilha).
    `powertrain`: motorizacao a ponderar (decisao 19); por padrao a dos segmentos (ICEV, como
    na planilha, que calcula so o ICEV e deriva as demais por equivalencia).
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
    if powertrain:
        membros = _members_by_powertrain(conn, idvc, powertrain, unidades)
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
        fator = conn.execute("SELECT ValueEC FROM P59_EquationConstant WHERE IDEC = ?",
                             (FRONTAL_AREA_KEY,)).fetchone()
        if fator is None:      # base anterior ao B2: o CSV de origem traz o mesmo valor
            from core.params import equation_constants
            fator = (equation_constants()[FRONTAL_AREA_KEY],)
        saida[IDMP_FRONTAL_AREA] = fator[0] * saida[IDMP_WIDTH] * saida[IDMP_HEIGHT]
    return saida


def _members_by_powertrain(conn: sqlite3.Connection, idvc: str, powertrain: str,
                           unidades: dict[int, int] | None) -> list[tuple[int, int]]:
    """Veiculos dos segmentos da categoria na motorizacao pedida (design, porte e grupo de
    combustivel dos segmentos; a motorizacao vem do argumento)."""
    segmentos = conn.execute("SELECT IDVDT, IDVS, FuelGroup FROM P70_ReferenceSegment "
                             "WHERE IDVC = ?", (idvc,)).fetchall()
    saida: list[tuple[int, int]] = []
    for idmv, dt_, sz, fuel, pt, un in conn.execute(
            "SELECT IDMV, IDVDT, IDVS, Fuel, IDVPT, COALESCE(SalesUnits,0) FROM P26_MarketVehicle "
            "WHERE IsSelecao = 0"):
        if pt != powertrain:
            continue
        if any(norm(dt_) == norm(d) and norm(sz) == norm(s) and (g == "X" or
                                                                 fuel_group(fuel) == g)
               for d, s, g in segmentos):
            saida.append((idmv, (unidades or {}).get(idmv, un)))
    return saida


def closest_vehicles(conn: sqlite3.Connection, idvc: str, powertrain: str = "ICEV",
                     limite: int = 5) -> list[dict]:
    """Veiculos de mercado mais proximos da referencia ponderada (decisao 19).

    Distancia = raiz da media dos quadrados do desvio relativo nos parametros medios que o
    veiculo tem. Serve a titulo de ilustracao: os parametros adotados sao os ponderados.
    """
    ref = reference_params(conn, idvc, powertrain=None if powertrain == "ICEV" else powertrain)
    ref = {p: v for p, v in ref.items() if p != IDMP_FRONTAL_AREA and v}
    valores = {(i, p): v for i, p, v in conn.execute(
        "SELECT IDMV, IDMP, Value FROM P27_MarketVehicleParam WHERE Value IS NOT NULL")}
    ranking = []
    for idmv, un in _members_by_powertrain(conn, idvc, powertrain, None):
        desv = [((valores[(idmv, p)] - v) / v) ** 2 for p, v in ref.items()
                if (idmv, p) in valores]
        if not desv:
            continue
        marca, modelo = conn.execute("SELECT Brand, Model FROM P26_MarketVehicle WHERE IDMV = ?",
                                     (idmv,)).fetchone()
        ranking.append({"IDMV": idmv, "Brand": marca, "Model": modelo, "Units": un,
                        "Distance": (sum(desv) / len(desv)) ** 0.5})
    return sorted(ranking, key=lambda r: r["Distance"])[:limite]


def save_segments(conn: sqlite3.Connection, idvc: str, linhas: list[dict]) -> int:
    """Substitui os segmentos de uma categoria (so o Master; decisao 17). Cada linha:
    IDVDT, IDVS, FuelGroup (EG, D ou X) e IDVPT. Devolve o numero de segmentos gravados."""
    for r in linhas:
        if r["FuelGroup"] not in ("EG", "D", "X"):
            raise ValueError(f"grupo de combustivel invalido: {r['FuelGroup']}")
        if not r.get("IDVDT") or not r.get("IDVS"):
            raise ValueError("segmento sem design ou porte")
    proximo = (conn.execute("SELECT COALESCE(MAX(IDRS), 0) FROM P70_ReferenceSegment"
                            ).fetchone()[0])
    conn.execute("DELETE FROM P70_ReferenceSegment WHERE IDVC = ?", (idvc,))
    for i, r in enumerate(linhas, 1):
        conn.execute("INSERT INTO P70_ReferenceSegment (IDRS, IDVC, IDVDT, IDVS, FuelGroup, "
                     "IDVPT, Origin) VALUES (?,?,?,?,?,?, 'Master')",
                     (proximo + i, idvc, r["IDVDT"], r["IDVS"], r["FuelGroup"],
                      r.get("IDVPT") or "ICEV"))
    conn.commit()
    return len(linhas)


def restore_workbook_segments(conn: sqlite3.Connection, idvc: str) -> int:
    """Devolve os segmentos de uma categoria ao padrao do Excel (CSV da fixture)."""
    import csv
    import os
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "data", "csv", "fase_b", "P70_ReferenceSegment.csv")
    with open(caminho, encoding="utf-8-sig", newline="") as fh:
        base = [r for r in csv.DictReader(fh, delimiter=";") if r["IDVC"] == idvc]
    conn.execute("DELETE FROM P70_ReferenceSegment WHERE IDVC = ?", (idvc,))
    for r in base:
        conn.execute("INSERT INTO P70_ReferenceSegment (IDRS, IDVC, IDVDT, IDVS, FuelGroup, "
                     "IDVPT, SheetRow, NotesRS, Origin) VALUES (?,?,?,?,?,?,?,?, 'Workbook')",
                     (int(r["IDRS"]), idvc, r["IDVDT"], r["IDVS"], r["FuelGroup"], r["IDVPT"],
                      int(r["SheetRow"]) if r["SheetRow"] else None, r["NotesRS"] or None))
    conn.commit()
    return len(base)


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


# --------------------------------------------------------------------------
# BLOCO MD8 -- tabelas do Anuario da ANFAVEA (emplacamento e frota estimada)
#   Linhas "ano automoveis comerciais-leves caminhoes onibus total", com ponto de milhar.
#   Tabelas: 2.3 (Anuario 2025, 1957-2024), 2.2.1 (Anuario 2026, 2016-2025) e 1.11 (frota
#   estimada; Anuario 2025: 2000-2024; Anuario 2026: 2016-2025). Cada edicao revisa os anos
#   anteriores: guarda-se a edicao de cada numero e vale a mais recente (decisao 14).
# --------------------------------------------------------------------------
ANFAVEA_CLASSES = ("Automobiles", "LightCommercials", "Trucks", "Buses", "Total")
_ANF_NUM = r"\d{1,3}(?:\.\d{3})*"
_ANF_ROW = re.compile(rf"(?<![\d.])((?:19[5-9]|20[0-3])\d)\s+({_ANF_NUM})\s+({_ANF_NUM})\s+"
                      rf"({_ANF_NUM})\s+({_ANF_NUM})\s+({_ANF_NUM})(?![\d.])")


def parse_anfavea_table(texto: str, titulo: str, janela: int = 500
                        ) -> dict[int, tuple[int, int, int, int, int]]:
    """{ano: (automoveis, comerciais leves, caminhoes, onibus, total)} da tabela de `titulo`.

    `titulo` e o numero e o inicio do nome (ex.: "2.2.1 Emplacamento"). O titulo tambem
    aparece no sumario; vale a ocorrencia que rende mais linhas. Linhas cuja soma difere do total
    por mais de 5 unidades sao descartadas (erro de leitura do PDF; a fonte arredonda).
    """
    linhas = texto.splitlines()
    melhor: dict[int, tuple[int, int, int, int, int]] = {}
    for i, lin in enumerate(linhas):
        if not re.match(rf"\s*{re.escape(titulo)}", lin):
            continue
        achados: dict[int, tuple[int, int, int, int, int]] = {}
        for lin2 in linhas[i + 1:i + janela]:
            if re.match(r"\s*(FONTE|SOURCE)\b", lin2):
                break
            for m in _ANF_ROW.finditer(lin2):
                v = [int(g.replace(".", "")) for g in m.groups()[1:]]
                if abs(sum(v[:4]) - v[4]) <= 5:          # arredondamento da fonte
                    achados[int(m.group(1))] = tuple(v)          # type: ignore[assignment]
        if len(achados) > len(melhor):
            melhor = achados
    return melhor


# --------------------------------------------------------------------------
# BLOCO MD9 -- divisao do modelo por motorizacao (decisao 9, 22/11/2026)
#   O informativo da FENABRAVE traz o total do modelo; o modelo de calculo precisa de uma
#   linha por modelo e motorizacao (P26: 'HR-V' ICEV e 'HR-V HEV'). Candidatas, em ordem:
#     Reported  numeros que o proprio informativo da FENABRAVE/ANFAVEA da por variante;
#     Previous  participacao da edicao anterior (P47.UnitsAdopted);
#     PBEV      participacao pelo numero de versoes de cada motorizacao no PBEV (P50);
#     Master    valor digitado pelo master (sobrepoe qualquer candidata).
#   O master ve as tres candidatas lado a lado; a escolha e o campo SplitMethod.
# --------------------------------------------------------------------------
SPLIT_METHODS = ("Reported", "Previous", "PBEV", "Master", "Base", "Workbook")


@dataclass
class SplitLine:
    sales_class: str
    ranking: int | None
    brand: str
    model: str                        # modelo do informativo
    bulletin_total: int               # unidades da linha do informativo
    pool_total: int                   # unidades a repartir entre as motorizacoes do grupo
    idmv: int
    vehicle: str                      # DsMV do catalogo
    powertrain: str
    reported: int | None = None
    previous: int | None = None
    pbev: int | None = None
    method: str = "Base"
    units: int = 0
    basis: str = ""


def largest_remainder(total: int, pesos: list[float]) -> list[int]:
    """Reparte `total` (inteiro) em partes proporcionais a `pesos`, somando exatamente `total`."""
    soma = sum(pesos)
    if total <= 0 or soma <= 0:
        return [0] * len(pesos)
    cotas = [total * p / soma for p in pesos]
    base = [int(c) for c in cotas]
    faltam = total - sum(base)
    ordem = sorted(range(len(pesos)), key=lambda i: cotas[i] - base[i], reverse=True)
    for i in ordem[:faltam]:
        base[i] += 1
    return base


def split_candidates(conn: sqlite3.Connection, resultados: list[CatalogMatch],
                     linhas: list[SalesRow], idmse_anterior: str | None = None
                     ) -> list[SplitLine]:
    """Uma `SplitLine` por modelo e motorizacao, com as candidatas e a escolha automatica.

    Modelos sem par no catalogo (status 'none') nao entram: a tela os lista (decisao 10).
    """
    chaves = {r.key: r.units for r in linhas}
    info = {i: (ds, pt, mk) for i, ds, pt, mk in conn.execute(
        "SELECT IDMV, DsMV, IDVPT, Brand || '/' || Model FROM P26_MarketVehicle")}
    chave_veic = {i: match_key(b, m) for i, b, m in conn.execute(
        "SELECT IDMV, Brand, Model FROM P26_MarketVehicle")}
    anterior: dict[int, int] = {}
    if idmse_anterior:
        anterior = dict(conn.execute("SELECT IDMV, UnitsAdopted FROM P47_MarketSales "
                                     "WHERE IDMSE = ? AND IDMV IS NOT NULL", (idmse_anterior,)))
    versoes = dict(conn.execute("SELECT IDMV, COUNT(*) FROM P50_MarketVehiclePBEV GROUP BY IDMV"))
    saida: list[SplitLine] = []
    for m in resultados:
        if not m.idmvs:
            continue
        r = m.row
        # variantes com linha propria no informativo sao "Reported" por si so
        proprias = {i: chaves[chave_veic[i]] for i in m.idmvs
                    if chave_veic[i] != r.key and chave_veic[i] in chaves}
        pool = [i for i in m.idmvs if i not in proprias]
        for i, un in proprias.items():
            saida.append(SplitLine(r.sales_class, None, r.brand, r.model, un, un, i,
                                   info[i][0], info[i][1], reported=un, method="Reported",
                                   units=un, basis="linha propria no informativo"))
        total = r.units
        if len(pool) == 1:
            i = pool[0]
            saida.append(SplitLine(r.sales_class, r.ranking, r.brand, r.model, total, total, i,
                                   info[i][0], info[i][1], reported=total, method="Reported",
                                   units=total, basis="informativo"))
            continue
        prev_w = [anterior.get(i, 0) for i in pool]
        pbev_w = [versoes.get(i, 0) for i in pool]
        prev_u = largest_remainder(total, prev_w) if sum(prev_w) > 0 else [None] * len(pool)
        pbev_u = largest_remainder(total, pbev_w) if sum(pbev_w) > 0 else [None] * len(pool)
        for k, i in enumerate(pool):
            if prev_u[k] is not None:
                met, un, base = "Previous", prev_u[k], "participacao da edicao anterior"
            elif pbev_u[k] is not None:
                met, un, base = "PBEV", pbev_u[k], "numero de versoes no PBEV"
            else:
                met, un, base = "Base", total if k == 0 else 0, \
                    "sem candidata: total na primeira motorizacao (ajustar)"
            saida.append(SplitLine(r.sales_class, r.ranking if k == 0 else None, r.brand,
                                   r.model, total, total, i, info[i][0], info[i][1],
                                   previous=prev_u[k], pbev=pbev_u[k], method=met, units=un,
                                   basis=base))
    return saida


def sort_split_lines(linhas: list[SplitLine]) -> list[SplitLine]:
    """Ordem de exibicao: classe (V, CL), posicao do modelo no informativo e, dentro do modelo,
    as motorizacoes uma embaixo da outra (o que difere entre elas e a motorizacao/versao)."""
    primeira: dict[tuple, int] = {}
    for ln in linhas:
        if ln.ranking is not None:
            k = (ln.sales_class, ln.brand, ln.model)
            primeira[k] = min(primeira.get(k, ln.ranking), ln.ranking)
    classe = {"V": 0, "CL": 1}
    return sorted(linhas, key=lambda ln: (
        classe.get(ln.sales_class, 9),
        primeira.get((ln.sales_class, ln.brand, ln.model), 10 ** 6),
        ln.brand, ln.model, ln.powertrain, ln.idmv))


def reconcile_totals(rows: list[SalesRow], resultados: list[CatalogMatch],
                     linhas: list[SplitLine]) -> list[dict]:
    """Conferencia dos semitotais do informativo (V, CL) e do total (V+CL) com o adotado.

    Informativo = soma das linhas lidas; Adotado = soma das unidades das motorizacoes; Fora do
    catalogo = linhas do informativo sem par (nao gravadas, decisao 10). A diferenca
    (informativo - adotado - fora do catalogo) deve ser zero."""
    sem_par: dict[str, int] = {}
    for m in resultados:
        if not m.idmvs:
            sem_par[m.row.sales_class] = sem_par.get(m.row.sales_class, 0) + m.row.units
    saida = []
    for rotulo, classes in (("V (cars)", ("V",)), ("CL (light commercials)", ("CL",)),
                            ("V + CL", ("V", "CL"))):
        boletim = sum(r.units for r in rows if r.sales_class in classes)
        adotado = sum(ln.units for ln in linhas if ln.sales_class in classes)
        fora = sum(sem_par.get(c, 0) for c in classes)
        saida.append({"Class": rotulo, "Bulletin": boletim, "Adopted": adotado,
                      "Not in catalogue": fora, "Difference": boletim - adotado - fora})
    return saida


def model_checks(linhas: list[SplitLine]) -> list[dict]:
    """Por modelo repartido entre motorizacoes: total do informativo x soma adotada."""
    grupos: dict[tuple, list[SplitLine]] = {}
    for ln in linhas:
        if ln.method == "Reported" and ln.basis.startswith("linha propria"):
            continue
        grupos.setdefault((ln.sales_class, ln.brand, ln.model), []).append(ln)
    saida = []
    for (classe, marca, modelo), g in grupos.items():
        if len(g) < 2:
            continue
        soma = sum(x.units for x in g)
        saida.append({"Class": classe, "Brand": marca, "Model": modelo,
                      "Powertrains": len(g), "Bulletin total": g[0].pool_total,
                      "Sum adopted": soma, "Difference": g[0].pool_total - soma})
    return saida


def apply_master_units(linhas: list[SplitLine], unidades: dict[int, int]) -> list[SplitLine]:
    """Sobrepoe as unidades digitadas pelo master ({IDMV: unidades}); marca `Master`."""
    for ln in linhas:
        if ln.idmv in unidades and unidades[ln.idmv] != ln.units:
            ln.units, ln.method, ln.basis = int(unidades[ln.idmv]), "Master", "digitado pelo master"
    return linhas


def validate_split(linhas: list[SplitLine]) -> list[str]:
    """Problemas que impedem gravar: as motorizacoes de um modelo devem somar o total a repartir."""
    problemas: list[str] = []
    grupos: dict[tuple, list[SplitLine]] = {}
    for ln in linhas:
        if ln.method == "Reported" and ln.basis.startswith("linha propria"):
            continue
        grupos.setdefault((ln.sales_class, ln.brand, ln.model), []).append(ln)
    for (_c, marca, modelo), g in grupos.items():
        if sum(x.units for x in g) != g[0].pool_total:
            problemas.append(f"{marca} {modelo}: soma {sum(x.units for x in g)} "
                             f"!= total {g[0].pool_total}")
    return problemas


def save_edition(conn: sqlite3.Connection, idmse: str, secao: SalesSection,
                 linhas: list[SplitLine], arquivo: str, publicada: str | None = None,
                 referencia: str | None = None, adotar: bool | None = None) -> int:
    """Grava a edicao em P48 e P47 (somente o master, na base de referencia). Devolve nº de linhas.

    Regra do periodo (decisao 11, 23/11): so entram acumulados de janeiro (YTD) e ha uma
    serie por ano: a edicao de periodo mais recente do ano fica adotada e as demais do mesmo
    ano ficam guardadas com `IsAdopted = 0`. Acumulado que termina antes de dezembro recebe a
    observacao de dados parciais. `adotar=False` grava sem adotar.
    Recusa edicao que ja existe, periodo que nao seja YTD e divisoes que nao fecham.
    """
    if secao.kind != "YTD":
        raise ValueError("so entram relatorios acumulados de janeiro (YTD); o mensal nao e "
                         "usado")
    if conn.execute("SELECT 1 FROM P48_MarketSalesEdition WHERE IDMSE = ?", (idmse,)).fetchone():
        raise ValueError(f"a edicao {idmse} ja existe na base")
    problemas = validate_split(linhas)
    if problemas:
        raise ValueError("divisao por motorizacao nao fecha: " + "; ".join(problemas))
    from datetime import datetime
    agora = datetime.now().isoformat(timespec="seconds")
    ano, mes = secao.period_end[:4], int(secao.period_end[5:7])
    atual = conn.execute("SELECT MAX(PeriodEnd) FROM P48_MarketSalesEdition WHERE "
                         "substr(PeriodEnd,1,4) = ? AND IsAdopted = 1", (ano,)).fetchone()[0]
    adotar = (atual is None or secao.period_end >= atual) if adotar is None else adotar
    if adotar:
        conn.execute("UPDATE P48_MarketSalesEdition SET IsAdopted = 0 WHERE "
                     "substr(PeriodEnd,1,4) = ?", (ano,))
    nota = "Importada pelo master (T40)"
    if mes < 12:
        nota += f"; dados parciais de janeiro a {secao.period_end[5:7]}/{ano}"
    conn.execute(
        "INSERT INTO P48_MarketSalesEdition (IDMSE, SourceName, PeriodKind, PeriodStart, "
        "PeriodEnd, EditionRef, SourceMSE, PublishedAt, ImportedAt, RecordCount, IsAdopted, "
        "NotesMSE) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (idmse, "FENABRAVE", secao.kind, f"{secao.period_end[:4]}-01" if secao.kind == "YTD"
         else secao.period_end, secao.period_end, referencia, arquivo, publicada, agora,
         len(linhas), int(adotar), nota))
    prox = (conn.execute("SELECT COALESCE(MAX(IDMS),0) FROM P47_MarketSales").fetchone()[0]) + 1
    for k, ln in enumerate(linhas):
        conn.execute(
            "INSERT INTO P47_MarketSales (IDMS, IDMSE, SalesClass, Ranking, Brand, Model, "
            "MatchKey, UnitsSource, UnitsAdopted, IDMV, AdjustmentNote, UnitsReported, "
            "UnitsPrevious, UnitsPBEV, SplitMethod, SplitBasis) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (prox + k, idmse, ln.sales_class, ln.ranking, ln.brand, ln.model,
             match_key(ln.brand, ln.model), ln.bulletin_total, ln.units, ln.idmv,
             ln.basis if ln.method not in ("Reported",) else None, ln.reported,
             ln.previous, ln.pbev, ln.method, ln.basis))
    conn.commit()
    return len(linhas)


def adopted_edition(conn: sqlite3.Connection, year: int | None = None) -> str | None:
    """Edicao adotada da FENABRAVE: a do `year`; sem ele, a do ultimo ano completo (acumulado
    ate dezembro) e, se nao houver, a mais recente (decisao 11)."""
    if year is not None:
        r = conn.execute("SELECT IDMSE FROM P48_MarketSalesEdition WHERE IsAdopted = 1 AND "
                         "substr(PeriodEnd,1,4) = ?", (str(year),)).fetchone()
        return r[0] if r else None
    for filtro in ("AND substr(PeriodEnd,6,2) = '12' ", ""):
        r = conn.execute("SELECT IDMSE FROM P48_MarketSalesEdition WHERE IsAdopted = 1 "
                         f"{filtro}ORDER BY PeriodEnd DESC").fetchone()
        if r:
            return r[0]
    return None


def adopted_years(conn: sqlite3.Connection) -> list[tuple[int, str, bool]]:
    """[(ano, IDMSE, parcial)] das edicoes adotadas, do mais recente ao mais antigo."""
    return [(int(pe[:4]), i, pe[5:7] != "12") for i, pe in conn.execute(
        "SELECT IDMSE, PeriodEnd FROM P48_MarketSalesEdition WHERE IsAdopted = 1 "
        "ORDER BY PeriodEnd DESC")]


# --------------------------------------------------------------------------
# BLOCO MD10 -- quadro design x motorizacao (guia "FENABRAVE 2025 Categories", R2:AB11)
# --------------------------------------------------------------------------
def design_powertrain_pivot(conn: sqlite3.Connection, idmse: str
                            ) -> dict[tuple[str, str], int]:
    """{(grupo de mercado, motorizacao): unidades adotadas}; Van e Chassis vao para 'Other'."""
    saida: dict[tuple[str, str], int] = {}
    for grupo, dt_, pt, un in conn.execute(
            "SELECT v.MarketGroup, v.IDVDT, v.IDVPT, SUM(s.UnitsAdopted) FROM P47_MarketSales s "
            "JOIN P26_MarketVehicle v USING (IDMV) WHERE s.IDMSE = ? GROUP BY 1,2,3", (idmse,)):
        chave = ("Other" if dt_ in ("Van", "Chassis") or not grupo else grupo.strip(), pt)
        saida[chave] = saida.get(chave, 0) + un
    return saida


# --------------------------------------------------------------------------
# BLOCO MD11 -- comparacao e exportacao da referencia ponderada (decisao 13)
#   Planilha (valores 'Avg' gravados em P27) x recalculo do aplicativo (reference_params).
# --------------------------------------------------------------------------
def reference_comparison(conn: sqlite3.Connection,
                         unidades: dict[int, int] | None = None) -> list[dict]:
    """Uma linha por categoria e parametro: valor da planilha, recalculado e diferenca."""
    nomes = dict(conn.execute("SELECT IDMP, DsMP FROM P54_MarketParam"))
    saida: list[dict] = []
    for idvc, idsel in conn.execute("SELECT IDVC, IDMVSelecao FROM P29_VehicleCategory "
                                    "ORDER BY CaseDigit"):
        guardado = dict(conn.execute("SELECT IDMP, Value FROM P27_MarketVehicleParam "
                                     "WHERE IDMV = ? AND ValueClass = 'Avg'", (idsel,)))
        calc = reference_params(conn, idvc, unidades)
        for p in sorted(guardado):
            x, y = guardado[p], calc.get(p)
            saida.append({"IDVC": idvc, "IDMP": p, "Parameter": nomes.get(p, str(p)),
                          "Excel model": x, "Recalculated": y,
                          "Difference": None if x is None or y is None else y - x})
    return saida


def export_reference_xlsx(conn: sqlite3.Connection, destino, unidades: dict[int, int] | None = None
                          ) -> None:
    """Escreve o xlsx com a comparacao e as unidades usadas (`destino`: caminho ou buffer)."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Reference parameters"
    ws.append(["IDVC", "IDMP", "Parameter", "Excel model", "Recalculated", "Difference"])
    for r in reference_comparison(conn, unidades):
        ws.append([r["IDVC"], r["IDMP"], r["Parameter"], r["Excel model"], r["Recalculated"],
                   r["Difference"]])
    ws2 = wb.create_sheet("Units used")
    ws2.append(["IDMV", "Vehicle", "Powertrain", "Units (base)", "Units (recalculation)"])
    for i, ds, pt, un in conn.execute("SELECT IDMV, DsMV, IDVPT, COALESCE(SalesUnits,0) FROM "
                                      "P26_MarketVehicle WHERE IsSelecao = 0 ORDER BY IDMV"):
        ws2.append([i, ds, pt, un, (unidades or {}).get(i, un)])
    wb.save(destino)


# --------------------------------------------------------------------------
# BLOCO MD8b -- emplacamento por motorizacao e cilindrada (Anuario ANFAVEA 2026)
#   2.2.8 combustivel/tecnologia (4 classes), 2.2.9 eletrificados por tecnologia (automoveis
#   e comerciais leves), 2.2.10 cilindrada (automoveis, sem eletricos). Formato longo: uma
#   linha por ano, classe, dimensao e categoria; o total da fonte confere cada linha.
# --------------------------------------------------------------------------
_F6 = ["Gasoline", "Ethanol", "FlexFuel", "Electrified", "Diesel", "Total"]
_T6 = ["Gasoline", "Ethanol", "Electrified", "NaturalGas", "Diesel", "Total"]
_E6 = ["BEV", "FlexHybrid", "GasolineHybrid", "DieselHybrid", "PHEV", "Total"]
#: tabela -> (dimensao, [blocos de linhas], cada bloco = [(classe, categorias)] lado a lado)
ANFAVEA_LAYOUTS = {
    "2.2.8": ("Fuel", [[("Automobiles", _F6), ("LightCommercials", _F6)],
                       [("Trucks", _T6), ("Buses", _T6)]]),
    "2.2.9": ("Electrified", [[("Automobiles", _E6)], [("LightCommercials", _E6)]]),
    "2.2.10": ("Displacement", [[("Automobiles", ["Upto1000cc", "1001to2000cc", "Over2000cc",
                                                   "Total"])]]),
}
_ANF_TOK = r"(?:\d{1,3}(?:\.\d{3})*|-)"
_ANF_DATA = re.compile(rf"^\s*((?:19|20)\d\d)((?:\s+{_ANF_TOK})+)\s*$")


def parse_anfavea_columns(texto: str, tabela: str, janela: int = 300
                          ) -> list[tuple[int, str, str, str, int]]:
    """[(ano, classe, dimensao, categoria, unidades)] de 2.2.8, 2.2.9 ou 2.2.10.

    Cada linha confere a soma das categorias com o total da fonte (tolerancia 5); linha que
    nao fecha e descartada. A ultima categoria de cada classe (Total) nao e devolvida.
    """
    dimensao, blocos = ANFAVEA_LAYOUTS[tabela]
    larg = sum(len(c) for _, c in blocos[0])
    linhas = texto.splitlines()
    melhor: list[list[tuple[int, list[int]]]] = []
    for i, lin in enumerate(linhas):
        if not re.match(rf"\s*{re.escape(tabela)} (Emplacamento|Registration)", lin):
            continue
        grupos: list[list[tuple[int, list[int]]]] = []
        for lin2 in linhas[i + 1:i + janela]:
            outra = re.match(r"\s*(\d\.\d+(?:\.\d+)?) [A-Za-z]", lin2)
            if outra and outra.group(1) != tabela:
                break
            m = _ANF_DATA.match(lin2)
            if not m:
                continue
            tok = [0 if t == "-" else int(t.replace(".", "")) for t in m.group(2).split()]
            if len(tok) != larg:
                continue
            ano = int(m.group(1))
            if not grupos or ano <= grupos[-1][-1][0]:
                grupos.append([])
            grupos[-1].append((ano, tok))
        if len(grupos) >= len(blocos) and sum(map(len, grupos)) > sum(map(len, melhor)):
            melhor = grupos
    saida: list[tuple[int, str, str, str, int]] = []
    for bloco, grupo in zip(blocos, melhor, strict=False):
        for ano, tok in grupo:
            pos = 0
            for classe, cats in bloco:
                v = tok[pos:pos + len(cats)]
                pos += len(cats)
                if abs(sum(v[:-1]) - v[-1]) > 5:
                    continue
                saida += [(ano, classe, dimensao, c, u) for c, u in zip(cats[:-1], v[:-1],
                                                                         strict=True)]
    return saida
