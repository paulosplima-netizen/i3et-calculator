# Roteiro de teste manual do B2 (v0.12)

**Data:** 22/11/2026 · Para o autor conferir no navegador antes da tag `v0.12.0`. Comando: `streamlit run app.py` na pasta do repositório. Use um projeto novo (T01). As tabelas de mercado (FENABRAVE, ANFAVEA, PBEV) aparecem só para o usuário Master. Boletim FENABRAVE: o PDF da pasta Documentação; Anuário: `ANFAVEA_Anuário_2026.pdf`.

| # | Tela | O que fazer | O que deve acontecer |
|---|---|---|---|
| 1 | T40 | Enviar o PDF do boletim FENABRAVE | As tabelas do boletim aparecem; a seleção "Table" lista os rankings de automóveis e comerciais leves |
| 2 | T40 | Ver "Needs attention" e "All" | Cada modelo tem uma linha por motorização; os totais por modelo batem com o boletim; a divisão mostra a origem (Reported, Previous, PBEV, Master, Base) |
| 3 | T40 | Em um modelo, ver as candidatas e ajustar as unidades por motorização (Master) | Todas as candidatas ficam visíveis; se a soma das variantes difere do total do boletim, "Save edition" fica desabilitado |
| 4 | T40 | "Save edition to the reference base" | A edição é gravada (commit do Master); "Export this split to Excel" baixa a divisão |
| 5 | T42 | Abrir Weighted references; ver os três níveis de cobertura | Seis referências = 2.008.914 (78,8% do mercado); ranking 50+50 = 2.424.281; total FENABRAVE = 2.549.462 |
| 6 | T42 | Escolher uma categoria (A0 a A5) | O veículo de referência ponderado aparece; compara com o valor do Excel (C33) |
| 7 | T42 | "Export comparison to Excel (Excel model × recalculation)" | O arquivo traz as duas versões; com tabelas do mesmo ano elas coincidem (60/60 no C33) |
| 8 | Importação ANFAVEA | Rodar `python tools/import_anfavea.py` com os textos dos Anuários 2025 e 2026 | P60 (393 linhas), P71 (175) e P72 (330) geradas sem erro |
| 9 | P72 | Conferir 2025, automóveis: Flex 1.592.071; BEV 79.714; PHEV 94.147; até 1.000 cc 1.078.308 | Valores iguais ao Anuário 2026 (2.2.8, 2.2.9, 2.2.10); a soma da 2.2.8 dá 1.997.264 |
| 10 | Base | `python tools/load_b2.py` e conferir o final da saída | `foreign_key_check: 0 violações`, `integrity: ok`, ParamBaseHash `401f68e3…` inalterado |

Se algo falhar, anote o número do passo e a mensagem na tela.
