# -*- coding: utf-8 -*-
"""Gera a Base de Dados revisada da Calculadora Berco-ao-Portao (Documento 3)."""
import os, re, openpyxl, datetime
from openpyxl.styles import Font, PatternFill, Alignment

BASE = os.path.expanduser("~/mnt/_Calculadora da Pegada de Carbono do Berço ao Portão")
# os documentos podem estar na raiz do diretorio ou na subpasta Documentacao
D = next((d for d in (os.path.join(BASE, "Documentação"), BASE)
          if os.path.exists(os.path.join(d, "LVManufacturingMassGHGSimulator_20260919a.xlsx"))), BASE)
SRC = os.path.join(D, "LVManufacturingMassGHGSimulator_20260919a.xlsx")
# Diretriz D6: o documento entregue leva a data e a letra da versao do dia.
# A letra avanca quando ja existe um arquivo do mesmo dia com conteudo anterior.
def _out_name(d):
    hoje = datetime.date.today().strftime("%Y%m%d")
    for letra in "abcdefghijklmnopqrstuvwxyz":
        nome = os.path.join(d, f"BaseDeDados_CalculadoraBP_{hoje}{letra}.xlsx")
        if not os.path.exists(nome):
            return nome
        ultimo = nome
    return ultimo

OUT = _out_name(D)
print("documentos em:", D)

src = openpyxl.load_workbook(SRC, data_only=True)

def rows(name):
    ws = src[name]
    it = ws.iter_rows(values_only=True)
    hdr = list(next(it))
    out = []
    for r in it:
        if all(v is None for v in r):
            continue
        out.append(dict(zip(hdr, r)))
    return hdr, out

log = []
def note(msg):
    log.append(msg); print("  *", msg)

# ---------------------------------------------------------------- P02..P20
h, P02 = rows("P02"); h, P03 = rows("P03"); h, P04 = rows("P04")
h, P05 = rows("P05"); h, P06 = rows("P06"); h, P07 = rows("P07")
h, P08 = rows("P08"); h, P09 = rows("P09"); h, P10 = rows("P10")
h, P11 = rows("P11"); h, P12 = rows("P12"); h, P13 = rows("P13")
h, P14 = rows("P14"); h, P15 = rows("P15"); h, P16 = rows("P16")
h, P17 = rows("P17"); h, P18 = rows("P18"); h, P19 = rows("P19")
h20, P20 = rows("P20")
h, D01 = rows("D01"); h, D02 = rows("D02"); h, D03 = rows("D03")

# IDM e TEXTO: a base usa 4a, 4b, 46a, 46b alem de codigos numericos
def sidm(x):
    if x is None: return None
    if isinstance(x, float) and x == int(x): x = int(x)
    return str(x).strip()
for lst in (P09, P11, P16, P20):
    for r in lst:
        r["IDM"] = sidm(r["IDM"])
# P16: pseudo-material 'ND' do grupo Iaux e a montagem da bateria chumbo-acido (IDM 84)
_nd = 0
for r in P16:
    if r["IDM"] == "ND":
        r["IDM"] = "84"; _nd += 1
if _nd:
    note_nd = _nd

print("linhas originais:", {k: len(v) for k, v in
      [("P06",P06),("P07",P07),("P09",P09),("P11",P11),("P16",P16),
       ("P19",P19),("P20",P20),("D01",D01),("D02",D02),("D03",D03)]})

# ---- P04 : IsBattery
BAT_GG = {"Iaux", "Iprinc"}
for r in P04:
    r["IsBattery"] = 1 if r["IDGG"] in BAT_GG else 0

# ---- P06 : fLM
for r in P06:
    r["fLM"] = 1.0

# ---- P07 : ParamClass + GCEquation (versao i3ET) + AppliesTo
EQ = {
  4:  ("Exo", "", ""),
  9:  ("End", "GC(9) = GC(7) * GC(8)", ""),
  15: ("End", "GC(15) = GC(3) se IDVPT em {SHEV,SPHEV}; senao MAX(GC(2),GC(3))", ""),
  16: ("End", "GC(16) = GC(15) * GC(9) * GC(14) * GC(29)", ""),
  18: ("End", "GC(18) = 0.04 * GC(2)", ""),
  25: ("Res", "GC(25) = C12.MassIDV  (resultado do modulo de massa)", ""),
  28: ("End", "GC(28) = GC(9) * GC(27)", ""),
  29: ("Exo", "", ""),
  30: ("End", "GC(30) = GC(25) * GC(29)", ""),
  33: ("End", "GC(33) = P19.PowerDensity(GC(32)); 'ND' se ausente", ""),
  34: ("End", "GC(34) = P19.EnergyDensity(GC(32)); 'ND' se ausente", ""),
  35: ("End", "se GC(33)='ND': (se GC(34)='ND' -> 0; senao GC(34)*GC(5)); "
              "senao: (se GC(24)>0 -> GC(33)*GC(24); senao GC(33)*GC(3))", ""),
  36: ("End", "GC(36) = P19.RefEnergy(GC(32))", ""),
  37: ("End", "GC(37) = GC(2) / GC(29)", ""),
  38: ("Res", "modulo M3 - fora do escopo bercoo-ao-portao", ""),
  39: ("Res", "modulo M3 - fora do escopo bercoo-ao-portao", ""),
  40: ("Res", "modulo M3 - fora do escopo bercoo-ao-portao", ""),
  42: ("End", "GC(42) = GC(41) * GC(15)", ""),
}
APPLIES = {2:"ICEV,HEV,PHEV,SHEV,SPHEV", 3:"HEV,PHEV,BEV,SHEV,SPHEV,FCEV",
           5:"HEV,PHEV,BEV,SHEV,SPHEV,FCEV", 19:"ICEV,HEV,PHEV,SHEV,SPHEV",
           20:"FCEV", 21:"FCEV", 23:"PHEV,BEV", 24:"HEV,FCEV",
           31:"HEV,PHEV,SHEV,SPHEV", 32:"HEV,PHEV,BEV,SHEV,SPHEV,FCEV"}
for r in P07:
    k = r["IDVP"]
    cls, eq, _ = EQ.get(k, ("Exo", "", ""))
    r["ParamClass"] = cls
    r["GCEquation"] = eq if eq else (r.get("GCEquation") or "")
    r["AppliesTo"] = APPLIES.get(k, "")

# ---- P09 : EFBasis / EFBasisParam / IsProcess
#   86 = Lithium Ion Battery Assembly  -> kg CO2e/kWh  sobre GC(5)
#   84/85 = montagens de bateria por massa ; 99 = A ; 100 = DR  -> por veiculo
ENERGY_BASIS = {"86": 5}
VEHICLE_BASIS = {"99", "100"}
PROCESS_IDM  = {"84", "85", "86", "99", "100"}
BREAKDOWN_IDM = {str(i) for i in range(87, 98)}   # marcadores de quimica do catodo
for r in P09:
    idm = r["IDM"]
    if idm in ENERGY_BASIS:
        r["EFBasis"], r["EFBasisParam"], r["IsProcess"] = "energy", ENERGY_BASIS[idm], 1
    elif idm in VEHICLE_BASIS:
        r["EFBasis"], r["EFBasisParam"], r["IsProcess"] = "vehicle", None, 1
    else:
        r["EFBasis"], r["EFBasisParam"] = "mass", None
        r["IsProcess"] = 1 if idm in PROCESS_IDM else 0
    r["ShareRole"] = ("process" if idm in PROCESS_IDM
                      else "breakdown" if idm in BREAKDOWN_IDM else "material")

# ---- P10 : GWPSet / SourceEFV / LicenseEFV
SRC_EFV = {"G22":"GREET 2022 (Argonne National Laboratory)",
           "G23":"GREET 2023 (Argonne National Laboratory)",
           "G24":"GREET 2024 (Argonne National Laboratory)",
           "BR25BR":"FGV/Unicamp - Berco ao Portao (Fundep / Programa Move) - 100% BR",
           "BR25m":"FGV/Unicamp - Berco ao Portao (Fundep / Programa Move) - mercado BR",
           "BR25GLO":"FGV/Unicamp - Berco ao Portao (Fundep / Programa Move) - internacional"}
LIC_GREET = ("GREET (c) UChicago Argonne, LLC - redistribuicao permitida para USO NAO COMERCIAL, "
             "com manutencao do aviso de copyright e da isencao de responsabilidade, credito ao "
             "Argonne National Laboratory, identificacao da versao e declaracao de que os dados de "
             "entrada foram modificados (valores extraidos e processados pelo i3ET). "
             "Ver https://greet.anl.gov/copyright")
LIC_BR = ("Projeto do Berco ao Portao (FGV/Unicamp para a Fundep - Programa Move, Governo "
          "Federal) - confirmado pelo autor, participante do projeto; sem restricao herdada "
          "do GREET. Condicoes de redistribuicao a registrar antes da publicacao.")
for r in P10:
    r["GWPSet"] = "AR6-100"
    r["SourceEFV"] = SRC_EFV.get(r["IDEFV"], "a confirmar")
    r["LicenseEFV"] = LIC_GREET if str(r["IDEFV"]).startswith("G") else LIC_BR

# ---- P11 : procedencia (EFnotes) ----
ORIGEM = {
 "G22": "GREET 2022 (Argonne National Laboratory). Valor extraido da aba 'Emission Factors GREET "
        "and BR' do LCA_LV_i3ET, coluna G22; nao e o arquivo GREET original (dado de entrada "
        "processado - ver Documento 1, secao 18.3).",
 "G23": "GREET 2023 (Argonne National Laboratory). Valor extraido da aba 'Emission Factors GREET "
        "and BR' do LCA_LV_i3ET, coluna G23; dado de entrada processado.",
 "G24": "GREET 2024 (Argonne National Laboratory). Valor extraido da aba 'Emission Factors GREET "
        "and BR' do LCA_LV_i3ET, coluna G24; dado de entrada processado.",
 "BR25BR": "Projeto do Berco ao Portao - FGV/Unicamp para a Fundep (Programa Move, Governo "
           "Federal). Recorte: producao 100% nacional.",
 "BR25m": "Projeto do Berco ao Portao - FGV/Unicamp para a Fundep (Programa Move, Governo "
          "Federal). Recorte: mercado brasileiro (mix nacional e importado).",
 "BR25GLO": "Projeto do Berco ao Portao - FGV/Unicamp para a Fundep (Programa Move, Governo "
            "Federal). Recorte: internacional.",
}
SEM_FATOR = ("Sem fator nesta versao ('ND' na fonte). Contribui com zero para as emissoes - "
             "ausencia de dado, nao desempenho ambiental nulo. Ver a aba CoberturaEF.")
n_sem = 0
for r in P11:
    base_nota = ORIGEM.get(r["IDEFV"], "procedencia a confirmar")
    if not r["EF"]:
        r["EFnotes"] = SEM_FATOR + " " + base_nota
        n_sem += 1
    else:
        r["EFnotes"] = base_nota
note("P11: coluna EFnotes preenchida nos %d fatores; %d marcados como sem fator na versao."
     % (len(P11), n_sem))

# ---- P12 : sem fH (a complexidade hibrida e exogena por veiculo, em D03 IDVP 29)

# ---- P19 : recalculo protegido das grandezas derivadas
def div(a, b):
    try:
        a = float(a); b = float(b)
    except (TypeError, ValueError):
        return None
    return a / b if b else None

for r in P19:
    if r["IDBMd"] == "NA":
        for c in ("RefRange","RefEnergy","RefPower","RefWeight","RefGHGIDBMd",
                  "EnergyDensity","PowerDensity","GravimetricEnergyDensity",
                  "GravimetricPowerDensity","GravimetricGHGDensity","EnergyGHGDensity"):
            r[c] = 0.0
        continue
    hev = (r.get("IDVPT") == "HEV")
    if hev:
        if r.get("RefPower") and r.get("PowerDensity"):
            r["RefWeight"] = float(r["RefPower"]) * float(r["PowerDensity"])
        r["EnergyDensity"] = div(r.get("RefWeight"), r.get("RefEnergy")) or r.get("EnergyDensity")
        if r.get("RefWeight") and r.get("GravimetricGHGDensity"):
            r["RefGHGIDBMd"] = float(r["RefWeight"]) * float(r["GravimetricGHGDensity"])
        r["EnergyGHGDensity"] = div(r.get("RefGHGIDBMd"), r.get("RefEnergy"))
        r["GravimetricPowerDensity"] = div(1, r.get("PowerDensity"))
    else:
        if r.get("RefEnergy") and r.get("EnergyDensity"):
            r["RefWeight"] = float(r["RefEnergy"]) * float(r["EnergyDensity"])
        if r.get("RefEnergy") and r.get("EnergyGHGDensity"):
            r["RefGHGIDBMd"] = float(r["RefEnergy"]) * float(r["EnergyGHGDensity"])
        r["GravimetricGHGDensity"] = div(r.get("RefGHGIDBMd"), r.get("RefWeight"))
    r["GravimetricEnergyDensity"] = div(1, r.get("EnergyDensity"))
    if r.get("GravimetricPowerDensity") in (None, "") and r.get("PowerDensity"):
        r["GravimetricPowerDensity"] = div(1, r.get("PowerDensity"))
note("P19: grandezas derivadas recalculadas com divisao protegida (sem 'inf')")

# ---- P20 : BMshare -> BMshareGG, colunas residuais removidas
P20n = [{"IDBMd": r["IDBMd"], "IDGG": r["IDGG"], "IDM": r["IDM"],
         "BMshareGG": r.get("BMshare")} for r in P20]
note("P20: coluna BMshare renomeada BMshareGG; %d colunas residuais removidas"
     % sum(1 for c in h20 if c is None))

# ---- P06/P08 : correcoes conferidas contra o M1 do i3ET --------------------
# O confronto parametro a parametro com o modulo M1 revelou exatamente duas
# divergencias em 43 subgrupos. Ambas no tanque de combustivel (IDSG 26):
# a massa de referencia estava zerada, o que fazia o subgrupo desaparecer de
# todo veiculo a combustao, e o grupo GREET apontava para o sistema auxiliar de
# celula a combustivel em vez do trem de forca.
CORR_P06 = {26: {"MR": 15.0}}
CORR_P08 = {26: {"IDGG": "D"}}
_n = 0
for r in P06:
    fix = CORR_P06.get(r["IDSG"])
    if fix:
        for k, v in fix.items():
            if r.get(k) != v:
                note("P06: IDSG %s %s corrigido de %s para %s (valor do i3ET)"
                     % (r["IDSG"], k, r.get(k), v))
                r[k] = v; _n += 1
for r in P08:
    fix = CORR_P08.get(r["IDSG"])
    if fix:
        for k, v in fix.items():
            if r.get(k) != v:
                note("P08: IDSG %s %s corrigido de %s para %s (valor do i3ET)"
                     % (r["IDSG"], k, r.get(k), v))
                r[k] = v; _n += 1

# ---- P08 : aplicabilidade do subgrupo por trem de forca (regra do i3ET, M1 col AB)
sgname = {r["IDSG"]: (r.get("DsSG") or "") for r in P02}
EXCL = {}
for r in P02:
    n = (r.get("DsSG") or "").lower()
    if "mbio" in n or "cambio" in n:          # Caixa de Cambio & Embreagem
        EXCL[r["IDSG"]] = "SHEV,SPHEV"
for r in P08:
    r["ExcludedVPT"] = EXCL.get(r["IDSG"], "")
note("P08: coluna ExcludedVPT criada; subgrupos excluidos por trem de forca: %s"
     % ({k: (sgname.get(k), v) for k, v in EXCL.items()} or "nenhum"))

# ---- P20 : neutralizar o BMshareGG do IDM 86 -------------------------------
# O valor original nao e participacao massica: e GravimetricEnergyDensity (kWh/kg)
# multiplicada por um EF(86) de OUTRA versao (modelos G22 trazem o fator da G24,
# modelos G23 trazem o da G22). Usa-lo produziria subestimativa de ~5% e, se o
# fator fosse aplicado de novo pela regra geral, erro de ~13x. A montagem da
# bateria e calculada pela regra documentada: GC(IDV,5) * EF(86, IDEFV do cenario).
ORIG86 = {}
for r in P20n:
    if r["IDM"] == "86" and (r["BMshareGG"] or 0) > 0:
        ORIG86[r["IDBMd"]] = r["BMshareGG"]
        r["BMshareGG"] = 0.0
if ORIG86:
    note("P20: BMshareGG do IDM 86 zerado em %d modelos de bateria. O valor original nao era "
         "participacao massica e trazia um fator de emissao de versao trocada embutido; a "
         "montagem da bateria passa a ser calculada por GC(IDV,5) * EF(86, IDEFV do cenario). "
         "Valores originais preservados na aba BMshare86_original." % len(ORIG86))

# ---- D01 : IsUserDefined
for r in D01:
    r["IsUserDefined"] = 0

# ---- D02 : IDAPV + Boundary
for r in D02:
    r["IDAPV"] = "A-EF"
    r["Boundary"] = "MAT_ASM"


# ---------------------------------------------------------------- D03
gc = {}
D03orig = {}
for r in D03:
    v = r["GC"]
    gc[(r["IDV"], r["IDVP"])] = v
    D03orig[(r["IDV"], r["IDVP"])] = v
vpt = {r["IDV"]: r["IDVPT"] for r in D01}
p19 = {r["IDBMd"]: r for r in P19}

def g(v, p):
    x = gc.get((v, p))
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

faltantes = []
for v in sorted(vpt):
    for p in [r["IDVP"] for r in P07]:
        if (v, p) not in gc:
            faltantes.append((v, p))
note("D03 original: %d pares (IDV,IDVP) ausentes" % len(faltantes))

ENDOG = [9, 15, 16, 18, 28, 33, 34, 35, 36, 37, 42]
FH_ORIG = {}

# ------------------------------------------------- sincronizacao com o i3ET
# Decisao de 20/09/2026: os parametros dos veiculos BP01..BP12 passam a vir das
# colunas homonimas do i3ET (diretriz D11). A base do simulador descrevia os
# mesmos nomes com dimensoes e potencias diferentes -- dois instantaneos que se
# separaram. Ver Documento 1, secao 16.6.
I3ET = os.path.join(D, "LCA_LV_i3ET_20260919a.xlsx")
D03_ANTES = {}
if os.path.exists(I3ET):
    import openpyxl as _ox
    _wb = _ox.load_workbook(I3ET, data_only=True, read_only=True)
    _m2 = {}
    # Rows 1..80 carry the configuration parameters; rows 617..626 carry the
    # fluids block, which is the composition of GREET group K -- see below.
    for _i, _row in enumerate(_wb["M2 GHG Mfg Module"].iter_rows(
            min_row=1, max_row=630, max_col=210, values_only=True), 1):
        if _i > 80 and not (615 <= _i <= 630):
            continue
        for _j, _v in enumerate(_row, 1):
            if _v is not None:
                _m2[(_i, _j)] = _v
    _bat = {}
    for _i, _row in enumerate(_wb["GREET Batteries Material List"].iter_rows(
            min_row=1, max_row=70, max_col=240, values_only=True), 1):
        for _j, _v in enumerate(_row, 1):
            if _v is not None:
                _bat[(_i, _j)] = _v
    _wb.close()

    bpcol = {str(v).strip(): c for (r, c), v in _m2.items()
             if r == 11 and str(v).strip().startswith("BP")}
    dsv = {r["DsV"]: r["IDV"] for r in D01}
    SYNC_SKIP = set(ENDOG) | {25, 30, 38, 39, 40, 41, 42}
    n_mud = n_ig = 0
    for nome, col in sorted(bpcol.items()):
        v = dsv.get(nome)
        if v is None:
            continue
        for idvp in range(2, 41):
            if idvp in SYNC_SKIP:
                continue
            val = _m2.get((10 + idvp, col))
            if val is None:
                continue
            antes = gc.get((v, idvp))
            if idvp == 32:
                novo = str(val).strip()
                antes_s = None if antes in (None, "") else str(antes).strip()
                if novo != antes_s:
                    D03_ANTES[(v, idvp)] = antes_s; gc[(v, idvp)] = novo; n_mud += 1
                else:
                    n_ig += 1
                continue
            if not isinstance(val, (int, float)):
                continue
            try:
                antes_f = float(antes)
            except (TypeError, ValueError):
                antes_f = None
            if antes_f is None or abs(antes_f - val) > 1e-9 * max(1.0, abs(val)):
                D03_ANTES[(v, idvp)] = antes_f; gc[(v, idvp)] = float(val); n_mud += 1
            else:
                n_ig += 1
    note("D03 sincronizada com as colunas BP do i3ET: %d valores alterados, %d ja iguais, "
         "em %d veiculos. Valores anteriores preservados na aba D03_antes_da_sincronizacao."
         % (n_mud, n_ig, len(bpcol)))

    # --- modelos de bateria do i3ET usados pelos BP (caminho gravimetrico) ---
    BCI_ROW = 67          # 'Mass Carbon Intensity', kg CO2e/kg
    idcol = {str(v).strip(): c for (r, c), v in _bat.items() if r == 4 and v is not None}
    usados = {str(gc.get((v, 32))).strip() for v in dsv.values()
              if gc.get((v, 32)) not in (None, "", "-", "NA")}
    existentes = {r["IDBMd"] for r in P19}
    tec = {r["IDBTe"] for r in P18}
    tipos = {r["IDBTy"] for r in P17}
    novos = []
    for bmd in sorted(usados - existentes):
        c = idcol.get(bmd)
        if c is None:
            note("ATENCAO: modelo de bateria %s citado pelos veiculos e ausente do i3ET" % bmd)
            continue
        f = lambda r: (_bat.get((r, c)) if isinstance(_bat.get((r, c)), (int, float)) else None)
        bty = str(_bat.get((15, c)) or "").strip()
        bte = str(_bat.get((16, c)) or "").strip()
        if bty and bty not in tipos:
            P17.append({"IDBTy": bty, "DsBTy": bty}); tipos.add(bty)
        if bte and bte not in tec:
            P18.append({"IDBTe": bte, "IDBTy": bty, "DsBTe": bte}); tec.add(bte)
        ed, pd_ = f(6), f(5)
        P19.append({
            "IDBMd": bmd, "IDEFV": None,
            "IDVPT": str(_bat.get((7, c)) or "").strip() or None,
            "IDBTe": bte or None,
            "RefRange": f(13), "RefEnergy": f(14), "RefPower": None,
            "RefWeight": None, "RefGHGIDBMd": None,
            "EnergyDensity": ed, "PowerDensity": pd_,
            "GravimetricEnergyDensity": (1 / ed) if ed else None,
            "GravimetricPowerDensity": (1 / pd_) if pd_ else None,
            "GravimetricGHGDensity": f(BCI_ROW),
            "EnergyGHGDensity": None,
            "DsBMd": "Projeto do Berco ao Portao; emissoes por intensidade de carbono massica",
        })
        novos.append((bmd, ed, pd_, f(BCI_ROW)))
    if novos:
        note("P19: %d modelos de bateria importados do i3ET: %s"
             % (len(novos), ", ".join(f"{b} (BCI={x} kg CO2e/kg)" for b, _, _, x in novos)))

# --- metodo de calculo da emissao da bateria, explicito em P19 ---------------
com_composicao = {r["IDBMd"] for r in P20n if (r.get("BMshareGG") or 0) > 0}
for r in P19:
    if r["IDBMd"] == "NA":
        r["GHGMethod"] = "none"
    elif r["IDBMd"] in com_composicao:
        r["GHGMethod"] = "composition"
    else:
        r["GHGMethod"] = "gravimetric"
from collections import Counter as _C
note("P19: coluna GHGMethod definida -- %s. O i3ET escolhe pelo prefixo 'PB' do identificador; "
     "aqui a escolha e explicita e segue a existencia de composicao de materiais em P20."
     % dict(_C(r["GHGMethod"] for r in P19)))

p19 = {r["IDBMd"]: r for r in P19}   # inclui os modelos recem-importados

recalc = {}
for v in sorted(vpt):
    pt = vpt[v]
    FH_ORIG[v] = g(v, 29)
    f = 1.0                      # i3ET: fH = 1 em todas as configuracoes (M2 linha 39)
    gc[(v, 29)] = f
    gc[(v, 9)] = g(v, 7) * g(v, 8)
    gc[(v, 15)] = g(v, 3) if pt in ("SHEV", "SPHEV") else max(g(v, 2), g(v, 3))
    gc[(v, 16)] = g(v, 15) * g(v, 9) * g(v, 14) * f
    gc[(v, 18)] = 0.04 * g(v, 2)
    gc[(v, 28)] = g(v, 9) * g(v, 27)
    gc[(v, 37)] = g(v, 2) / f if f else 0.0
    bmd = gc.get((v, 32))
    bmd = None if bmd in (None, "", "-", "NA") else str(bmd).strip()
    b = p19.get(bmd) if bmd else None
    pd_ = (b or {}).get("PowerDensity") or 0
    ed_ = (b or {}).get("EnergyDensity") or 0
    gc[(v, 33)] = float(pd_) if pd_ else 0.0
    gc[(v, 34)] = float(ed_) if ed_ else 0.0
    gc[(v, 36)] = float((b or {}).get("RefEnergy") or 0)
    if not pd_:
        gc[(v, 35)] = (float(ed_) * g(v, 5)) if ed_ else 0.0
    else:
        gc[(v, 35)] = float(pd_) * (g(v, 24) if g(v, 24) > 0 else g(v, 3))
    gc[(v, 42)] = g(v, 41) * g(v, 15)
    gc[(v, 30)] = None   # depende de C12.MassIDV: calculado apos o modulo de massa
    for p in ENDOG:
        recalc[(v, p)] = gc[(v, p)]

p06 = {(r["IDMPV"], r["IDSG"]): r for r in P06}
sg_por_vp = {}
for r in P08:
    sg_por_vp.setdefault(r["IDVP"], []).append(r["IDSG"])
mpv = {r["IDV"]: r["IDMPV"] for r in D02}

note("fH (IDVP 29) fixado em 1,0 para todos os veiculos, conforme o i3ET, onde a linha 39 do modulo "
     "M2 vale 1 em todas as 57 configuracoes. Na base original fH valia 1 (ICEV), 2 (HEV e BEV) e "
     "4 (PHEV). Com fH=1 o fR (IDVP 16) coincide com a base original e a equacao do i3ET "
     "GC(15)*GC(9)*GC(14)*GC(29) passa a valer sem efeito sobre os resultados.")

def massa(idv, ids, valor):
    pr = p06.get((mpv[idv], ids))
    if not pr or not pr.get("GCR"): return None
    try: return pr["MR"] * ((valor / pr["GCR"]) ** pr["Beta"])
    except Exception: return None

impacto = []
for (v, pvp), novo_val in sorted(recalc.items()):
    velho = D03orig.get((v, pvp))
    try: velho = float(velho)
    except (TypeError, ValueError): continue
    if abs((novo_val or 0) - velho) < 1e-9: continue
    for ids in sg_por_vp.get(pvp, []):
        mn, mv = massa(v, ids, novo_val or 0), massa(v, ids, velho)
        if mn is None or mv is None or abs(mn - mv) < 1e-6: continue
        impacto.append((v, vpt[v], pvp, ids, sgname.get(ids), mv, mn, mn - mv))

if impacto:
    por_v = {}
    for v, _pt, _vp, _ids, _nm, mv, mn, d_ in impacto:
        por_v[v] = por_v.get(v, 0.0) + d_
    note("Efeito das equacoes adotadas sobre a massa, em relacao a base original: %d subgrupos "
         "afetados; variacao por veiculo (kg): %s"
         % (len(impacto), {k: round(x, 2) for k, x in sorted(por_v.items())}))
    for v, pt_, pvp, ids, nm, mv, mn, d_ in sorted(impacto, key=lambda x: -abs(x[7]))[:10]:
        note("   IDV %s (%s) via IDVP %s -> subgrupo %s '%s': %.3f -> %.3f kg (%+.3f)"
             % (v, pt_, pvp, ids, nm, mv, mn, d_))
else:
    note("Efeito das equacoes adotadas sobre a massa: nenhum subgrupo afetado.")

difs = []
for (v, p), novo in sorted(recalc.items()):
    orig = D03orig.get((v, p))
    try: orig = float(orig)
    except (TypeError, ValueError): orig = None
    if orig is None: continue
    den = max(abs(orig), 1e-12)
    if abs(novo - orig) / den > 1e-9:
        difs.append((v, p, orig, novo))
note("Confronto D03 original x endogenos recalculados: %d de %d valores divergem (tol. 1e-9)"
     % (len(difs), len(recalc)))
for v, p, o, n in difs[:12]:
    note("   IDV %s IDVP %s: original %.6f -> recalculado %.6f" % (v, p, o, n))

D03n = []
for v in sorted(vpt):
    for p in [r["IDVP"] for r in P07]:
        if p in (25, 30, 38, 39, 40):    # resultados: dependem do modulo de massa ou de M3
            continue
        val = gc.get((v, p))
        txt = None
        if p == 32:
            txt = "NA" if val in (None, "", "-", "NA") else str(val).strip()
            val = 0.0
        else:
            try:
                val = float(val)
            except (TypeError, ValueError):
                val = 0.0
        D03n.append({"IDV": v, "IDVP": p, "GC": val, "GCText": txt,
                     "IsCalculated": 1 if p in ENDOG else 0})
note("D03 revisada: %d linhas (12 veiculos x %d parametros); %d valores endogenos calculados"
     % (len(D03n), len(D03n) // 12, len(recalc)))

# ---------------------------------------------------------------- P21..P25 (montagem)
P21 = [
 {"IDAP":1,"DsAP":"Paint Production","IncludedInA":0,
  "NotesAP":"producao da tinta: energia de producao de material, ja contabilizada via IDM da tinta; fora do agregado A do i3ET"},
 {"IDAP":2,"DsAP":"Vehicle Assembly - Painting","IncludedInA":1,"NotesAP":""},
 {"IDAP":3,"DsAP":"Vehicle Assembly - HVAC & Lighting","IncludedInA":1,"NotesAP":""},
 {"IDAP":4,"DsAP":"Vehicle Assembly - Heating","IncludedInA":1,"NotesAP":""},
 {"IDAP":5,"DsAP":"Vehicle Assembly - Material Handling","IncludedInA":1,"NotesAP":""},
 {"IDAP":6,"DsAP":"Vehicle Assembly - Welding","IncludedInA":1,"NotesAP":""},
 {"IDAP":7,"DsAP":"Vehicle Assembly - Compressed Air","IncludedInA":1,"NotesAP":""},
]
INA = {r["IDAP"]: r["IncludedInA"] for r in P21}
P24 = [{"IDFuel":"ResidOil","DsFuel":"Oleo residual"},
       {"IDFuel":"Diesel","DsFuel":"Diesel"},
       {"IDFuel":"NaturalGas","DsFuel":"Gas natural"},
       {"IDFuel":"Coal","DsFuel":"Carvao"},
       {"IDFuel":"Electricity","DsFuel":"Eletricidade da rede"}]
FUELS = ["ResidOil","Diesel","NaturalGas","Coal","Electricity"]
# aba ADR-Assembling Disposal Recycling do i3ET: MJ/veiculo e participacao por combustivel
ADR = {1:(302.801,[0,0,0,0,1]), 2:(2910.8991,[0,0,0.834,0,0.166]),
       3:(1044.5053,[0,0,0,0,1]), 4:(3146.1765,[0,0,1,0,0]),
       5:(216.2864,[0,0,0,0,1]), 6:(288.0302,[0,0,0,0,1]),
       7:(431.5178,[0,0,0,0,1])}
P23 = [
 {"IDAPV":"A-EF","DsAPV":"Montagem lida da tabela de fatores (IDM 99), conforme a versao IDEFV",
  "DateIDAPV":datetime.date(2026,9,19),"Method":"from_EF","FixedGHGPerVehicle":None,
  "Status":"recommended","IDEFVdefault":None,
  "SourceAPV":"P11, IDM 99 'A - Assembling', EFBasis=vehicle. E como o i3ET faz (M2 linha 510). "
              "Cobre automaticamente todas as versoes de fatores"},
 {"IDAPV":"A-G22","DsAPV":"Montagem por processo - GREET 2022 (detalhamento)",
  "DateIDAPV":datetime.date(2022,12,31),"Method":"process","FixedGHGPerVehicle":None,
  "Status":"recommended","IDEFVdefault":"G22",
  "SourceAPV":"GREET 2022, Vehi_Input (via aba ADR do LCA_LV_i3ET). Decomposicao por processo e "
              "combustivel; deve reconciliar com P11 IDM 99 da versao G22"},
 {"IDAPV":"A-G23","DsAPV":"Montagem por processo - GREET 2023 (detalhamento)",
  "DateIDAPV":datetime.date(2023,12,31),"Method":"process","FixedGHGPerVehicle":None,
  "Status":"recommended","IDEFVdefault":"G23",
  "SourceAPV":"GREET 2023; mesma repartic. energetica do GREET 2022 - confirmar contra a planilha"},
 {"IDAPV":"i3ET-BR23","DsAPV":"Montagem agregada do i3ET (legado, em conflito com o GREET)",
  "DateIDAPV":datetime.date(2023,12,31),"Method":"fixed","FixedGHGPerVehicle":227.284,
  "Status":"legacy","IDEFVdefault":None,
  "SourceAPV":"LCA_LV_i3ET, M2 linha 510 como constante. Nao consta de P11 em nenhuma versao; "
              "mantido apenas para reproduzir resultados anteriores"}]
P22 = []
for apv in ("A-G22", "A-G23"):
    for idap,(e,sh) in ADR.items():
        for f,s in zip(FUELS,sh):
            P22.append({"IDAPV":apv,"IDAP":idap,"IDFuel":f,
                        "EnergyPerVehicle":e,"FuelShare":float(s)})
# fatores dos energeticos (g CO2e/MJ)
EF_G22 = {"ResidOil":96.3639,"Diesel":89.0790,"NaturalGas":69.2923,
          "Coal":100.5280,"Electricity":129.5837}
EF_BR  = dict(EF_G22); EF_BR["Electricity"] = 25.64      # EPE/ANEEL/ONS, i3ET Control Panel
P25 = []
for f in FUELS:
    P25.append({"IDFuel":f,"IDEFV":"G22","EFfuel":EF_G22[f],
                "EFfuelNotes":"GREET 2022 - aba ADR do i3ET"})
    for efv in ("BR25BR","BR25m","BR25GLO"):
        P25.append({"IDFuel":f,"IDEFV":efv,"EFfuel":EF_BR[f],
                    "EFfuelNotes":"eletricidade: rede BR (EPE/ANEEL/ONS, 25,64 g CO2e/MJ); "
                                  "demais: GREET - a substituir pelos fatores do Projeto Berco ao Portao"})
ghg_proc = sum(e*s*EF_G22[f] for idap,(e,sh) in ADR.items() if INA[idap] for f,s in zip(FUELS,sh))/1000.0
note("Montagem A por processo, fatores GREET: %.2f kg CO2e/veiculo (i3ET aba ADR: 705,46)" % ghg_proc)
ghg_br = sum(e*s*EF_BR[f] for idap,(e,sh) in ADR.items() if INA[idap] for f,s in zip(FUELS,sh))/1000.0
note("Montagem A por processo, eletricidade BR (25,64 g CO2e/MJ): %.2f kg CO2e/veiculo" % ghg_br)
note("Montagem: a versao padrao (A-EF) le o valor da propria tabela de fatores, IDM 99, conforme a "
     "versao IDEFV escolhida - 705,462 (G22 e G23), 697,92 (G24), 318,91 (BR25BR e BR25m) e "
     "756,496 (BR25GLO) kg CO2e/veiculo. As versoes A-G22 e A-G23 trazem a decomposicao por "
     "processo, que reconcilia com o IDM 99 (705,46). O valor de 227,28 do i3ET nao consta de P11 "
     "em nenhuma versao e fica marcado como 'legacy'.")

# ---- P16 : receita do grupo K (Fluidos), ausente da base do simulador ------
# A base do simulador nao traz composicao para o grupo K. O i3ET traz: as linhas
# 620 a 626 do M2 sao as massas, em kg, de cada fluido (IDM 77 a 83), e a linha
# 617 e a emissao do grupo, que e a soma dessas massas vezes os respectivos
# fatores. Sem essas linhas, a calculadora carrega a massa dos fluidos e lhes
# atribui emissao zero -- entre 1,5% e 2,3% do total do veiculo desaparece em
# silencio, que e exatamente o que a diretriz D13 e a cobertura de fatores
# existem para impedir. Diretriz D11: prevalece o i3ET.
#
# As participacoes sao tomadas da familia de configuracoes de referencia
# (G01 a G05 e BP01 a BP12), que e a familia dos veiculos do projeto. O i3ET
# permite composicoes diferentes por configuracao; aqui elas entram por receita
# (IDVMR), que e a granularidade do modelo relacional.
FLUID_ROWS = {620: "77", 621: "78", 622: "79", 623: "80",
              624: "81", 625: "82", 626: "83"}
#: A receita do SHEV nao tem configuracao com fluidos preenchidos no i3ET.
#: Adotada a do HEV, por ser hibrido com motor a combustao. Registrado no
#: Relatorio de Divergencias.
FLUID_FALLBACK = {"SHEV": "HEV"}
if os.path.exists(I3ET) and _m2:
    _cfg = {str(v).strip(): c for (r, c), v in _m2.items()
            if r == 11 and re.match(r"^[A-Z]{1,2}\d{1,2}$", str(v).strip())}
    _ref = {c: col for c, col in _cfg.items()
            if re.match(r"^(G\d{1,2}|BP\d{2})$", c)}
    _bypt = {}
    for _code, _col in sorted(_ref.items()):
        _pt = str(_m2.get((10, _col)) or "").strip()
        _m = {idm: float(_m2.get((r, _col)) or 0.0) for r, idm in FLUID_ROWS.items()}
        _tot = sum(_m.values())
        if _tot <= 0:
            continue
        _frac = {k: v / _tot for k, v in _m.items()}
        _prev = _bypt.get(_pt)
        if _prev is None:
            _bypt[_pt] = (_frac, [_code])
        else:
            _same = all(abs(_prev[0][k] - _frac[k]) < 1e-9 for k in _frac)
            if _same:
                _prev[1].append(_code)
            else:
                note("P16 grupo K: %s tem composicao de fluidos diferente da de %s; "
                     "adotada a primeira (%s)" % (_code, _prev[1][0], _prev[1][0]))
    _ja = {(r["IDVMR"], r["IDGG"]) for r in P16}
    _add = 0
    for _r in P15:
        _vmr, _pt = _r["IDVMR"], _r["IDVPT"]
        if (_vmr, "K") in _ja:
            continue
        _src_pt = _pt if _pt in _bypt else FLUID_FALLBACK.get(_pt)
        _hit = _bypt.get(_src_pt)
        if _hit is None:
            note("P16 grupo K: sem composicao de fluidos para %s (receita %s)" % (_pt, _vmr))
            continue
        for _idm, _f in sorted(_hit[0].items(), key=lambda kv: int(kv[0])):
            P16.append({"IDVMR": _vmr, "IDGG": "K", "IDM": _idm, "MshareGG": _f})
            _add += 1
        if _src_pt != _pt:
            note("P16 grupo K: receita %s (%s) adotou a composicao de fluidos do %s "
                 "(o i3ET nao traz configuracao de %s com fluidos preenchidos)"
                 % (_vmr, _pt, _src_pt, _pt))
    note("P16: %d participacoes do grupo K (Fluidos) importadas do i3ET, linhas 620 a 626 "
         "do M2. Antes o grupo tinha massa e emissao zero. Trens de forca com composicao "
         "propria: %s" % (_add, ", ".join(sorted(_bypt))))

# ---------------------------------------------------------------- verificacoes
PROC = {r["IDM"] for r in P09 if r["ShareRole"] != "material"}
def fechamento(lst, keys, col, nome, skip_proc=True):
    from collections import defaultdict
    acc = defaultdict(float)
    for r in lst:
        if skip_proc and r.get("IDM") in PROC: continue
        try: acc[tuple(r[k] for k in keys)] += float(r[col] or 0)
        except (TypeError, ValueError): pass
    bad = [(k, v) for k, v in acc.items() if abs(v - 1) > 1e-6 and v != 0]
    note("%s: %d de %d combinacoes fora do fechamento (|soma-1|>1e-6)"
         % (nome, len(bad), len(acc)))
    return bad

bad16 = fechamento(P16, ["IDVMR","IDGG"], "MshareGG", "P16 (receitas de materiais)")
bad20 = fechamento(P20n, ["IDBMd","IDGG"], "BMshareGG", "P20 (receitas de bateria)")
bad22 = fechamento(P22, ["IDAPV","IDAP"], "FuelShare", "P22 (repartic. de combustiveis)", skip_proc=False)
for k, v in bad16[:8]: note("   P16 %s soma=%.6f" % (k, v))
for k, v in bad20[:8]: note("   P20 %s soma=%.6f" % (k, v))

# --- normalizacao (decisao de 19/09/2026): dividir pela soma dos itens 'material'
from collections import defaultdict
NORM = []
def normalizar(lst, keys, col, tab):
    acc = defaultdict(float)
    for r in lst:
        if r.get("IDM") in PROC: continue
        try: acc[tuple(r[k] for k in keys)] += float(r[col] or 0)
        except (TypeError, ValueError): pass
    for r in lst:
        if r.get("IDM") in PROC: continue
        k = tuple(r[k2] for k2 in keys)
        tot = acc.get(k) or 0.0
        if tot <= 0: continue
        r[col] = float(r[col] or 0) / tot
    for k, tot in sorted(acc.items()):
        if tot <= 0: continue
        NORM.append({"IDTable": tab, "Chave": " | ".join(str(x) for x in k),
                     "SomaOriginal": tot, "FatorAplicado": (1.0 / tot) if tot else None,
                     "DesvioOriginal_ppm": (tot - 1.0) * 1e6})
    return acc

normalizar(P16, ["IDVMR","IDGG"], "MshareGG", "P16")
normalizar(P20n, ["IDBMd","IDGG"], "BMshareGG", "P20")
piores = sorted(NORM, key=lambda x: -abs(x["DesvioOriginal_ppm"]))[:5]
note("Receitas normalizadas: cada participacao foi dividida pela soma dos itens de papel 'material' "
     "do seu grupo. %d grupos ajustados; maior desvio original: %.0f ppm (%s)."
     % (len(NORM), abs(piores[0]["DesvioOriginal_ppm"]), piores[0]["Chave"]) if NORM else "sem grupos")
for x in piores:
    note("   %s %s: soma %.9f -> fator %.9f" % (x["IDTable"], x["Chave"], x["SomaOriginal"], x["FatorAplicado"]))
fechamento(P16, ["IDVMR","IDGG"], "MshareGG", "P16 apos normalizacao")
fechamento(P20n, ["IDBMd","IDGG"], "BMshareGG", "P20 apos normalizacao")

efs = {(r["IDM"], r["IDEFV"]) for r in P11}
efv_usados = {r["IDEFV"] for r in D02}
idm_usados = {r["IDM"] for r in P16} | {r["IDM"] for r in P20n}
idm_p09 = {r["IDM"] for r in P09}
orfaos = sorted(idm_usados - idm_p09)
note("IDM citados em P16/P20 e ausentes de P09: %s" % (orfaos if orfaos else "nenhum"))
note("IDM e TEXTO na base (ha codigos 4a, 4b, 46a, 46b) - tipagem corrigida para TEXT")
faltaEF = sorted({(m, e) for m in idm_usados if isinstance(m, int)
                  for e in efv_usados if (m, e) not in efs})
note("Cobertura de fatores de emissao: %d pares (IDM,IDEFV) ausentes em P11" % len(faltaEF))
if faltaEF: note("   exemplos: %s" % faltaEF[:10])

vmr_ok = {r["IDVMR"]: r["IDVPT"] for r in P15}
vpt_d01 = {r["IDV"]: r["IDVPT"] for r in D01}
avisos = [(r["IDV"], r["IDVMR"], vmr_ok.get(r["IDVMR"]), vpt_d01.get(r["IDV"]))
          for r in D02 if vmr_ok.get(r["IDVMR"]) != vpt_d01.get(r["IDV"])]
note("Consistencia receita x trem de forca (I9): %d avisos" % len(avisos))
note("RESOLVIDO - fR (IDVP 16): adotada a equacao do i3ET com fH=1. Sem efeito sobre os resultados.")
note("DIVERGENCIA A CONFIRMAR - IDVP 15 (Combined Power): para os veiculos 1 e 11 a base traz valor "
     "diferente de MAX(GC(2),GC(3)) - IDV 1: 85,300 contra 85,318 (arredondamento); IDV 11: 110,536 "
     "contra 173,992 (a base usa a potencia do motor a combustao, nao a maior das duas). "
     "Adotada a regra do i3ET.")
note("DIVERGENCIA A CONFIRMAR - IDVP 42: a base traz 0 para os hibridos, embora GC(41)=1; "
     "a equacao GC(41)*GC(15) produz valor nao nulo. Adotada a equacao.")
note("DIVERGENCIA A CONFIRMAR - IDVP 36: a base traz 0 para IDV 7 a 9; o modelo de bateria "
     "G22-HEV-NMC111 tem RefEnergy = 2 kWh. Adotado o valor de P19.")
for a in avisos[:12]: note("   IDV %s usa %s (%s) mas e %s" % a)

# ---------------------------------------------------------------- P01 revisada
P01n = []
def dd(tab, nome, cols):
    for i, c in enumerate(cols, 1):
        P01n.append({"IDTable": tab, "ColumnName": c[0], "ColumnOrder": i,
                     "SQLType": c[1], "KeyRole": c[2], "FKTarget": c[3],
                     "Unit": c[4], "ParamClass": c[5], "Required": c[6],
                     "Domain": c[7], "DsColumnName": c[8],
                     "ColumnCalculationFormula": c[9], "TableName": nome})

dd("P02","Vehicle Subgroup List",[
 ("IDSG","INTEGER","PK","","","Idx",1,"1..43","identificacao do subgrupo",""),
 ("DsSG","TEXT","-","","","Dsc",1,"","nome do subgrupo","")])
dd("P03","Generic Groups List",[
 ("IDG","INTEGER","PK","","","Idx",1,"1..9","identificacao do grupo generico",""),
 ("DsG","TEXT","-","","","Dsc",1,"","nome do grupo","")])
dd("P04","GREET Group List",[
 ("IDGG","TEXT","PK","","","Idx",1,"A,B,C,D,E,F,G,H,Iaux,Iprinc,J,K","grupo GREET",""),
 ("DsGG","TEXT","-","","","Dsc",1,"","nome do grupo",""),
 ("IsBattery","INTEGER","-","","","Dsc",1,"0,1","1 para grupos de bateria","")])
dd("P05","Mass Parameters List",[
 ("IDMPV","INTEGER","PK","","","Idx",1,"","versao dos parametros de massa",""),
 ("DsMPV","TEXT","-","","","Dsc",1,"","nome da versao",""),
 ("DateIDMPV","DATE","-","","","Dsc",1,"","data de referencia",""),
 ("SourceMPV","TEXT","-","","","Dsc",0,"","origem","")])
dd("P06","Mass Estimation Parameters",[
 ("IDMPV","INTEGER","PK","P05.IDMPV","","Idx",1,"","versao dos parametros",""),
 ("IDSG","INTEGER","PK","P02.IDSG","","Idx",1,"","subgrupo",""),
 ("Beta","REAL","-","","","Exo",1,">=0","expoente da lei de escala",""),
 ("GCR","REAL","-","","conf. utGCR","Exo",1,">0","parametro de referencia",""),
 ("utGCR","TEXT","-","","","Dsc",1,"","unidade de GCR",""),
 ("MR","REAL","-","","kg","Exo",1,">=0","massa de referencia",""),
 ("fLM","REAL","-","","","Exo",1,">0","fator de leveza (M5); 1,0 nesta versao",""),
 ("Reference","TEXT","-","","","Dsc",0,"","fonte","")])
dd("P07","Vehicle Parameters List",[
 ("IDVP","INTEGER","PK","","","Idx",1,"2..42","parametro do veiculo",""),
 ("DsVP","TEXT","-","","","Dsc",1,"","nome",""),
 ("utVP","TEXT","-","","","Dsc",1,"","unidade",""),
 ("ParamClass","TEXT","-","","","Dsc",1,"Exo,End,Res","classificacao",""),
 ("GCEquation","TEXT","-","","","Dsc",0,"","equacao quando End ou Res",""),
 ("AppliesTo","TEXT","-","","","Dsc",0,"","trens de forca aplicaveis","")])
dd("P08","Group and subgroup correlation",[
 ("IDSG","INTEGER","PK","P02.IDSG","","Idx",1,"","subgrupo",""),
 ("IDVP","INTEGER","FK","P07.IDVP","","Idx",1,"","parametro dimensionador",""),
 ("IDG","INTEGER","FK","P03.IDG","","Idx",1,"","grupo generico",""),
 ("IDGG","TEXT","FK","P04.IDGG","","Idx",1,"","grupo GREET",""),
 ("ExcludedVPT","TEXT","-","","","Dsc",0,"","trens de forca em que o subgrupo nao existe","GC = 0 e ME = 0")])
dd("P09","Material List",[
 ("IDM","INTEGER","PK","","","Idx",1,"","material",""),
 ("DsM","TEXT","-","","","Dsc",1,"","nome",""),
 ("Mspec","TEXT","-","","","Dsc",0,"","especificacao",""),
 ("EFBasis","TEXT","-","","","Dsc",1,"mass,energy,vehicle","base de aplicacao do fator",""),
 ("EFBasisParam","INTEGER","FK","P07.IDVP","","Dsc",0,"","IDVP que fornece a base",""),
 ("IsProcess","INTEGER","-","","","Dsc",1,"0,1","1 para pseudo-material de processo",""),
 ("ShareRole","TEXT","-","","","Dsc",1,"material,process,breakdown","papel na soma das receitas","apenas 'material' entra no fechamento = 1")])
dd("P10","Emission Factors Version List",[
 ("IDEFV","TEXT","PK","","","Idx",1,"","versao dos fatores",""),
 ("DsEFV","TEXT","-","","","Dsc",1,"","nome",""),
 ("DateIDEFV","DATE","-","","","Dsc",1,"","data",""),
 ("GWPSet","TEXT","-","","","Dsc",1,"AR6-100","conjunto de GWP",""),
 ("SourceEFV","TEXT","-","","","Dsc",1,"","fonte",""),
 ("LicenseEFV","TEXT","-","","","Dsc",0,"","condicoes de redistribuicao","")])
dd("P11","Emission Factors values list",[
 ("IDM","INTEGER","PK","P09.IDM","","Idx",1,"","material",""),
 ("IDEFV","TEXT","PK","P10.IDEFV","","Idx",1,"","versao",""),
 ("EF","REAL","-","","conf. P09.EFBasis","Exo",1,">=0","fator de emissao",""),
 ("EFnotes","TEXT","-","","","Dsc",0,"","observacoes","")])
dd("P12","Power Train List",[
 ("IDVPT","TEXT","PK","","","Idx",1,"ICEV,HEV,PHEV,BEV,SHEV,SPHEV,FCEV","trem de forca",""),
 ("DsVPT","TEXT","-","","","Dsc",1,"","descricao","")])
dd("P13","Design List",[
 ("IDVDT","TEXT","PK","","","Idx",1,"","tipo de carroceria",""),
 ("DsVDT","TEXT","-","","","Dsc",1,"","descricao","")])
dd("P14","Size List",[
 ("IDVS","TEXT","PK","","","Idx",1,"","porte",""),
 ("DsVS","TEXT","-","","","Dsc",1,"","descricao","")])
dd("P15","Vehicle Material Recipe List",[
 ("IDVMR","TEXT","PK","","","Idx",1,"","receita de materiais",""),
 ("IDVPT","TEXT","FK","P12.IDVPT","","Idx",1,"","trem de forca tipico",""),
 ("IDVDT","TEXT","FK","P13.IDVDT","","Idx",0,"","carroceria tipica",""),
 ("IDVS","TEXT","FK","P14.IDVS","","Idx",0,"","porte tipico",""),
 ("DsVMR","TEXT","-","","","Dsc",1,"","descricao","")])
dd("P16","Vehicle Material Recipe per GREET group",[
 ("IDVMR","TEXT","PK","P15.IDVMR","","Idx",1,"","receita",""),
 ("IDGG","TEXT","PK","P04.IDGG","","Idx",1,"","grupo GREET",""),
 ("IDM","INTEGER","PK","P09.IDM","","Idx",1,"","material",""),
 ("MshareGG","REAL","-","","fracao","Exo",1,"0..1","participacao massica","soma = 1 por (IDVMR,IDGG)")])
dd("P17","Battery Types",[
 ("IDBTy","TEXT","PK","","","Idx",1,"","tipo de bateria",""),
 ("DsBTy","TEXT","-","","","Dsc",1,"","descricao","")])
dd("P18","Battery Technologies per Type",[
 ("IDBTe","TEXT","PK","","","Idx",1,"","tecnologia",""),
 ("IDBTy","TEXT","FK","P17.IDBTy","","Idx",1,"","tipo",""),
 ("DsBTe","TEXT","-","","","Dsc",1,"","descricao","")])
dd("P19","Battery Models Parameters",[
 ("IDBMd","TEXT","PK","","","Idx",1,"","modelo de bateria; 'NA' = sem bateria",""),
 ("IDEFV","TEXT","FK","P10.IDEFV","","Idx",0,"","versao de fatores de origem",""),
 ("IDVPT","TEXT","FK","P12.IDVPT","","Idx",0,"","trem de forca de destino",""),
 ("IDBTe","TEXT","FK","P18.IDBTe","","Idx",0,"","tecnologia",""),
 ("RefRange","REAL","-","","km","Exo",1,">=0","autonomia de referencia",""),
 ("RefEnergy","REAL","-","","kWh","Exo",1,">=0","capacidade de referencia",""),
 ("RefPower","REAL","-","","kW","Exo",1,">=0","potencia de referencia",""),
 ("RefWeight","REAL","-","","kg","End",1,">=0","massa de referencia","HEV: RefPower*PowerDensity; demais: RefEnergy*EnergyDensity"),
 ("RefGHGIDBMd","REAL","-","","kg CO2e","End",1,">=0","emissao de referencia","HEV: RefWeight*GravimetricGHGDensity; demais: RefEnergy*EnergyGHGDensity"),
 ("EnergyDensity","REAL","-","","kg/kWh","Exo/End",1,"","densidade de energia","HEV: RefWeight/RefEnergy"),
 ("PowerDensity","REAL","-","","kg/kW","Exo",1,"","densidade de potencia",""),
 ("GravimetricEnergyDensity","REAL","-","","kWh/kg","End",0,"","1/EnergyDensity","divisao protegida"),
 ("GravimetricPowerDensity","REAL","-","","kW/kg","End",0,"","1/PowerDensity","divisao protegida"),
 ("GravimetricGHGDensity","REAL","-","","kg CO2e/kg","Exo/End",0,"","","demais: RefGHGIDBMd/RefWeight"),
 ("EnergyGHGDensity","REAL","-","","kg CO2e/kWh","Exo/End",0,"","","HEV: RefGHGIDBMd/RefEnergy"),
 ("DsBMd","TEXT","-","","","Dsc",0,"","descricao","")])
dd("P20","Battery Material Recipe per Model",[
 ("IDBMd","TEXT","PK","P19.IDBMd","","Idx",1,"","modelo de bateria",""),
 ("IDGG","TEXT","PK","P04.IDGG","","Idx",1,"","grupo GREET",""),
 ("IDM","INTEGER","PK","P09.IDM","","Idx",1,"","material",""),
 ("BMshareGG","REAL","-","","fracao","Exo",1,"0..1","participacao massica","renomeada de BMshare")])
dd("P21","Assembly Process List",[
 ("IDAP","INTEGER","PK","","","Idx",1,"","processo de montagem",""),
 ("DsAP","TEXT","-","","","Dsc",1,"","nome do processo","")])
dd("P22","Assembly Energy and Fuel Shares",[
 ("IDAPV","TEXT","PK","P23.IDAPV","","Idx",1,"","versao dos parametros de montagem",""),
 ("IDAP","INTEGER","PK","P21.IDAP","","Idx",1,"","processo",""),
 ("IDFuel","TEXT","PK","P24.IDFuel","","Idx",1,"","portador de energia",""),
 ("EnergyPerVehicle","REAL","-","","MJ/veiculo","Exo",1,">=0","energia do processo por veiculo",""),
 ("FuelShare","REAL","-","","fracao","Exo",1,"0..1","participacao do portador","soma = 1 por (IDAPV,IDAP)")])
dd("P23","Assembly Parameters Version List",[
 ("IDAPV","TEXT","PK","","","Idx",1,"","versao dos parametros de montagem",""),
 ("DsAPV","TEXT","-","","","Dsc",1,"","nome",""),
 ("DateIDAPV","DATE","-","","","Dsc",1,"","data",""),
 ("FixedGHGPerVehicle","REAL","-","","kg CO2e/veiculo","Exo",0,">=0","valor agregado quando Method='fixed'",""),
 ("Status","TEXT","-","","","Dsc",1,"recommended,legacy","situacao da versao",""),
 ("Method","TEXT","-","","","Dsc",1,"from_EF,process,fixed","de onde vem o valor da montagem",""),
 ("IDEFVdefault","TEXT","FK","P10.IDEFV","","Idx",0,"","versao de fatores a que corresponde",""),
 ("SourceAPV","TEXT","-","","","Dsc",1,"","fonte","")])
dd("P24","Energy Carrier List",[
 ("IDFuel","TEXT","PK","","","Idx",1,"","portador de energia",""),
 ("DsFuel","TEXT","-","","","Dsc",1,"","descricao","")])
dd("P25","Fuel Emission Factors",[
 ("IDFuel","TEXT","PK","P24.IDFuel","","Idx",1,"","portador",""),
 ("IDEFV","TEXT","PK","P10.IDEFV","","Idx",1,"","versao",""),
 ("EFfuel","REAL","-","","g CO2e/MJ","Exo",1,"","fator de emissao",""),
 ("EFfuelNotes","TEXT","-","","","Dsc",0,"","rastreabilidade","")])
dd("D04","User Emission Factor Version List",[
 ("IDEFV","TEXT","PK","","","Idx",1,"","versao criada pelo usuario; nao pode colidir com P10",""),
 ("DsEFV","TEXT","-","","","Dsc",1,"","nome",""),
 ("DateIDEFV","DATE","-","","","Dsc",1,"","data",""),
 ("GWPSet","TEXT","-","","","Dsc",1,"","conjunto de GWP",""),
 ("SourceEFV","TEXT","-","","","Dsc",1,"","fonte declarada pelo usuario",""),
 ("LicenseEFV","TEXT","-","","","Dsc",0,"","licenca declarada pelo usuario",""),
 ("BasedOnIDEFV","TEXT","FK","P10.IDEFV","","Idx",0,"","versao base herdada para os IDM nao informados","")])
dd("D05","User Emission Factors",[
 ("IDM","TEXT","PK","P09.IDM","","Idx",1,"","material",""),
 ("IDEFV","TEXT","PK","D04.IDEFV","","Idx",1,"","versao do usuario",""),
 ("EF","REAL","-","","conf. P09.EFBasis","Exo",1,">=0","fator informado pelo usuario",""),
 ("EFnotes","TEXT","-","","","Dsc",0,"","origem do valor","")])
dd("D01","Vehicle List",[
 ("IDV","INTEGER","PK","","","Idx",1,"","veiculo",""),
 ("DsV","TEXT","-","","","Dsc",1,"","nome",""),
 ("IDVPT","TEXT","FK","P12.IDVPT","","Idx",1,"","trem de forca",""),
 ("IDVDT","TEXT","FK","P13.IDVDT","","Idx",1,"","carroceria",""),
 ("IDVS","TEXT","FK","P14.IDVS","","Idx",1,"","porte",""),
 ("IDLR","TEXT","-","","","Idx",1,"Regular,Luxury","classificacao",""),
 ("IsUserDefined","INTEGER","-","","","Dsc",1,"0,1","1 se criado pelo usuario",""),
 ("NotesIDV","TEXT","-","","","Dsc",0,"","observacoes","")])
dd("D02","Vehicle Evaluation Criteria",[
 ("IDV","INTEGER","PK","D01.IDV","","Idx",1,"","veiculo",""),
 ("IDEA","INTEGER","PK","","","Idx",1,"","alternativa de avaliacao",""),
 ("IDMPV","INTEGER","FK","P05.IDMPV","","Idx",1,"","versao de parametros de massa",""),
 ("IDVMR","TEXT","FK","P15.IDVMR","","Idx",1,"","receita de materiais (prevalece sobre P15)",""),
 ("IDEFV","TEXT","FK","P10.IDEFV","","Idx",1,"","versao de fatores de emissao",""),
 ("IDAPV","TEXT","FK","P23.IDAPV","","Idx",1,"","versao de parametros de montagem",""),
 ("Boundary","TEXT","-","","","Idx",1,"MAT,MAT_ASM","fronteira do sistema",""),
 ("NotesIDEA","TEXT","-","","","Dsc",0,"","observacoes","")])
dd("D03","Vehicle Parameters Values",[
 ("IDV","INTEGER","PK","D01.IDV","","Idx",1,"","veiculo",""),
 ("IDVP","INTEGER","PK","P07.IDVP","","Idx",1,"","parametro",""),
 ("GC","REAL","-","","conf. P07.utVP","Exo/End",1,"","valor do parametro","conforme P07.GCEquation quando IsCalculated=1"),
 ("GCText","TEXT","-","","","Exo",0,"","valor textual (apenas IDVP 32)",""),
 ("IsCalculated","INTEGER","-","","","Dsc",1,"0,1","1 se endogeno","")])
CALC = [("C01","Mass Estimation per subgroup","IDV,IDEA,IDSG","ME","ME = MR*((GC/GCR)^Beta)*fLM"),
 ("C02","Mass per GREET group","IDV,IDEA,IDGG","MassIDGG","soma de C01.ME por IDGG; Iprinc = D03.GC(IDV,35)"),
 ("C03","Mass per material per group","IDV,IDEA,IDGG,IDM","MassIDMpGG","C02.MassIDGG * P16.MshareGG"),
 ("C04","GHG per material per group","IDV,IDEA,IDGG,IDM","GHGIDMpGG","C03.MassIDMpGG * P11.EF"),
 ("C05","GHG per group","IDV,IDEA,IDGG","GHGIDGG","soma de C04 por IDGG"),
 ("C06","Battery mass per material","IDV,IDEA,IDBMd,IDGG,IDM","MassIDMpGGB","D03.GC(IDV,35) * P20.BMshareGG"),
 ("C07","Battery GHG per material","IDV,IDEA,IDBMd,IDGG,IDM","GHGIDMpGGB","C06 * P11.EF; base conforme P09.EFBasis"),
 ("C08","Battery mass and GHG (view)","IDV,IDEA,IDBMd,IDGG,IDM","-","juncao C06 x C07"),
 ("C09","Material mass and GHG (view)","IDV,IDEA,IDGG,IDM","-","juncao C03 x C04"),
 ("C10","Mass and GHG per group","IDV,IDEA,IDGG","MassIDGG,GHGIDGG","C02 + C05/C07"),
 ("C11","Mass and GHG per material","IDV,IDEA,IDM","MassIDM,GHGIDM","soma de C03+C06 e C04+C07 por IDM"),
 ("C12","Mass and GHG per vehicle","IDV,IDEA","MassIDV,GHGIDV","soma de C10"),
 ("C13","Assembly GHG","IDV,IDEA,IDAP","GHGAssembly","P22 x P25 ou P23.FixedGHGPerVehicle"),
 ("C14","Cradle-to-gate total","IDV,IDEA","GHGCradleToGate","C12.GHGIDV + C13 conforme D02.Boundary")]

# ---------------------------------------------------------------- escrita
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(color="FFFFFF", bold=True)

out = openpyxl.Workbook()
out.remove(out.active)

def sheet(name, cols, data, nota=""):
    ws = out.create_sheet(name)
    ws.append(list(cols))
    for c in ws[1]:
        c.fill = HDR_FILL; c.font = HDR_FONT; c.alignment = Alignment(vertical="center")
    for r in data:
        ws.append([r.get(c) for c in cols])
    ws.freeze_panes = "A2"
    for i, c in enumerate(cols, 1):
        w = max(len(str(c)) + 2, 10)
        w = min(w, 42)
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    return ws

# Leia-me
ws = out.create_sheet("LEIAME")
info = [
 ["Base de Dados da Calculadora da Pegada de Carbono de Veiculos Leves - do Berco ao Portao"],
 ["Documento 3 de 4  -  versao 20260919a"],
 [""],
 ["Este arquivo e a base de dados revisada. Ele contem APENAS parametros (P) e dados de cenario (D)."],
 ["As tabelas calculadas (C) e de relatorio (R) sao geradas pelo programa e nao sao armazenadas aqui."],
 [""],
 ["Fonte: LVManufacturingMassGHGSimulator_20260919a.xlsx e LCA_LV_i3ET_20260919a.xlsx"],
 ["Regra de conflito: prevalece o modelo i3ET (diretriz D11 do Documento 1)."],
 ["Metrica: kg CO2e, GWP-100, IPCC AR6."],
 [""],
 ["Alteracoes em relacao a base original:"],
]
for m in log: info.append(["  - " + m])
info += [[""], ["Documentos relacionados:"],
 ["  Documento 1: EspecificacaoFuncional_CalculadoraBP_20260919a.md"],
 ["  Documento 2: DicionarioDeDados_ModeloRelacional_20260919a.md"],
 ["  Documento 4: EspecificacaoTecnica_ArquiteturaESaidas_20260919a.md"]]
for row in info: ws.append(row)
ws.column_dimensions["A"].width = 120
ws["A1"].font = Font(bold=True, size=13)

# Index
idx = [{"IDTable":"P01","TableName":"Data Dictionary","Prefixo":"P","Escrita":"referencia"}]
NOMES = {"D04":"User Emission Factor Version List","D05":"User Emission Factors","P02":"Vehicle Subgroup List","P03":"Generic Groups List","P04":"GREET Group List",
 "P05":"Mass Parameters List","P06":"Mass Estimation Parameters","P07":"Vehicle Parameters List",
 "P08":"Group and subgroup correlation","P09":"Material List","P10":"Emission Factors Version List",
 "P11":"Emission Factors values list","P12":"Power Train List","P13":"Design List","P14":"Size List",
 "P15":"Vehicle Material Recipe List","P16":"Vehicle Material Recipe per GREET group",
 "P17":"Battery Types","P18":"Battery Technologies per Type","P19":"Battery Models Parameters",
 "P20":"Battery Material Recipe per Model","P21":"Assembly Process List",
 "P22":"Assembly Energy and Fuel Shares","P23":"Assembly Parameters Version List",
 "P24":"Energy Carrier List","P25":"Fuel Emission Factors",
 "D01":"Vehicle List","D02":"Vehicle Evaluation Criteria","D03":"Vehicle Parameters Values"}
for k in sorted(NOMES):
    idx.append({"IDTable":k,"TableName":NOMES[k],"Prefixo":k[0],
                "Escrita":"referencia" if k[0]=="P" else "cenario do usuario"})
for t, n, pk, val, eq in CALC:
    idx.append({"IDTable":t,"TableName":n,"Prefixo":"C","Escrita":"gerada pelo programa"})
sheet("Index", ["IDTable","TableName","Prefixo","Escrita"], idx)

P01COLS = ["IDTable","ColumnName","ColumnOrder","SQLType","KeyRole","FKTarget","Unit",
           "ParamClass","Required","Domain","DsColumnName","ColumnCalculationFormula","TableName"]
sheet("P01", P01COLS, P01n)

sheet("P02", ["IDSG","DsSG"], P02)
sheet("P03", ["IDG","DsG"], P03)
sheet("P04", ["IDGG","DsGG","IsBattery"], P04)
sheet("P05", ["IDMPV","DsMPV","DateIDMPV","SourceMPV"], P05)
sheet("P06", ["IDMPV","IDSG","Beta","GCR","utGCR","MR","fLM","Reference"], P06)
sheet("P07", ["IDVP","DsVP","utVP","ParamClass","GCEquation","AppliesTo"], P07)
sheet("P08", ["IDSG","IDVP","IDG","IDGG","ExcludedVPT"], P08)
sheet("P09", ["IDM","DsM","Mspec","EFBasis","EFBasisParam","IsProcess","ShareRole"], P09)
sheet("P10", ["IDEFV","DsEFV","DateIDEFV","GWPSet","SourceEFV","LicenseEFV"], P10)
sheet("P11", ["IDM","IDEFV","EF","EFnotes"], P11)
sheet("P12", ["IDVPT","DsVPT"], P12)
sheet("P13", ["IDVDT","DsVDT"], P13)
sheet("P14", ["IDVS","DsVS"], P14)
sheet("P15", ["IDVMR","IDVPT","IDVDT","IDVS","DsVMR"], P15)
sheet("P16", ["IDVMR","IDGG","IDM","MshareGG"], P16)
sheet("P17", ["IDBTy","DsBTy"], P17)
sheet("P18", ["IDBTe","IDBTy","DsBTe"], P18)
sheet("P19", ["IDBMd","IDEFV","IDVPT","IDBTe","RefRange","RefEnergy","RefPower","RefWeight",
              "RefGHGIDBMd","EnergyDensity","PowerDensity","GravimetricEnergyDensity",
              "GravimetricPowerDensity","GravimetricGHGDensity","EnergyGHGDensity",
              "GHGMethod","DsBMd"], P19)
sheet("P20", ["IDBMd","IDGG","IDM","BMshareGG"], P20n)
sheet("P21", ["IDAP","DsAP","IncludedInA","NotesAP"], P21)
sheet("P22", ["IDAPV","IDAP","IDFuel","EnergyPerVehicle","FuelShare"], P22)
sheet("P23", ["IDAPV","DsAPV","DateIDAPV","Method","FixedGHGPerVehicle","Status","IDEFVdefault","SourceAPV"], P23)
sheet("P24", ["IDFuel","DsFuel"], P24)
sheet("P25", ["IDFuel","IDEFV","EFfuel","EFfuelNotes"], P25)
sheet("D04", ["IDEFV","DsEFV","DateIDEFV","GWPSet","SourceEFV","LicenseEFV","BasedOnIDEFV"], [])
sheet("D05", ["IDM","IDEFV","EF","EFnotes"], [])
sheet("D01", ["IDV","DsV","IDVPT","IDVDT","IDVS","IDLR","IsUserDefined","NotesIDV"], D01)
sheet("D02", ["IDV","IDEA","IDMPV","IDVMR","IDEFV","IDAPV","Boundary","NotesIDEA"], D02)
sheet("D03", ["IDV","IDVP","GC","GCText","IsCalculated"], D03n)

# esquema das tabelas calculadas (referencia, sem dados)
sheet("C_Schema", ["IDTable","TableName","ChavePrimaria","ColunasDeValor","Equacao"],
      [{"IDTable":t,"TableName":n,"ChavePrimaria":pk,"ColunasDeValor":val,"Equacao":eq}
       for t,n,pk,val,eq in CALC])

sheet("D03_antes_da_sincronizacao", ["IDV","IDVP","ValorAnterior","ValorNovo_i3ET"],
      [{"IDV": k[0], "IDVP": k[1], "ValorAnterior": v, "ValorNovo_i3ET": gc.get(k)}
       for k, v in sorted(D03_ANTES.items())])

sheet("BMshare86_original", ["IDBMd","BMshareGG_original","Observacao"],
      [{"IDBMd": k, "BMshareGG_original": v,
        "Observacao": "= GravimetricEnergyDensity (kWh/kg) x EF(86) de outra versao; "
                      "zerado na base, ver Documento 1 secao 16.1"} for k, v in sorted(ORIG86.items())])

sheet("Normalizacao", ["IDTable","Chave","SomaOriginal","FatorAplicado","DesvioOriginal_ppm"], NORM)

# cobertura de fatores de emissao
usados = {}
for r in P16:
    if (r.get("MshareGG") or 0) > 0:
        usados.setdefault(str(r["IDM"]), set()).add(("P16", r["IDVMR"], r["IDGG"]))
for r in P20n:
    if (r.get("BMshareGG") or 0) > 0:
        usados.setdefault(str(r["IDM"]), set()).add(("P20", r["IDBMd"], r["IDGG"]))
efmap = {(str(r["IDM"]), r["IDEFV"]): r["EF"] for r in P11}
dsm = {str(r["IDM"]): r.get("DsM") for r in P09}
COB = []
for v in sorted({r["IDEFV"] for r in P10}):
    for m in sorted(usados, key=lambda x: (len(x), x)):
        if not efmap.get((m, v)):
            COB.append({"IDEFV": v, "IDM": m, "DsM": dsm.get(m),
                        "GruposAfetados": len(usados[m]),
                        "Consequencia": "emissao contabilizada como zero"})
por_v = {}
for x in COB: por_v[x["IDEFV"]] = por_v.get(x["IDEFV"], 0) + 1
note("Cobertura de fatores: dos %d materiais com participacao > 0 nas receitas, ficam sem fator "
     "por versao: %s. Detalhe na aba CoberturaEF." % (len(usados), por_v))
piores = {}
for x in COB: piores[x["IDM"]] = max(piores.get(x["IDM"], 0), x["GruposAfetados"])
for m, n in sorted(piores.items(), key=lambda kv: -kv[1])[:4]:
    note("   IDM %s '%s' aparece em %d grupos e nao tem fator em ao menos uma versao"
         % (m, dsm.get(m), n))

sheet("CoberturaEF", ["IDEFV","IDM","DsM","GruposAfetados","Consequencia"], COB)

# log de verificacao
ver = [{"Verificacao": m} for m in log]
sheet("Verificacao", ["Verificacao"], ver)

out.save(OUT)
print("\nGravado:", OUT)
print("abas:", len(out.sheetnames))
