# Relatório de Divergências — anexo da Fase A

**Data:** 17/11/2026 · **Fonte:** `LCA_LV_i3ET_20261101.xlsx` · Complementa o `05-relatorio-de-divergencias.md`

O relatório principal é gerado por `tools/report_divergences.py` e trata da aderência do cálculo de massa e de emissões. Este anexo é escrito à mão: reúne o que os levantamentos da planilha para a Fase A encontraram, de 10 a 16/11/2026. Vale o mesmo princípio: **o i3ET em Excel não é alterado**; a calculadora adota a regra coerente e registra a diferença, para orientar ajustes futuros na planilha.

Cada item diz o que foi encontrado, o que a calculadora faz e o que se sugere para a planilha.

---

## A. Potência combinada (IDVP 15)

| # | Constatação | Na calculadora | Sugestão para o i3ET |
|---|---|---|---|
| A1 | A planilha não usa uma regra só. Na tabela de saídas da rodada equalizada, o PHEV soma os dois motores (90,08 + 90,08 = 180,16 kW), o HEV repete o motor a combustão (76,94) e SHEV e SPHEV repetem o motor elétrico (78,42 e 83,97). Na livre escolha, o PHEV usa 132 kW, que é o motor elétrico (o a combustão tem 81 kW) | A potência combinada é `FatorICE × P_ICE + FatorEE × P_EE`. Os fatores do HEV e do PHEV são arbitrados caso a caso para igualar a planilha (`P56`) e ficam provisórios até o fim da validação; o padrão (`P53`) é a soma; o usuário ajusta por caso (`D12`) | Adotar uma regra explícita, igual nos dois modos |
| A2 | Com a soma, o HEV equalizado da rodada gravada passa de 76,94 para 115,41 kW. O valor real fica entre a soma e o motor a combustão | Os fatores finais do HEV e do PHEV serão definidos depois da validação, pelo critério decidido pelo autor em 17/11 (abaixo, em *O que depende do autor*) | Avaliar fatores intermediários na planilha |
| A3 | A matriz de valores padrão (Market Vehicles P274:V274) indica `ICE` para ICEV e HEV e `BEE` para as demais, o que não coincide com A1 no PHEV equalizado | `P35` guarda a matriz como está; os fatores efetivos são os de `P53`, `P56` e `D12` | Alinhar a matriz à regra adotada |
| A4 | **O bloco auxiliar e a tabela de saídas divergem no PHEV equalizado de A0.** A tabela de saídas (BS10:BS12) grava ICE 90,08, EE 90,08 e combinada 180,16 kW (soma). O bloco auxiliar (Market Vehicles, linha A04) grava ICE 85,64, EE 85,64 e combinada 85,64 kW (um dos motores). Os valores de ICE e EE também diferem. É o mesmo tipo de divergência do BEV-A06 (C3) e pode vir do cálculo iterativo no arquivo salvo | O par arbitrado de A04 vem da tabela de saídas, que prevalece: (1; 1). A nota fica em `P56.NotesCPF` | Recalcular o arquivo com a iteração convergida |
| A5 | **PHEV equalizado das categorias A1 a A5.** O bloco auxiliar grava os dois motores com a mesma potência e a combinada igual a elas (por exemplo, A14: 112,87 kW nos três). Não há como saber, pelo valor, se a planilha usou o motor a combustão ou o elétrico. Se a soma valesse, como na tabela de saídas de A0, a combinada seria o dobro | Cinco casos `Tie` em `P56`, com o par (1; 0) e `IsProvisional = 1`. A potência combinada fica igual à gravada; o que se registra é a ambiguidade | **Decidido em 17/11 pelo autor:** o uso mais sustentável do PHEV evita os dois motores em paralelo; mantém-se o par provisório (1; 0) onde isso é coerente com a potência combinada informada |

## B. Regras de valor padrão (Market Vehicles M257:AW299)

Contagens sobre os 148 veículos reais, do levantamento de 10/11.

| # | Constatação | Na calculadora | Sugestão para o i3ET |
|---|---|---|---|
| B1 | Ar-condicionado (17): a fórmula compara o porte da linha anterior e tem uma referência sem travar. 34 veículos diferem da regra tabulada | `P35` traz a regra tabulada (versão `TAB`); o valor que a fórmula gravou está em `P27`, classe `Def`. A tela T11 mostrará os dois | Corrigir a fórmula |
| B2 | Instrumentação (22) e partida (18) testam uma coluna vazia nas linhas dos veículos. A instrumentação difere em 34 veículos; a partida não muda, porque o fator é igual nas três faixas | idem | Corrigir a referência |
| B3 | Vidros (13): não há regra para Van e Chassis. 25 veículos ficam com 0 m² | Van e Chassis entram no catálogo sem cálculo (`IsCalculable = 0`) | Incluir as duas carrocerias na matriz |
| B4 | Porte (44): a fórmula nunca atribui `Extralarge`, porque usa 8,5 m² como último corte. 19 veículos diferem; 20 têm área de 10,5 m² ou mais | `P35` traz as cinco faixas da matriz | Corrigir o último corte |
| B5 | Colunas calculadas com valor digitado por cima da fórmula: área (9) em 65 veículos, robustez (16) em 70, tamanho da carroceria (28) em 70, área frontal (50) em 73 | `P27` marca cada valor: `Calc` quando vem da fórmula, `Man` quando foi digitado | Decidir, por coluna, se o valor é calculado ou informado |
| B6 | A matriz não declara a ordem de precedência entre os critérios | Adotada a ordem luxo, motorização, carroceria, faixa de potência, porte, carroceria × porte, que reproduz as descrições do autor para os parâmetros 17 e 22 | Declarar a ordem na planilha |

## C. Control Panel

| # | Constatação | Na calculadora | Sugestão para o i3ET |
|---|---|---|---|
| C1 | O bloco Basic guarda valores próprios, diferentes dos do Expert, em quatro parâmetros: eletricidade 28,68 contra 25,64 g CO₂e/MJ; eficiência do ICEV 0,301 contra 0,24; densidade da bateria 0,17 contra 0,172 kWh/kg; intensidade de carbono da bateria 11,5 contra 9,6 kg CO₂e/kg | **Decidido em 17/11 pelo autor:** os valores padrão são os mesmos nos três perfis (Basic, Expert e Expanded); a diferença da planilha vem de uma simulação. `P30.BasicValue` continua gravado como a planilha o traz, mas não é usado: o valor efetivo é o de `DefaultValue` | Unificar os valores do bloco Basic aos do Expert |
| C2 | Três parâmetros têm o mínimo maior que o máximo (recíprocos de densidade de bateria). Dois digitáveis (`X64`, `X65`) valem zero, abaixo do mínimo. Um tem valor e mais frequente acima do máximo (55,8 contra 52,7) | Gravados como estão. Valor fora da faixa gera aviso e não bloqueia | Rever as faixas |
| C3 | BEV-A06: o bloco auxiliar da Market Vehicles guarda 79,6 kW, 53,8 kWh e 1.324 kg; a tabela de saídas guarda 83,6 kW, 68,4 kWh e 1.382 kg. Pode ser efeito do cálculo iterativo no arquivo salvo | `P52` guarda as duas referências. A paridade de massa usa a tabela de saídas | Recalcular e salvar com a iteração convergida |
| C4 | A célula AX17 do bloco Basic mostra `#REF!` | Sem efeito: o rótulo vem de outra célula | Corrigir a referência |
| C5 | No acumulado de emissões, o fim de vida entra inteiro no último ano (degrau no ano 14) | Registrado para o M4 | Avaliar a distribuição ao longo da vida |
| C6 | Trocar o combustível nos gráficos só é exato para o combustível escolhido; a planilha avisa | Cada combustível é uma rodada. A troca rápida na T05 é prévia | — |
| C7 | O nome da categoria e o porte do veículo SELEÇÃO não coincidem em três casos: A0 "Hatch Compact" tem SELEÇÃO `Subcompact`; A2 "Sedan Midsize" tem `Compact`; A3 "SUV Large" tem `Midsize` | `P29` guarda o porte do veículo | Alinhar os nomes |

## D. Fatores de emissão e receitas

| # | Constatação | Na calculadora | Sugestão para o i3ET |
|---|---|---|---|
| D1 | A rodada gravada usa a lista `BR23`, que a base da 0.9.0 não tinha. A planilha traz ainda `GLO23` e cinco variantes de `BR23` por motorização | As sete listas entraram em `P10` e `P11`, com a célula de origem. Conjunto de GWP `AR6-100`, confirmado pelo autor em 16/11. **Licença esclarecida em 17/11:** as listas foram publicadas com o relatório *Pegada de Carbono do Berço ao Portão* e disponibilizadas à AEA e ao governo federal, sem restrição de uso declarada e com a ressalva de como foram calculadas; o autor participou da elaboração de ambas e as usa conforme as recomendações do relatório. `P10.LicenseEFV` registra isso | — |
| D2 | **Alumínio e versões do GREET.** Até o G22 o GREET tem um só alumínio (forjado, IDM 4, 15,74 kg CO₂e/kg); do G23 em diante tem chapa (4a) e extrudado (4b), e as receitas seguem a mesma divisão. Na lista `G22` a planilha traz 15,74 para o IDM 4 e `ND` para 4a e 4b; a base da 0.9.0 trazia aí os valores do G23 (11,94; 11,94; 4,77). Os outros 309 fatores de `G22`, `G23` e `G24` são iguais | **Resolvido em 17/11 (decisão do autor).** `G22` foi corrigido para a planilha. `P57` liga o alumínio único a chapa e extrudado, com pesos 0,6206 e 0,3794 (média das 30 receitas da família GREET 2024, provisório). Quando a receita e a lista são de versões diferentes, `core/ef_equivalence.py` adapta o fator e registra o aviso I28: receita nova com lista antiga usa o fator único nos dois tipos; receita antiga com lista nova usa a média ponderada. Nenhuma das 68 receitas da base usa o IDM 4 (as colunas T a CA do M2 só têm chapa e extrudado), então só o primeiro caso ocorre hoje | Definir como converter entre versões do GREET |
| D3 | **Receitas da rodada gravada.** As configurações da rodada gravada usam receitas com o nome da configuração do GREET (`ICEV-G21`, `HEV-G22`, `PHEV-G23`, `BEV-G24`, e as séries `S`, `P`, `GL` e `PL`). A base só tem as duas famílias importadas em setembro (`BISD*` e `PBP_BISD*`) | **Resolvido em 17/11.** As 56 receitas do bloco T:CA do M2 (GREET 2022, 2023 e 2024, incluindo Fuel Cell) foram importadas para `P15` e `P16`, por decisão do autor de incluir na biblioteca todas as receitas da planilha, usadas ou não. Decisão de 16/11: a receita é escolha do usuário na parametrização, entre as associadas à motorização e ao porte | — |
| D4 | Cada lista nova tem 5 materiais sem fator (`ND`) | Gravados como ausentes, nunca como zero | — |
| D6 | **Modelos de bateria da rodada gravada.** A planilha usa `G24-HEV-Ni-MH`, `G24-PHEV50-NMC111` e `G24-BEV300-NMC111`. A base tem modelos do GREET 2022 e 2023 e os do Projeto do Berço ao Portão | **Resolvido em 17/11 (passo 5), por outro caminho (D12).** A tabela de saídas da rodada gravada não usa os modelos `G24-*`, e sim `PB-*-indefinido`; os `G24-*` ficam no bloco auxiliar. Importá-los para `P19` e `P20` fica para quando houver uma referência que os use | — |
| D7 | **Primeira conta do ICEV da rodada gravada (A01):** 1.087,25 kg e 4.527,4 kg CO₂e na calculadora, 1.083,03 kg e 4.513,84 kg CO₂e na planilha (0,4% e 0,3%) | **Resolvido em 17/11 (passo 5).** A causa estava nas entradas (D13 e D14), e não em `P06`. Com elas, massa e GEE das seis motorizações ficam dentro de 0,2% do Control Panel; sobra 1,5 kg no ICEV, atribuído ao fator do motor de partida | — |
| D8 | Nas receitas do GREET 2022 a 2024, 28 participações são negativas (resíduo de fechamento da linha *Others*), em 24 receitas: 12 nas de 2022 e 2023 e 16 nas de 2024 (séries `S` e `P`) | Entram como zero e o grupo é normalizado, como decidido em 20/09 | Fechar a soma sem resíduo negativo |
| D9 | As receitas dos híbridos em série não existem na família GREET: a planilha usa a do HEV no SHEV e a do PHEV no SPHEV | A tela oferecerá as do HEV ao SHEV e as do PHEV ao SPHEV | — |
| D5 | A platina vale 126,5 kg CO₂e/kg nas listas GREET e 69.670 na `BR23` (já registrado no relatório principal, §7.2) | Usa o fator da lista escolhida | — |
| D10 | **O i3ET trata `ND` como zero.** Com a lista `G22` e uma receita de 2023 em diante (chapa e extrudado), o Excel aloca zero aos dois tipos de alumínio, e o resultado fica abaixo do correto | Adota o fator do alumínio único e avisa (D2, I28) | Aplicar o mesmo critério, ou impedir a combinação |
| D11 | **Efeito de D2 nos doze veículos de referência.** BP01 a BP12 usam a lista `G22` com receitas `BISD`, que só têm alumínio chapa. Com 15,74 no lugar de 11,94, o GEE do berço ao portão sobe de 1,2% a 3,5%: BP01 4.075,0 para 4.191,5; BP02 4.249,6 para 4.377,4; BP03 4.644,7 para 4.807,9; BP04 8.316,7 para 8.421,3; BP05 12.880,6 para 13.031,6; BP06 10.028,2 para 10.149,9; BP07 4.708,1 para 4.844,9; BP08 5.225,7 para 5.387,8; BP09 5.354,0 para 5.506,9; BP10 6.760,9 para 6.905,4; BP11 8.126,3 para 8.324,8; BP12 7.260,6 para 7.441,6 kg CO₂e. A massa não muda | Regressão recongelada em 17/11 (hash `163fb8cc…`). Os números publicados da 0.9.0 diferem destes | **Aceito pelo autor em 17/11**, quando a lista `G22` é usada (o modelo em Excel dá preferência à lista `BR23`, que não cria o problema). Citar a diferença ao republicar os resultados do projeto |
| D12 | **Bateria de tração sem composição.** `PB-HEV-indefinido`, `PB-PHEV-indefinido` e `PB-BEV-indefinido` não têm linhas de material na guia de baterias do GREET: a massa é um parâmetro do Control Panel (X72, X70, X67, em kg/kW ou kg/kWh) vezes a potência elétrica (HEV, SHEV, FCEV) ou a energia (PHEV, SPHEV, BEV), e a pegada é a massa vezes a intensidade de carbono (X88, X86, X83). A rodada gravada usa o modelo do BEV também no PHEV e no SPHEV | Tabela `P58`; o rótulo do modelo escolhe a base de dimensionamento. Valores em `P30` e `D08` | Documentar o rótulo como escolha de dimensionamento, e não de química |
| D13 | **O M2 usa entradas diferentes do bloco auxiliar.** Em ET:EY o ar-condicionado do ICEV vale 14.000 (20.000 no bloco auxiliar), o fator de utilidades 0,6 em vez de 0,72 em quatro motorizações, a área de vidros 4 em vez de 0 nas híbridas e no BEV, e o motor de partida varia por motorização. O bloco auxiliar guarda outro estado do cálculo iterativo | `P52` ganha o conjunto `M2_IN` (228 valores, de `tools/extract_m2_inputs.py`) e a análise gravada o aplica entre `MV_AUX` e `CP_OUT_EC` | Registrar qual estado o arquivo salvo guarda, ou recalcular o bloco auxiliar |
| D14 | **Existência do módulo de combinação híbrida (IDVP 41).** O i3ET dá massa ao subgrupo "Módulo de Combinação Híbrida" no HEV (26,6 kg) e no PHEV (47,7 kg), com potência combinada e `GC(41) = 1`. A calculadora criava os veículos com `GC(41) = 0` e o módulo desaparecia | `analysis.create_ec` e `create_fc` gravam `IDVP 41` = 1 em HEV e PHEV e 0 nas demais | — |

## E. Rótulos e catálogo

| # | Constatação | Na calculadora | Sugestão para o i3ET |
|---|---|---|---|
| E1 | `Hatch` na planilha e `Hatchback` na base; `Extralarge` e `ExtraLarge` | Normalizados na extração | — |
| E2 | `Electricity` e `Eletricidade` convivem na coluna de combustível | Gravados como estão em `P27` | Unificar |
| E3 | MHEV e FCEV aparecem na Market Vehicles e não estão entre as motorizações calculadas | Entram em `P12` com `IsCalculable = 0` | — |
| E4 | O fator `fT` vai de 0,5 a 18, apesar do título "1,0 ou 1,2" | Gravado como está | Rever os valores ou o título |
| E5 | A busca do PBEV devolve sempre a primeira versão do modelo; 64 veículos têm mais de uma | `P50` guarda todos os registros de cada veículo e marca o que a planilha usa. A T10 deixará escolher | — |
| E6 | Grafia das misturas: o plano de telas escreve `B00`, `B10`, `B100`; a planilha escreve `Gas VMB B0` | **Decidido em 17/11 pelo autor** (nomenclatura abaixo); o código das misturas entra com o M4 | — |

---

## O que depende do autor

1. A2: depois da validação, os fatores de uso combinado de HEV e PHEV serão definidos assim (decidido em 17/11): nos veículos com potência combinada informada pelo fabricante, `FatorICE` = 1 e `FatorEE` = (P_comb − P_ICE) / P_EE; com os fatores calculados escolhe-se o padrão para os HEV e PHEV sem informação do fabricante. Valores fora de 0 a 1 serão listados para revisão.

**Nomenclatura das misturas (E6, decidida em 17/11).** Gás: `CNG` (*Compressed Natural Gas*, fóssil), `CBM` (*Compressed BioMethane*) e `VMB` (*Vehicular Methane Blend*, mistura de CNG e CBM), seguido de `B0` a `B100` para o teor de CBM em % do volume. Diesel: `B0` a `B100`, teor de biodiesel em % do volume. Gasolina: `E0` a `E99` indicam a mistura de etanol anidro na gasolina fóssil, em % do volume (`E1` ou `E01` até `E99`; `E0` é a gasolina fóssil pura); `E100` é outro combustível, o etanol hidratado puro, e não uma mistura. A letra `B` indica biometano no gás e biodiesel no diesel; o combustível-base distingue os dois.

Termos de uso da ANFAVEA: mesmo critério da FENABRAVE e do PBEV/INMETRO (citar a fonte, manter as unidades publicadas e registrar que nenhuma restrição foi encontrada), decidido em 17/11.

Resolvido em 17/11: D6 e D7 (passo 5); C1 (valores padrão iguais nos três perfis); E6 (nomenclatura das misturas); D2 (alumínio de `G22`, com o critério de equivalência entre versões); D11 (aceito); D1 (licença de `BR23` e `GLO23` esclarecida); FENABRAVE (fonte citada e quantidades importadas, não as participações; o commit pode ser feito quando o autor pedir); A5 (par (1; 0) mantido); significado da variante `L` das receitas GREET 2024 (*Large*, veículos grandes).
