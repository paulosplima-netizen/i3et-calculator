# Roteiro de teste manual do B1 (v0.11)

**Data:** 19/11/2026; revisto em 20/11/2026 · Para o autor conferir no navegador antes da tag `v0.11.0`. Comando: `streamlit run app.py` na pasta do repositório (Windows: `C:\Users\pspli\Projetos\i3et-calculator`). Use um projeto novo (T01), não o exemplo.

| # | Tela | O que fazer | O que deve acontecer |
|---|---|---|---|
| 1 | T03 | Criar uma análise EC com a categoria padrão | A análise aparece; os campos Emission factors, Mass parameters e Assembly listam também as suas cópias, quando existirem |
| 2 | T41 | Validar e congelar | Sem erros; uma rodada `Frozen`; depois executar e ver o resultado |
| 3 | T12 | Procurar "Híbrida" (ou IDSG 43) na tabela e ler a legenda abaixo dela | A linha "Modulo de Combinação Híbrida (adicional de massa)" existe (nome em português, como no M1); a legenda em inglês fala em módulo de combinação híbrida e não em defeito da planilha |
| 4 | T13 | Copiar o conjunto de parâmetros (UM-1), mudar MR de um subsistema | A pré-visualização muda; a base não muda |
| 5 | T15 | Escolher uma lista Typed, corrigir um fator com motivo | Marca "Typed, altered"; o histórico mostra a alteração; a aba History exporta as correções em CSV |
| 6 | T15 | Aba "Versions & coverage": copiar uma lista para uma versão Typed | A cópia aparece como "Typed, derived from …" e é editável |
| 7 | T41 | Executar de novo a rodada congelada antes da correção do passo 5 | A execução é recusada com "I53"; congelar de novo resolve |
| 8 | T38 | Ver a coluna "Mass basis" da tabela; informar a massa declarada de um veículo e calibrar; marcar/desmarcar "Calibrate automatically…" | Veículo teórico (parâmetro 25 calculado): base `ESTIMATED_ITERATIVE`, sem rateio. Veículo de mercado com 25 informado: base `DECLARED_MARKET`, calibração automática depois de congelar e executar de novo. O `s` padrão é o das massas estimadas; o aviso aparece só se a diferença para o GREET for de 5 pontos ou mais |
| 9 | T14 e T46 | Ver as participações de uma receita e de uma bateria; na T14, escolher "All groups (vehicle bill of materials)" no dropdown Group, escolher a rodada e o veículo e marcar/desmarcar a bateria | Participações com 2 casas decimais (formato padrão). A lista acumulada mostra massa por material (veículo, bateria, total e participação); sem a bateria o total diminui; com ela, fecha com a massa do veículo na T18 (aba By material) |
| 10 | T47 | Escolher o perfil Custom (por exemplo, fator de emissão com 3 casas), massa em t, separador decimal vírgula; salvar | T13, T14, T15, T17, T18, T38 e T46, além de T05 e T06, passam a mostrar o novo formato; o relatório diz qual formato usou |
| 11 | T18 (Vehicle life) | Abrir uma rodada executada; percorrer as abas Life stages, By GREET group, By material, Battery e Assembly | Os quatro totais no topo aparecem; a produção inicial da aba Life stages é igual ao Cradle to gate; a soma das etapas fecha com o total; a unidade segue o formato do projeto; vindo do clique na T05, o veículo já vem escolhido |
| 12 | T08 | Exportar a rodada (JSON); depois "Prepare Excel, CSV and report" e baixar os três arquivos | O JSON baixa e o hash confere. Os três arquivos seguem o formato da T47 (Excel com o valor completo e o formato na célula; CSV com os separadores do projeto; relatório com a frase do formato); a validação aparece antes dos downloads |

Se algo falhar, anote o número do passo e a mensagem na tela.
