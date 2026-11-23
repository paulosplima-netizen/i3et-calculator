# Roteiro de teste manual do B2 (v0.12)

**Data:** 22/11/2026; revisto em 23/11/2026 (d: conferência de totais na T40) · Para o autor conferir no navegador antes da tag `v0.12.0`. Comando: `streamlit run app.py` na pasta do repositório. Use um projeto novo (T01). As tabelas de mercado (FENABRAVE, ANFAVEA, PBEV) aparecem só para quem entrou com uma conta Master (passo 0). Boletim FENABRAVE: o PDF da pasta Documentação; Anuário: `ANFAVEA_Anuário_2026.pdf`.

| # | Tela | O que fazer | O que deve acontecer |
|---|---|---|---|
| 0 | T01 | Antes de abrir o app, defina a senha de instalação: no PowerShell `$env:I3ET_MASTER_PASSWORD="sua-senha"` e depois `.\rodar_app.bat` (ou `master_password = "…"` em `.streamlit\secrets.toml`). Na T01, abra "Sign in · master access", aba "First master", informe e-mail, nova senha e a senha de instalação | Entra como Master ("Signed in as … · Master"); aparece "Manage users (master)". Depois disso a senha de instalação não é mais pedida |
| 0b | T01 | Sair ("Sign out"), criar uma segunda conta (aba "Create account") e abrir a T40 | A conta nova é User; a T40 diz que é só para o Master e não mostra tabelas nem campo de senha |
| 0c | T01 | Entrar de novo como Master, em "Manage users" escolher a segunda conta e "Make master"; depois "Make user" | O papel muda; o último Master não pode ser rebaixado ("The last master cannot be demoted") |
| 1 | T40 | Enviar o PDF do boletim FENABRAVE | As tabelas do boletim aparecem; a seleção "Table" lista os rankings de automóveis e comerciais leves |
| 2 | T40 | Ver "Needs attention" e "All" | Cada modelo tem uma linha por motorização; os totais por modelo batem com o boletim; a divisão mostra a origem (Reported, Previous, PBEV, Master, Base) |
| 3 | T40 | Em "Split by powertrain", ver o quadro "Check: bulletin totals × adopted units" e o "Check by model". Em um modelo (por exemplo HR-V), ajustar as unidades por motorização (Master) | As motorizações de cada modelo aparecem uma embaixo da outra e só a motorização muda. O quadro de totais mostra V, CL e V+CL (Bulletin, Adopted, Not in catalogue, Difference); com o boletim de dez/2025: V 1.872.220, CL 552.062, V+CL 2.424.282, e Difference = 0 em todas. Ao digitar um valor errado, a diferença aparece na hora (modelo e classe), o aviso fica vermelho e "Save edition" fica desabilitado |
| 3b | T40 | No topo da tela (edições gravadas), ver os totais adotados por classe | V 1.872.219; CL 552.062; V+CL 2.424.281 (o V do boletim tem 1 unidade a mais: SONG 42.181 no boletim e 42.180 no modelo) |
| 4 | T40 | "Save edition to the reference base" | A edição é gravada (commit do Master); "Export this split to Excel" baixa a divisão |
| 5 | T42 | Abrir Weighted references; ver os três níveis de cobertura | Seis referências = 2.008.914 (78,8% do mercado); ranking 50+50 = 2.424.281; total FENABRAVE = 2.549.462 |
| 6 | T42 | Escolher uma categoria (A0 a A5) | O veículo de referência ponderado aparece; compara com o valor do Excel (C33) |
| 7 | T42 | "Export comparison to Excel (Excel model × recalculation)" | O arquivo traz as duas versões; com tabelas do mesmo ano elas coincidem (60/60 no C33) |
| 8 | Importação ANFAVEA | Rodar `python tools/import_anfavea.py` com os textos dos Anuários 2025 e 2026 | P60 (393 linhas), P71 (175) e P72 (330) geradas sem erro |
| 9 | P72 | Conferir 2025, automóveis: Flex 1.592.071; BEV 79.714; PHEV 94.147; até 1.000 cc 1.078.308 | Valores iguais ao Anuário 2026 (2.2.8, 2.2.9, 2.2.10); a soma da 2.2.8 dá 1.997.264 |
| 10 | T42 | Em uma categoria, editar um segmento (por exemplo remover uma linha), "Save segments (master)" e depois "Restore the Excel model's segments" | Os parâmetros ponderados mudam ao salvar e voltam ao padrão do Excel ao restaurar (60/60) |
| 11 | T42 | Escolher outra motorização em "Powertrain of the reference"; ver "Market vehicles closest to the weighted reference" | No ICEV, A0 mostra ARGO e A5 mostra STRADA como mais próximos; a tabela deixa claro que é só ilustração |
| 12 | P72 | Conferir 1957 (automóveis, gasolina: 9.478, origem i3EF) e 2025 (95.421 do Anuário; 79.039 do i3EF só como comparação) | Antes de 2016 vale o i3EF; de 2016 em diante vale o Anuário |
| 13 | T42 | Ver o seletor "Sales year (FENABRAVE)" | Só 2025 aparece, como ano completo (padrão); o ano corrente parcial só aparece depois de importar um relatório de 2026, com o aviso de parcial |
| 14 | T40 | Importar um relatório mensal acumulado (por exemplo até março) e gravar | Fica adotado como a série do ano e a observação diz "dados parciais de janeiro a 03/…"; um relatório que não seja acumulado é recusado; um acumulado mais recente do mesmo ano substitui o anterior, que fica como histórico |
| 15 | Base | `python tools/load_b2.py` e conferir o final da saída | `foreign_key_check: 0 violações`, `integrity: ok`, ParamBaseHash `c972269f…` (mudou em 23/11 com o parâmetro `FRONTAL_AREA_FACTOR`; as tabelas do B2 não o alteram) |

Se algo falhar, anote o número do passo e a mensagem na tela.
