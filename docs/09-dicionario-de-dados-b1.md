# Dicionário de Dados — Bloco B1 (esquema 0.11, proposta)
## Passo 2 do método para o B1: base e esquema

18/11/2026 · versão a · Complementa `07-dicionario-de-dados-fase-a.md`. **Especificação, sem código:** este documento define o que o B1 acrescenta ao esquema; a definição normativa passará a ser o DDL de `core/schema.py` (bloco S11) quando o B1 for implementado. Especificações por tela, com fórmulas da planilha e critérios de pronto, estão nos documentos do projeto: `b1-especificacao.md`, `b1-t14-materiais-e-receitas.md`, `b1-t16-manutencao.md`, `b1-t17-fim-de-vida-e-rotas-br23.md`, `b1-t38-validacao-de-massa.md`, `b1-t46-bateria-e-montagem.md`, `b1-t15-fatores-de-emissao.md` e `b1-t18-fabricacao-e-vida-do-veiculo.md`.

Convenções do Documento 2, §2. Na coluna **Obr.**, `S` é `NOT NULL`. Datas em ISO no banco e `dd/mm/aaaa` na tela. Massa (kg) e pegada (kg CO₂e) em valor absoluto são exibidas com **uma casa decimal**.

## 1. Decisões que moldam este esquema (autor, 18/11/2026)

1. `P33` e `P34` do quadro foram **dispensadas**: os parâmetros de fim de vida e de rotas ficam em `P30`.
2. Fim de vida: prevalecem os parâmetros do painel (0,2 kg CO₂e/kg; 20 kg CO₂e/kWh) sobre o fator por veículo do GREET (IDM 100).
3. Os fatores de aço e alumínio da lista BR23 são recompostos a partir dos parâmetros do painel (`X91` a `X101`).
4. Reposições por quilometragem: quantidade calculada pela vida do veículo; sem reposição no fim da vida.
5. Todas as listas de fatores atuais são `Typed` (digitadas) até a fonte ser identificada e importada; edição com histórico.
6. Descartados: classificações "Artigo" e "BNDES" e o código BRIGHT.

## 2. Numeração

Próximos livres antes do B1: P60 (reservado à ANFAVEA, B2), D14, C35, R54. Tomados pelo B1: `P31`, `P31b`, `P32`, `P61`, `P62`, `D10` (já no quadro como MaintenanceScenario), `D13` a `D22`, `C15`, `C16`, `C34`, `C35`. Correção de 18/11: o `D10` do quadro Monday é MaintenanceScenario; as tabelas de receita, bateria, montagem e histórico do usuário usam `D13` a `D21`. Reservados a outros blocos: `D11` (M5), `D12` existente. `P47` e `P48` são do B2.

## 3. Tabelas de parâmetros (P)

### P31 — `P31_MaintenanceItem` (itens de reposição do i3ET)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDMI` | TEXT | PK | S | `TIRE`, `BATT_AUX`, `BATT_TRAC`, `FLD_77` a `FLD_83` |
| `DsMI` | TEXT | — | S | Nome |
| `ItemKind` | TEXT | — | S | `PART`, `BATTERY` ou `FLUID` |
| `IDGG` | TEXT | FK→P04 | N | Grupo GREET reposto (`Iaux`, `Iprinc`, `K`) |
| `IDM` | TEXT | FK→P09 | N | Material do fluido (77 a 83) |
| `IntervalKm` | REAL | — | N | Intervalo de reposição, km; nulo = item inativo |
| `IntervalSource` | TEXT | — | S | `i3ET-compatible` ou `Entered` |
| `RefCount` | REAL | — | N | Contagem da planilha (teste de paridade) |
| `MassPerUnitKg` | REAL | — | N | Só `PART`: 9,0718 kg por jogo |
| `NotesMI` | TEXT | — | N | Origem da célula |

Intervalos: pneus 40.000 km; óleo do motor 5.000; fluido do para-brisa 10.000; freio e arrefecimento 50.000; transmissão 100.000; bateria auxiliar 70.000 (`Entered`); bateria de tração 150.000 (`Entered`); direção e adesivos sem intervalo. Com a vida de referência de 200.000 km reproduzem as contagens da planilha (4, 39, 19, 3, 3, 1, 2, 1, 0, 0).

### P31b — `P31b_MaintenancePartShare` (composição do jogo de pneus)

`IDMI` (FK→P31), `IDM` (FK→P09), `Share` (REAL; aço 1/3, borracha 2/3), `NotesMPS`. PK (`IDMI`, `IDM`).

### P32 — `P32_CorrectiveMaintenance` (manutenção corretiva; extensão)

`IDCM` PK, `CorrectivePct` (REAL, 0 por padrão), `Basis` (`PART_MASS_SHARE` ou `PRODUCTION_GHG_SHARE`), `SourceCM` (texto; "extensão sem fonte" enquanto 0). Mecanismo mínimo no B1; calibração no B6.

### P61 — `P61_BRRouteFactor` (fatores por rota da BR23)

Linhas 11 (aço, IDM 1), 14 (ferro fundido, 3), 18 (alumínio de chapa, 4a) e 20 (alumínio extrudado, 4b) da guia `Emission Factors BR`; 4 rotas por material (16 linhas). O IDM 4 (alumínio forjado) não tem linha na guia.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDM` | TEXT | PK, FK→P09 | S | Material (1, 3, 4a, 4b) |
| `Route` | TEXT | PK | S | `RECYCLED` (M), `VIRGIN_MAIN` (N), `VIRGIN_ALT` (O), `GREEN` (P) |
| `EFRoute` | REAL | — | N | kg CO₂e/kg da rota (blocos `AS:BD`) |
| `EFGlobal` | REAL | — | N | FE 100% global (coluna L); repetido nas quatro rotas |
| `LossGlobalAdjusted` | REAL | — | N | Perdas ajustadas no FE global (G) |
| `LossGlobalAdopted` | REAL | — | N | Perdas adotadas no FE global (H) |
| `LossNationalAdjusted` | REAL | — | N | Perdas ajustadas no FE nacional (I), quando constante |
| `LossNationalAdjIDCP` | TEXT | FK→P30 | N | Parâmetro do painel que dá `I` (aço `X91`; alumínio `X97`) |
| `LossNationalAdopted` | REAL | — | N | Perdas adotadas no FE nacional (J) |
| `Origin` | TEXT | — | S | `Typed` (decisão 3) |
| `SourceRF` | TEXT | — | N | Célula/guia de origem |

### P62 — `P62_BRRouteShare` (participações das rotas e da fração importada)

Nove linhas por material: as quatro rotas e a fração importada por tipo de veículo (`IMP_ICEV`, `IMP_ICEV_SUV`, `IMP_HEV`, `IMP_PHEV`, `IMP_BEV`; colunas `BK:BO`). 36 linhas.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDM` | TEXT | PK, FK→P09 | S | Material |
| `Route` | TEXT | PK | S | Rota ou fração importada |
| `ShareRule` | TEXT | — | S | `CONSTANT`, `PARAM` ou `FORMULA` |
| `IDCP` | TEXT | FK→P30 | N | Parâmetro `X91`…`X101`, quando `PARAM` |
| `ShareValue` | REAL | — | N | Valor, quando `CONSTANT` |
| `RuleExpr` | TEXT | — | N | Quando `FORMULA`: aritmética com números, `X92`…`X101` e `[IDM:ROTA]` (ex.: `(X92-0.1)/0.9`) |
| `SourceRS` | TEXT | — | N | Células de origem |

Reproduz as regras `BG:BK` (aço reciclado `(X92 − 0,1)/0,9`; aço principal `1 − outros`; ferro fundido = 0,9 × aço, importado = `X95/2`; alumínio reciclado `X98`, verde `X100`, principal `(1−X98−X100)·X99`, alternativo `(1−X98−X100)·(1−X99)`, importado `X101`). Gerada por `tools/import_br_routes.py`. Núcleo: `core/br23_routes.py` (sem Streamlit).

### P64 e P65 — `P64_ParamRevision` e `P65_ParamRevisionSource` (revisões dos parâmetros; Painel de parâmetros, 21/11/2026)
Conteúdo editorial da revisão periódica dos parâmetros do bloco Expert (UPP, PET, LMP, FEF, MEF, AUC, LWP). **Não guarda valores nem faixas**: esses ficam em `P30` e o painel os lê de lá (a planilha prevalece). Uma linha por parâmetro e por data de revisão. Só consulta; nada aqui entra no cálculo.

`P64`: `IDRV` (PK), `IDCP` (FK→P30), `ReviewDate` (AAAA-MM-DD; primeira segunda-feira do mês), `Action` (`keep`, `adjust` ou `verify`), `Field` (`min`, `mf` ou `max`, nulo quando não há sugestão), `SuggestedValue` (valor sugerido; sem efeito no cálculo), `FromValue` (valor da planilha na data da revisão), `LinkedAlerts` (nº de alertas de novos desenvolvimentos ligados), `Rationale`, `Caveat`, `Alert` (alerta de consistência da fonte; o painel o recalcula do `P30`), `Tag` (`bat` bateria, `ice` motor a combustão), `Spotlight` (0/1), `Accepted` (0/1: sugestão já incorporada à planilha), `AcceptedDate`. Chave única (`IDCP`, `ReviewDate`).

`P65`: `IDRV` (PK, FK→P64), `Seq` (PK), `Reference` (autor ou instituição), `Year` (texto; nulo quando a fonte não traz ano).

Regras: a revisão vigente de um parâmetro é a de maior `ReviewDate`; as anteriores formam o histórico; carregar uma nova data só acrescenta. Fixtures: `data/csv/fase_b/P64_ParamRevision.csv` (120 linhas: 106 `keep`, 9 `adjust`, 5 `verify`; 17 destaques; 11 aceites) e `P65_ParamRevisionSource.csv` (260 linhas), geradas por `tools/import_param_review.py` a partir de `tools/fontes/parametros_expert_20260804.json` (extraído do artefato "I3et Parametros Expert", revisão de 03/08/2026 e aceites de 04/08/2026). Ligação por nome e seção, com cinco exceções (UPP 14 e 15 = `X32` e `X33`; Green Steel = `X94`; Green Aluminum = `X100`; Energy Price = `X120`).

### Ampliação de `P10_EFVersion` e `D04_UserEFVersion`

Colunas novas (nulas até a fonte ser identificada): `Origin` (`Typed`, `Published`, `Own`; padrão `Typed`), `SourceDocTitle`, `SourceInstitution`, `SourceEdition`, `SourceURL`, `SourceAccessDate`, `ImportFile`, `ImportHash`, `ImportedBy`, `ImportedAt`.

### Ampliação de `P11_EmissionFactor`

Opcionais: `Route`, `Region`, `RefYear`, `EFLow`, `EFHigh`.

### Ampliação de `P16_MaterialShare`

`MshareRaw` (REAL, opcional): valor bruto da planilha, preenchido só nas 28 linhas de resíduo negativo (usado = 0, grupo normalizado).

### Ampliação de `P02_VehicleSubgroup`

`IDVPGC` (FK→P54; parâmetro do veículo usado como GC), `SourceRow` (linha do M1), `NotesSG` (nota livre; a linha 37 do M1, IDSG 43, é o módulo de combinação híbrida, que soma massa à caixa de câmbio da linha 36, IDSG 23, e tem parâmetros próprios).

## 4. Tabelas do usuário (D)

### D10 — `D10_MaintenanceScenario` (escolhas de manutenção e vida útil; T16)

`IDMS` PK, `IDA` (FK→D06, uma linha por análise), `MaintenanceMode` (`Sim`, `Sim Bat`, `Não`; padrão `Sim`), `Scenario` (`REFERENCE` ou `USER`), `VehicleLifeKm` e `BatteryLifeKm` (opcionais; padrão `X74` e `X75` do painel), `Author`, `ChangedAt`. Linhas filhas `D10_Item` (`IDMS`, `IDMI`, `IntervalKm`, `Active`) guardam o intervalo e a ativação de cada item no cenário do usuário. Regras I32, I33, I39.

### D13 — `D13_UserRecipe` (receita do usuário, cabeçalho)

`IDVMRU` PK (`U-` + sequência), `DsVMRU` (S), `IDVMRBase` (S, FK→P15), `IDVPT` (S, FK→P12), `IDVDT` (S), `IDVS` (S), `Author`, `CreatedAt`, `UpdatedAt` (S), `NotesU` (N).

### D14 — `D14_UserMaterialShare` (linhas da receita do usuário)

`IDVMRU` (FK→D13), `IDGG` (FK→P04), `IDM` (FK→P09), `MshareGG` (REAL, ≥ 0), `SourceU` (obrigatório quando difere da receita-base), `ChangedBy`, `ChangedAt`. PK (`IDVMRU`, `IDGG`, `IDM`).

### D15 e D16 — `D15_UserBatteryModel` e `D16_UserBatteryShare`

`D15`: `IDBMdU` PK, `DsBMdU`, `IDBMdBase` (FK→P19), `IDVPT`, `IDBTe`, parâmetros de referência (`RefEnergy`, `RefPower`, `RefWeight`), origem, autor, datas. `D16`: `IDBMdU`, `IDGG`, `IDM`, `BMshareGG` (fecha em 1 por grupo).

### D17 e D18 — `D17_UserAssemblyVersion` e `D18_UserAssemblyEnergy`

`D17`: `IDAPVU` PK, `DsAPVU`, `Method` (`fixed`, `from_EF`, `process`), `FixedGHGPerVehicle`, origem, autor, datas. `D18`: `IDAPVU`, `IDAP` (FK→P21), `IDFuel`, `EnergyPerVehicle`, `FuelShare`.

### D22 — `D22_FormatSetting` (formato de exibição dos números; T47)

Configuração de exibição do projeto (decisão 12 de 19/11/2026). Colunas: `SettingKey` (PK; hoje só `format`) e `SettingValue` (JSON: perfil `default`/`article`/`audit`/`custom`, casas decimais por classe de grandeza, unidade de massa e de GEE `kg`/`t`, participação em `percent`/`fraction`, separadores decimal e de milhar, separador de campos do CSV, limite de notação científica e `csv_rounded`). Sem linha, vale o perfil padrão e o relatório mantém o formato anterior. O formato só muda a exibição (telas, relatório HTML, formato de célula do XLSX e CSV); cálculo e resultados congelados nunca são arredondados. Regras em `core/formatting.py`.

### D02 e D06 (alteradas na 0.11 — 19/11/2026)

`D02_EvaluationAlternative.IDMPV`/`IDAPV` e `D06_Analysis.IDMPV`/`IDAPV` deixam de ter chave estrangeira para `P05` e `P23`: aceitam também `D20.IDMPVU` (prefixo `UM-`) e `D17.IDAPVU` (prefixo `UA-`). A regra I60 confere que cada versão existe em uma das duas tabelas. A rodada congelada guarda `user_versions` (hash de `D18` e `D21`) e `execute` recusa a execução se mudaram (I53). `core/schema.relax_d02_d06` recria as tabelas, com os mesmos dados e índices.

### D05 (alterada na 0.11 — decisão 11 de 19/11/2026)

`D05_UserEmissionFactor.IDEFV` deixa de ter chave estrangeira para `D04`: uma linha pode sobrepor um fator de uma versão `Typed` da base (`P10`) ou de uma versão do usuário (`D04`). Versões `Published` não recebem linhas (a regra está em `core/ef_edit.py`, I48); linhas sem versão correspondente são apontadas por I59. A rodada congelada guarda `emission_factors` (hash dos fatores efetivos de cada lista do usuário ou alterada) e `execute` recusa a execução se o hash mudou (I53). Colunas `Author`, `ChangedAt` e `Reason` registram a última alteração; o histórico completo está em `D19`. `core/schema.relax_d05` faz a migração (recria a tabela e a visão `EF_Effective`).

### D20 e D21 — `D20_UserMassParamVersion` e `D21_UserMassParam` (conjunto de parâmetros de massa do usuário; T13)

Cópia editável do conjunto de parâmetros de estimativa de massa (`P05` e `P06`), com a regra de origem e histórico (decisão 3 do B1). `D20`: `IDMPVU` PK, `DsMPVU`, `IDMPVBase` (FK→P05), `Origin` (`Own`), `Author`, `CreatedAt`, `NotesMPV`. `D21`: `IDMPVU`, `IDSG` (FK→P02), `Beta`, `GCR`, `utGCR`, `MR`, `fLM`, `Reference`, `ChangedBy`, `ChangedAt`; PK (`IDMPVU`, `IDSG`). `D06.IDMPV` aceita `P05.IDMPV` ou `D20.IDMPVU` (prefixo). Regra I58: `MR` ≥ 0, `GCR` > 0, `fLM` ≥ 0; as linhas 54 e 55 (consumíveis) ficam neutras (GCR = 1, MR = 0).

### D19 — `D19_EFChangeLog` (histórico dos fatores)

`IDLog` PK, `IDEFV`, `IDM`, `Action` (`edit`, `override`, `restore`, `remove`, `import`), `OldEF`, `NewEF`, `Author`, `ChangedAt`, `Reason`.

### Ampliação de `D05_UserEmissionFactor`

Camada de sobrescrita: a base é imutável; a edição de uma lista `Typed` grava a diferença em `D05` e o fator efetivo é o de `D05` quando existe, senão o de `P11`. Colunas acrescentadas: `Author`, `ChangedAt`, `Reason`.

### Parâmetros do usuário (`D03`/`D08`)

Novos parâmetros de veículo/painel: `MassAdjBodyChassisKg` (kg com sinal, padrão 0; T38; **definido em `P54`**, como dado do veículo, decisão de 18/11; valor do usuário, não vem do GREET; a razão chassi/carroceria `k` é parâmetro por classe de veículo, de `M2` linhas 54 e 55 (linha 627 = B/A)). Valores do usuário por caso, em colunas novas de `D07` (T38; decisão de 18/11, tarde): `DeclaredMassKg` (massa declarada, nulo se não houver), `MassAdjustmentKg` (kg com sinal, padrão 0; o botão "Calibrate to declared mass" grava declarada − calculada), `MassBodyShare` (`s` do usuário, 0 a 1; nulo = participação da carroceria nas massas estimadas do veículo; `P63` é só diagnóstico), `DeclaredSource` e `MassCalibrationMode` (decisão de 20/11/2026: nulo = regra padrão, `ON` liga e `OFF` desliga a calibração automática). **Massa declarada efetiva e calibração automática (20/11/2026):** o parâmetro 25 do veículo é a massa conhecida quando é informado (`D03.IsCalculated = 0`, veículo de mercado); em veículo teórico (potência e bateria variadas) ele é calculado, não há massa conhecida, não há rateio e a massa estimada é o resultado. Precedência da massa declarada: `D07.DeclaredMassKg`, depois o parâmetro 25 informado. A calibração é automática (ajuste = declarada − estimada, calculado na própria rodada, repartido por `s`) para `SizingOrigin = Manufacturer`; nos demais casos, inclusive `ExcelReference` (para manter a paridade), só com `MassCalibrationMode = 'ON'`; `OFF` desliga. Um ajuste manual (`MassAdjustmentKg` ≠ 0) prevalece sobre o automático. `C34.MassBasis` registra `DECLARED_TYPED`, `DECLARED_MARKET`, `ESTIMATED_ITERATIVE` (parâmetro 25 calculado) ou `ESTIMATED` (parâmetro 25 informado, calibração não ativa). Escolhas de análise em `D06`: `MaintenanceMode` (espelha `D10`), `EoLMethod` (`GLIDER_BATTERY`, `AGGREGATE_VEHICLE`, `EXCLUDED`; padrão `GLIDER_BATTERY`), `IDVMRU` e `IDBMdU` quando houver receita e bateria do usuário.

## 5. Tabelas de resultado (C)

### C15 — `C15_Replacement` (reposições, T16)
Por rodada, caso e item: `IDA`, `IDCase`, `IDMI`, `EventIndex`, `EventKm`, `GHGkg`. Total por item é a soma dos eventos.

### C16 — `C16_EndOfLife` (fim de vida, T17)
`IDA`, `IDCase`, `EoLMethod`, `GliderMassKg`, `BatteryKWh`, `FactorGlider`, `FactorBattery`, `FactorVehicle`, `GHGEoL`.

### P63 — `P63_RecipeBodyChassisMass` (massas de referência de carroceria e chassi por receita; T38)
Uma linha por receita de `P15` (68: 56 GREET, 6 BISD, 6 PBP_BISD), vinda das colunas do bloco de receitas do `M2` (T8:DD627). Colunas: `IDVMR` (PK, FK→P15), `ColumnM2`, `BodyMassRefKg` (linha 54), `ChassisMassRefKg` (linha 55), `ChassisBodyRatio` (`k`, linha 627 "Parameter Chassi/Body weight", ID 620; = B/A), `BodyShareOfMassAdj` (`s` = A/(A+B); referência do GREET, não entra no cálculo), `SourceNote`. As massas são digitadas no M2 e vêm das alocações da planilha do GREET, não das massas do M1 (autor, 18/11/2026). Fixture: `data/csv/fase_b/P63_RecipeBodyChassisMass.csv`, gerada por `tools/import_body_chassis.py` (importada em 18/11/2026; teste `tests/test_body_chassis_p63.py`). A carga no banco entra no passo "base e esquema" do B1 (migração 0.11).

**Parcela `s` (T38; decisão de 19/11/2026, que substitui a de 18/11).** Parcela da diferença de massa (declarada − calculada, positiva ou negativa) que vai para a carroceria; `1 − s` vai para o chassi; `0 ≤ s ≤ 1` (I45). **O padrão é `s = A_est/(A_est + B_est)`, a participação da carroceria nas massas estimadas do próprio veículo**, de modo que a proporção A:B final é igual à estimada; o usuário pode informar outro `s` (`D07.MassBodyShare`). `BodyShareOfMassAdj` de `P63` (`s = 1/(1+k)`, por receita, `A/(A+B)` do GREET) **não entra no cálculo**: é a referência do diagnóstico (`C34.BodyShareReference`); a T38 avisa quando a diferença para o `s` estimado chega a 5 pontos (`b1_choices.SHARE_DEVIATION_WARN`), indicando betas ou massas de referência a recalibrar. O `k` da planilha fica só para o método `P69` (paridade; divergência B1-DIV-01: transfere massa entre A e B mesmo sem diferença). Em 6 receitas o chassi pesa mais que a carroceria nos valores digitados (`k` > 1: FCV-P25, HEV-P27, PHEV-P28, BEV-P29, FCV-P30, PHEV-S28); conferir a digitação.

### C34 — `C34_MassValidation` (validação de massa, T38)
`IDA`, `IDCase`, `IDV`, `IDEA`, `MassBasis`, `DeclaredMassKg`, `CalculatedMassKg`, `DiffKg`, `DiffPct`, `AdjustmentKg`, `ResidualKg`, `DeclaredSource`, `BodyShare` (s usado), `BodyShareEstimated` (s = A/(A+B) das massas estimadas do veículo; diagnóstico e padrão de `BodyShare`), `BodyShareReference` (s do GREET para a receita, `P63`; só referência, nulo se a receita não está em `P63`), `BodyChassisMassBefore`, `BodyChassisMassAfter`.

**Ampliação de `C02` (massa por grupo; T38, decisão de 18/11).** Colunas `EstimatedMassKg`, `CalibrationKg`, `FinalMassKg`; `MassKg` = `FinalMassKg` (igual ao atual quando o ajuste é 0). `CalibrationKg` é diferente de zero só em carroceria e chassi (`A_final = A_est + s·Adj`, `B_final = B_est + (1−s)·Adj`, calibração = `s·Adj` e `(1−s)·Adj`). Botão da T38: "Calibrate to declared mass".

### C35 — `C35_VehicleLifeStage` (vida do veículo por estágio, T18)
`IDA`, `IDCase`, `IDV`, `Stage` (`INITIAL_PRODUCTION`, `LIFETIME_REPLACEMENTS`, `END_OF_LIFE`), `SubStage`, `GHGkg`, `SourceCell`, `Method`, `Note`. Cria a coluna de rastreio para `T511 = T495 + T509 + T510 + T516 + T560 + T571 + T617`.

## 6. Regras novas

| Código | Regra | Onde |
|---|---|---|
| I45 | `0 ≤ s ≤ 1` (parcela da diferença de massa para a carroceria) | código |
| I44 | Em `C02`, Σ `CalibrationKg` = `AdjustmentKg` de `C34` e Σ `FinalMassKg` = Σ `EstimatedMassKg` + `AdjustmentKg` | código |
| I29 | Receita do usuário: cada grupo não vazio fecha em 1 (10⁻⁶) ou é todo zero; participação de material ≥ 0; processo e detalhamento fora da soma; rascunho inválido não pode ser escolhido | código |
| I30 | Receita do usuário usada por rodada congelada não muda; edição gera nova versão | código |
| I31 | A receita da análise aceita `P15.IDVMR` ou `D13.IDVMRU` | código |
| I32 | `MaintenanceMode` é `Sim`, `Sim Bat` ou `Não` | banco |
| I33 | A bateria de tração só entra com `Sim Bat` | código |
| I34 | Material sem fator conta como dado ausente (T18), nunca zero | código |
| I35 | Reposições são linha própria do resultado; a produção inicial não se repete | código |
| I36 | O método de fim de vida escolhido é o único que contribui | código |
| I37 | Parâmetros `X91`…`X101` em [0, 1]; rotas somam no máximo 1 | código |
| I38 | Com os parâmetros do i3ET, a BR23 recomposta é igual à digitada (1e-9) | teste |
| I39 | Intervalo > 0; eventos em `k × intervalo < L`; vida ≤ 0 não gera eventos | código |
| I40 | Ajuste de massa mantém carroceria + chassi ≥ 0 | código |
| I41 | O ajuste reparte só a diferença entre A e B pela parcela `s` (0 a 1); sem transferência de massa | código |
| I42 | O ajuste de massa altera massa e GEE do grupo recomposto | código |
| I43 | Massa declarada ausente → sem Δ, nunca Δ = 0 | código |
| I44 | Modelo de bateria do usuário fecha cada grupo em 1 | código |
| I45 | Bateria genérica não admite composição | banco |
| I46 | Montagem `process` reconcilia com `from_EF` (relatório, não bloqueia) | teste |
| I47 | A versão de montagem é escolha da análise; mudar cria nova rodada | código |
| I48 | `Published` não é editável; `Typed` (da base, alterada só no projeto) e `Own` registram toda alteração em `D19` | código |
| I49 | Alterar valor exige motivo; remover sobrescrita registra `restore` | código |
| I50 | Zero explícito só com sobrescrita documentada; `ND` nunca vira zero | código |
| I51 | Versão do usuário exige fonte e ID único | banco |
| I52 | Comparar versões com `GWPSet` diferente avisa | código |
| I53 | Fatores efetivos da rodada são congelados (hash): a rodada guarda `emission_factors` e `execute` recusa a execução se os fatores mudaram | código, teste |
| I54 | O berço ao portão não contém reposições nem fim de vida | teste |
| I55 | Com "Aggregate vehicle factor" e as contagens de referência, a vida do veículo reproduz `T511` | teste |
| I56 | Estágio com material sem fator mostra dado ausente | código |
| I58 | Conjunto de parâmetros de massa do usuário: `MR` ≥ 0, `GCR` > 0, `fLM` ≥ 0; consumíveis neutros | código |
| I59 | Todo fator de `D05` pertence a uma versão que existe em `P10` ou `D04` (a chave estrangeira foi removida) | código, teste |
| I60 | Toda versão de massa (`IDMPV`) e de montagem (`IDAPV`) usada em `D06` e `D02` existe em `P05`/`D20` e `P23`/`D17` | código, teste |
| I57 | A T18 mostra o método de fim de vida e os intervalos usados | código |

## 7. Migração e fixtures

- Migração 0.10 → 0.11: acrescenta as colunas opcionais, as tabelas novas e carrega `P31`, `P31b`, `P61`, `P62` por CSV em `data/csv/fase_b1/` (gerados por script a partir da planilha, com hash). Repetível, só acrescenta.
- Fixtures de paridade: (1) `T495` das 12 configurações nos três valores do seletor; (2) BR23 recomposta × lista digitada (aço e alumínio por tipo de veículo); (3) fim de vida "Aggregate vehicle factor" = `T509`; (4) validação de massa SV1 a SV4; (5) receitas: fechamento das 68 receitas; (6) `T511` da vida do veículo.
- Critérios de pronto por tela: nos documentos `b1-t*.md`.


## 8. Divergências do B1 e fixtures de paridade

- **B1-DIV-01** (T38): o método `P69` da planilha transfere massa entre carroceria e chassi mesmo sem diferença; o aplicativo reparte só a diferença com `s` entre 0 e 1 (`P63`).
- **B1-DIV-02** (T16): a fórmula de `T495` do `M2` difere entre blocos de colunas. 94 colunas (GREET 2022 e 2024, SV1 a SV4) usam a chave `P495`; 28 colunas (GREET 2023 e BISD) usam `$R$495 × (… + T500 + T509)`, ignoram a chave e contam o fim de vida duas vezes em `T511`. O aplicativo reproduz a fórmula da chave.
- Fixtures: `data/csv/fase_b/P63_RecipeBodyChassisMass.csv` e `tests/fixtures/b1_reference.json`, geradas por `tools/import_body_chassis.py` e `tools/extract_b1_reference.py`; testes `test_body_chassis_p63.py` e `test_b1_reference.py`.
