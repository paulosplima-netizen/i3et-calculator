# Glossário e rótulos das telas (português ↔ inglês)

A interface está em inglês; a documentação, em português. Esta tabela liga os dois.

| Tela | Rótulo na interface | Significado |
|---|---|---|
| T01 | Home | Início: projeto, tipo de análise, diagrama "How i3ET works" |
| T02 | Vehicle picker | Seletor de veículos do catálogo de mercado (P26) |
| T03 | Project Configuration | Configuração do projeto: modo, versões, casos, potência combinada |
| T04 | Selected Parameters | Parâmetros do Painel de Controle (P30) em três profundidades |
| T05 | Dashboard | Resultados de uma rodada congelada, cada número com selo |
| T06 | Multiple Projects | Rodadas de vários projetos lado a lado (somente leitura) |
| T07 | Equations & glossary | Equações (Documento 1) e este glossário |
| T08 | Export | Exportação da rodada ou do projeto, em JSON com hash |
| T09 | Market Vehicles | Veículos do catálogo de mercado |
| T10 | Vehicle parameters | Parâmetros de cada veículo |
| T11 | Default parameters | Regras que preenchem valores ausentes |
| T41 | Validate and Freeze Inputs | Verificações e congelamento da rodada |

| Termo | Significado |
|---|---|
| EC (Equalized comparison) | Comparação equalizada: seis motorizações de uma categoria |
| FC (Free comparison) | Comparação livre: de 1 a 7 veículos do mercado |
| Freeze and run | Congela as entradas (D09, com hash) e calcula (R45) |
| Seal | Selo de origem do valor: *Calculated*, *Excel reference* ou *Preview* |
| Calculated (run Sn) | Calculado pelo núcleo na rodada n |
| Excel reference | Valor lido da planilha i3ET, só para a configuração gravada |
| Preview | Prévia: nunca entra em relatório nem em exportação |
| Combined power | Potência combinada: P = kICE·P_ICE + kEE·P_EE |
| Default factors / Excel parity | Regra padrão (HEV e PHEV com 1;1, provisória) / pares ajustados à planilha |
| Restore default | Apaga a alteração do usuário e volta ao valor de referência |
| Read-only | Projeto de exemplo, ou mais de um projeto selecionado |
| ExportHash | SHA-256 do JSON canônico exportado, sem o próprio campo |
