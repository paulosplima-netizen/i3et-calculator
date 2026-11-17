"""Selo de origem dos numeros exibidos (Fase A, passo 4).

Todo numero em tela pertence a uma de tres classes (docs/06, secao 7):

    Calculated      calculado pelo nucleo, em uma rodada
    ExcelReference  valor gravado no arquivo de referencia (so para a
                    configuracao gravada na planilha)
    Preview         estimativa sem motor; nao entra em relatorio nem exportacao

Uma funcao decide o selo; nenhuma tela escreve o selo por conta propria.

Blocos:
    PV1  classe do valor
    PV2  texto do selo

Este modulo nao importa streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass

CALCULATED = "Calculated"
EXCEL_REFERENCE = "ExcelReference"
PREVIEW = "Preview"
ORIGINS = (CALCULATED, EXCEL_REFERENCE, PREVIEW)

#: Nota para a celula que fica vazia (modulo ainda nao entregue).
NOT_AVAILABLE = "Available with M3/M4/M6"


@dataclass(frozen=True)
class Seal:
    origin: str | None     # None: celula vazia
    note: str | None = None


# --------------------------------------------------------------------------
# BLOCO PV1 -- classe do valor
#   Le      : P51.CalcStatus do indicador, se o caso e uma configuracao gravada
#             na planilha, se existe valor de referencia e se o valor e previa.
#   Devolve : Seal.
# --------------------------------------------------------------------------
def classify(calc_status: str, *, is_recorded_case: bool, has_reference: bool,
             is_preview: bool = False) -> Seal:
    """Classe de um valor de indicador.

    - Indicador que o nucleo calcula (`CalcStatus = Calculated`): Calculated.
    - Indicador so existente na planilha: ExcelReference, apenas para a
      configuracao gravada e se o valor de referencia existe; senao, vazio.
    - Previa explicita: Preview (vale mesmo para indicadores calculaveis).
    """
    if calc_status not in (CALCULATED, EXCEL_REFERENCE):
        raise ValueError(f"unknown CalcStatus: {calc_status!r}")
    if is_preview:
        return Seal(PREVIEW)
    if calc_status == CALCULATED:
        return Seal(CALCULATED)
    if is_recorded_case and has_reference:
        return Seal(EXCEL_REFERENCE)
    return Seal(None, NOT_AVAILABLE)


# --------------------------------------------------------------------------
# BLOCO PV2 -- texto do selo
#   Devolve : texto curto para st.caption ou cabecalho de coluna.
# --------------------------------------------------------------------------
def label(seal: Seal, run_seq: int | None = None) -> str:
    if seal.origin is None:
        return seal.note or ""
    if seal.origin == CALCULATED:
        return f"Calculated (run S{run_seq})" if run_seq else "Calculated"
    if seal.origin == EXCEL_REFERENCE:
        return "Excel reference"
    return "Preview"


def allowed_in_report(seal: Seal) -> bool:
    """Previas nao entram em relatorio nem em exportacao de resultados."""
    return seal.origin in (CALCULATED, EXCEL_REFERENCE)
