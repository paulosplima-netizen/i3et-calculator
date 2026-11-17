# Fase A — navegação, projeto e análise (versão 0.10.0)
## Passo 1 do método: documentação suficiente para recriar o programa

17/11/2026 · versão h · Referência de validação: `LCA_LV_i3ET_20261101.xlsx` · Ponto de partida: i3ET Calculator 0.9.0

Este documento abre a adoção das **Interfaces Revisadas T01–T46 de 16/11/2026**. Ele especifica a Fase A inteira, no nível necessário para programá-la sem consulta adicional. Os passos 2 a 8 do método seguem este texto. Onde ele contrariar a planilha, a planilha prevalece e a diferença vai para o relatório de divergências.

Situação: **passo 1 concluído.** Os quatro pontos que estavam a confirmar foram respondidos pelo autor em 16/11 e estão incorporados (§12). Nenhum código foi alterado.

Versão de 17/11 (potência combinada): a regra de potência passa a ser a combinação `FatorICE × P_ICE + FatorEE × P_EE`, com fatores provisórios arbitrados para igualar a planilha (§6; tabelas `P53`, `P56` e `D12`).

Versão de 17/11 (alumínio): `P57` liga o alumínio único do GREET até 2022 a chapa e extrudado do GREET 2023 em diante, e `core/ef_equivalence.py` adapta os fatores quando a lista e a receita são de versões diferentes, com aviso (regra I28). A lista `G22` foi corrigida (divergência D2 do anexo `05a`).

Versão b: regra de potência configurável por motorização (§6, tabela `D12`); lista de fatores `BR23` extraída da planilha (§9); este pacote passa a ser a base e os anteriores foram para `Documentação/Versões anteriores`.

Versão de 17/11 (receitas): todas as receitas do bloco T:CA do M2 (GREET 2022, 2023 e 2024, com Fuel Cell) estão na base, 56 ao todo (§5.2). Antes disso, as da família GREET 2024 importadas; o §5.2, o §9, o §10 e o §11 refletem isso, e o §9 registra o que a primeira conta mostrou.

Versão d: a receita de materiais passa a ser escolha do usuário, por caso (§5.2 e T03); registradas três respostas do autor (§12, itens 5 a 7).

Versão c: alinhada ao que os passos 2 e 3 construíram. Mudaram o §5.4 (chave de `R45`), o §5.5 (tabelas `P54` e `P55`, `P13`, identificadores), o §9 (receitas da rodada gravada), o §10 (blocos de código como ficaram) e o §11 (situação dos passos).

---

## 1. O que foi decidido em 16/11

O autor aceitou as dez recomendações da avaliação de viabilidade. Em resumo:

| # | Decisão | Onde está aplicada |
|---|---|---|
| 1 | As Interfaces Revisadas são a especificação-alvo de navegação e funções, adotada em três fases | §2 |
| 2 | Potência combinada: fatores de uso combinado dos motores; o padrão de HEV e PHEV é a soma (provisório), *Excel parity* usa os fatores arbitrados para igualar o arquivo de 01/11 (revisto em 17/11) | §6 |
| 3 | Todo número em tela traz um selo de origem | §7 |
| 4 | O ID do projeto é neutro; o dono fica em campo próprio | §4.1 |
| 5 | Os dados do pacote HTML passam a ser gerados das fixtures | §10, bloco X |
| 6 | Matriz de paridade por tela, com os casos sem referência listados à parte | §9 |
| 7 | Contas, projetos no servidor e compartilhamento ficam para a Fase C | §2 |
| 8 | Comparação livre com 1 a 4 casos agora; 5 a 7 casos e misturas na Fase B | §5.2 |
| 9 | Edições importadas e referências do usuário nunca alteram a base imutável | Fase B |
| 10 | Corrigir as inconsistências do plano revisado e escrever o glossário | §3, §11 |

O plano revisado também respondeu a pontos que estavam em debate desde 10 e 11/11:

- O veículo de referência da comparação equalizada é o SELEÇÃO da categoria por padrão, e os ICEV elegíveis da categoria são alternativas.
- Combustível, norma de ensaio, curva de distância, lista de fatores, perfil e regra de potência ficam na T03.
- Expert é a referência quando os valores divergem. Basic pode ter edições próprias, que valem para a rodada e não mexem no Expert.
- Cada combustível é uma rodada. A troca rápida de combustível na T05 é prévia.
- O caso BEV-A06 conserva as duas referências da planilha até a reconciliação.
- A T05 tem quatro gráficos: composição de GEE, emissões acumuladas, massa × GEE e custo × GEE.
- As telas T39 a T46 entram no plano.

## 2. As três fases

| Fase | Conteúdo | Arquitetura |
|---|---|---|
| **A · 0.10.0** | Quatro menus; telas T01 a T11 e T41; tabelas D06 a D09, M03, P26 a P30, P35, P36, P49 a P53, P56, P57; comparação equalizada (EC) e livre (FC) | A atual: Streamlit, projeto em arquivo SQLite, base imutável, Streamlit Community Cloud. Sem contas |
| **B · módulos** | Um módulo por vez, pelos oito passos: complemento do M1–M2 (manutenção, fim de vida, validação de massa, baterias e montagem), importações PBEV e FENABRAVE, M3, M4, M5, M6. Depois sensibilidade, Monte Carlo e FCEV | A mesma |
| **C · contas** | Login por provedor externo, projetos no servidor, projetos master públicos, compartilhamento por link | Banco externo e autenticação OpenID Connect. O núcleo não muda |

A Fase A não calcula nada além do que o núcleo da 0.9.0 já calcula (massa e GEE do berço ao portão). O que ela entrega é a estrutura em que os módulos seguintes se encaixam: projeto, configuração da análise, catálogo de parâmetros, rodada congelada e painel.

## 3. Navegação

Quatro menus, com `st.navigation` em seções. Cada tela tem um só menu de origem. Os demais acessos são atalhos (`st.page_link`).

| Menu | Telas da Fase A | Arquivo |
|---|---|---|
| Home | T01 Home · T02 Vehicle picker · T03 Project Configuration | `pages/T01_Home.py`, `T02_Vehicle_picker.py`, `T03_Project_configuration.py` |
| Analysis Parameters Setup | T04 Selected Parameters · T10 Vehicle parameters · T11 Default parameters · T41 Validate and Freeze Inputs | `pages/T04_…`, `T10_…`, `T11_…`, `T41_…` |
| Results | T05 Dashboard · T06 Multiple Projects · T18 Manufacturing results (a tela Results da 0.9.0, sem mudança) | `pages/T05_…`, `T06_…`, `T18_…` |
| Auxiliary Data | T09 Market Vehicles · T15 Emission factors (a tela da 0.9.0, sem mudança) | `pages/T09_…`, `T15_…` |
| Acesso global | T07 Equations & glossary · T08 Export | `pages/T07_…`, `T08_…` |

Correspondência com a 0.9.0: `1_Home` vira T01; `2_Vehicles` vira T09; `3_Vehicle_parameters` vira T10; `4_Scenario` é absorvida pela T03; `5_Results` vira T18; `6_Emission_factors` vira T15; `7_Export` vira T08.

O menu só lista telas entregues. As telas das fases seguintes aparecem no diagrama da T01, com a situação do módulo.

Correções ao plano revisado:

- T38 tem origem em Results, com atalho em Auxiliary Data.
- T46 tem origem em Analysis Parameters Setup, com atalho em Auxiliary Data.
- T42 mantém as duas funções (veículos conceito e referências ponderadas) numa tela, com duas abas.
- A grafia das misturas foi decidida em 17/11 (`docs/05a`, E6): gás `CNG`, `CBM` e `VMB` com `B0` a `B100` (teor de CBM); diesel `B0` a `B100` (biodiesel); gasolina `E0` a `E99` (etanol anidro na gasolina fóssil; `E0` = gasolina pura) e `E100` = etanol hidratado puro. Misturas em % do volume. O código entra com o M4.

## 4. Projeto

### 4.1 Identidade — tabela `M03_Project`

O projeto continua sendo um arquivo SQLite que o usuário baixa e reabre. Ele ganha uma identidade própria.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `ProjectID` | TEXT | PK | S | Identificador neutro e estável: `PRJ-` mais oito caracteres aleatórios (letras maiúsculas e dígitos). Não contém login, nome nem data |
| `ProjectName` | TEXT | — | S | Nome dado pelo usuário. Pode mudar |
| `Domain` | TEXT | — | S | `LV` (veículos leves). Pesados e frota são futuros |
| `OwnerLabel` | TEXT | — | N | Rótulo de quem criou, informado pelo usuário. Não é credencial |
| `CreatedAt` | TEXT | — | S | Data e hora ISO 8601 |
| `CopiedFromProjectID` | TEXT | — | N | Projeto de origem quando criado por *Save as* |
| `SchemaVersion` | TEXT | — | S | Versão do esquema do arquivo (`0.10`) |
| `IsExample` | INTEGER | — | S | 1 para os projetos de exemplo distribuídos com o programa |

A tabela tem uma linha só. `M01_RunMetadata` e `M02_ValidationLog` não mudam.

**Migração.** Um projeto da 0.9.0 aberto na 0.10.0 recebe `M03` e as tabelas novas vazias. Seus veículos e cenários (`D01` a `D05`) ficam como estão e continuam calculáveis pela T18.

### 4.2 Edição e leitura

| Situação | Comportamento |
|---|---|
| Um projeto próprio aberto | Edição |
| Projeto de exemplo (`IsExample = 1`) | Leitura. *Save as* cria uma cópia editável, com novo `ProjectID` e `CopiedFromProjectID` preenchido |
| Dois ou mais projetos selecionados na T01 | Todos em leitura. Serve à comparação na T06 |

Em leitura, os controles de entrada ficam desabilitados e a tela mostra o motivo numa linha (`st.info`).

Os projetos de exemplo fazem, na Fase A, o papel dos projetos master. Ficam em `data/examples/`. O primeiro reproduz a rodada gravada na planilha: categoria A0, SELEÇÃO HATCH C, etanol E100, NBR, lista BR23.

## 5. Análise

### 5.1 Configuração — tabela `D06_Analysis`

Um projeto tem uma análise na Fase A. A chave `IDA` já permite mais de uma.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDA` | INTEGER | PK | S | Análise |
| `DsA` | TEXT | — | S | Nome |
| `Mode` | TEXT | — | S | `EC` (comparação equalizada) ou `FC` (comparação livre) |
| `AnalysisType` | TEXT | — | S | `GHG_LCA_LCC` (padrão). `SENSITIVITY`, `MONTE_CARLO` e `LIGHTWEIGHTING` existem no domínio e ficam desabilitados até a fase correspondente |
| `IDVC` | TEXT | FK→P29 | EC | Categoria A0 a A5 (Control Panel Z11) |
| `IDMVRef` | INTEGER | FK→P26 | EC | ICEV de referência. Padrão: o SELEÇÃO da categoria |
| `FuelScenario` | TEXT | — | S | Combustível da rodada (Control Panel Z19). Vira FK→P41 com o M4 |
| `TestNorm` | TEXT | — | S | `NBR`, `EPA`, `NEDC` ou `WLTC` |
| `DistanceCurve` | TEXT | — | S | Curva de distância diária |
| `IDEFV` | TEXT | — | S | Versão dos fatores de emissão dos materiais (P10 ou D04) |
| `IDMPV` | INTEGER | FK→P05 | S | Versão dos parâmetros de massa |
| `IDAPV` | TEXT | FK→P23 | S | Versão dos parâmetros de montagem |
| `Boundary` | TEXT | — | S | `MAT` ou `MAT_ASM` |
| `SPHEVEco` | INTEGER | — | S | 0 ou 1 |
| `LightweightingOn` | INTEGER | — | S | 0 ou 1. Fica em 0 até o M5 |
| `ParamProfile` | TEXT | — | S | `Basic`, `Expert` (padrão) ou `Expanded` |
| `CombinedPowerRule` | TEXT | — | S | `Default` (padrão) ou `ExcelParity`. Ajuste por caso em `D12` (§6) |
| `NotesIDA` | TEXT | — | N | Observações |

`IDVC` e `IDMVRef` são obrigatórios em `EC` e nulos em `FC`. A T03 absorve a tela Scenario: `IDEFV`, `IDMPV`, `IDAPV` e `Boundary` passam a ser escolhidos uma vez por análise e copiados para `D02` de cada caso. A receita de materiais (`IDVMR`) continua por veículo.

### 5.2 Casos — tabela `D07_AnalysisVehicle`

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDA` | INTEGER | PK, FK→D06 | S | Análise |
| `IDCase` | INTEGER | PK | S | Ordem do caso, de 1 a 7 |
| `CaseKey` | TEXT | — | S | Rótulo estável: `A01`…`A56` em EC (letra, dígito da categoria, ordem da motorização); `SV1`…`SV7` em FC |
| `CaseRole` | TEXT | — | S | `REF` (ICEV de referência), `EQ` (motorização equalizada) ou `FC` |
| `IDVPT` | TEXT | FK→P12 | S | Motorização |
| `IDMV` | INTEGER | FK→P26 | N | Veículo de mercado de origem |
| `IDV`, `IDEA` | INTEGER | FK→D02 | S | Veículo e alternativa do projeto que o núcleo calcula |
| `FuelBlend` | TEXT | — | N | Combustível ou mistura do caso. Nulo herda `D06.FuelScenario` |
| `IDPBE` | TEXT | FK→P36 | N | Edição do PBEV usada |
| `SizingOrigin` | TEXT | — | S | `Manufacturer`, `ExcelReference`, `Calculated` ou `Pending` |

Regras:

- **EC** tem exatamente seis casos, um por motorização, na ordem ICEV, HEV, SHEV, PHEV, SPHEV, BEV. O primeiro é `REF`.
- **FC** tem de um a sete casos no esquema. A tela aceita até quatro na Fase A (limite em `config/app.toml`, chave `fc_max_cases`). Um veículo pode aparecer em mais de um caso.
- Criar um caso cria o veículo em `D01`, seus parâmetros em `D03` e sua alternativa em `D02`. Apagar o caso apaga os três.

**Receita de materiais do caso** (decisão de 16/11). A receita é escolha do usuário, feita na parametrização, caso a caso. As receitas de `P15` estão associadas à motorização e ao porte do veículo, e é por essa associação que a tela as oferece:

- a lista de cada caso traz as receitas da motorização do caso, com as da mesma carroceria e porte primeiro. SHEV recebe também as receitas do HEV, e SPHEV as do PHEV, que é o que a planilha faz;
- a receita inicial é a que a planilha nomeia para a configuração, quando o caso vem da rodada gravada; nos demais, a primeira da lista;
- a escolha fica em `D02.IDVMR` do veículo do caso e é congelada na rodada;
- sem receita compatível, a tela avisa e lista todas, como a tela Scenario da 0.9.0 já faz.

As 56 receitas do bloco T:CA do M2 estão em `P15` e `P16` desde 17/11: 10 do GREET 2022 (`ICEV-G01` a `FCV-G10`), 10 do GREET 2023 (`ICEV-G11` a `FCV-G20`) e 36 do GREET 2024 (séries `G`, `S`, `P`, com as variantes `L`), incluindo as de Fuel Cell (`FCV-*`, motorização `FCEV`, sem cálculo). Entraram todas, usadas ou não, por decisão do autor. Com as 12 da 0.9.0, a base tem 68 receitas.

**De onde vem o dimensionamento em EC.** Potência do motor a combustão, potência do motor elétrico, gerador e energia da bateria das cinco motorizações equalizadas são resultado do M3, que ainda não existe. Na Fase A:

- Para as 36 configurações gravadas na planilha (bloco auxiliar da Market Vehicles, B164:DC204), o aplicativo usa os valores gravados, com `SizingOrigin = ExcelReference`. O núcleo calcula massa e GEE de fabricação a partir deles.
- Se o usuário troca o ICEV de referência por outro que não o SELEÇÃO, ou altera parâmetro que afeta o dimensionamento, as cinco motorizações ficam `Pending`. A tela diz que dependem do M3 e calcula só o caso `REF`.

Em FC, os parâmetros vêm do catálogo (`Manufacturer`) e o cálculo de massa e GEE de fabricação é completo.

### 5.3 Catálogo de parâmetros — `P30_ControlParam` e `D08_ControlParamValue`

`P30` tem um registro por parâmetro escalar do Control Panel. A extração de 11/11 contou **205** parâmetros: 12 no nível Basic, 108 no Expert e 85 no Expanded; 139 digitáveis e 66 calculados; sete seções (UPP, PET, LMP, FEF, MEF, AUC, LWP).

| Coluna de `P30` | Descrição |
|---|---|
| `IDCP` (PK) | Código do parâmetro, como `X23` |
| `Cell` | Célula no Control Panel |
| `Section`, `Level` | Seção e nível (`B`, `E`, `X`) |
| `DsCP`, `utCP` | Nome e unidade |
| `IsCalculated` | 1 quando a planilha o calcula |
| `DefaultValue`, `DefaultText` | Valor do Expert no arquivo de 01/11 |
| `BasicValue` | Valor próprio do bloco Basic, quando existe (o bloco tem nove valores, em AY18:AY29) |
| `MinValue`, `MostFrequent`, `MaxValue`, `Distribution`, `StdDev` | Faixa e distribuição |
| `Reference` | Fonte bibliográfica |
| `UsedByModule` | Módulo que consome o parâmetro (`M1M2`, `M3`, `M4`, `M5`, `M6`). Preenchido no passo 3 |

`D08` guarda só o que o usuário alterou. Chave: (`IDA`, `IDCP`, `Profile`). Colunas: `Value`, `ValueText`, `ValueSource` (obrigatória: de onde veio o valor) e `UpdatedAt`.

**Valor efetivo** de um parâmetro numa análise:

1. o valor em `D08` para o perfil ativo, se existir;
2. senão, `P30.DefaultValue`, que é o mesmo nos três perfis (decisão de 17/11; `P30.BasicValue` fica gravado como na planilha e não é usado).

Valor fora da faixa gera aviso e não bloqueia. Parâmetro calculado não tem campo de entrada. Parâmetro cujo módulo ainda não existe é gravado e congelado, e a tela diz *Recorded — not used until M3* (ou o módulo correspondente).

### 5.4 Rodada — `D09_Run`, `R45_PowertrainSummary`, `R46_RunComparison`

A rodada congela o que entrou no cálculo.

| Coluna de `D09` | Descrição |
|---|---|
| `RunID` (PK, FK→M01) | Execução |
| `IDA` (FK→D06), `RunSeq` | Análise e número de ordem (`S1`, `S2`, …) |
| `FrozenAt` | Data e hora |
| `InputSnapshot` | JSON canônico com a linha de `D06`, os casos de `D07` com os parâmetros de cada veículo, os valores efetivos dos 205 parâmetros, a regra de potência e as versões |
| `InputHash` | SHA-256 de `InputSnapshot` |
| `ParamBaseHash` | Impressão digital da base |
| `ReferenceWorkbook`, `CalculatorVersion` | Arquivo de validação e versão do programa |
| `Status` | `Frozen`, `Calculated` ou `Failed` |

`R45` guarda o resultado da rodada: chave (`RunID`, `CaseKey`, `IDInd`), com a motorização do caso, `Value`, `ValueText` e `ValueOrigin` (`Calculated`, `ExcelReference` ou `Preview`). `IDInd` vem de `P51_OutputIndicator`, o catálogo das linhas da tabela de saídas (Control Panel BN7:BU56).

A chave usa o rótulo do caso, e não a sua ordem em `D07`, para que o resultado de uma rodada congelada não dependa de casos que o usuário pode alterar depois. `R45` fica gravada no arquivo de projeto. É exceção deliberada à regra de que tabelas `R` são derivadas: uma rodada congelada tem de sobreviver a uma troca de base. `R46` é uma visão que põe rodadas lado a lado.

Duas rodadas com o mesmo `InputHash` e o mesmo `ParamBaseHash` têm de dar os mesmos números. Esse é um teste.

### 5.5 Tabelas de parâmetros novas

O detalhe de colunas está no dicionário de dados (`docs/07`), e a origem de cada tabela, em `docs/08`. `IDMV` e `IDPBR` são o número da linha na planilha. Conteúdo:

| Tabela | Conteúdo | Origem na planilha |
|---|---|---|
| `P26_MarketVehicle` | 154 veículos, incluindo os seis SELEÇÃO | Market Vehicles, linhas 7–161 |
| `P54_MarketParam` | Catálogo dos 58 parâmetros da planilha, com o `IDVP` de `P07` nos parâmetros 2 a 40 | Market Vehicles N4:BS6 |
| `P27_MarketVehicleParam` | Parâmetros 1 a 58 por veículo, com a classe do valor (fabricante, padrão, calculado, PBEV, média, representativo) | Market Vehicles N:BS |
| `P28_PBEVRecord`, `P36_PBEVEdition`, `P55_PBEVRecordValue` | 843 registros da edição 2026; os 25 campos de cada um ficam em formato longo, porque as colunas mudam de uma edição para outra | PBEV - INMETRO - 2026 |
| `P50_MarketVehiclePBEV` | Vínculo veículo–registro por edição | Market Vehicles BT:CV |
| `P29_VehicleCategory` | Seis categorias, SELEÇÃO e veículo representativo de cada uma | Control Panel X12:Z17 |
| `P30_ControlParam` | §5.3 | Control Panel |
| `P35_VehicleParamDefaultRule`, `P49_DefaultRuleVersion` | Regras de valor padrão, uma por célula preenchida da matriz (91 regras; versão `TAB`). A versão `FML`, o que as fórmulas gravaram, não tem regras: está em `P27`, classe `Def` | Market Vehicles M257:AW299 |
| `P51_OutputIndicator` | Indicadores da tabela de saídas | Control Panel BN7:BU56 |
| `P52_ExcelReferenceValue` | Valores gravados, com a célula: saídas da rodada gravada e dimensionamento das 40 configurações | Control Panel; Market Vehicles B164:DC204 |
| `P53_CombinedPowerRule`, `P56_CombinedPowerFit` | §6 | Control Panel linha 12 (BP12:BU12, BF12:BI12); Market Vehicles B164:DC204 |
| `P12_Powertrain`, `P13_DesignType` (ampliar) | Coluna `IsCalculable`: MHEV, FCEV, Van e Chassis entram no catálogo com 0. Descrições das motorizações no lugar do marcador provisório (redação do passo 3, a revisar) | Market Vehicles |
| `P10_EFVersion`, `P11_EmissionFactor` (ampliar) | Sete listas de fatores: `GLO23`, `BR23` e cinco variantes | Emission Factors GREET and BR |

## 6. Potência combinada (IDVP 15)

Decisão de 17/11/2026. A potência combinada deixa de ser uma regra escolhida entre fórmulas (soma, maior valor) e passa a ser uma combinação ponderada dos dois motores, com dois parâmetros, os **fatores de uso combinado**:

```
P_combinada = FatorICE × P_ICE + FatorEE × P_EE
```

`P_ICE` é a potência do motor a combustão (IDVP 2) e `P_EE` a do motor elétrico (IDVP 3). `FatorICE` é o fator de uso combinado do motor a combustão; `FatorEE`, o do motor elétrico. Cada um vai de 0 a 1.

| Motorização | FatorICE | FatorEE | Ajustável |
|---|---|---|---|
| ICEV | 1 | 0 | não |
| BEV, FCEV, SHEV, SPHEV | 0 | 1 | não |
| HEV, PHEV | 1 | 1, **provisório** | sim |

Nos híbridos em série (SHEV e SPHEV) só o motor elétrico traciona, e no ICEV só o motor a combustão; por isso esses pares são fixos.

**Valores provisórios.** Até terminar a validação que compara o aplicativo ao modelo em Excel, os fatores do HEV e do PHEV são arbitrados caso a caso para que a potência combinada do aplicativo bata com a da planilha:

| O que a planilha fez no caso | FatorICE | FatorEE | `FitKind` |
|---|---|---|---|
| Somou os dois motores | 1 | 1 | `Sum` |
| Usou o motor a combustão | 1 | 0 | `ICE` |
| Usou o motor elétrico | 0 | 1 | `EE` |
| Os dois motores têm a mesma potência e a combinada é igual a ela (não dá para saber qual foi usado) | 1 | 0 | `Tie` |

Depois da validação (decidido em 17/11), para os HEV e PHEV com potência combinada informada pelo fabricante, `FatorICE` = 1 e `FatorEE` = (P_comb − P_ICE) / P_EE. Com esses fatores escolhe-se o padrão de HEV e PHEV para os veículos sem informação do fabricante; valores fora de 0 a 1 serão listados para revisão.

**Onde ficam os valores.**

- `P53`: o par padrão de cada motorização. HEV e PHEV valem (1; 1) com `IsProvisional = 1`, a soma decidida em 16/11. É o que vale para um veículo que não está na planilha.
- `P56`: o par arbitrado para cada uma das 40 configurações gravadas na planilha (36 equalizadas e 4 de livre escolha), com as potências gravadas, o tipo de ajuste e a fonte. Gerada por `tools/fit_combined_power.py`.
- `D12`: o ajuste do usuário por caso (`IDA`, `IDCase`, `FactorICE`, `FactorEE`). Só casos de HEV e PHEV aceitam ajuste.

**Nos protótipos de interface** (`Interfaces Revisadas…`, ajustados em 17/11), a regra aparece como *Default factors* (`Default`), *Excel parity* (`ExcelParity`) e *Custom factors*, que são os dois fatores do usuário, de 0 a 1, gravados por caso em `D12`. As telas T03, T04, T09/T10, T21 e T23 deixaram de oferecer *Sum* e *Maximum*.

**Regra da análise** (`D06.CombinedPowerRule`):

- `Default`: pares de `P53`.
- `ExcelParity`: pares de `P56` nas configurações gravadas; nas demais, `P53`. Reproduz as dez potências do Control Panel (BP12:BU12 e BF12:BI12) e serve à validação.

O par efetivo de um caso é, nesta ordem: o ajuste de `D12`; se a regra é `ExcelParity` e o caso tem par em `P56`, esse par; senão, o de `P53`. Motorizações de par fixo ignoram a regra. A rodada congela o par efetivo e a origem (`Fixed`, `Default`, `ExcelFit` ou `UserOverride`) de cada caso.

Na T03, a potência combinada aparece como uma tabela de seis linhas, uma por motorização, com os dois fatores, a potência resultante e o selo `provisional`. Os campos de HEV e PHEV são editáveis, de 0 a 1; as linhas alteradas ficam marcadas e *Restore default* apaga a linha de `D12`.

**O que a planilha mostrou** (levantamento de 17/11, detalhes em `docs/05a`, A1 a A5):

- Rodada equalizada gravada (tabela de saídas): HEV no motor a combustão (76,94 kW), PHEV na soma (90,08 + 90,08 = 180,16 kW).
- Livre escolha: o PHEV usa o motor elétrico (132 kW, que é maior que os 81 kW do motor a combustão), e não o motor a combustão. O maior valor nem sempre é o do motor a combustão.
- Nas 40 configurações do bloco auxiliar, os PHEV equalizados das categorias A1 a A5 têm os dois motores com a mesma potência e a combinada igual a elas: cinco empates. O bloco auxiliar de A0 também mostra empate, mas a tabela de saídas, que prevalece, mostra a soma.

## 7. Selo de origem

Todo número exibido pertence a uma de três classes. O selo aparece ao lado do valor ou no cabeçalho da coluna (`st.caption` ou coluna própria na tabela; sem CSS injetado).

| Selo | Significado |
|---|---|
| `Calculated (run S3)` | Calculado pelo núcleo, na rodada indicada |
| `Excel reference` | Valor gravado no arquivo de 01/11, com a célula disponível no detalhe |
| `Preview` | Estimativa sem motor, que não entra em relatório nem em exportação de resultados |

Na Fase A, são `Calculated` a massa por subsistema, grupo e material e o GEE do berço ao portão. Energia, fase de uso, berço ao túmulo e custo aparecem só como `Excel reference`, e só para a configuração gravada na planilha. Para qualquer outra configuração a célula fica vazia, com a nota *Available with M3/M4/M6*.

A função que decide o selo é uma só (`core/provenance.py`). Nenhuma tela escreve o selo por conta própria.

## 8. Telas

Primitivas: as mesmas da 0.9.0 (Especificação Técnica §4). Interface em inglês.

### T01 · Home

- **Project.** Criar (nome), abrir arquivo, abrir exemplo, *Save as*. Lista os projetos abertos na sessão com `ProjectID`, nome, tipo (EC ou FC) e modo (edição ou leitura). Caixa de seleção por projeto.
- **Analysis type.** `st.radio` com os quatro tipos; três desabilitados, com a fase em que entram.
- **How i3ET works.** Onze blocos em três colunas (`st.columns`): entradas (Vehicle Design, Regional Conditions, Real-World Use), ciclo de cálculo (Performance Equivalence, Component Sizing, Vehicle Mass, Energy Intensity) e saídas (GHG Emissions, Life-Cycle Cost, Energy Use, Fleet Model Inputs). Cada bloco é um botão que abre um `st.dialog` com: o que o bloco faz, as escolhas do projeto selecionado que lhe dizem respeito, a situação do módulo (entregue, em construção, futuro) e atalhos para as telas.
- **Reference base.** Hash, versão do programa, arquivo de validação.

### T02 · Vehicle picker

Catálogo de `P26` com busca e filtros (grupo, design, porte, motorização, marca, combustível). Mostra vendas de 2025 e os parâmetros principais. Em EC, escolhe o ICEV de referência entre os elegíveis da categoria. Em FC, acrescenta casos. Devolve a escolha à T03.

### T03 · Project Configuration

1. Modo: EC ou FC.
2. EC: categoria e ICEV de referência. FC: lista de casos (veículo, combustível), com botão que abre a T02. Em cada caso, a receita de materiais, escolhida entre as da motorização e do porte (§5.2).
3. Condições: combustível, norma, curva de distância.
4. Versões: fatores de emissão, parâmetros de massa, montagem, fronteira.
5. Perfil de parâmetros e regra de potência combinada.
6. Frase-resumo, igual à da planilha (*Hatch Compact Regular - Ethanol E100 & Electricity - NBR - BR23 (SPHEV : Standard)*).

Salvar grava `D06` e `D07` e cria os veículos. Mostra, por caso, o `SizingOrigin`.

### T04 · Selected Parameters

Os parâmetros de `P30` em três profundidades (Basic, Expert, Expanded), por seção. Cada linha: nome, unidade, valor efetivo, faixa (mínimo, mais frequente, máximo), fonte, módulo que usa. Aviso de fora da faixa. *Restore default* apaga a linha de `D08`. As escolhas da T03 aparecem em leitura. Bloqueada quando há mais de um projeto selecionado.

### T10 · Vehicle parameters e T11 · Default parameters

T10: a tela atual, por caso, com a classe de cada valor (fabricante, padrão, calculado, PBEV), a coluna do valor na planilha e a escolha da edição do PBEV. T11: as regras de `P35` em leitura, um cartão por regra, com a comparação entre a regra tabulada e o que as fórmulas da planilha produzem.

### T41 · Validate and Freeze Inputs

Lista de verificações antes do cálculo: projeto em edição; configuração completa; casos com parâmetros obrigatórios; versões declaradas; parâmetros fora da faixa (aviso); casos `Pending` (aviso, com o que será e o que não será calculado). Botão *Freeze and run*: grava `D09`, executa o núcleo, grava `R45` e leva à T05.

### T05 · Dashboard

Seletor de rodada. Tabela de indicadores por caso (`R45`), com selo por valor. Quatro gráficos, cada um com sua tabela: composição do GEE por km, emissões acumuladas, massa × GEE e custo × GEE. Na Fase A, os gráficos que dependem de M4 e M6 só aparecem para a configuração gravada, marcados `Excel reference`. Clique num caso leva à T18.

### T06 · Multiple Projects

Rodadas lado a lado, do mesmo projeto ou de projetos diferentes abertos em leitura. Mostra primeiro o que difere nas entradas (comparação dos `InputSnapshot`) e depois os indicadores.

### T07 · Equations & glossary

Uma aba por módulo entregue, com equações, símbolos e fonte de cada parâmetro. Inclui o glossário português–inglês dos rótulos de tela (`docs/glossario.md`).

### T08 · Export

A exportação atual, mais: rodadas congeladas (`D09`, `R45`), a configuração (`D06` a `D08`) e o projeto em JSON (`core/run_export.py`; formato `i3et-export`, versão 1; previas nunca saem; o arquivo leva `ExportHash`, SHA-256 do conteúdo canônico). Toda exportação registra `ProjectID`, `RunID`, hashes e o selo de cada valor.

### T09 · Market Vehicles

A lista de veículos do projeto, com origem. Botão *Add from Market Vehicles* abre a T02. Veículo próprio continua possível.

## 9. Matriz de paridade — Fase A

Tolerância: a dos testes atuais (`TOL` de `tools/validate_core`), salvo indicação.

| Tela | O que se compara | Células da planilha | Critério | Teste | Situação |
|---|---|---|---|---|---|
| T02, T09 | 154 veículos, 58 parâmetros | Market Vehicles N7:BS161 | Igualdade, valor a valor | `test_fixtures_fase_a::test_catalogo_de_veiculos_de_mercado` (contagens) e `validate_core` | Feito |
| T03 | Seis categorias, SELEÇÃO e representativo | Control Panel X12:Z17 | Igualdade | `test_categorias`, `test_selecao_tem_dez_medias…` | Feito |
| T03 | Dimensionamento das 36 configurações equalizadas e das 4 de livre escolha | Market Vehicles B164:DC204 | Igualdade (são entradas na Fase A) | `test_bloco_auxiliar_tem_as_quarenta_configuracoes` | Feito |
| T03 | Frase-resumo da rodada gravada | Control Panel (título) | Texto igual | — | Passa ao passo 7: a frase é gerada pela tela |
| T04 | 205 parâmetros: valor, faixa, nível, seção | Control Panel F:Q, X:AD, AW:AY | Igualdade | `test_catalogo_de_parametros_do_painel` | Feito |
| T04 | Nove valores próprios do Basic | Control Panel AY18:AY29 | Igualdade | `test_bloco_basic_tem_valores_proprios` | Feito |
| T10 | Potência combinada com `ExcelParity` | Control Panel BP12:BU12 e BF12:BI12 | `TOL` | `test_power_rule::test_excel_parity_reproduz_as_dez_potencias_gravadas` e `test_generic_battery` (rodada) | Feito: exata |
| T11 | Regras de valor padrão, versão tabulada e versão das fórmulas | Market Vehicles M257:AW299 e colunas dos veículos | Contagem de veículos divergentes igual à do levantamento de 10/11 | `test_vehicle_defaults::test_contagens_de_divergencia…` | Feito |
| T05, T18 | Massa do veículo, seis motorizações da rodada gravada, com `ExcelParity` | Control Panel BP20:BU20 (1083,03 · 1213,31 · 1275,78 · 1475,69 · 1388,89 · 1382,06 kg) | 0,3% (A06: 0,1%) | `test_generic_battery::test_recorded_mass_is_close_to_the_sheet` | Feito: resíduo de 0,12% a 0,17% |
| T05, T18 | GEE de fabricação, mesmos casos | Control Panel BP29:BU29 (4.513,84 · 5.196,43 · 5.719,82 · 7.132,26 · 6.754,38 · 8.226,98 kg CO₂e) | 0,2% (A06: 0,1%) | `test_generic_battery::test_recorded_ghg_is_close_to_the_sheet` | Feito: resíduo de 0,04% a 0,11% |
| T41 | Mesma entrada, mesmo resultado | — | `InputHash` igual implica `R45` igual | `test_project_analysis_run::test_freeze_execute_is_reproducible` e `test_paridade_matriz::test_mesma_entrada…` | Feito |

A tolerância de 0,2% a 0,3% (e não a do `TOL`, mais folgada) é a que a rodada gravada permite depois das correções do passo 5. O resíduo conhecido é de 1,5 kg no ICEV (`docs/05a`, D7).

**Sem referência na planilha** (testes próprios, fora da paridade):

- comparação livre com 5 a 7 casos (`test_paridade_matriz::test_livre_escolha_com_sete_casos…`) e as misturas de gás e diesel, de `B0` a `B100` (Fase B);
- qualquer comparação equalizada cujo dimensionamento não esteja gravado, casos `Pending` (`test_caso_pending_nao_recebe_valor_calculado…`);
- resultados com os fatores padrão (1; 1) no HEV, que a planilha não usa (`test_fatores_padrao_somam_no_hev_e_no_phev…`);
- FCEV, que fica fora da comparação equalizada (`test_fcev_fica_fora…`).

**Divergências já conhecidas a levar ao relatório:**

1. BEV-A06: o bloco auxiliar grava 79,6 kW, 53,8 kWh e 1.324 kg; a tabela de saídas grava 83,6 kW, 68,4 kWh e 1.382 kg. A paridade de massa usa a tabela de saídas; as duas ficam em `P52`.
2. **Receitas e baterias da rodada gravada.** As configurações gravadas usam receitas com o nome da configuração do GREET (`ICEV-G21`, `HEV-G22`, `PHEV-G23`, `BEV-G24`), importadas em 17/11. A tabela de saídas usa baterias sem composição (`PB-*-indefinido`), calculadas por parâmetros do Control Panel (`P58`). **Fechado em 17/11:** com as entradas do M2 (`M2_IN`) e o módulo de combinação híbrida, massa e GEE ficam dentro de 0,2% (`docs/05a`, D12 a D14).
3. A lista de fatores da rodada gravada é `BR23`, e o Control Panel oferece `G22; G23; G24; GLO23; BR23`. A base atual (`P10`) tem `G22`, `G23`, `G24`, `BR25BR`, `BR25m` e `BR25GLO`. Decisão de 16/11: vale a lista configurada na planilha. No passo 3, `BR23` e `GLO23` são extraídas da planilha e entram em `P10` e `P11` como versões novas, com a célula de origem; as versões `BR25*` permanecem.
4. Bloco Basic com valores diferentes do Expert em quatro parâmetros; três parâmetros fora da própria faixa (levantamento de 11/11).
5. **Potência combinada** (`docs/05a`, A4 e A5): a tabela de saídas e o bloco auxiliar divergem no PHEV equalizado de A0 (soma contra um dos motores); nos PHEV equalizados de A1 a A5 os dois motores têm a mesma potência e a combinada é igual a elas (cinco empates; par (1; 0) mantido por decisão do autor em 17/11, pois o PHEV mais sustentável não usa os dois motores em paralelo).

A lista completa está em `docs/05a-divergencias-fase-a.md`.

## 10. Blocos de código

O código é dividido em blocos delimitados e identificados, como combinado. Cada bloco tem um cabeçalho com o identificador, o que faz, o que lê e o que devolve.

| Arquivo | Blocos | Função | Situação |
|---|---|---|---|
| `tools/xlsx_cells.py` | XL1 textos compartilhados · XL2 guia → arquivo · XL3 grade da guia · XL4 colunas e endereços | Lê uma guia da planilha por vez | Feito |
| `tools/fase_a_common.py` | FA1 planilha de referência · FA2 escrita dos CSV · FA3 normalização de rótulos | Apoio comum | Feito |
| `tools/extract_control_panel.py` | CP1 parâmetros · CP2 categorias · CP3 indicadores e saídas · CP4 gravação | Gera `P30`, `P29`, `P51`, parte de `P52` | Feito |
| `tools/import_market_vehicles.py` | MV1 catálogo de parâmetros · MV2 veículos · MV3 valores e classe · MV4 bloco auxiliar · MV5 gravação | Gera `P54`, `P26`, `P27`, parte de `P52` | Feito |
| `tools/import_pbev.py` | PB1 edição · PB2 registros e campos · PB3 vínculos · PB4 gravação | Gera `P36`, `P28`, `P55`, `P50` | Feito |
| `tools/build_default_rules.py` | DR1 colunas → critérios · DR2 células → regras · DR3 porte pela área · DR4 gravação | Gera `P49`, `P35` | Feito |
| `tools/import_ef_versions.py` | EF1 conferência · EF2 versões · EF3 fatores · EF4 gravação | Acrescenta sete listas a `P10` e `P11` | Feito |
| `tools/build_static_tables.py` | ST1 motorizações · ST2 carrocerias · ST3 fatores de uso combinado · ST4 gravação | Gera `P53` e linhas de `P12` e `P13` | Feito |
| `tools/import_recipes.py` | RC1 leiaute · RC2 colunas da família · RC3 participações, normalização e fluidos · RC4 conferência · RC5 gravação | Acrescenta as 56 receitas do bloco T:CA (GREET 2022, 2023 e 2024) a `P15` e `P16` | Feito |
| `tools/load_fase_a.py` | LD1 migração · LD2 acréscimos · LD3 tabelas novas · LD4 dicionário em dados · LD5 verificação e hash | Carrega os CSV na base | Feito |
| `tools/build_review_data.py` | X1 leitura das fixtures · X2 `model-data.js` | Mantém o pacote HTML de revisão igual à base | Por fazer (adiado para depois do passo 7); em 17/11 os protótipos T03, T04, T09, T10, T21 e T23 passaram aos fatores de uso combinado, e a T46 e a T03 ganharam o modelo genérico de bateria e a escolha da receita, à mão |
| `core/schema.py` | S5 parâmetros novos · S6 análise e rodada · S7 `M03` · S8 migração 0.9 → 0.10 · S9 impressão digital · S10 parâmetros da Fase A num projeto antigo | DDL e manutenção do arquivo | Feito |
| `core/loader.py` | — | Lê as tabelas da 0.10 quando existem | Feito |
| `core/project.py` | PJ1 identidade · PJ2 *Save as* · PJ3 edição ou leitura | Projeto. A criação do `ProjectID` já está em `schema.migrate` | Feito em 17/11 |
| `core/power_rule.py` | PR1 fatores padrão e arbitrados (`P53`, `P56`) · PR2 ajuste de `D12` · PR3 fatores efetivos e potência combinada | Substitui a regra fixa de `core/params.py` (`resolve` aceita `power_factors`) | Feito em 17/11 |
| `tools/fit_combined_power.py` | CF1 leitura das potências gravadas · CF2 arbitragem · CF3 gravação | Gera `P56` | Feito |
| `core/ef_equivalence.py` | EQ1 pares e pesos (`P57`) · EQ2 adaptação da tabela de fatores e alertas | Fator de uma versão do GREET aplicado à receita de outra; `calc.calculate_vehicle` o chama antes do cálculo | Feito em 17/11 |
| `tools/build_material_equivalence.py` | ME1 fatores de `G22` · ME2 pesos · ME3 gravação | Corrige `P11` (`G22`) e gera `P57` | Feito em 17/11 |
| `core/battery.py` | `generic_model` (modelo sem composição) · `by_material` com `generic=` | Bateria de tração paramétrica (`P58`): massa e pegada a partir de `P30`/`D08` | Feito em 17/11 |
| `tools/build_generic_battery.py` | GB1 vínculos · GB2 gravação | Gera `P58` | Feito em 17/11 |
| `tools/extract_m2_inputs.py` | M2I1 leitura de ET:EY · M2I2 gravação | Gera o conjunto `M2_IN` de `P52` | Feito em 17/11 |
| `core/run_export.py` | RX1 uma rodada · RX2 o projeto · RX3 JSON canônico e hash · RX4 gravar · RX5 verificar | Exportação em JSON (T08): sem `Preview`; `ExportHash` detecta alteração | Feito em 17/11 |
| `tools/export_run.py` | linha de comando de `run_export` | `python tools/export_run.py projeto.sqlite [--run RUNID]` | Feito em 17/11 |
| `core/analysis.py` | AN1 criar EC · AN2 criar FC · AN3 gerar casos em `D01`–`D03` · AN4 validar | Análise | Feito em 17/11 |
| `core/vehicle_defaults.py` | VD1 avaliar as regras de `P35` · VD2 comparar com `P27` | Valores padrão | Feito em 17/11 |
| `core/control_params.py` | CT1 valor efetivo · CT2 faixa · CT3 restaurar | Catálogo de parâmetros | Feito em 17/11 |
| `core/run.py` | RN1 verificação prévia · RN2 congelar · RN3 executar · RN4 gravar `R45` | Rodada | Feito em 17/11 |
| `core/provenance.py` | PV1 classe do valor · PV2 texto do selo | Selo de origem | Feito em 17/11 |
| `ui/navigation.py` | NV1 menus · NV2 atalhos | Navegação | Feito em 17/11 (passo 7) |
| `ui/components.py` | UC7 selo · UC8 aviso de leitura · UC9 bloco do diagrama | Componentes novos. Feitos em `ui/flow.py` (`begin`, `seal_of`, aviso de leitura) e na T01 (diagrama) | Feito em 17/11 (passo 7) |
| `pages/T01…T11, T41` | um bloco por seção da tela | Telas. `pages/2_Vehicles.py` já filtra motorizações e carrocerias calculáveis | Feito em 17/11 (passo 7) |

Regra mantida: `core/` não importa `streamlit`.

## 11. Os oito passos da Fase A

| Passo | Entrega | Situação |
|---|---|---|
| 1 Documentação | Este documento; plano revisado no Monday | **Concluído em 16/11** |
| 2 Base e esquema | Dicionário de dados 0.10 (`docs/07`), DDL e migração | **Concluído em 16/11** |
| 3 Fixtures | Scripts de extração, CSV e base reconstruída (`docs/08`) | **Concluído em 17/11**, com as receitas da rodada gravada |
| 4 Núcleo | `power_rule`, `project`, `analysis`, `vehicle_defaults`, `control_params`, `run`, `provenance`; regras I16 a I23 | **Feito em 17/11**: `power_rule`, `P56`, `P57`, `P58`, `ef_equivalence`, `provenance`, `control_params`, `vehicle_defaults`, `project`, `analysis`, `run`; regras I16 a I23 em `validate.check_analysis` e `check_run_origin`; ruff e `validate_core` passam. Pendente: fatores efetivos de HEV/PHEV após a validação (A2) |
| 5 Testes | Matriz de §9; migração de projeto 0.9; determinismo da rodada | **Feito em 17/11**: matriz de §9 como testes (217 de 217; a frase-resumo da T03 passa ao passo 7); paridade de massa e GEE das seis motorizações dentro de 0,2%; migração da 0.9 e determinismo cobertos por `test_projeto_da_090…` e `test_freeze_execute_is_reproducible`; protótipos das telas ajustados à regra de fatores de uso combinado |
| 6 Saídas e exportação | `R45`, `R46`, exportação das rodadas e do projeto em JSON | **Feito em 17/11**: `R45` gravada por `run.write_results`; `R46` é a visão do esquema; `core/run_export.py` e `tools/export_run.py` exportam a rodada e o projeto em JSON com `ProjectID`, `RunID`, `InputHash`, `ParamBaseHash`, selo de cada valor e `ExportHash`; 225 testes |
| 7 Telas | T01 a T11 e T41, navegação, glossário | — |
| 8 Publicação | 0.10.0 no Streamlit Community Cloud, com DOI | — |

**Critérios de aceite da Fase A**

1. Todos os testes da 0.9.0 continuam passando, com `ExcelParity`.
2. A matriz de §9 passa.
3. Um projeto da 0.9.0 abre na 0.10.0 sem perda.
4. O projeto de exemplo reproduz a massa das seis motorizações da rodada gravada.
5. Nenhum número aparece em tela sem selo.
6. Outra pessoa consegue recriar as tabelas e as regras a partir deste documento e do dicionário.

## 12. Pontos confirmados em 16/11

| # | Ponto | Resposta do autor | Onde está |
|---|---|---|---|
| 1 | HEV com a regra `Sum` | A soma é o padrão, e o usuário pode configurar. Em 17/11 a regra virou fatores de uso combinado (§6) | §6, `D12` |
| 2 | Comparação equalizada antes do M3 com o dimensionamento gravado na planilha | De acordo | §5.2 |
| 3 | Lista de fatores `BR23` | A configurada na planilha | §9, divergência 2 |
| 4 | Pacotes de interface | O pacote de 16/11 é a base. Os anteriores ficam em `Documentação/Versões anteriores` | §13 |
| 5 | Receita de materiais | Deve ser possível escolher a receita na parametrização; as receitas estão associadas à motorização e ao porte do veículo | §5.2, T03 |
| 6 | Listas `BR23` e `GLO23` | Confirmado o conjunto de GWP `AR6-100`, igual ao das demais listas | `docs/08`, `data/NOTICE.md` |
| 7 | Descrições das motorizações em `P12` | Mantidas como redigidas no passo 3 | `docs/08` |

## 13. Fontes

- `Documentação/Interfaces Revisadas para o i3ET_T01-T46_20261116/`, que é a base de interface do projeto a partir de 16/11. O pacote anterior (`Interfaces Originais para o i3ET_20260921`) foi movido para `Documentação/Versões anteriores`. Arquivos lidos: `PlanoTelasETabelas_i3ETCompleto_20261116a.md`, `Alteracoes_20261116a.md`, `LEIA-ME.md`, `model-data.js`, `review.js`, `i3ET_Introduction_20261116c.xlsx` (só as primeiras linhas de cada guia foram lidas).
- `PlanoTelasETabelas_i3ETCompleto_20261110b.md`, e as etapas de 10 e 11/11 (telas T09–T11 e T01–T05).
- Dicionário de Dados `20260919a`, Especificação Técnica `20260921b`.
- Repositório `i3et-calculator`, versão 0.9.0 (commit `825b581`): `core/schema.py`, `core/params.py`, `app.py`, `data/csv/`.
- Quadro Monday `18439268212`, revisado em 16/11/2026.

Em 17/11 (passo 5) os protótipos foram ajustados à mão: fatores de uso combinado em `review.js`, T21 e T23; escolha da receita de materiais por motorização na T03; modelo genérico de bateria (`P58`) na T46. O pacote é a base de interface, e os ajustes foram testados só quanto à sintaxe do JavaScript; o teste visual no navegador fica para o passo 7.

Os números de parâmetros, veículos, categorias e saídas vêm de `model-data.js`, que é cópia extraída da planilha fora do processo de fixtures. Serão conferidos contra a planilha no passo 3.
