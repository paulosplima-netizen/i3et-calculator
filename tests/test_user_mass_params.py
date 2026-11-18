"""Parametros de massa do usuario (T13): copia igual a base reproduz C01; I58; previa."""

from __future__ import annotations

import os
import shutil
import sqlite3

import pytest

from core import calc, loader, project, user_mass_params as ump

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")


@pytest.fixture()
def pj(tmp_path):
    path = str(tmp_path / "p.sqlite")
    shutil.copy(DB, path)
    c = sqlite3.connect(path)
    project.create(c, "T13")
    yield c, path
    c.close()


def _calcular(base, idmpv):
    cen = base["D02"].iloc[0]
    idv = int(cen["IDV"])
    rows = base["D03"][base["D03"]["IDV"] == idv]
    gc = {int(r["IDVP"]): float(r["GC"] or 0.0) for _, r in rows.iterrows()}
    supplied = {int(r["IDVP"]) for _, r in rows.iterrows() if not int(r["IsCalculated"] or 0)}
    hit = rows[rows["IDVP"] == 32]
    bid = hit.iloc[0]["GCText"] if len(hit) else None
    veic = base["D01"].set_index("IDV").loc[idv]
    return calc.calculate_vehicle(
        base, gc, powertrain=veic["IDVPT"], battery_id=bid, idmpv=idmpv, idvmr=cen["IDVMR"],
        idefv=cen["IDEFV"], idapv=cen["IDAPV"], boundary="MAT_ASM",
        ef_table=loader.effective_emission_factors(base), supplied=supplied)


def test_previa_segue_a_formula():
    assert ump.preview(100.0, 2.0, 1.0, 1.0, 1.0) == pytest.approx(200.0)
    assert ump.preview(100.0, 4.0, 1.0, 0.5, 2.0) == pytest.approx(400.0)
    assert ump.preview(100.0, 1.0, 0.0, 1.0) == 0.0


def test_copia_igual_a_base_reproduz_a_massa_e_o_ghg(pj):
    c, path = pj
    base0 = loader.load_sqlite(path)
    idmpv = int(base0["D02"].iloc[0]["IDMPV"])
    ump.copy_version(c, "UM-1", idmpv, "copia")
    c.commit()
    base = loader.load_sqlite(path)
    a, b = _calcular(base, idmpv), _calcular(base, "UM-1")
    assert b["totals"]["MassIDV"] == pytest.approx(a["totals"]["MassIDV"], rel=1e-12)
    assert b["totals"]["GHGCradleToGate"] == pytest.approx(a["totals"]["GHGCradleToGate"],
                                                           rel=1e-12)


def test_edicao_muda_a_massa_e_i58_recusa_valores_invalidos(pj):
    c, path = pj
    idmpv = int(loader.load_sqlite(path)["D02"].iloc[0]["IDMPV"])
    ump.copy_version(c, "UM-1", idmpv, "copia")
    linha = c.execute("SELECT IDSG, Beta, GCR, MR, fLM FROM D21_UserMassParam WHERE "
                      "IDMPVU = 'UM-1' AND MR > 0 ORDER BY MR DESC LIMIT 1").fetchone()
    with pytest.raises(ValueError, match="I58"):
        ump.set_param(c, "UM-1", linha[0], beta=linha[1], gcr=0.0, mr=linha[3], flm=linha[4])
    ump.set_param(c, "UM-1", linha[0], beta=linha[1], gcr=linha[2], mr=linha[3] * 2,
                  flm=linha[4], reference="teste")
    c.commit()
    base = loader.load_sqlite(path)
    nova = _calcular(base, "UM-1")["totals"]["MassIDV"]
    assert nova > _calcular(base, idmpv)["totals"]["MassIDV"]
    with pytest.raises(ValueError, match="UM-"):
        ump.copy_version(c, "X", idmpv, "n")
