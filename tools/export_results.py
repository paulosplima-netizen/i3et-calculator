"""Gerar e exportar todas as tabelas.

Documento 4, secao 6.1. E a mesma sequencia que o botao unico do aplicativo
vai executar, e por isso ela mora aqui e nao na interface:

    1. recalcular tudo a partir de D (nunca exportar cache)
    2. rodar os invariantes
    3. se houver ERRO: interromper; nada e exportado
    4. montar R00..R44
    5. gerar os formatos escolhidos
    6. gravar os arquivos

Uso:
    python tools/export_results.py [pasta] [--formatos xlsx,csv,html,pdf]
                                   [--csv-dialeto br|iso] [--forcar]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import calc, export, loader, report, validate  # noqa: E402
from core.log import Log  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(REPO, "data", "base_referencia.sqlite")
PREFIXO = "Resultados_CalculadoraBP"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pasta", nargs="?", default=os.path.join(REPO, "saidas"))
    ap.add_argument("--formatos", default="xlsx,csv,html,pdf")
    ap.add_argument("--csv-dialeto", default="br", choices=sorted(export.CSV_DIALECTS))
    ap.add_argument("--base", default=DB)
    ap.add_argument("--forcar", action="store_true",
                    help="exportar mesmo com erros de validacao (nao recomendado)")
    args = ap.parse_args(argv)
    formatos = [f.strip().lower() for f in args.formatos.split(",") if f.strip()]
    os.makedirs(args.pasta, exist_ok=True)

    base = loader.load_sqlite(args.base)
    log = Log()

    # 1 e 2 -- recalcular e validar, nesta ordem
    validate.check_base(base, log)
    resultados = calc.calculate(base, log=log)
    for (idv, idea), r in sorted(resultados.items()):
        validate.check_result(r, log, context=f"IDV {idv} / IDEA {idea}")

    erros = log.of("ERRO")
    print(f"validacao: {log.summary()}")
    for e in erros[:10]:
        print(f"   ERRO {e.rule}: {e.message}")
    if erros and not args.forcar:
        print("\nNada foi exportado. Corrija os erros ou use --forcar.")
        return 1

    # 4 -- montar as tabelas
    R = report.build(base, resultados, log=log)
    print(f"{len(R)} tabelas, {sum(len(df) for df in R.values())} linhas no total")

    # 5 e 6 -- gerar e gravar
    gerados = []
    if "xlsx" in formatos:
        gerados.append(export.to_xlsx(
            R, export.filename(PREFIXO, "xlsx", args.pasta)))
    if "csv" in formatos:
        gerados.append(export.to_csv_zip(
            R, export.filename(PREFIXO, "zip", args.pasta), dialect=args.csv_dialeto))
    html = None
    if "html" in formatos or "pdf" in formatos:
        html = export.to_html(R, export.filename(PREFIXO, "html", args.pasta))
        if "html" in formatos:
            gerados.append(html)
    if "pdf" in formatos and html:
        pdf = export.to_pdf(html, export.filename(PREFIXO, "pdf", args.pasta))
        if pdf:
            gerados.append(pdf)
        else:
            print("PDF nao gerado: WeasyPrint ausente neste ambiente. O HTML "
                  "traz a folha de estilo de impressao -- imprimir para PDF "
                  "pelo navegador produz o mesmo documento.")
        if "html" not in formatos and html and os.path.exists(html):
            os.remove(html)

    for g in gerados:
        print(f"gravado: {g}  ({os.path.getsize(g) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
