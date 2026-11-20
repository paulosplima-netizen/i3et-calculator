# Roteiro de teste manual do B1 (v0.11)

**Data:** 19/11/2026 · Para o autor conferir no navegador antes da tag `v0.11.0`. Comando: `streamlit run app.py` na pasta do repositório (Windows: `C:\Users\pspli\Projetos\i3et-calculator`). Use um projeto novo (T01), não o exemplo.

| # | Tela | O que fazer | O que deve acontecer |
|---|---|---|---|
| 1 | T03 | Criar uma análise EC com a categoria padrão | A análise aparece; os campos Emission factors, Mass parameters e Assembly listam também as suas cópias, quando existirem |
| 2 | T41 | Validar e congelar | Sem erros; uma rodada `Frozen`; depois executar e ver o resultado |
| 3 | T12 | Abrir e procurar "Hybrid" | O IDSG 43 aparece como módulo de combinação híbrida; a legenda não fala em defeito da planilha |
| 4 | T13 | Copiar o conjunto de parâmetros (UM-1), mudar MR de um subsistema | A pré-visualização muda; a base não muda |
| 5 | T15 | Escolher uma lista Typed, corrigir um fator com motivo | Marca "Typed, altered"; o histórico mostra a alteração; a aba History exporta as correções em CSV |
| 6 | T15 | Aba "Versions & coverage": copiar uma lista para uma versão Typed | A cópia aparece como "Typed, derived from …" e é editável |
| 7 | T41 | Executar de novo a rodada congelada antes da correção do passo 5 | A execução é recusada com "I53"; congelar de novo resolve |
| 8 | T38 | Informar a massa declarada de um veículo e calibrar | O `s` padrão é o das massas estimadas; o aviso aparece só se a diferença para o GREET for de 5 pontos ou mais |
| 9 | T14 e T46 | Ver as participações de uma receita e de uma bateria | Participações com 2 casas decimais (formato padrão) |
| 10 | T47 | Escolher o perfil Custom, massa em t, separador decimal vírgula; salvar | T13, T14, T18, T38 e T46 passam a mostrar o novo formato; o relatório diz qual formato usou |
| 11 | T18 (Vehicle life) | Abrir uma rodada executada; percorrer as abas Life stages, By GREET group, By material, Battery e Assembly | Os quatro totais no topo aparecem; a produção inicial da aba Life stages é igual ao Cradle to gate; a soma das etapas fecha com o total; a unidade segue o formato do projeto; vindo do clique na T05, o veículo já vem escolhido |
| 12 | T08 | Exportar a rodada (JSON) | O arquivo baixa; o hash confere |

Se algo falhar, anote o número do passo e a mensagem na tela.
