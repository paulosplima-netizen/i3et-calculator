"""Bateria e montagem do usuario (T46): copias reproduzem a base; rascunho invalido nao chega."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import calc, loader, project, user_assets

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture()
def pj(tmp_path):
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    c = sqlite3.connect(path)
    project.create(c, "T46")
    yield c, path
    c.close()


def _caso(base):
    cen = base["D02"].iloc[0]
    idv = int(cen["IDV"])
    rows = base["D03"][base["D03"]["IDV"] == idv]
    gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
    supplied = {int(r["IDVP"]) for _, r in rows.iterrows() if not int(r["IsCalculated"] or 0)}
    hit = rows[rows["IDVP"] == 32]
    bid = hit.iloc[0]["GCText"] if len(hit) else None
    return cen, idv, gc, supplied, bid


def _calcular(base, bateria=None, montagem=None):
    cen, idv, gc, supplied, bid = _caso(base)
    veic = base["D01"].set_index("IDV").loc[idv]
    return calc.calculate_vehicle(
        base, gc, powertrain=veic["IDVPT"], battery_id=bateria or bid,
        idmpv=int(cen["IDMPV"]), idvmr=cen["IDVMR"], idefv=cen["IDEFV"],
        idapv=montagem or cen["IDAPV"], boundary="MAT_ASM",
        ef_table=loader.effective_emission_factors(base), supplied=supplied)


def test_bateria_do_usuario_igual_a_base_reproduz_o_resultado(pj):
    c, path = pj
    base0 = loader.load_sqlite(path)
    bid = _caso(base0)[4]
    if not bid or base0["P19"].set_index("IDBMd").loc[bid, "GHGMethod"] != "composition":
        bid = base0["P19"][base0["P19"]["GHGMethod"] == "composition"]["IDBMd"].iloc[0]
    user_assets.copy_battery(c, "UB-1", bid, "copia")
    c.commit()
    base = loader.load_sqlite(path)
    a, b = _calcular(base, bateria=bid), _calcular(base, bateria="UB-1")
    assert b["totals"]["GHGCradleToGate"] == pytest.approx(a["totals"]["GHGCradleToGate"],
                                                           rel=1e-12)


def test_bateria_invalida_nao_chega_ao_calculo(pj):
    c, path = pj
    bid = c.execute("SELECT m.IDBMd FROM P19_BatteryModel m WHERE GHGMethod = 'composition' "
                    "AND EXISTS (SELECT 1 FROM P20_BatteryMaterialShare s JOIN P09_Material p "
                    "USING (IDM) WHERE s.IDBMd = m.IDBMd AND p.ShareRole = 'material' "
                    "AND s.BMshareGG > 0) LIMIT 1").fetchone()[0]
    user_assets.copy_battery(c, "UB-1", bid, "x")
    linha = c.execute("SELECT IDGG, IDM, BMshareGG FROM D16_UserBatteryShare WHERE IDBMdU = "
                      "'UB-1' AND BMshareGG > 0 AND IDM IN (SELECT IDM FROM P09_Material "
                      "WHERE ShareRole = 'material') LIMIT 1").fetchone()
    user_assets.set_battery_share(c, "UB-1", linha[0], linha[1], linha[2] * 0.5)
    c.commit()
    assert user_assets.check_battery(c, "UB-1")
    assert "UB-1" not in set(loader.load_sqlite(path)["P19"]["IDBMd"])


def test_montagem_do_usuario_igual_a_base_reproduz_o_resultado(pj):
    c, path = pj
    base0 = loader.load_sqlite(path)
    apv = _caso(base0)[0]["IDAPV"]
    user_assets.copy_assembly(c, "UA-1", apv, "copia")
    c.commit()
    base = loader.load_sqlite(path)
    a, b = _calcular(base), _calcular(base, montagem="UA-1")
    assert b["totals"]["GHGAssembly"] == pytest.approx(a["totals"]["GHGAssembly"], rel=1e-12)


def test_prefixos_e_unicidade(pj):
    c, path = pj
    with pytest.raises(ValueError, match="UB-"):
        user_assets.copy_battery(c, "X", "G22-BEV", "n")
    with pytest.raises(ValueError, match="UA-"):
        user_assets.copy_assembly(c, "X", "A-EF", "n")
    with pytest.raises(ValueError, match="origem"):
        user_assets.copy_assembly(c, "UA-9", "NAO-EXISTE", "n")
