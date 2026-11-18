"""Receitas do usuario (T14): copia, I29, escolha em analise e igualdade com a base."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import analysis, calc, loader, project, run, user_recipes

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture()
def pj(tmp_path):
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    c = sqlite3.connect(path)
    project.create(c, "R")
    yield c, path
    c.close()


def _receita(c):
    return c.execute("SELECT IDVMR FROM P15_VehicleMaterialRecipe WHERE IDVMR LIKE 'ICEV%' "
                     "ORDER BY IDVMR LIMIT 1").fetchone()[0]


def test_copia_e_validacao_i29(pj):
    c, _ = pj
    base_id = _receita(c)
    user_recipes.copy_recipe(c, "U-1", base_id, "minha", "Paulo")
    assert user_recipes.check(c, "U-1") == []
    n16 = c.execute("SELECT COUNT(*) FROM P16_MaterialShare WHERE IDVMR = ?",
                    (base_id,)).fetchone()[0]
    assert c.execute("SELECT COUNT(*) FROM D14_UserMaterialShare WHERE IDVMRU = 'U-1'"
                     ).fetchone()[0] == n16
    linha = c.execute("SELECT d.IDGG, d.IDM, d.MshareGG FROM D14_UserMaterialShare d "
                      "JOIN P09_Material p USING (IDM) WHERE d.IDVMRU = 'U-1' AND "
                      "p.ShareRole = 'material' AND d.MshareGG > 0 LIMIT 1").fetchone()
    with pytest.raises(ValueError, match="fonte"):
        user_recipes.set_share(c, "U-1", linha[0], linha[1], linha[2] / 2)
    user_recipes.set_share(c, "U-1", linha[0], linha[1], linha[2] / 2, source="medicao")
    assert any("soma" in v for v in user_recipes.check(c, "U-1"))
    assert "U-1" not in user_recipes.valid_ids(c)
    assert user_recipes.normalize_group(c, "U-1", linha[0])
    assert user_recipes.check(c, "U-1") == []


def test_identificador_e_origem(pj):
    c, _ = pj
    with pytest.raises(ValueError, match="U-"):
        user_recipes.copy_recipe(c, "X1", _receita(c), "n")
    with pytest.raises(ValueError, match="origem"):
        user_recipes.copy_recipe(c, "U-2", "NAO-EXISTE", "n")
    user_recipes.copy_recipe(c, "U-2", _receita(c), "n")
    with pytest.raises(ValueError, match="ja existe"):
        user_recipes.copy_recipe(c, "U-2", _receita(c), "n")


def test_so_receita_valida_chega_ao_calculo_e_e_oferecida(pj):
    c, path = pj
    base_id = _receita(c)
    user_recipes.copy_recipe(c, "U-1", base_id, "ok")
    user_recipes.copy_recipe(c, "U-2", base_id, "rascunho")
    linha = c.execute("SELECT IDGG, IDM, MshareGG FROM D14_UserMaterialShare WHERE "
                      "IDVMRU = 'U-2' AND MshareGG > 0 AND IDM IN (SELECT IDM FROM "
                      "P09_Material WHERE ShareRole = 'material') LIMIT 1").fetchone()
    user_recipes.set_share(c, "U-2", linha[0], linha[1], linha[2] * 0.5, source="x")
    c.commit()
    base = loader.load_sqlite(path)
    ids = set(base["P15"]["IDVMR"])
    assert "U-1" in ids and "U-2" not in ids
    pt = c.execute("SELECT IDVPT FROM P15_VehicleMaterialRecipe WHERE IDVMR = ?",
                   (base_id,)).fetchone()[0]
    oferecidas = analysis.recipes_for(c, pt)
    assert "U-1" in oferecidas and "U-2" not in oferecidas


def test_receita_do_usuario_igual_a_base_reproduz_o_resultado(pj):
    c, path = pj
    base_id = _receita(c)
    user_recipes.copy_recipe(c, "U-1", base_id, "copia")
    c.commit()
    base = loader.load_sqlite(path)
    cen = base["D02"].iloc[0]
    idv = int(cen["IDV"])
    rows = base["D03"][base["D03"]["IDV"] == idv]
    gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
    supplied = {int(r["IDVP"]) for _, r in rows.iterrows() if not int(r["IsCalculated"] or 0)}
    hit = rows[rows["IDVP"] == 32]
    bid = hit.iloc[0]["GCText"] if len(hit) else None
    veic = base["D01"].set_index("IDV").loc[idv]
    ef = loader.effective_emission_factors(base)

    def calcular(rec):
        return calc.calculate_vehicle(
            base, gc, powertrain=veic["IDVPT"], battery_id=bid, idmpv=int(cen["IDMPV"]),
            idvmr=rec, idefv=cen["IDEFV"], idapv=cen["IDAPV"], boundary="MAT_ASM",
            ef_table=ef, supplied=supplied)
    a, b = calcular(base_id), calcular("U-1")
    assert b["totals"]["GHGCradleToGate"] == pytest.approx(a["totals"]["GHGCradleToGate"],
                                                           rel=1e-12)
    assert run is not None
