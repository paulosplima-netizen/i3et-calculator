"""Reposicoes (T16): eventos por quilometragem e paridade com o M2 T496 a T501, T495."""

from __future__ import annotations

import json
import os
import re
import sqlite3

import pytest

from core import maintenance as mt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
REF = os.path.join(REPO, "tests", "fixtures", "b1_reference.json")
LIFE = 200000.0


@pytest.fixture(scope="module")
def base():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = c.execute("SELECT * FROM P31_MaintenanceItem")
    nomes = [d[0] for d in cur.description]
    items = [dict(zip(nomes, r)) for r in cur]
    shares: dict[str, dict[str, float]] = {}
    for i, m, s in c.execute("SELECT IDMI, IDM, Share FROM P31b_MaintenancePartShare"):
        shares.setdefault(i, {})[m] = s
    ef = {m: e for m, e in c.execute(
        "SELECT IDM, EF FROM P11_EmissionFactor WHERE IDEFV='BR23' AND EF IS NOT NULL")}
    yield c, items, shares, ef
    c.close()


@pytest.fixture(scope="module")
def ref():
    with open(REF, encoding="utf-8") as fh:
        return json.load(fh)["m2_columns"]


def _idvmr(rec):
    """Nome da receita na linha 9 do M2 -> IDVMR de P15 (BISD e PBP_BISD perdem o prefixo)."""
    m = re.match(r"^(?:ICEV|HEV|SHEV|PHEV|BEV|FCV)-((?:PBP_)?BISD\d+s?)$", rec)
    return m.group(1) if m else rec


def _entradas(c, rec, rows, ef):
    rec = _idvmr(rec)
    fluidos = ("77", "78", "79", "80", "81", "82", "83")
    marcas = ",".join("?" * len(fluidos))
    sh = dict(c.execute("SELECT IDM, MshareGG FROM P16_MaterialShare WHERE IDVMR=? AND "
                        f"IDGG='K' AND IDM IN ({marcas})", (rec, *fluidos)))
    fm = {m: float(rows["81"]) * s for m, s in sh.items()}
    aux = sum(float(rows["78"]) * s * ef.get(m, 0.0) for m, s in c.execute(
        "SELECT IDM, MshareGG FROM P16_MaterialShare WHERE IDVMR=? AND IDGG='Iaux'", (rec,)))
    return fm, aux


# --------------------------------------------------------------------------
# Eventos
# --------------------------------------------------------------------------
@pytest.mark.parametrize("intervalo,vida,n", [
    (40000, 200000, 4), (50000, 200000, 3), (70000, 200000, 2), (150000, 200000, 1),
    (5000, 200000, 39), (10000, 200000, 19), (100000, 200000, 1), (40000, 150000, 3),
    (40000, 300000, 7), (200000, 200000, 0), (None, 200000, 0), (40000, 0, 0)])
def test_numero_de_eventos(intervalo, vida, n):
    assert mt.event_count(vida, intervalo) == n


def test_nenhum_evento_cai_na_vida_do_veiculo(base):
    _, items, shares, ef = base
    out = mt.replacements(items, life_km=LIFE, mode="Sim Bat", part_shares=shares, ef=ef,
                          fluid_mass={"77": 2.0}, group_ghg={"Iaux": 20.0, "Iprinc": 900.0})
    assert out["events"] and all(0 < e["EventKm"] < LIFE for e in out["events"])


def test_modos_de_manutencao(base):
    _, items, shares, ef = base
    kw = dict(life_km=LIFE, part_shares=shares, ef=ef, fluid_mass={"77": 2.0},
              group_ghg={"Iaux": 20.0, "Iprinc": 900.0})
    sim = mt.replacements(items, mode="Sim", **kw)
    bat = mt.replacements(items, mode="Sim Bat", **kw)
    nao = mt.replacements(items, mode="Não", **kw)
    assert nao["total"] == 0 and nao["events"] == []
    assert sim["components"]["traction_battery"] == 0
    assert bat["components"]["traction_battery"] == pytest.approx(900.0)   # 1 troca
    assert bat["total"] - sim["total"] == pytest.approx(900.0)
    with pytest.raises(ValueError):
        mt.replacements(items, mode="Talvez", **kw)


def test_vida_maior_gera_mais_eventos_e_item_inativo_nao_conta(base):
    _, items, shares, ef = base
    kw = dict(part_shares=shares, ef=ef, fluid_mass={"77": 2.0}, group_ghg={"Iaux": 20.0})
    a = mt.replacements(items, life_km=150000, mode="Sim", **kw)
    b = mt.replacements(items, life_km=300000, mode="Sim", **kw)
    pneus = lambda o: len([e for e in o["events"] if e["IDMI"] == "TIRE"])   # noqa: E731
    assert (pneus(a), pneus(b)) == (3, 7)
    sem_pneu = mt.replacements(items, life_km=LIFE, mode="Sim", active={"TIRE": False}, **kw)
    assert sem_pneu["components"]["tires"] == 0


def test_cenario_do_usuario_igual_a_referencia_reproduz_a_referencia(base):
    _, items, shares, ef = base
    kw = dict(life_km=LIFE, mode="Sim", part_shares=shares, ef=ef,
              fluid_mass={"77": 2.0}, group_ghg={"Iaux": 20.0})
    copia = [dict(i) for i in items]
    assert mt.replacements(copia, **kw)["total"] == mt.replacements(items, **kw)["total"]


# --------------------------------------------------------------------------
# Paridade com a planilha: colunas do M2 com receita em P15
#   Ficam de fora as colunas PBP_BISD (CX:DC), que tem pneus e bateria auxiliar
#   proprios na planilha, e as de receitas BISD9 e BISD11, que nao estao em P15.
# --------------------------------------------------------------------------
def _validas(c, ref):
    ids = {r[0] for r in c.execute("SELECT IDVMR FROM P15_VehicleMaterialRecipe")}
    return {col: d for col, d in ref.items()
            if "PBP_" not in d["recipe"] and _idvmr(d["recipe"]) in ids}


def test_parcelas_reproduzem_t496_t499_t501(base, ref):
    c, items, shares, ef = base
    cols = _validas(c, ref)
    assert len(cols) == 108
    for col, d in cols.items():
        r = d["rows"]
        fm, aux = _entradas(c, d["recipe"], r, ef)
        out = mt.replacements(items, life_km=LIFE, mode="Sim", part_shares=shares, ef=ef,
                              fluid_mass=fm, group_ghg={"Iaux": aux})["components"]
        assert out["tires"] == pytest.approx(r["496"], rel=1e-6), col
        assert out["aux_battery"] == pytest.approx(r["499"], rel=1e-6), col
        assert out["fluids"] == pytest.approx(r["501"], rel=1e-6), col


def test_t495_nos_tres_valores_do_seletor(base, ref):
    """Colunas que seguem o seletor P495: T495 = I x (T496 + T499 + J x T500 + T501)."""
    c, items, shares, ef = base
    n = 0
    for col, d in _validas(c, ref).items():
        r = d["rows"]
        base = r["496"] + r["499"] + r["501"]
        if not (abs(r["495"] - base) < 1e-6 or abs(r["495"] - base - r["500"]) < 1e-6):
            continue                      # formula antiga (B1-DIV-02): nao segue o seletor
        fm, aux = _entradas(c, d["recipe"], r, ef)
        trac = float(r["500"])
        for modo, i, j in (("Sim", 1, 0), ("Sim Bat", 1, 1), ("Não", 0, 0)):
            out = mt.replacements(items, life_km=LIFE, mode=modo, part_shares=shares, ef=ef,
                                  fluid_mass=fm, group_ghg={"Iaux": aux, "Iprinc": trac})
            esperado = i * (r["496"] + r["499"] + j * trac + r["501"])
            assert out["total"] == pytest.approx(esperado, rel=1e-6, abs=1e-9), (col, modo)
        n += 1
    assert n >= 70
