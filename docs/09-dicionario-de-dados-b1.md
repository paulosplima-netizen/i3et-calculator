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

Próximos livres antes do B1: P60 (reservado à ANFAVEA, B2), D14, C35, R54. Tomados pelo B1: `P31`, `P31b`, `P32`, `P61`, `P62`, `D10` (já no quadro como MaintenanceScenario), `D13` a `D21`, `C15`, `C16`, `C34`, `C35`. Correção de 18/11: o `D10` do quadro Monday é MaintenanceScenario; as tabelas de receita, bateria, montagem e histórico do usuário usam `D13` a `D21`. Reservados a outros blocos: `D11` (M5), `D12` existente. `P47` e `P48` são do B2.

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

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDM` | TEXT | PK, FK→P09 | S | Material (1, 3, 4, 4a, 4b) |
| `Route` | TEXT | PK | S | `RECYCLED`, `VIRGIN_MAIN`, `VIRGIN_ALT`, `GREEN` |
| `EFRoute` | REAL | — | N | kg CO₂e/kg da rota (`Emission Factors BR`, blocos `AS:BD`) |
| `EFGlobal` | REAL | — | N | FE 100% global (coluna L), perdas adotadas no FE global (`H`) e nacional (`J`) em colunas `LossGlobalAdopted`, `LossNationalAdopted` |
| `Origin` | TEXT | — | S | `Typed` (decisão 3) |
| `SourceRF` | TEXT | — | N | Célula/guia de origem |

### P62 — `P62_BRRouteShare` (participações das rotas e fração importada)

`IDM`, `Route`, `ShareRule` (`CONSTANT` ou `PARAM`), `IDCP` (FK→P30: `X91`…`X101`, quando `PARAM`), `ShareValue` (quando `CONSTANT`), `ImportedShareRule`. Reproduz as regras `BG:BK` da `Emission Factors BR` (aço reciclado `(P124 − 0,1)/0,9`; aço principal `1 − outros`; ferro fundido = `0,9 × aço`; alumínio reciclado, prebaked/Søderberg, importado). Núcleo: `core/br23_routes.py` (sem Streamlit).

### Ampliação de `P10_EFVersion` e `D04_UserEFVersion`

Colunas novas (nulas até a fonte ser identificada): `Origin` (`Typed`, `Published`, `Own`; padrão `Typed`), `SourceDocTitle`, `SourceInstitution`, `SourceEdition`, `SourceURL`, `SourceAccessDate`, `ImportFile`, `ImportHash`, `ImportedBy`, `ImportedAt`.

### Ampliação de `P11_EmissionFactor`

Opcionais: `Route`, `Region`, `RefYear`, `EFLow`, `EFHigh`.

### Ampliação de `P16_MaterialShare`

`MshareRaw` (REAL, opcional): valor bruto da planilha, preenchido só nas 28 linhas de resíduo negativo (usado = 0, grupo normalizado).

### Ampliação de `P02_VehicleSubgroup`

`IDVPGC` (FK→P54; parâmetro do veículo usado como GC), `SourceRow` (linha do M1), `NotesSG` (nota sobre o ID 23 duplicado: linha 37 = IDSG 43).

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

### D20 e D21 — `D20_UserMassParamVersion` e `D21_UserMassParam` (conjunto de parâmetros de massa do usuário; T13)

Cópia editável do conjunto de parâmetros de estimativa de massa (`P05` e `P06`), com a regra de origem e histórico (decisão 3 do B1). `D20`: `IDMPVU` PK, `DsMPVU`, `IDMPVBase` (FK→P05), `Origin` (`Own`), `Author`, `CreatedAt`, `NotesMPV`. `D21`: `IDMPVU`, `IDSG` (FK→P02), `Beta`, `GCR`, `utGCR`, `MR`, `fLM`, `Reference`, `ChangedBy`, `ChangedAt`; PK (`IDMPVU`, `IDSG`). `D06.IDMPV` aceita `P05.IDMPV` ou `D20.IDMPVU` (prefixo). Regra I58: `MR` ≥ 0, `GCR` > 0, `fLM` ≥ 0; as linhas 54 e 55 (consumíveis) ficam neutras (GCR = 1, MR = 0).

### D19 — `D19_EFChangeLog` (histórico dos fatores)

`IDLog` PK, `IDEFV`, `IDM`, `Action` (`edit`, `override`, `restore`, `remove`, `import`), `OldEF`, `NewEF`, `Author`, `ChangedAt`, `Reason`.

### Ampliação de `D05_UserEmissionFactor`

Camada de sobrescrita: a base é imutável; a edição de uma lista `Typed` grava a diferença em `D05` e o fator efetivo é o de `D05` quando existe, senão o de `P11`. Colunas acrescentadas: `Author`, `ChangedAt`, `Reason`.

### Parâmetros do usuário (`D03`/`D08`)

Novos parâmetros de veículo/painel: `MassAdjBodyChassisKg` (kg com sinal, padrão 0; T38; **definido em `P54`**, como dado do veículo, decisão de 18/11; valor do usuário, não vem do GREET; a razão chassi/carroceria `k` é parâmetro por classe de veículo, de `M2` linhas 54 e 55 (linha 627 = B/A)). Escolhas de análise em `D06`: `MaintenanceMode` (espelha `D10`), `EoLMethod` (`GLIDER_BATTERY`, `AGGREGATE_VEHICLE`, `EXCLUDED`; padrão `GLIDER_BATTERY`), `IDVMRU` e `IDBMdU` quando houver receita e bateria do usuário.

## 5. Tabelas de resultado (C)

### C15 — `C15_Replacement` (reposições, T16)
Por rodada, caso e item: `IDA`, `IDCase`, `IDMI`, `EventIndex`, `EventKm`, `GHGkg`. Total por item é a soma dos eventos.

### C16 — `C16_EndOfLife` (fim de vida, T17)
`IDA`, `IDCase`, `EoLMethod`, `GliderMassKg`, `BatteryKWh`, `FactorGlider`, `FactorBattery`, `FactorVehicle`, `GHGEoL`.

**Parâmetro `ChassisBodyRatio` (`k`, ID 620 da planilha; T38).** Por classe de veículo (coluna do `M2`), `k = massa do chassi (linha 55) / massa da carroceria (linha 54)`; 0,43 a 1,74 (SV1 a SV4: 0,480 a 0,493). Tabela por classe a definir na implementação (candidata: classe de referência do veículo, junto de `P02`/`P54`). Regra I41: `B_final / A_final = k`.

### C34 — `C34_MassValidation` (validação de massa, T38)
`IDA`, `IDCase`, `IDV`, `IDEA`, `MassBasis`, `DeclaredMassKg`, `CalculatedMassKg`, `DiffKg`, `DiffPct`, `AdjustmentKg`, `ResidualKg`, `DeclaredSource`, `ChassisBodyRatio` (k usado), `BodyChassisMassBefore`, `BodyChassisMassAfter`.

**Ampliação de `C02` (massa por grupo; T38, decisão de 18/11).** Colunas `EstimatedMassKg`, `CalibrationKg`, `FinalMassKg`; `MassKg` = `FinalMassKg` (igual ao atual quando o ajuste é 0). `CalibrationKg` é diferente de zero só em carroceria e chassi (`A_final = (A_est+B_est+Adj)/(1+k)`, `B_final = k·A_final`, calibração = final − estimada). Botão da T38: "Calibrate to declared mass".

### C35 — `C35_VehicleLifeStage` (vida do veículo por estágio, T18)
`IDA`, `IDCase`, `IDV`, `Stage` (`INITIAL_PRODUCTION`, `LIFETIME_REPLACEMENTS`, `END_OF_LIFE`), `SubStage`, `GHGkg`, `SourceCell`, `Method`, `Note`. Cria a coluna de rastreio para `T511 = T495 + T509 + T510 + T516 + T560 + T571 + T617`.

## 6. Regras novas

| Código | Regra | Onde |
|---|---|---|
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
| I41 | O ajuste redistribui A + B pela razão `k` por classe (M2 linha 627) | código |
| I42 | O ajuste de massa altera massa e GEE do grupo recomposto | código |
| I43 | Massa declarada ausente → sem Δ, nunca Δ = 0 | código |
| I44 | Modelo de bateria do usuário fecha cada grupo em 1 | código |
| I45 | Bateria genérica não admite composição | banco |
| I46 | Montagem `process` reconcilia com `from_EF` (relatório, não bloqueia) | teste |
| I47 | A versão de montagem é escolha da análise; mudar cria nova rodada | código |
| I48 | `Published` não é editável; `Typed` e `Own` registram toda alteração em `D19` | código |
| I49 | Alterar valor exige motivo; remover sobrescrita registra `restore` | código |
| I50 | Zero explícito só com sobrescrita documentada; `ND` nunca vira zero | código |
| I51 | Versão do usuário exige fonte e ID único | banco |
| I52 | Comparar versões com `GWPSet` diferente avisa | código |
| I53 | Fatores efetivos da rodada são congelados (hash) | código |
| I54 | O berço ao portão não contém reposições nem fim de vida | teste |
| I55 | Com "Aggregate vehicle factor" e as contagens de referência, a vida do veículo reproduz `T511` | teste |
| I56 | Estágio com material sem fator mostra dado ausente | código |
| I58 | Conjunto de parâmetros de massa do usuário: `MR` ≥ 0, `GCR` > 0, `fLM` ≥ 0; consumíveis neutros | código |
| I57 | A T18 mostra o método de fim de vida e os intervalos usados | código |

## 7. Migração e fixtures

- Migração 0.10 → 0.11: acrescenta as colunas opcionais, as tabelas novas e carrega `P31`, `P31b`, `P61`, `P62` por CSV em `data/csv/fase_b1/` (gerados por script a partir da planilha, com hash). Repetível, só acrescenta.
- Fixtures de paridade: (1) `T495` das 12 configurações nos três valores do seletor; (2) BR23 recomposta × lista digitada (aço e alumínio por tipo de veículo); (3) fim de vida "Aggregate vehicle factor" = `T509`; (4) validação de massa SV1 a SV4; (5) receitas: fechamento das 68 receitas; (6) `T511` da vida do veículo.
- Critérios de pronto por tela: nos documentos `b1-t*.md`.
