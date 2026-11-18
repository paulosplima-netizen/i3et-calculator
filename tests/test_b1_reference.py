"""Fixture de referencia do B1: coerencia interna dos valores lidos da planilha.

Estes testes nao exercitam o nucleo (que ainda nao tem o B1); garantem que a
fixture tem as identidades que o teste de paridade vai cobrar do aplicativo.
"""

import json
import os

import pytest

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "b1_reference.json")


@pytest.fixture(scope="module")
def ref():
    with open(REF, encoding="utf-8") as fh:
        return json.load(fh)


def _completas(ref, linhas):
    return {c: v for c, v in ref["m2_columns"].items()
            if all(str(r) in v["rows"] and isinstance(v["rows"][str(r)], float) for r in linhas)}


def test_total_m2_e_soma_das_parcelas(ref):
    """T511 = T495 + T509 + T510 + T516 + T560 + T571 + T617."""
    cols = _completas(ref, [495, 509, 510, 511, 516, 560, 571, 617])
    assert len(cols) >= 12
    for c, v in cols.items():
        r = {k: v["rows"][k] for k in v["rows"]}
        soma = sum(r[str(i)] for i in (495, 509, 510, 516, 560, 571, 617))
        assert soma == pytest.approx(r["511"], rel=1e-9), c


def _forma_t495(r, chave):
    """'seletor' (T495 = chave x (pneus + chumbo-acido + J x ion-litio + fluidos)),
    'antiga' (ion-litio sempre e fim de vida dentro de T495) ou None."""
    base = r["496"] + r["499"] + r["501"]
    if chave == "Não":
        return "seletor" if abs(r["495"]) < 1e-9 else None
    if abs(r["495"] - base) < 1e-6 or abs(r["495"] - base - r["500"]) < 1e-6:
        return "seletor"
    if abs(r["495"] - (base + r["500"] + r["509"])) < 1e-6:
        return "antiga"
    return None


def test_reposicoes_t495_formas(ref):
    """94 colunas usam a formula com a chave P495; 28 (GREET 2023 e BISD) usam uma
    formula antiga que ignora a chave e soma o fim de vida (T509) dentro de T495,
    contado de novo em T511 (divergencia B1-DIV-02). As colunas usadas pelo aplicativo
    (GREET 2022 e 2024 e SV1 a SV4) usam a chave."""
    cols = _completas(ref, [495, 496, 499, 500, 501, 509])
    forma = {c: _forma_t495(v["rows"], v["switch_P495"]) for c, v in cols.items()}
    assert sum(f == "seletor" for f in forma.values()) == 94
    antigas = sorted(c for c, f in forma.items() if f == "antiga")
    assert len(antigas) == 28
    assert {"AF", "AO", "CD", "CV"} <= set(antigas)
    for c in ("T", "AC", "AR", "CA", "FD", "FE", "FF", "FG"):
        assert forma[c] == "seletor", c


def test_massa_total_e_soma_dos_grupos(ref):
    cols = _completas(ref, [69] + list(range(70, 82)))
    assert len(cols) >= 4
    for c, v in cols.items():
        r = v["rows"]
        assert sum(r[str(i)] for i in range(70, 82)) == pytest.approx(r["69"], rel=1e-9), c


def test_calibracao_de_massa_sv1_a_sv4(ref):
    """FD628 + FD629 = A + B quando declarada = calculada; B/A = k (metodo P69)."""
    esperado_k = {"FD": 0.4801512287334592, "FE": 0.4929019363360543,
                  "FF": 0.48015122873345956, "FG": 0.4929019363360541}
    for c, k in esperado_k.items():
        m = ref["mass_calibration"][c]
        assert m["k"] == pytest.approx(k, rel=1e-12)
        assert m["B_sheet"] == pytest.approx(m["k"] * m["A_sheet"], rel=1e-9)
        assert m["declared_row35"] == pytest.approx(m["calc_row69"], rel=1e-12)
        assert m["A_sheet"] + m["B_sheet"] == pytest.approx(m["A_est"] + m["B_est"], rel=1e-9)
    # transferencia de massa do metodo da planilha (divergencia B1-DIV-01)
    m = ref["mass_calibration"]["FD"]
    assert m["A_est"] - m["A_sheet"] == pytest.approx(54.2, abs=0.05)


def test_br23_recomposta_e_parametros_do_painel(ref):
    cp, ef = ref["br23_control_panel"], ref["emission_factors_br"]
    assert cp["P123"] == cp["Z91"] and cp["P124"] == cp["Z92"] and cp["P133"] == cp["Z101"]
    assert ef["Z11"] == pytest.approx(cp["Z96"], rel=1e-12)      # aco, EF recomposto (Z11 = 3,0332)
    assert ef["Z18"] == pytest.approx(cp["Z102"], rel=1e-12)     # aluminio (8,3751)
    assert ef["AA11"] == pytest.approx(3.103833941176471, rel=1e-12)
    assert cp["Z74"] == 200.0 and cp["Z76"] == 0.2 and cp["Z77"] == 20.0   # vida util, fim de vida
