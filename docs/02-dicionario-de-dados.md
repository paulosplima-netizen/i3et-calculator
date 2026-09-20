# Dicionário de Dados e Modelo Relacional
## Calculadora da Pegada de Carbono de Veículos Leves — do Berço ao Portão

**Documento 2 de 4** · Versão `20260919a` · Projeto NIPE/UNICAMP

Este documento é a evolução da tabela `P01` do arquivo `LVManufacturingMassGHGSimulator`. Ele define, para cada tabela e cada coluna, o tipo, a unidade, o domínio, a obrigatoriedade, a classificação (exógeno / endógeno / resultado), as chaves e as restrições de integridade, e encerra com o DDL SQL completo, suficiente para criar a base do zero.

---

## Sumário

1. [Princípios do modelo](#1-princípios-do-modelo)
2. [Convenções do dicionário](#2-convenções-do-dicionário)
3. [Mapa de relacionamentos](#3-mapa-de-relacionamentos)
4. [Tabelas de parâmetros (P)](#4-tabelas-de-parâmetros-p)
5. [Tabelas de dados do cenário (D)](#5-tabelas-de-dados-do-cenário-d)
6. [Tabelas calculadas (C)](#6-tabelas-calculadas-c)
7. [Tabelas de relatório (R)](#7-tabelas-de-relatório-r)
8. [Regras de integridade além das chaves](#8-regras-de-integridade-além-das-chaves)
9. [Versionamento e reprodutibilidade](#9-versionamento-e-reprodutibilidade)
10. [DDL SQL completo](#10-ddl-sql-completo)

---

## 1. Princípios do modelo

**P1 — Uma linha, um fato.** Nenhuma tabela mistura granularidades. Onde a planilha original repetia colunas para conveniência de leitura, o modelo normaliza e a redundância volta apenas nas tabelas de relatório (`R`).

**P2 — Toda junção é declarada.** Não existe correspondência posicional. Toda associação entre tabelas passa por chave estrangeira explícita, verificável pelo banco.

**P3 — Versão é chave, não anotação.** `IDMPV`, `IDVMR`, `IDEFV` e `IDAPV` fazem parte da chave primária de todo resultado. Dois resultados só são comparáveis se as versões estiverem declaradas, e nenhum resultado pode existir sem elas.

**P4 — Base imutável, cenário mutável.** As tabelas `P` são carregadas de uma base de referência somente leitura. As tabelas `D` pertencem ao arquivo de projeto do usuário. As tabelas `C` e `R` são derivadas e podem ser apagadas e recalculadas a qualquer momento sem perda de informação.

**P5 — Ausência é erro, não zero.** Campos numéricos obrigatórios são `NOT NULL`. A inexistência de um componente no veículo é representada por zero explícito.

**P6 — Nomes preservados.** Nomes de tabelas e colunas seguem a nomenclatura do i3ET e do GREET, em inglês, mesmo com a documentação em português.

---

## 2. Convenções do dicionário

Cada tabela é apresentada com o seguinte cabeçalho de colunas:

| Campo | Significado |
|---|---|
| **Coluna** | Nome da coluna |
| **Tipo** | Tipo SQL: `INTEGER`, `REAL`, `TEXT`, `DATE` |
| **Chave** | `PK` (chave primária), `FK→tabela.coluna` (chave estrangeira), `—` |
| **Un.** | Unidade de medida |
| **Classe** | `Exo` (exógeno), `End` (endógeno), `Res` (resultado), `Idx` (índice), `Dsc` (descritivo) |
| **Obr.** | `S` para `NOT NULL` |
| **Descrição / regra** | Semântica e, quando aplicável, a equação |

> **Mudança em relação a `P01`.** A coluna `ColumnType` original assumia os valores `IDprimary`, `IDsecondary`, `Data`, `Calc` e `Info`, misturando papel de chave com natureza do dado. Aqui os dois conceitos são separados em **Chave** e **Classe**, o que permite gerar o DDL automaticamente e classificar parâmetros conforme a diretriz D4.

---

## 3. Mapa de relacionamentos

```
                       P12 IDVPT ──┐
                       P13 IDVDT ──┼──► P15 IDVMR ──► P16 (IDVMR,IDGG,IDM) ──► MshareGG
                       P14 IDVS  ──┘                         ▲        ▲
                                                             │        │
 D01 IDV ──┬──► D02 (IDV,IDEA) ──┬──► IDMPV  P05             │      P09 IDM ──► P11 (IDM,IDEFV) EF
           │                     ├──► IDVMR  P15 ────────────┘        ▲
           │                     └──► IDEFV  P10 ─────────────────────┘
           │
           └──► D03 (IDV,IDVP) GC ──► P07 IDVP
                                        ▲
                       P02 IDSG ──► P08 (IDSG,IDVP,IDG,IDGG) ──► P03 IDG
                            │                                     P04 IDGG
                            └──► P06 (IDMPV,IDSG) Beta,GCR,MR

 P17 IDBTy ──► P18 IDBTe ──► P19 IDBMd ──► P20 (IDBMd,IDGG,IDM) BMshareGG

 P21 IDAP ──► P22 (IDAPV,IDAP,IDFuel) FuelShare ──► P24 IDFuel
                    ▲                                    │
              P23 IDAPV                                  └──► P25 (IDFuel,IDEFV) EFfuel
```

---

## 4. Tabelas de parâmetros (P)

### P01 — `DataDictionary` (List of Tables)

Metatabela: descreve todas as demais. É lida pelo programa para gerar a interface, validar a carga e produzir esta documentação.

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição / regra |
|---|---|---|---|---|---|---|
| `IDTable` | TEXT | PK | — | Idx | S | Identificação da tabela (`P01`…`R99`) |
| `ColumnName` | TEXT | PK | — | Idx | S | Nome da coluna |
| `ColumnOrder` | INTEGER | — | — | Dsc | S | Ordem de apresentação |
| `SQLType` | TEXT | — | — | Dsc | S | `INTEGER`, `REAL`, `TEXT`, `DATE` |
| `KeyRole` | TEXT | — | — | Dsc | S | `PK`, `FK`, `—` |
| `FKTarget` | TEXT | — | — | Dsc | N | `tabela.coluna` quando `KeyRole = FK` |
| `Unit` | TEXT | — | — | Dsc | N | Unidade de medida |
| `ParamClass` | TEXT | — | — | Dsc | S | `Exo`, `End`, `Res`, `Idx`, `Dsc` |
| `Required` | INTEGER | — | — | Dsc | S | 1 = `NOT NULL` |
| `Domain` | TEXT | — | — | Dsc | N | Domínio admissível (lista, faixa) |
| `DsColumnName` | TEXT | — | — | Dsc | N | Descrição em linguagem natural |
| `ColumnCalculationFormula` | TEXT | — | — | Dsc | N | Equação, quando `ParamClass ∈ {End, Res}` |
| `TableName` | TEXT | — | — | Dsc | S | Nome extenso da tabela |

**Novidades em relação a `P01` original:** `ColumnOrder`, `KeyRole`, `FKTarget`, `Unit`, `ParamClass`, `Required` e `Domain`. A coluna `IDTable` é sempre textual (corrigindo a divergência 10 do Documento 1).

### P02 — `VehicleSubgroup` (Vehicle Subgroup List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDSG` | INTEGER | PK | — | Idx | S | Subgrupo do veículo (1 a 43) |
| `DsSG` | TEXT | — | — | Dsc | S | Nome do subgrupo |

### P03 — `GenericGroup` (Generic Groups List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDG` | INTEGER | PK | — | Idx | S | Grupo genérico (1 a 9) |
| `DsG` | TEXT | — | — | Dsc | S | Nome do grupo |

### P04 — `GreetGroup` (GREET Group List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDGG` | TEXT | PK | — | Idx | S | Grupo GREET: `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`, `Iaux`, `Iprinc`, `J`, `K` |
| `DsGG` | TEXT | — | — | Dsc | S | Nome do grupo |
| `IsBattery` | INTEGER | — | — | Dsc | S | 1 para `Iaux` e `Iprinc`; controla o tratamento de §11 do Documento 1 |

### P05 — `MassParamVersion` (Mass Parameters List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDMPV` | INTEGER | PK | — | Idx | S | Versão dos parâmetros de massa |
| `DsMPV` | TEXT | — | — | Dsc | S | Nome da versão |
| `DateIDMPV` | DATE | — | — | Dsc | S | Data de referência |
| `SourceMPV` | TEXT | — | — | Dsc | N | Origem da versão |

### P06 — `MassEstimationParam` (Mass Estimation Parameters)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição / regra |
|---|---|---|---|---|---|---|
| `IDMPV` | INTEGER | PK, FK→P05 | — | Idx | S | Versão dos parâmetros |
| `IDSG` | INTEGER | PK, FK→P02 | — | Idx | S | Subgrupo |
| `Beta` | REAL | — | — | Exo | S | Expoente da lei de escala; `Beta ≥ 0` |
| `GCR` | REAL | — | conf. `utGCR` | Exo | S | Valor de referência do parâmetro; `GCR > 0` |
| `utGCR` | TEXT | — | — | Dsc | S | Unidade de `GCR` |
| `MR` | REAL | — | kg | Exo | S | Massa de referência; `MR ≥ 0` |
| `fLM` | REAL | — | — | Exo | S | Fator de leveza; padrão `1,0`; ver §15.3 do Documento 1 |
| `Reference` | TEXT | — | — | Dsc | N | Fonte do parâmetro |

### P07 — `VehicleParam` (Vehicle Parameters List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição / regra |
|---|---|---|---|---|---|---|
| `IDVP` | INTEGER | PK | — | Idx | S | Parâmetro do veículo (2 a 42) |
| `DsVP` | TEXT | — | — | Dsc | S | Nome do parâmetro |
| `utVP` | TEXT | — | — | Dsc | S | Unidade |
| `ParamClass` | TEXT | — | — | Dsc | S | `Exo`, `End` ou `Res` |
| `GCEquation` | TEXT | — | — | Dsc | N | Equação quando `ParamClass ≠ Exo` (§7.2 do Documento 1) |
| `AppliesTo` | TEXT | — | — | Dsc | N | Lista de `IDVPT` a que o parâmetro se aplica; vazio = todos |

### P08 — `SubgroupCorrelation` (Group and subgroup correlation)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDSG` | INTEGER | PK, FK→P02 | — | Idx | S | Subgrupo |
| `IDVP` | INTEGER | FK→P07 | — | Idx | S | Parâmetro dimensionador do subgrupo |
| `IDG` | INTEGER | FK→P03 | — | Idx | S | Grupo genérico |
| `IDGG` | TEXT | FK→P04 | — | Idx | S | Grupo GREET |
| `ExcludedVPT` | TEXT | — | — | Dsc | N | Lista de `IDVPT` em que o subgrupo **não existe**; nesses veículos `GC = 0` e `ME = 0` |

> **Mudança:** na origem, as quatro colunas eram `IDprimary`. Como cada subgrupo tem exatamente um parâmetro, um grupo e um grupo GREET, a chave primária é apenas `IDSG` e as demais são estrangeiras. Isso torna a cardinalidade explícita e impede que um subgrupo seja contado em dois grupos — causa de dupla contagem de massa.

### P09 — `Material` (Material List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição / regra |
|---|---|---|---|---|---|---|
| `IDM` | TEXT | PK | — | Idx | S | Material. **É texto**: além de códigos numéricos, a base usa `4a`, `4b`, `46a` e `46b` |
| `DsM` | TEXT | — | — | Dsc | S | Nome do material |
| `Mspec` | TEXT | — | — | Dsc | N | Especificação |
| `EFBasis` | TEXT | — | — | Dsc | S | Base de aplicação do fator: `mass` (kg CO₂e/kg), `energy` (kg CO₂e/kWh), `vehicle` (kg CO₂e/veículo) |
| `EFBasisParam` | INTEGER | FK→P07 | — | Dsc | N | `IDVP` que fornece a base quando `EFBasis ≠ mass` (ex.: `5` para `IDM 86`) |
| `IsProcess` | INTEGER | — | — | Dsc | S | 1 para pseudo-materiais de processo (montagem, descarte) |
| `ShareRole` | TEXT | — | — | Dsc | S | `material`, `process` ou `breakdown`. **Só os de papel `material` entram na soma que deve dar 1** |

> **Mudança:** `EFBasis`, `EFBasisParam`, `IsProcess` e `ShareRole` substituem as exceções codificadas para `IDM 86`, `84`, `99` e `100` (divergência 13 do Documento 1).
>
> **Por que `ShareRole` é indispensável.** As receitas de materiais da base original trazem, dentro do mesmo grupo, três coisas diferentes: os materiais propriamente ditos; pseudo-materiais de **processo** (a montagem da bateria, por exemplo, com participação 1); e **redetalhamentos** do material ativo da bateria por química do cátodo (`IDM 87` a `97`), que repetem massa já contada em `IDM 41`. Somar tudo produz receitas que fecham em 2 ou em 3 — exatamente o que se observa na base original. `ShareRole` separa os três papéis e torna o invariante de fechamento verificável.

### P10 — `EFVersion` (Emission Factors Version List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDEFV` | TEXT | PK | — | Idx | S | Versão dos fatores: `G22`, `G23`, `G24`, `BR25BR`, `BR25m`, `BR25GLO`, … |
| `DsEFV` | TEXT | — | — | Dsc | S | Nome da versão |
| `DateIDEFV` | DATE | — | — | Dsc | S | Data de referência |
| `GWPSet` | TEXT | — | — | Dsc | S | Conjunto de GWP: `AR6-100` (diretriz D12) |
| `SourceEFV` | TEXT | — | — | Dsc | S | Fonte: `GREET 2022`, `FGV/Unicamp — Berço ao Portão / Fundep — Programa Move`, … |
| `LicenseEFV` | TEXT | — | — | Dsc | N | Condições de redistribuição |

### P11 — `EmissionFactor` (Emission Factors values list)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDM` | TEXT | PK, FK→P09 | — | Idx | S | Material |
| `IDEFV` | TEXT | PK, FK→P10 | — | Idx | S | Versão dos fatores |
| `EF` | REAL | — | conf. `P09.EFBasis` | Exo | S | Fator de emissão; `EF ≥ 0` |
| `EFnotes` | TEXT | — | — | Dsc | **S** | Procedência do valor. Obrigatório: identifica a fonte, a versão e se o dado foi processado. Quando o fator é nulo, registra que a emissão é contabilizada como zero por ausência de dado |

### P12 / P13 / P14 — `Powertrain`, `DesignType`, `VehicleSize`

| Tabela | Coluna | Tipo | Chave | Descrição |
|---|---|---|---|---|
| P12 | `IDVPT` | TEXT | PK | `ICEV`, `HEV`, `PHEV`, `BEV`, `SHEV`, `SPHEV`, `FCEV` |
| P12 | `DsVPT` | TEXT | — | Descrição |

> **Nota.** A complexidade híbrida `fH` **não** é atributo do trem de força: ela é exógena por veículo e reside em `D03`, no `IDVP 29`. Na base de referência ela vale **1 para todos os veículos**, como na linha 39 do módulo M2 do i3ET. Duplicá-la em `P12` criaria duas fontes de verdade.

| P13 | `IDVDT` | TEXT | PK | `Hatchback`, `Sedan`, `SUV`, `PUT` |
| P13 | `DsVDT` | TEXT | — | Descrição |
| P14 | `IDVS` | TEXT | PK | `Subcompact`, `Compact`, `Midsize`, `Large`, `Pickup` |
| P14 | `DsVS` | TEXT | — | Descrição |

### P15 — `VehicleMaterialRecipe` (Vehicle Material Recipe List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDVMR` | TEXT | PK | — | Idx | S | Receita de materiais |
| `IDVPT` | TEXT | FK→P12 | — | Idx | S | Trem de força típico da receita |
| `IDVDT` | TEXT | FK→P13 | — | Idx | N | Carroceria típica |
| `IDVS` | TEXT | FK→P14 | — | Idx | N | Porte típico |
| `DsVMR` | TEXT | — | — | Dsc | S | Descrição |

> **Nota de uso.** `IDVPT`, `IDVDT` e `IDVS` aqui são **características típicas**, não restrições. Quem determina a receita de um veículo é `D02.IDVMR` (divergência 9 do Documento 1). Divergência entre a receita escolhida e as características do veículo gera **aviso**, não erro.

### P16 — `MaterialShare` (Vehicle Material Recipe per GREET group)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDVMR` | TEXT | PK, FK→P15 | — | Idx | S | Receita |
| `IDGG` | TEXT | PK, FK→P04 | — | Idx | S | Grupo GREET |
| `IDM` | TEXT | PK, FK→P09 | — | Idx | S | Material |
| `MshareGG` | REAL | — | fração | Exo | S | Participação mássica; `0 ≤ MshareGG ≤ 1` |

**Restrição de fechamento:** para todo (`IDVMR`, `IDGG`), somando apenas os `IDM` com `P09.ShareRole = material`, `|Σ MshareGG − 1| ≤ 10⁻⁶`.

> **Valores normalizados.** As participações desta base foram normalizadas: cada uma foi dividida pela soma dos itens `material` do seu grupo, corrigindo desvios de arredondamento de até 1 300 ppm herdados da origem. A aba `Normalizacao` do Documento 3 registra, para cada grupo, a soma original e o fator aplicado.

### P17 / P18 — `BatteryType`, `BatteryTechnology`

| Tabela | Coluna | Tipo | Chave | Descrição |
|---|---|---|---|---|
| P17 | `IDBTy` | TEXT | PK | Tipo de bateria (`Li-Ion`, `Ni-MH`, `Lead-Acid`) |
| P17 | `DsBTy` | TEXT | — | Descrição |
| P18 | `IDBTe` | TEXT | PK | Tecnologia (`NMC111`, `LFP`, `NCA`, …) |
| P18 | `IDBTy` | TEXT | FK→P17 | Tipo a que pertence |
| P18 | `DsBTe` | TEXT | — | Descrição |

> **Correção de tipo:** `P17.DsBTy` e `P18.DsBTe` estavam declarados como `Float` em `P01`, sendo textos.

### P19 — `BatteryModel` (Battery Models Parameters)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição / regra |
|---|---|---|---|---|---|---|
| `IDBMd` | TEXT | PK | — | Idx | S | Modelo de bateria; `'NA'` = veículo sem bateria de tração |
| `IDEFV` | TEXT | FK→P10 | — | Idx | N | Versão de fatores de origem |
| `IDVPT` | TEXT | FK→P12 | — | Idx | N | Trem de força de destino |
| `IDBTe` | TEXT | FK→P18 | — | Idx | N | Tecnologia |
| `RefRange` | REAL | — | km | Exo | S | Autonomia de referência |
| `RefEnergy` | REAL | — | kWh | Exo | S | Capacidade de referência |
| `RefPower` | REAL | — | kW | Exo | S | Potência de referência |
| `RefWeight` | REAL | — | kg | End | S | `HEV`: `RefPower × PowerDensity`; demais: `RefEnergy × EnergyDensity` |
| `RefGHGIDBMd` | REAL | — | kg CO₂e | End | S | `HEV`: `RefWeight × GravimetricGHGDensity`; demais: `RefEnergy × EnergyGHGDensity` |
| `EnergyDensity` | REAL | — | kg/kWh | Exo/End | S | `HEV`: `RefWeight / RefEnergy`; demais: exógeno |
| `PowerDensity` | REAL | — | kg/kW | Exo | S | Exógeno |
| `GravimetricEnergyDensity` | REAL | — | kWh/kg | End | S | `1 / EnergyDensity`, com `EnergyDensity ≠ 0` |
| `GravimetricPowerDensity` | REAL | — | kW/kg | End | S | `1 / PowerDensity`, com `PowerDensity ≠ 0` |
| `GravimetricGHGDensity` | REAL | — | kg CO₂e/kg | Exo/End | S | `HEV`: exógeno; demais: `RefGHGIDBMd / RefWeight` |
| `EnergyGHGDensity` | REAL | — | kg CO₂e/kWh | Exo/End | S | `HEV`: `RefGHGIDBMd / RefEnergy`; demais: exógeno |
| `DsBMd` | TEXT | — | — | Dsc | N | Descrição |

> **Regra de divisão protegida.** Toda derivação com denominador nulo grava `NULL` e uma linha no log de validação. A linha `IDBMd = 'NA'` tem todos os campos numéricos iguais a zero e nenhuma derivação é executada sobre ela — é o que elimina o `inf` observado em `Results_ALL_tables` (divergência 8).

### P20 — `BatteryMaterialShare` (Battery Material Recipe per Model)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDBMd` | TEXT | PK, FK→P19 | — | Idx | S | Modelo de bateria |
| `IDGG` | TEXT | PK, FK→P04 | — | Idx | S | Grupo GREET (`Iprinc` ou `Iaux`) |
| `IDM` | TEXT | PK, FK→P09 | — | Idx | S | Material |
| `BMshareGG` | REAL | — | fração | Exo | S | Participação mássica; renomeada de `BMshare` (divergência 1) |

### P21 — `AssemblyProcess` *(nova)*

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDAP` | INTEGER | PK | — | Idx | S | Processo de montagem |
| `DsAP` | TEXT | — | — | Dsc | S | Nome do processo |
| `IncludedInA` | INTEGER | — | — | Dsc | S | 1 se o processo compõe o agregado **A (Assembling)**. `Paint Production` tem 0: é energia de produção de material, já contada pelo `IDM` da tinta |
| `NotesAP` | TEXT | — | — | Dsc | N | Observações |

### P22 — `AssemblyEnergy` *(nova)*

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDAPV` | TEXT | PK, FK→P23 | — | Idx | S | Versão dos parâmetros de montagem |
| `IDAP` | INTEGER | PK, FK→P21 | — | Idx | S | Processo |
| `IDFuel` | TEXT | PK, FK→P24 | — | Idx | S | Portador de energia |
| `EnergyPerVehicle` | REAL | — | MJ/veículo | Exo | S | Energia do processo por veículo |
| `FuelShare` | REAL | — | fração | Exo | S | Participação do portador no processo |

**Restrição de fechamento:** para todo (`IDAPV`, `IDAP`), `|Σ FuelShare − 1| ≤ 10⁻⁶`, e `EnergyPerVehicle` é constante dentro do par.

### P23 — `AssemblyParamVersion` *(nova)*

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDAPV` | TEXT | PK | — | Idx | S | Versão dos parâmetros de montagem |
| `DsAPV` | TEXT | — | — | Dsc | S | Nome |
| `DateIDAPV` | DATE | — | — | Dsc | S | Data de referência |
| `Method` | TEXT | — | — | Dsc | S | `from_EF` (lê o `IDM 99` de `P11` na versão `IDEFV` do cenário — **padrão**), `process` (calcula por `P22` × `P25`) ou `fixed` (usa o valor agregado) |
| `FixedGHGPerVehicle` | REAL | — | kg CO₂e/veículo | Exo | N | Valor agregado, quando `Method = fixed` |
| `Status` | TEXT | — | — | Dsc | S | `recommended` ou `legacy`. Versões `legacy` existem para reproduzir resultados anteriores e não são selecionadas por padrão |
| `IDEFVdefault` | TEXT | FK→P10 | — | Idx | N | Versão de fatores a que esta versão de montagem corresponde |
| `SourceAPV` | TEXT | — | — | Dsc | S | Fonte |

### P24 — `EnergyCarrier` *(nova)*

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDFuel` | TEXT | PK | — | Idx | S | `ResidOil`, `Diesel`, `NaturalGas`, `Coal`, `Electricity` |
| `DsFuel` | TEXT | — | — | Dsc | S | Descrição |

### P25 — `FuelEmissionFactor` *(nova)*

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDFuel` | TEXT | PK, FK→P24 | — | Idx | S | Portador |
| `IDEFV` | TEXT | PK, FK→P10 | — | Idx | S | Versão dos fatores |
| `EFfuel` | REAL | — | g CO₂e/MJ | Exo | S | Fator de emissão; é aqui que entram os fatores brasileiros (D13) |
| `EFfuelNotes` | TEXT | — | — | Dsc | N | Rastreabilidade |

---

## 5. Tabelas de dados do cenário (D)

### D01 — `Vehicle` (Vehicle List)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDV` | INTEGER | PK | — | Idx | S | Veículo |
| `DsV` | TEXT | — | — | Dsc | S | Nome (`BP01`…`BP12` na base de referência) |
| `IDVPT` | TEXT | FK→P12 | — | Idx | S | Trem de força |
| `IDVDT` | TEXT | FK→P13 | — | Idx | S | Carroceria |
| `IDVS` | TEXT | FK→P14 | — | Idx | S | Porte |
| `IDLR` | TEXT | — | — | Idx | S | `Regular` ou `Luxury` |
| `IsUserDefined` | INTEGER | — | — | Dsc | S | 1 quando criado pelo usuário |
| `NotesIDV` | TEXT | — | — | Dsc | N | Observações |

### D02 — `EvaluationAlternative` (Vehicle Evaluation Criteria)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDV` | INTEGER | PK, FK→D01 | — | Idx | S | Veículo |
| `IDEA` | INTEGER | PK | — | Idx | S | Alternativa de avaliação |
| `IDMPV` | INTEGER | FK→P05 | — | Idx | S | Versão dos parâmetros de massa |
| `IDVMR` | TEXT | FK→P15 | — | Idx | S | Receita de materiais **(prevalece sobre `P15`)** |
| `IDEFV` | TEXT | FK→P10 | — | Idx | S | Versão dos fatores de emissão |
| `IDAPV` | TEXT | FK→P23 | — | Idx | S | Versão dos parâmetros de montagem |
| `Boundary` | TEXT | — | — | Idx | S | Fronteira: `MAT` (só materiais) ou `MAT_ASM` (materiais + montagem, padrão) |
| `NotesIDEA` | TEXT | — | — | Dsc | N | Observações |

> **Mudança:** a chave primária passa a ser (`IDV`, `IDEA`). Na origem, as cinco primeiras colunas eram todas `IDprimary`, o que permitiria duas linhas com o mesmo (`IDV`, `IDEA`) e versões diferentes — um cenário ambíguo. `IDAPV` e `Boundary` são novas e decorrem da incorporação da montagem.

### D04 — `UserEFVersion` *(nova)* — versões de fatores criadas pelo usuário

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDEFV` | TEXT | PK | — | Idx | S | Identificador da versão; **não pode colidir com `P10.IDEFV`** |
| `DsEFV` | TEXT | — | — | Dsc | S | Nome dado pelo usuário |
| `DateIDEFV` | DATE | — | — | Dsc | S | Data de referência |
| `GWPSet` | TEXT | — | — | Dsc | S | Conjunto de GWP declarado |
| `SourceEFV` | TEXT | — | — | Dsc | S | **Obrigatório**: origem dos valores. Sem procedência declarada, a versão não é aceita |
| `LicenseEFV` | TEXT | — | — | Dsc | N | Condições de uso declaradas pelo usuário |
| `BasedOnIDEFV` | TEXT | FK→P10 | — | Idx | N | Versão da base cujos fatores são herdados para os materiais não informados em `D05` |

### D05 — `UserEmissionFactor` *(nova)*

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDM` | TEXT | PK, FK→P09 | — | Idx | S | Material |
| `IDEFV` | TEXT | PK, FK→D04 | — | Idx | S | Versão do usuário |
| `EF` | REAL | — | conf. `P09.EFBasis` | Exo | S | Fator informado |
| `EFnotes` | TEXT | — | — | Dsc | N | Origem do valor |

> **Resolução dos fatores.** Na carga, o programa monta a tabela efetiva como `P11 ∪ D05`, com `D05` tendo precedência sobre a versão herdada em `BasedOnIDEFV`. A base de referência permanece intacta, e toda saída marca as linhas que usaram uma versão do usuário. É este o mecanismo que também recebe os fatores do Projeto Berço ao Portão antes de sua incorporação definitiva.

### D03 — `VehicleParamValue` (Vehicle Parameters Values)

| Coluna | Tipo | Chave | Un. | Classe | Obr. | Descrição |
|---|---|---|---|---|---|---|
| `IDV` | INTEGER | PK, FK→D01 | — | Idx | S | Veículo |
| `IDVP` | INTEGER | PK, FK→P07 | — | Idx | S | Parâmetro |
| `GC` | REAL | — | conf. `P07.utVP` | Exo/End | S | Valor do parâmetro |
| `GCText` | TEXT | — | — | Exo | N | Valor textual, usado apenas por `IDVP 32` (`IDBMd`) |
| `IsCalculated` | INTEGER | — | — | Dsc | S | 1 quando `P07.ParamClass ≠ Exo`; o valor é recalculado a cada execução |

> **Mudança:** `P01` declarava `D03.GC` como `Text` com `ColumnType = Calc`. Separam-se agora o valor numérico (`GC`, `REAL`) do único parâmetro textual do modelo (`GCText`, para `IDVP 32`), o que permite tipagem forte e validação de faixa.

---

## 6. Tabelas calculadas (C)

Todas as tabelas `C` têm a mesma natureza: são **derivadas**, reconstruídas do zero a cada execução, e todas as suas colunas de valor têm `ParamClass = Res`. Por isso apresentamos apenas chaves e colunas de valor.

| Tabela | Nome | Chave primária | Colunas de valor | Equação (Documento 1) |
|---|---|---|---|---|
| `C01` | `MassBySubgroup` | `IDV`, `IDEA`, `IDSG` | `IDGG`, `IDVP`, `GC`, `Beta`, `GCR`, `MR`, `fLM`, `ME` | §8.1 |
| `C02` | `MassByGroup` | `IDV`, `IDEA`, `IDGG` | `MassIDGG` | §9 |
| `C03` | `MassByMaterialGroup` | `IDV`, `IDEA`, `IDGG`, `IDM` | `MshareGG`, `MassIDMpGG` | §10 |
| `C04` | `GHGByMaterialGroup` | `IDV`, `IDEA`, `IDGG`, `IDM` | `EF`, `GHGIDMpGG` | §12 |
| `C05` | `GHGByGroup` | `IDV`, `IDEA`, `IDGG` | `GHGIDGG` | §12 |
| `C06` | `BatteryMassByMaterial` | `IDV`, `IDEA`, `IDBMd`, `IDGG`, `IDM` | `BMshareGG`, `MassIDMpGGB` | §11.3 |
| `C07` | `BatteryGHGByMaterial` | `IDV`, `IDEA`, `IDBMd`, `IDGG`, `IDM` | `EF`, `GHGIDMpGGB` | §11.4 |
| `C08` | `BatteryMassGHG` | `IDV`, `IDEA`, `IDBMd`, `IDGG`, `IDM` | `MassIDMpGGB`, `GHGIDMpGGB` | junção `C06 ⋈ C07` |
| `C09` | `MaterialMassGHG` | `IDV`, `IDEA`, `IDGG`, `IDM` | `MassIDMpGG`, `GHGIDMpGG` | junção `C03 ⋈ C04` |
| `C10` | `MassGHGByGroup` | `IDV`, `IDEA`, `IDGG` | `MassIDGG`, `GHGIDGG` | §14 |
| `C11` | `MassGHGByMaterial` | `IDV`, `IDEA`, `IDM` | `MassIDM`, `GHGIDM` | §14 |
| `C12` | `MassGHGByVehicle` | `IDV`, `IDEA` | `MassIDV`, `GHGIDV` | §14 |
| `C13` | `AssemblyGHG` | `IDV`, `IDEA`, `IDAP` | `EnergyPerVehicle`, `GHGAssembly` | §13.2 |
| `C14` | `CradleToGate` | `IDV`, `IDEA` | `MassIDV`, `GHGMaterials`, `GHGAssembly`, `GHGCradleToGate`, `GHGperKg` | §14 |

> **Simplificação de chave.** Na origem, toda tabela `C` repetia `IDMPV`, `IDVMR` e `IDEFV` na chave primária. Como essas três versões são atributos de (`IDV`, `IDEA`) em `D02`, elas são **derivadas** e não precisam compor a chave. O modelo guarda (`IDV`, `IDEA`) e recupera as versões por junção. **As tabelas de relatório (`R`) restituem as três colunas**, porque ali a redundância é desejável: o arquivo exportado precisa ser autoexplicativo fora do banco. Esse é o único ponto do modelo em que normalização e legibilidade foram separadas deliberadamente.

### Colunas de rastreabilidade em `C01`, `C03`, `C04`, `C06` e `C07`

As tabelas de cálculo guardam, além do resultado, os **insumos usados** (`Beta`, `GCR`, `MR`, `GC`, `MshareGG`, `EF`). Isso duplica dado que já existe nas tabelas `P` — deliberadamente. Sem esses campos, auditar um número exige refazer as junções; com eles, a linha exportada contém a conta inteira. É a mesma decisão que a planilha `Results_ALL_tables` já tomava em `T19` e `T29`, aqui tornada regra.

---

## 7. Tabelas de relatório (R)

As tabelas `R` são a materialização do arquivo de exportação. Cada uma é uma consulta sobre `P`, `D` e `C`, desnormalizada e com todas as versões explícitas. A especificação completa, com o mapeamento `T → R` em relação ao `Results_ALL_tables` original, está no Documento 4.

Regras comuns a todas as tabelas `R`:

1. As colunas `IDMPV`, `IDVMR`, `IDEFV` e `IDAPV` aparecem sempre, mesmo quando constantes;
2. Toda coluna numérica tem a unidade declarada no cabeçalho da aba e no dicionário;
3. Toda tabela `R` traz, na primeira linha de metadados, a data e a hora da execução, a versão da calculadora e o *hash* da base de parâmetros utilizada;
4. Nenhuma tabela `R` é editável: é saída.

---

## 8. Regras de integridade além das chaves

| # | Regra | Verificação |
|---|---|---|
| I1 | Fechamento das receitas de materiais | `∀(IDVMR, IDGG)`, somando apenas `IDM` com `P09.ShareRole = material`: `|Σ P16.MshareGG − 1| ≤ 10⁻⁶` |
| I2 | Fechamento das receitas de bateria | `∀(IDBMd, IDGG)` com massa não nula, somando apenas `ShareRole = material`: `|Σ P20.BMshareGG − 1| ≤ 10⁻⁶` |
| I3 | Fechamento da repartição de combustíveis | `∀(IDAPV, IDAP)`: `|Σ P22.FuelShare − 1| ≤ 10⁻⁶` |
| I4 | Cobertura de fatores de emissão | Todo `IDM` citado em `P16` ou `P20` tem linha em `P11` para todo `IDEFV` usado em `D02` |
| I5 | Cobertura de parâmetros do veículo | Todo `IDV` tem linha em `D03` para todo `IDVP` aplicável ao seu `IDVPT` |
| I6 | Domínio de `Beta` e `GCR` | `P06.Beta ≥ 0` e `P06.GCR > 0` |
| I7 | Domínio das participações | `0 ≤ MshareGG ≤ 1`, `0 ≤ BMshareGG ≤ 1`, `0 ≤ FuelShare ≤ 1` |
| I8 | Não negatividade | `EF ≥ 0`, `MR ≥ 0`, `GC ≥ 0` (exceto parâmetros explicitamente autorizados a serem negativos, marcados em `P01.Domain`) |
| I9 | Consistência receita × veículo | `D02.IDVMR` cujo `P15.IDVPT` difira de `D01.IDVPT` gera **aviso** registrado no log |
| I10 | Unicidade do parâmetro dimensionador | Cada `IDSG` aparece exatamente uma vez em `P08` |
| I11 | Bateria coerente | Se `D01.IDVPT ∈ {BEV, PHEV, HEV, SHEV, SPHEV, FCEV}` então `D03.GCText(IDVP 32) ≠ 'NA'`; se `IDVPT = ICEV` então `= 'NA'` |
| I12 | Conservação de massa | `Σ C11.MassIDM = C12.MassIDV`, tolerância relativa 10⁻⁹ |
| I14 | Identificadores do usuário | Nenhum `D04.IDEFV` colide com `P10.IDEFV` |
| I15 | Procedência declarada | Todo `D04.SourceEFV` é não vazio |
| I13 | Conservação de emissões | `Σ C11.GHGIDM = C12.GHGIDV = Σ C10.GHGIDGG`, tolerância relativa 10⁻⁹ |

I1 a I11 são verificadas na **carga**; I12 e I13, após o **cálculo**. Falha em qualquer uma bloqueia a exportação e é exibida com a identificação exata da linha envolvida.

---

## 9. Versionamento e reprodutibilidade

Um resultado da calculadora só é reproduzível se for possível recuperar, sem ambiguidade, todos os insumos que o geraram. O modelo garante isso por quatro mecanismos:

1. **Versões como chave** — `IDMPV`, `IDVMR`, `IDEFV` e `IDAPV` acompanham cada linha de `D02` e são restituídas em toda exportação;
2. **Base imutável** — as tabelas `P` da base de referência não são alteradas pelo usuário; criar variantes significa criar uma nova versão, com novo identificador e data;
3. **Impressão digital da base** — o programa calcula um *hash* SHA-256 sobre o conteúdo ordenado das tabelas `P` e o grava em toda exportação. Dois relatórios com o mesmo *hash* usaram exatamente os mesmos parâmetros;
4. **Arquivo de projeto** — o SQLite do usuário contém as tabelas `D`, o *hash* da base e as tabelas `C` da última execução. Reabri-lo reproduz a análise integralmente.

Tabela de controle correspondente:

### M01 — `RunMetadata`

| Coluna | Tipo | Chave | Descrição |
|---|---|---|---|
| `RunID` | TEXT | PK | Identificador da execução (UUID) |
| `RunTimestamp` | TEXT | — | Data e hora ISO 8601 |
| `CalculatorVersion` | TEXT | — | Versão da calculadora |
| `ParamBaseHash` | TEXT | — | SHA-256 da base de parâmetros |
| `ProjectName` | TEXT | — | Nome do projeto do usuário |
| `ValidationStatus` | TEXT | — | `OK` ou `FALHA`, com a lista de invariantes violados |

---

## 10. DDL SQL completo

O DDL abaixo cria a base inteira em SQLite e é a definição normativa do modelo. As restrições `CHECK` implementam os domínios; as restrições de fechamento (I1, I2, I3) e de conservação (I12, I13) são verificadas em código, por dependerem de agregação.

```sql
PRAGMA foreign_keys = ON;

-- ---------- Metatabela ----------
CREATE TABLE P01_DataDictionary (
  IDTable                  TEXT    NOT NULL,
  ColumnName               TEXT    NOT NULL,
  ColumnOrder              INTEGER NOT NULL,
  SQLType                  TEXT    NOT NULL CHECK (SQLType IN ('INTEGER','REAL','TEXT','DATE')),
  KeyRole                  TEXT    NOT NULL CHECK (KeyRole IN ('PK','FK','-')),
  FKTarget                 TEXT,
  Unit                     TEXT,
  ParamClass               TEXT    NOT NULL CHECK (ParamClass IN ('Exo','End','Res','Idx','Dsc')),
  Required                 INTEGER NOT NULL CHECK (Required IN (0,1)),
  Domain                   TEXT,
  DsColumnName             TEXT,
  ColumnCalculationFormula TEXT,
  TableName                TEXT    NOT NULL,
  PRIMARY KEY (IDTable, ColumnName)
);

-- ---------- Parâmetros: estrutura do veículo ----------
CREATE TABLE P02_VehicleSubgroup (
  IDSG INTEGER PRIMARY KEY,
  DsSG TEXT NOT NULL
);

CREATE TABLE P03_GenericGroup (
  IDG INTEGER PRIMARY KEY,
  DsG TEXT NOT NULL
);

CREATE TABLE P04_GreetGroup (
  IDGG      TEXT PRIMARY KEY,
  DsGG      TEXT NOT NULL,
  IsBattery INTEGER NOT NULL DEFAULT 0 CHECK (IsBattery IN (0,1))
);

CREATE TABLE P07_VehicleParam (
  IDVP       INTEGER PRIMARY KEY,
  DsVP       TEXT NOT NULL,
  utVP       TEXT NOT NULL,
  ParamClass TEXT NOT NULL CHECK (ParamClass IN ('Exo','End','Res')),
  GCEquation TEXT,
  AppliesTo  TEXT
);

CREATE TABLE P08_SubgroupCorrelation (
  IDSG        INTEGER PRIMARY KEY REFERENCES P02_VehicleSubgroup(IDSG),
  IDVP        INTEGER NOT NULL REFERENCES P07_VehicleParam(IDVP),
  IDG         INTEGER NOT NULL REFERENCES P03_GenericGroup(IDG),
  IDGG        TEXT    NOT NULL REFERENCES P04_GreetGroup(IDGG),
  ExcludedVPT TEXT
);

-- ---------- Parâmetros: massa ----------
CREATE TABLE P05_MassParamVersion (
  IDMPV     INTEGER PRIMARY KEY,
  DsMPV     TEXT NOT NULL,
  DateIDMPV DATE NOT NULL,
  SourceMPV TEXT
);

CREATE TABLE P06_MassEstimationParam (
  IDMPV     INTEGER NOT NULL REFERENCES P05_MassParamVersion(IDMPV),
  IDSG      INTEGER NOT NULL REFERENCES P02_VehicleSubgroup(IDSG),
  Beta      REAL NOT NULL CHECK (Beta >= 0),
  GCR       REAL NOT NULL CHECK (GCR  >  0),
  utGCR     TEXT NOT NULL,
  MR        REAL NOT NULL CHECK (MR   >= 0),
  fLM       REAL NOT NULL DEFAULT 1.0 CHECK (fLM > 0),
  Reference TEXT,
  PRIMARY KEY (IDMPV, IDSG)
);

-- ---------- Parâmetros: materiais e fatores ----------
CREATE TABLE P09_Material (
  IDM           TEXT PRIMARY KEY,
  DsM           TEXT NOT NULL,
  Mspec         TEXT,
  EFBasis       TEXT NOT NULL DEFAULT 'mass' CHECK (EFBasis IN ('mass','energy','vehicle')),
  EFBasisParam  INTEGER REFERENCES P07_VehicleParam(IDVP),
  IsProcess     INTEGER NOT NULL DEFAULT 0 CHECK (IsProcess IN (0,1)),
  ShareRole     TEXT NOT NULL DEFAULT 'material'
                CHECK (ShareRole IN ('material','process','breakdown')),
  CHECK (EFBasis = 'mass' OR EFBasisParam IS NOT NULL OR EFBasis = 'vehicle')
);

CREATE TABLE P10_EFVersion (
  IDEFV      TEXT PRIMARY KEY,
  DsEFV      TEXT NOT NULL,
  DateIDEFV  DATE NOT NULL,
  GWPSet     TEXT NOT NULL DEFAULT 'AR6-100',
  SourceEFV  TEXT NOT NULL,
  LicenseEFV TEXT
);

CREATE TABLE P11_EmissionFactor (
  IDM     TEXT    NOT NULL REFERENCES P09_Material(IDM),
  IDEFV   TEXT    NOT NULL REFERENCES P10_EFVersion(IDEFV),
  EF      REAL    NOT NULL CHECK (EF >= 0),
  EFnotes TEXT,
  PRIMARY KEY (IDM, IDEFV)
);

-- ---------- Parâmetros: tipologia do veículo ----------
CREATE TABLE P12_Powertrain (
  IDVPT TEXT PRIMARY KEY,
  DsVPT TEXT NOT NULL
);

CREATE TABLE P13_DesignType (
  IDVDT TEXT PRIMARY KEY,
  DsVDT TEXT NOT NULL
);

CREATE TABLE P14_VehicleSize (
  IDVS TEXT PRIMARY KEY,
  DsVS TEXT NOT NULL
);

CREATE TABLE P15_VehicleMaterialRecipe (
  IDVMR TEXT PRIMARY KEY,
  IDVPT TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDVDT TEXT REFERENCES P13_DesignType(IDVDT),
  IDVS  TEXT REFERENCES P14_VehicleSize(IDVS),
  DsVMR TEXT NOT NULL
);

CREATE TABLE P16_MaterialShare (
  IDVMR    TEXT    NOT NULL REFERENCES P15_VehicleMaterialRecipe(IDVMR),
  IDGG     TEXT    NOT NULL REFERENCES P04_GreetGroup(IDGG),
  IDM      TEXT    NOT NULL REFERENCES P09_Material(IDM),
  MshareGG REAL    NOT NULL CHECK (MshareGG BETWEEN 0 AND 1),
  PRIMARY KEY (IDVMR, IDGG, IDM)
);

-- ---------- Parâmetros: baterias ----------
CREATE TABLE P17_BatteryType (
  IDBTy TEXT PRIMARY KEY,
  DsBTy TEXT NOT NULL
);

CREATE TABLE P18_BatteryTechnology (
  IDBTe TEXT PRIMARY KEY,
  IDBTy TEXT NOT NULL REFERENCES P17_BatteryType(IDBTy),
  DsBTe TEXT NOT NULL
);

CREATE TABLE P19_BatteryModel (
  IDBMd                    TEXT PRIMARY KEY,
  IDEFV                    TEXT REFERENCES P10_EFVersion(IDEFV),
  IDVPT                    TEXT REFERENCES P12_Powertrain(IDVPT),
  IDBTe                    TEXT REFERENCES P18_BatteryTechnology(IDBTe),
  RefRange                 REAL NOT NULL DEFAULT 0 CHECK (RefRange  >= 0),
  RefEnergy                REAL NOT NULL DEFAULT 0 CHECK (RefEnergy >= 0),
  RefPower                 REAL NOT NULL DEFAULT 0 CHECK (RefPower  >= 0),
  RefWeight                REAL NOT NULL DEFAULT 0 CHECK (RefWeight >= 0),
  RefGHGIDBMd              REAL NOT NULL DEFAULT 0 CHECK (RefGHGIDBMd >= 0),
  EnergyDensity            REAL NOT NULL DEFAULT 0,
  PowerDensity             REAL NOT NULL DEFAULT 0,
  GravimetricEnergyDensity REAL,
  GravimetricPowerDensity  REAL,
  GravimetricGHGDensity    REAL,
  EnergyGHGDensity         REAL,
  DsBMd                    TEXT
);

CREATE TABLE P20_BatteryMaterialShare (
  IDBMd     TEXT    NOT NULL REFERENCES P19_BatteryModel(IDBMd),
  IDGG      TEXT    NOT NULL REFERENCES P04_GreetGroup(IDGG),
  IDM       TEXT    NOT NULL REFERENCES P09_Material(IDM),
  BMshareGG REAL    NOT NULL CHECK (BMshareGG BETWEEN 0 AND 1),
  PRIMARY KEY (IDBMd, IDGG, IDM)
);

-- ---------- Parâmetros: montagem ----------
CREATE TABLE P21_AssemblyProcess (
  IDAP        INTEGER PRIMARY KEY,
  DsAP        TEXT NOT NULL,
  IncludedInA INTEGER NOT NULL DEFAULT 1 CHECK (IncludedInA IN (0,1)),
  NotesAP     TEXT
);

CREATE TABLE P23_AssemblyParamVersion (
  IDAPV              TEXT PRIMARY KEY,
  DsAPV              TEXT NOT NULL,
  DateIDAPV          DATE NOT NULL,
  Method             TEXT NOT NULL DEFAULT 'from_EF'
                     CHECK (Method IN ('from_EF','process','fixed')),
  FixedGHGPerVehicle REAL CHECK (FixedGHGPerVehicle IS NULL OR FixedGHGPerVehicle >= 0),
  Status             TEXT NOT NULL DEFAULT 'recommended'
                     CHECK (Status IN ('recommended','legacy')),
  IDEFVdefault       TEXT REFERENCES P10_EFVersion(IDEFV),
  SourceAPV          TEXT NOT NULL,
  CHECK (Method <> 'fixed' OR FixedGHGPerVehicle IS NOT NULL)
);

CREATE TABLE P24_EnergyCarrier (
  IDFuel TEXT PRIMARY KEY,
  DsFuel TEXT NOT NULL
);

CREATE TABLE P22_AssemblyEnergy (
  IDAPV            TEXT    NOT NULL REFERENCES P23_AssemblyParamVersion(IDAPV),
  IDAP             INTEGER NOT NULL REFERENCES P21_AssemblyProcess(IDAP),
  IDFuel           TEXT    NOT NULL REFERENCES P24_EnergyCarrier(IDFuel),
  EnergyPerVehicle REAL    NOT NULL CHECK (EnergyPerVehicle >= 0),
  FuelShare        REAL    NOT NULL CHECK (FuelShare BETWEEN 0 AND 1),
  PRIMARY KEY (IDAPV, IDAP, IDFuel)
);

CREATE TABLE P25_FuelEmissionFactor (
  IDFuel      TEXT NOT NULL REFERENCES P24_EnergyCarrier(IDFuel),
  IDEFV       TEXT NOT NULL REFERENCES P10_EFVersion(IDEFV),
  EFfuel      REAL NOT NULL,
  EFfuelNotes TEXT,
  PRIMARY KEY (IDFuel, IDEFV)
);

-- ---------- Dados do cenário ----------
CREATE TABLE D01_Vehicle (
  IDV           INTEGER PRIMARY KEY,
  DsV           TEXT NOT NULL,
  IDVPT         TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDVDT         TEXT NOT NULL REFERENCES P13_DesignType(IDVDT),
  IDVS          TEXT NOT NULL REFERENCES P14_VehicleSize(IDVS),
  IDLR          TEXT NOT NULL CHECK (IDLR IN ('Regular','Luxury')),
  IsUserDefined INTEGER NOT NULL DEFAULT 0 CHECK (IsUserDefined IN (0,1)),
  NotesIDV      TEXT
);

CREATE TABLE D02_EvaluationAlternative (
  IDV        INTEGER NOT NULL REFERENCES D01_Vehicle(IDV),
  IDEA       INTEGER NOT NULL,
  IDMPV      INTEGER NOT NULL REFERENCES P05_MassParamVersion(IDMPV),
  IDVMR      TEXT    NOT NULL REFERENCES P15_VehicleMaterialRecipe(IDVMR),
  IDEFV      TEXT    NOT NULL REFERENCES P10_EFVersion(IDEFV),
  IDAPV      TEXT    NOT NULL REFERENCES P23_AssemblyParamVersion(IDAPV),
  Boundary   TEXT    NOT NULL DEFAULT 'MAT_ASM' CHECK (Boundary IN ('MAT','MAT_ASM')),
  NotesIDEA  TEXT,
  PRIMARY KEY (IDV, IDEA)
);

CREATE TABLE D04_UserEFVersion (
  IDEFV        TEXT PRIMARY KEY,
  DsEFV        TEXT NOT NULL,
  DateIDEFV    DATE NOT NULL,
  GWPSet       TEXT NOT NULL DEFAULT 'AR6-100',
  SourceEFV    TEXT NOT NULL,
  LicenseEFV   TEXT,
  BasedOnIDEFV TEXT REFERENCES P10_EFVersion(IDEFV)
);

CREATE TABLE D05_UserEmissionFactor (
  IDM     TEXT NOT NULL REFERENCES P09_Material(IDM),
  IDEFV   TEXT NOT NULL REFERENCES D04_UserEFVersion(IDEFV),
  EF      REAL NOT NULL CHECK (EF >= 0),
  EFnotes TEXT,
  PRIMARY KEY (IDM, IDEFV)
);

-- Visao efetiva dos fatores: base + versoes do usuario (usuario tem precedencia)
CREATE VIEW EF_Effective AS
  SELECT IDM, IDEFV, EF, EFnotes, 0 AS IsUserDefined FROM P11_EmissionFactor
  UNION ALL
  SELECT d.IDM, d.IDEFV, d.EF, d.EFnotes, 1 FROM D05_UserEmissionFactor d
  UNION ALL
  SELECT p.IDM, v.IDEFV, p.EF, p.EFnotes, 1
    FROM D04_UserEFVersion v
    JOIN P11_EmissionFactor p ON p.IDEFV = v.BasedOnIDEFV
   WHERE NOT EXISTS (SELECT 1 FROM D05_UserEmissionFactor d
                      WHERE d.IDEFV = v.IDEFV AND d.IDM = p.IDM);

CREATE TABLE D03_VehicleParamValue (
  IDV          INTEGER NOT NULL REFERENCES D01_Vehicle(IDV),
  IDVP         INTEGER NOT NULL REFERENCES P07_VehicleParam(IDVP),
  GC           REAL    NOT NULL DEFAULT 0,
  GCText       TEXT,
  IsCalculated INTEGER NOT NULL DEFAULT 0 CHECK (IsCalculated IN (0,1)),
  PRIMARY KEY (IDV, IDVP)
);

-- ---------- Tabelas calculadas ----------
CREATE TABLE C01_MassBySubgroup (
  IDV   INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDSG INTEGER NOT NULL,
  IDGG  TEXT NOT NULL, IDVP INTEGER NOT NULL,
  GC    REAL NOT NULL, Beta REAL NOT NULL, GCR REAL NOT NULL,
  MR    REAL NOT NULL, fLM  REAL NOT NULL, ME  REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDSG),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C02_MassByGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL,
  MassIDGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C03_MassByMaterialGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  MshareGG REAL NOT NULL, MassIDMpGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG, IDM),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C04_GHGByMaterialGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  EF REAL NOT NULL, GHGIDMpGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG, IDM),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C05_GHGByGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL,
  GHGIDGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C06_BatteryMassByMaterial (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDBMd TEXT NOT NULL,
  IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  BMshareGG REAL NOT NULL, MassIDMpGGB REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDBMd, IDGG, IDM),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C07_BatteryGHGByMaterial (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDBMd TEXT NOT NULL,
  IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  EF REAL NOT NULL, GHGIDMpGGB REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDBMd, IDGG, IDM),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C10_MassGHGByGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL,
  MassIDGG REAL NOT NULL, GHGIDGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C11_MassGHGByMaterial (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDM TEXT NOT NULL,
  MassIDM REAL NOT NULL, GHGIDM REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDM),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C12_MassGHGByVehicle (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL,
  MassIDV REAL NOT NULL, GHGIDV REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C13_AssemblyGHG (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDAP INTEGER NOT NULL,
  EnergyPerVehicle REAL NOT NULL, GHGAssembly REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDAP),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE C14_CradleToGate (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL,
  MassIDV         REAL NOT NULL,
  GHGMaterials    REAL NOT NULL,
  GHGAssembly     REAL NOT NULL,
  GHGCradleToGate REAL NOT NULL,
  GHGperKg        REAL,
  PRIMARY KEY (IDV, IDEA),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

-- C08 e C09 são VIEWs: junções de conveniência, sem dado próprio.
CREATE VIEW C08_BatteryMassGHG AS
  SELECT m.IDV, m.IDEA, m.IDBMd, m.IDGG, m.IDM,
         m.MassIDMpGGB, g.GHGIDMpGGB
    FROM C06_BatteryMassByMaterial m
    JOIN C07_BatteryGHGByMaterial g USING (IDV, IDEA, IDBMd, IDGG, IDM);

CREATE VIEW C09_MaterialMassGHG AS
  SELECT m.IDV, m.IDEA, m.IDGG, m.IDM,
         m.MassIDMpGG, g.GHGIDMpGG
    FROM C03_MassByMaterialGroup m
    JOIN C04_GHGByMaterialGroup g USING (IDV, IDEA, IDGG, IDM);

-- ---------- Controle de execução ----------
CREATE TABLE M01_RunMetadata (
  RunID             TEXT PRIMARY KEY,
  RunTimestamp      TEXT NOT NULL,
  CalculatorVersion TEXT NOT NULL,
  ParamBaseHash     TEXT NOT NULL,
  ProjectName       TEXT,
  ValidationStatus  TEXT NOT NULL
);

CREATE TABLE M02_ValidationLog (
  RunID    TEXT NOT NULL REFERENCES M01_RunMetadata(RunID),
  Severity TEXT NOT NULL CHECK (Severity IN ('INFO','AVISO','ERRO')),
  RuleID   TEXT NOT NULL,
  Message  TEXT NOT NULL,
  Context  TEXT
);

-- ---------- Índices de apoio ----------
CREATE INDEX ix_P11_EFV   ON P11_EmissionFactor (IDEFV);
CREATE INDEX ix_P16_GG    ON P16_MaterialShare  (IDGG, IDM);
CREATE INDEX ix_P20_GG    ON P20_BatteryMaterialShare (IDGG, IDM);
CREATE INDEX ix_D03_VP    ON D03_VehicleParamValue (IDVP);
CREATE INDEX ix_C03_M     ON C03_MassByMaterialGroup (IDM);
CREATE INDEX ix_C04_M     ON C04_GHGByMaterialGroup  (IDM);
```

---

*Documento gerado em 19/09/2026 — versão `a`.*
