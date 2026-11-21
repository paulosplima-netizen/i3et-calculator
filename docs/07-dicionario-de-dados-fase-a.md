# Dicionário de Dados — Fase A (esquema 0.10)
## Passo 2 do método: base e esquema

17/11/2026 · versão h · Complementa o Documento 2 (`DicionarioDeDados_ModeloRelacional_20260919a`), que continua valendo para as tabelas da 0.9.0.

Este documento define, coluna a coluna, as tabelas que a Fase A acrescenta. A definição normativa é o DDL de `core/schema.py`, blocos S5 a S8. Um teste (`tests/test_schema_010.py`) confere que as colunas listadas aqui são as do banco, na mesma ordem.

As convenções são as do Documento 2, §2. Na coluna **Obr.**, `S` é `NOT NULL`.

Versão de 17/11 (potência combinada, passo 4): `P53` passa a guardar fatores de uso combinado por motorização, `P56` é nova (fatores arbitrados por configuração da planilha) e `D12` passa a ser por caso, com os dois fatores; `D06.CombinedPowerRule` vale `Default` ou `ExcelParity`. A base tem 23 tabelas novas.

Versão de 17/11 (alumínio): `P57` é nova (equivalência entre o alumínio único do GREET até 2022 e chapa e extrudado do GREET 2023 em diante) e a regra I28 (§6) registra o aviso quando a receita e a lista de fatores são de versões diferentes.

Versão b (passo 3): as tabelas de parâmetros foram carregadas; `P13` também ganhou `IsCalculable`; entraram os blocos S9 (impressão digital) e S10 (parâmetros da Fase A num projeto antigo). As tabelas do usuário (`D`, `R45`, `M03`) continuam vazias na base.

---

## 1. O que este passo entrega

| Entrega | Onde |
|---|---|
| 23 tabelas novas e uma visão | `core/schema.py`, blocos S5, S6 e S7 |
| Coluna `IsCalculable` em `P12_Powertrain` | bloco S8 |
| Migração de arquivos da 0.9.0, sem perda e repetível | `schema.migrate()`, bloco S8 |
| Carregador que abre arquivos da 0.9.0 e da 0.10 | `core/loader.py` |
| 20 testes novos | `tests/test_schema_010.py` |

O que **não** muda neste passo: `data/base_referencia.sqlite` (e portanto o `ParamBaseHash`), o núcleo de cálculo, as telas e nenhum resultado.

## 2. Ajustes em relação à especificação da Fase A

A especificação (`docs/06`) descrevia as tabelas em nível de conteúdo. Ao fechar as colunas, cinco pontos mudaram:

1. **`P54_MarketParam` é nova.** A Market Vehicles tem 58 parâmetros por veículo, e `P07` só tem os 41 que o núcleo usa (IDVP 2 a 42). Os parâmetros 43 a 58 (modelo, design, porte, Cd, fr, área frontal, cilindrada, eficiências) não cabem em `P07` sem refazer a tabela. `P54` cataloga os 58 e aponta para o `IDVP` de `P07` quando há correspondência.
2. **`P55_PBEVRecordValue` é nova.** As colunas da tabela do INMETRO mudam de uma edição para outra. Os valores de cada registro ficam em formato longo (um campo por linha), e `P28` guarda só a identificação.
3. **`P35` é indexada por `IDMP`**, não por `IDVP`, porque o parâmetro 44 (porte) tem regra de valor padrão e não existe em `P07`.
4. **`R45` é indexada por `CaseKey`**, não por `IDCase`, e traz a motorização. Assim o resultado de uma rodada congelada não depende de `D07`, que o usuário pode alterar depois.
5. **`D06.CombinedPowerRule` tem domínio fixo** (`Default`, `ExcelParity`) em vez de chave estrangeira. Em 17/11 a regra de potência combinada passou de fórmulas (`ICE`, `EE`, `SUM`, `MAX`) para fatores de uso combinado dos motores: `P53` guarda o par padrão por motorização, `P56` os pares arbitrados para igualar a planilha e `D12` o ajuste do usuário por caso.

Próximos números livres: T47, P60, D13, C35, R54, M04.

---

## 3. Tabelas de parâmetros (P) — bloco S5

### P54 — `P54_MarketParam` (parâmetros da Market Vehicles)

Origem: Market Vehicles, linhas 4 a 6, colunas N:BS.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDMP` | INTEGER | PK | S | Número do parâmetro na linha 4 da planilha, de 1 a 58 |
| `DsMP` | TEXT | — | S | Nome, da linha 5 |
| `utMP` | TEXT | — | N | Unidade, da linha 6 |
| `SheetColumn` | TEXT | — | S | Coluna na planilha (`N` a `BS`) |
| `IDVP` | INTEGER | FK→P07 | N | Parâmetro correspondente do núcleo, quando existe |
| `ValueKind` | TEXT | — | S | `Num` ou `Text` |

### P26 — `P26_MarketVehicle` (veículos de mercado)

Origem: Market Vehicles, linhas 7 a 161. 154 veículos, seis deles SELEÇÃO.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDMV` | INTEGER | PK | S | Veículo de mercado |
| `DsMV` | TEXT | única | S | ID Vehicle da planilha (parâmetro 1), como `FIAT ARGO` |
| `Brand` | TEXT | — | N | Marca |
| `Model` | TEXT | — | N | Modelo |
| `IDVPT` | TEXT | FK→P12 | S | Motorização |
| `IDVDT` | TEXT | FK→P13 | S | Carroceria |
| `IDVS` | TEXT | FK→P14 | S | Porte |
| `IDLR` | TEXT | — | S | `Regular` ou `Luxury` |
| `Fuel` | TEXT | — | N | Combustível declarado |
| `MarketGroup` | TEXT | — | N | Grupo de mercado (`HATCH C`, `SUV C`, …, `Other`) |
| `SalesClass` | TEXT | — | S | `V` (60 automóveis mais licenciados), `CL` (50 comerciais leves) ou `ND` |
| `SalesRefYear` | INTEGER | — | N | Ano dos licenciamentos gravados na planilha |
| `SalesUnits` | INTEGER | — | N | Unidades licenciadas nesse ano. Substituído por `P47` na Fase B |
| `IsSelecao` | INTEGER | — | S | 1 para os seis veículos SELEÇÃO |
| `IDMVRepresentative` | INTEGER | FK→P26 | N | Para um SELEÇÃO, o veículo real de que herda os parâmetros não ponderados |
| `SheetRow` | INTEGER | — | N | Linha na planilha |
| `NotesMV` | TEXT | — | N | Observação |
| `SourceMV` | TEXT | — | N | Fonte dos dados |

Os rótulos de carroceria e porte da planilha (`Hatch`, `Extralarge`, `Van`, `Chassis`) são normalizados para os de `P13` e `P14` no passo 3, que também acrescenta a `P12`, `P13` e `P14` as linhas que faltam.

### P27 — `P27_MarketVehicleParam` (valores dos parâmetros por veículo)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDMV` | INTEGER | PK, FK→P26 | S | Veículo |
| `IDMP` | INTEGER | PK, FK→P54 | S | Parâmetro |
| `Value` | REAL | — | N | Valor numérico |
| `ValueText` | TEXT | — | N | Valor textual |
| `ValueClass` | TEXT | — | S | Classe do valor: `Man` (fabricante), `Def` (regra de valor padrão), `Calc` (calculado), `Eng` (estimativa de engenharia), `PBEV`, `Avg` (média ponderada do SELEÇÃO) ou `Rep` (copiado do representativo) |

Exatamente um entre `Value` e `ValueText` é preenchido.

### P36 — `P36_PBEVEdition` (edições do PBEV/INMETRO)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDPBE` | TEXT | PK | S | Edição, como `PBEV2026` |
| `EditionYear` | INTEGER | — | S | Ano |
| `EditionVersion` | TEXT | — | N | Versão dentro do ano |
| `SourcePBE` | TEXT | — | S | Fonte (arquivo ou endereço) |
| `PublishedAt` | DATE | — | N | Data de publicação |
| `ImportedAt` | TEXT | — | N | Data e hora da importação |
| `RecordCount` | INTEGER | — | N | Registros da edição |
| `NotesPBE` | TEXT | — | N | Observações |

### P28 — `P28_PBEVRecord` (registros do PBEV)

Origem: `PBEV - INMETRO - 2026`, B22:AD864. 843 registros.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDPBR` | INTEGER | PK | S | Registro |
| `IDPBE` | TEXT | FK→P36 | S | Edição |
| `MatchKey` | TEXT | — | S | Chave padronizada de cruzamento: marca, espaço, modelo, em maiúsculas |
| `Brand` | TEXT | — | S | Marca |
| `Model` | TEXT | — | S | Modelo |
| `Version` | TEXT | — | N | Versão |
| `SheetRow` | INTEGER | — | N | Linha na planilha |

### P55 — `P55_PBEVRecordValue` (campos de cada registro do PBEV)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDPBR` | INTEGER | PK, FK→P28 | S | Registro |
| `FieldName` | TEXT | PK | S | Nome do campo, como no cabeçalho da edição |
| `Value` | REAL | — | N | Valor numérico |
| `ValueText` | TEXT | — | N | Valor textual, incluindo `ND` e `N.A.` |

Exatamente um entre `Value` e `ValueText` é preenchido.

### P50 — `P50_MarketVehiclePBEV` (vínculo veículo–registro)

Origem: Market Vehicles BT:CV. 92 dos 154 veículos têm registro; 64 têm mais de um.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDMV` | INTEGER | PK, FK→P26 | S | Veículo |
| `IDPBR` | INTEGER | PK, FK→P28 | S | Registro |
| `IDPBE` | TEXT | FK→P36 | S | Edição do registro |
| `IsFirstMatch` | INTEGER | — | S | 1 para o registro que a busca da planilha devolve (a primeira versão) |

### P29 — `P29_VehicleCategory` (categorias A0 a A5)

Origem: Control Panel X12:Z17.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDVC` | TEXT | PK | S | Categoria, de `A0` a `A5` |
| `DsVC` | TEXT | — | S | Nome, como `Hatch Compact Regular` |
| `CaseDigit` | INTEGER | única | S | Dígito da categoria no rótulo dos casos (`A0` → casos `A01` a `A06`) |
| `IDVDT` | TEXT | FK→P13 | S | Carroceria |
| `IDVS` | TEXT | FK→P14 | S | Porte |
| `IDLR` | TEXT | — | S | `Regular` ou `Luxury` |
| `MarketGroup` | TEXT | — | N | Grupo de mercado de onde saem os ICEV elegíveis como referência |
| `IDMVSelecao` | INTEGER | FK→P26 | S | Veículo SELEÇÃO da categoria |
| `IDMVRepresentative` | INTEGER | FK→P26 | N | Veículo real representativo |

### P30 — `P30_ControlParam` (catálogo de parâmetros do painel)

Origem: Control Panel, colunas F:Q, X:AD e AW:AY. 205 parâmetros.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDCP` | TEXT | PK | S | Código do parâmetro, como `X23` |
| `Cell` | TEXT | — | S | Célula do valor no Control Panel |
| `Section` | TEXT | — | S | Seção (`UPP`, `PET`, `LMP`, `FEF`, `MEF`, `AUC`, `LWP`) |
| `Level` | TEXT | — | S | `B` (Basic), `E` (Expert) ou `X` (Expanded) |
| `DsCP` | TEXT | — | S | Nome |
| `utCP` | TEXT | — | N | Unidade |
| `IsCalculated` | INTEGER | — | S | 1 quando a planilha calcula o valor |
| `DefaultValue` | REAL | — | N | Valor do Expert no arquivo de referência |
| `DefaultText` | TEXT | — | N | Valor textual, para parâmetros de escolha |
| `BasicValue` | REAL | — | N | Valor próprio do bloco Basic, quando existe |
| `BasicCell` | TEXT | — | N | Célula do valor Basic |
| `MinValue` | REAL | — | N | Mínimo da faixa usual |
| `MostFrequent` | REAL | — | N | Valor mais frequente |
| `MaxValue` | REAL | — | N | Máximo da faixa usual |
| `Distribution` | TEXT | — | N | Distribuição de probabilidade |
| `StdDev` | REAL | — | N | Desvio padrão |
| `Reference` | TEXT | — | N | Fonte bibliográfica |
| `UsedByModule` | TEXT | — | N | Módulo que consome o parâmetro: `M1M2`, `M3`, `M4`, `M5`, `M6` ou `UI` |

`DefaultValue` e `DefaultText` não são preenchidos ao mesmo tempo. O banco não exige `MinValue ≤ MaxValue`, porque a planilha tem três parâmetros com a faixa invertida; o passo 3 os registra como estão e o relatório de divergências os lista.

### P49 — `P49_DefaultRuleVersion` (versões das regras de valor padrão)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDDRV` | TEXT | PK | S | Versão: `TAB` (regra como tabulada em M257:AW299) ou `FML` (regra como as fórmulas da planilha a aplicam) |
| `DsDRV` | TEXT | — | S | Descrição |
| `IsDefault` | INTEGER | — | S | 1 para a versão que o aplicativo usa |
| `NotesDRV` | TEXT | — | N | Observações |

### P35 — `P35_VehicleParamDefaultRule` (regras de valor padrão)

Origem: Market Vehicles M257:AW299. Parâmetros 4, 13, 15, 17, 18, 22, 26, 29 e 44.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDDRV` | TEXT | PK, FK→P49 | S | Versão da regra |
| `IDMP` | INTEGER | PK, FK→P54 | S | Parâmetro que recebe o valor padrão |
| `RuleSeq` | INTEGER | PK | S | Ordem de avaliação |
| `IDVPT` | TEXT | FK→P12 | N | Critério: motorização |
| `IDVDT` | TEXT | FK→P13 | N | Critério: carroceria |
| `IDVS` | TEXT | FK→P14 | N | Critério: porte |
| `IDLR` | TEXT | — | N | Critério: `Regular` ou `Luxury` |
| `PowerMinHP` | REAL | — | N | Critério: potência do motor a combustão maior ou igual, em hp |
| `PowerMaxHP` | REAL | — | N | Critério: potência menor que, em hp |
| `AreaMin` | REAL | — | N | Critério: área (comprimento × largura) maior ou igual, em m² |
| `AreaMax` | REAL | — | N | Critério: área menor que, em m² |
| `Value` | REAL | — | N | Valor atribuído, ou multiplicador quando `FactorOfIDMP` está preenchido |
| `ValueText` | TEXT | — | N | Valor textual atribuído (porte; fórmula da potência combinada) |
| `FactorOfIDMP` | INTEGER | FK→P54 | N | Parâmetro que `Value` multiplica (partida = 0,03 × potência do motor a combustão) |
| `SourceCell` | TEXT | — | N | Célula de origem |

**Como se lê.** Para um veículo e um parâmetro, vale a primeira regra, em ordem de `RuleSeq`, cujos critérios preenchidos são todos atendidos. Critério nulo não restringe. Exatamente um entre `Value` e `ValueText` é preenchido.

### P51 — `P51_OutputIndicator` (indicadores da tabela de saídas)

Origem: Control Panel BN7:BU56. 47 linhas, das quais 3 são títulos de bloco.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDInd` | TEXT | PK | S | Indicador: `O` mais a linha no Control Panel, como `O20` |
| `DsInd` | TEXT | — | S | Nome |
| `utInd` | TEXT | — | N | Unidade |
| `SourceModule` | TEXT | — | N | Módulo de origem na planilha |
| `PanelRow` | INTEGER | — | N | Linha no Control Panel |
| `IsHeader` | INTEGER | — | S | 1 para título de bloco |
| `ValueKind` | TEXT | — | S | `Num` ou `Text` |
| `FuelScenario` | TEXT | — | N | Combustível a que a linha se refere, quando é específica de um |
| `CalcStatus` | TEXT | — | S | `Calculated` quando o núcleo já calcula o indicador; `ExcelReference` enquanto o valor só existe na planilha |

`CalcStatus` muda de `ExcelReference` para `Calculated` à medida que os módulos são entregues. É essa coluna que decide o selo de origem.

### P52 — `P52_ExcelReferenceValue` (valores gravados no Excel)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDXR` | INTEGER | PK | S | Valor de referência |
| `RefSet` | TEXT | — | S | Conjunto: `CP_OUT_EC` (saídas da rodada equalizada gravada), `CP_OUT_FC` (saídas da livre escolha), `MV_AUX` (bloco auxiliar da Market Vehicles, B164:DC204) ou `M2_IN` (entradas que o M2, colunas ET:EY, usa nas seis configurações da rodada gravada) |
| `CaseKey` | TEXT | — | S | Caso, como `A01` ou `SV3` |
| `IDInd` | TEXT | FK→P51 | N | Indicador, nos conjuntos `CP_OUT_*` |
| `IDMP` | INTEGER | FK→P54 | N | Parâmetro, nos conjuntos `MV_AUX` e `M2_IN` |
| `Value` | REAL | — | N | Valor numérico |
| `ValueText` | TEXT | — | N | Valor textual |
| `Workbook` | TEXT | — | S | Arquivo, como `LCA_LV_i3ET_20261101.xlsx` |
| `Sheet` | TEXT | — | S | Guia |
| `Cell` | TEXT | — | S | Célula |

Exatamente um entre `IDInd` e `IDMP` é preenchido. A combinação (`RefSet`, `CaseKey`, indicador ou parâmetro) é única. É aqui que ficam as duas referências do BEV-A06: 83,6 kW em `CP_OUT_EC` e 79,6 kW em `MV_AUX`.

### P53 — `P53_CombinedPowerRule` (fatores de uso combinado, padrão por motorização)

A potência combinada (IDVP 15) é `FactorICE × P_ICE + FactorEE × P_EE`, com `P_ICE` a potência do motor a combustão (IDVP 2) e `P_EE` a do motor elétrico (IDVP 3).

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDVPT` | TEXT | PK, FK→P12 | S | Motorização |
| `FactorICE` | REAL | — | S | Fator de uso combinado do motor a combustão, de 0 a 1 |
| `FactorEE` | REAL | — | S | Fator de uso combinado do motor elétrico, de 0 a 1 |
| `IsProvisional` | INTEGER | — | S | 1 enquanto o valor for arbitrado até o fim da validação contra o Excel |
| `NotesCPR` | TEXT | — | N | Observação |

Seis linhas. ICEV vale (1; 0); BEV, SHEV e SPHEV, (0; 1); esses pares são fixos. HEV e PHEV valem (1; 1), a soma decidida em 16/11, provisório.

### P56 — `P56_CombinedPowerFit` (fatores arbitrados para igualar a planilha)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `CaseKey` | TEXT | PK | S | Configuração: `A01`…`A56` ou `SV1`…`SV4` |
| `IDVPT` | TEXT | FK→P12 | S | Motorização |
| `RefSet` | TEXT | — | S | Conjunto de `P52` de onde vieram as potências (`CP_OUT_*` quando a configuração está na rodada gravada; senão `MV_AUX`) |
| `PowerICE` | REAL | — | S | Potência do motor a combustão gravada, kW |
| `PowerEE` | REAL | — | S | Potência do motor elétrico gravada, kW |
| `PowerCombined` | REAL | — | S | Potência combinada gravada, kW |
| `FactorICE` | REAL | — | S | Fator arbitrado, de 0 a 1 |
| `FactorEE` | REAL | — | S | Fator arbitrado, de 0 a 1 |
| `FitKind` | TEXT | — | S | `Fixed` (ICEV, BEV, SHEV, SPHEV), `Sum` (1; 1), `ICE` (1; 0), `EE` (0; 1), `Tie` (motores iguais e combinada igual a eles: (1; 0), ambíguo) ou `NoFit` |
| `IsProvisional` | INTEGER | — | S | 0 para `Fixed`; 1 para os demais |
| `NotesCPF` | TEXT | — | N | Observação, como a diferença entre `CP_OUT_*` e `MV_AUX` |

Quarenta linhas: as 36 configurações equalizadas e as 4 de livre escolha. É gerada por `tools/fit_combined_power.py`.

### P57 — `P57_MaterialEquivalence` (equivalência de materiais entre versões do GREET)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDMParent` | TEXT | PK, FK→P09 | S | Material que as versões antigas tratam como um só (alumínio forjado, IDM 4) |
| `IDMChild` | TEXT | PK, FK→P09 | S | Material em que as versões novas o dividem (4a chapa, 4b extrudado) |
| `Weight` | REAL | — | S | Peso do filho na média ponderada, maior que 0 e até 1. Os pesos de um pai somam 1 |
| `WeightSource` | TEXT | — | S | De onde veio o peso |
| `NotesME` | TEXT | — | N | Observação |

Duas linhas, do alumínio: chapa 0,6206 e extrudado 0,3794, média das 30 receitas da família GREET 2024 (provisório). É gerada por `tools/build_material_equivalence.py`. Quando a receita escolhida e a lista de fatores são de versões diferentes, `core/ef_equivalence.py` converte (regra I28): a receita nos tipos novos com lista no tipo único usa o fator do tipo único para os dois; a receita no tipo único com lista nos tipos novos usa a média ponderada. Pesos por receita equivalente ficam para quando houver receita com o tipo único (hoje nenhuma das 68 receitas da base usa o IDM 4).

### P58 — `P58_GenericBatteryModel` (modelos genéricos de bateria de tração)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDBMd` | TEXT | PK | S | Identificador do modelo no i3ET (`PB-HEV-indefinido`, `PB-PHEV-indefinido`, `PB-BEV-indefinido`) |
| `IDVPT` | TEXT | FK→P12 | S | Motorização do modelo |
| `SizingBasis` | TEXT | — | S | `Power` (massa por kW da potência elétrica) ou `Energy` (massa por kWh da energia da bateria) |
| `IDCPMass` | TEXT | FK→P30 | S | Parâmetro de controle com a massa por unidade (X72, X70, X67) |
| `IDCPCarbon` | TEXT | FK→P30 | S | Parâmetro de controle com a intensidade de carbono em kg CO2e/kg (X88, X86, X83) |
| `SourceGBM` | TEXT | — | S | Origem na planilha |
| `NotesGBM` | TEXT | — | N | Observação |

Três linhas. O modelo não tem composição: a massa é o parâmetro vezes a potência ou a energia, e a pegada é a massa vezes a intensidade de carbono. Os valores ficam em `P30`/`D08`, editáveis. A rodada gravada usa `PB-HEV-indefinido` no HEV e no SHEV e `PB-BEV-indefinido` no PHEV, no SPHEV e no BEV. É gerada por `tools/build_generic_battery.py`.

### P59 — `P59_EquationConstant` (constantes de equação como parâmetros)

Bloco B0 da Fase B (18/11/2026). Todo fator é parâmetro: o que estava embutido no código passa a ser linha desta tabela.

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDEC` | TEXT | PK | S | Nome da constante (`STARTER_PER_KW`, `HP_PER_KW`) |
| `ValueEC` | REAL | — | S | Valor |
| `UnitEC` | TEXT | — | N | Unidade |
| `SourceEC` | TEXT | — | S | Origem na planilha |
| `NotesEC` | TEXT | — | N | Observação |
| `IsProvisional` | INTEGER | — | S | 1 se o valor ainda depende de validação |

Duas linhas, de `tools/build_equation_constants.py`. `STARTER_PER_KW` (0,03) é o fator do motor de partida: `IDVP 18` = fator × `IDVP 2`; o doc 01 trazia 0,04, a planilha grava 0,03 (divergência D15 em `05a`). `HP_PER_KW` (1,34102) converte kW em hp nas faixas de potência das regras de P35. `core/params.equation_constants` lê a tabela da base; sem base (testes de unidade), lê o mesmo CSV.

### P12 e P13 — `P12_Powertrain` e `P13_DesignType` (coluna nova)

| Coluna nova | Tipo | Obr. | Descrição |
|---|---|---|---|
| `IsCalculable` | INTEGER | S | 1 quando o núcleo calcula a motorização ou a carroceria. As linhas da 0.9.0 valem 1. MHEV, FCEV, Van e Chassis estão no catálogo de mercado e valem 0; a tela de veículos não as oferece |

---

## 4. Tabelas do usuário (D) e resultado (R) — bloco S6

### D06 — `D06_Analysis` (análise)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDA` | INTEGER | PK | S | Análise |
| `DsA` | TEXT | — | S | Nome |
| `Mode` | TEXT | — | S | `EC` (comparação equalizada) ou `FC` (comparação livre) |
| `AnalysisType` | TEXT | — | S | `GHG_LCA_LCC` (padrão), `SENSITIVITY`, `MONTE_CARLO` ou `LIGHTWEIGHTING` |
| `IDVC` | TEXT | FK→P29 | EC | Categoria |
| `IDMVRef` | INTEGER | FK→P26 | EC | ICEV de referência |
| `FuelScenario` | TEXT | — | S | Combustível da rodada |
| `TestNorm` | TEXT | — | S | `NBR`, `EPA`, `NEDC` ou `WLTC` |
| `DistanceCurve` | TEXT | — | S | Curva de distância diária |
| `IDEFV` | TEXT | — | S | Versão dos fatores de emissão (`P10` ou `D04`; sem chave estrangeira, como em `D02`) |
| `IDMPV` | INTEGER | FK→P05 | S | Versão dos parâmetros de massa |
| `IDAPV` | TEXT | FK→P23 | S | Versão dos parâmetros de montagem |
| `Boundary` | TEXT | — | S | `MAT` ou `MAT_ASM` (padrão) |
| `SPHEVEco` | INTEGER | — | S | 0 (padrão) ou 1 |
| `LightweightingOn` | INTEGER | — | S | 0 (padrão) ou 1 |
| `ParamProfile` | TEXT | — | S | `Basic`, `Expert` (padrão) ou `Expanded` |
| `CombinedPowerRule` | TEXT | — | S | `Default` (padrão: fatores de `P53`) ou `ExcelParity` (fatores de `P56` onde existirem) |
| `NotesIDA` | TEXT | — | N | Observações |
| `EoLMethod` | TEXT | — | S | Método de fim de vida (B1, T17): `GLIDER_BATTERY` (padrão), `AGGREGATE_VEHICLE` ou `EXCLUDED`. Coluna acrescentada na 0.11 |

O banco exige `IDVC` e `IDMVRef` preenchidos em `EC` e nulos em `FC`.

### D07 — `D07_AnalysisVehicle` (casos da análise)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDA` | INTEGER | PK, FK→D06 | S | Análise |
| `IDCase` | INTEGER | PK | S | Ordem do caso, de 1 a 7 |
| `CaseKey` | TEXT | única na análise | S | Rótulo estável: `A01`…`A56` em EC, `SV1`…`SV7` em FC |
| `CaseRole` | TEXT | — | S | `REF`, `EQ` ou `FC` |
| `IDVPT` | TEXT | FK→P12 | S | Motorização |
| `IDMV` | INTEGER | FK→P26 | N | Veículo de mercado de origem |
| `IDV` | INTEGER | FK→D02 | S | Veículo do projeto |
| `IDEA` | INTEGER | FK→D02 | S | Alternativa de avaliação do veículo |
| `FuelBlend` | TEXT | — | N | Combustível ou mistura do caso. Nulo herda `D06.FuelScenario` |
| `IDPBE` | TEXT | FK→P36 | N | Edição do PBEV usada |
| `SizingOrigin` | TEXT | — | S | `Manufacturer`, `ExcelReference`, `Calculated` ou `Pending` |
| `DeclaredMassKg` | REAL | — | N | Massa declarada do caso, kg (B1, T38). Nulo: sem declarada. Coluna da 0.11 |
| `MassAdjustmentKg` | REAL | — | S | Diferença de massa alocada a carroceria e chassi, kg com sinal; padrão 0. Coluna da 0.11 |
| `MassBodyShare` | REAL | — | N | Parcela `s` da diferença para a carroceria, 0 a 1. Nulo: `P63` da receita. Coluna da 0.11 |
| `DeclaredSource` | TEXT | — | N | Origem da massa declarada. Coluna da 0.11 |
| `MassCalibrationMode` | TEXT | `ON`, `OFF` | N | Calibração automática da massa: nulo = regra padrão (automática só para `SizingOrigin = Manufacturer`), `ON` liga, `OFF` desliga. Coluna da 0.11 (20/11/2026) |

(`IDV`, `IDEA`) é chave estrangeira composta para `D02`.

### D08 — `D08_ControlParamValue` (parâmetros alterados pelo usuário)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDA` | INTEGER | PK, FK→D06 | S | Análise |
| `IDCP` | TEXT | PK, FK→P30 | S | Parâmetro |
| `Profile` | TEXT | PK | S | Perfil a que a alteração pertence: `Basic`, `Expert` ou `Expanded` |
| `Value` | REAL | — | N | Valor numérico |
| `ValueText` | TEXT | — | N | Valor textual |
| `ValueSource` | TEXT | — | S | Origem do valor. Não pode ser vazia |
| `UpdatedAt` | TEXT | — | S | Data e hora da alteração |

Exatamente um entre `Value` e `ValueText` é preenchido. Só existe linha para o que difere da base.

**Perfis interligados (21/11/2026).** Basic, Expert e Expanded compartilham o valor alterado: `core.control_params.set_value` grava a mesma linha nos três perfis e `restore` apaga nos três (`restore_all` apaga todas as alterações da análise). Projetos antigos com valores diferentes por perfil não são migrados: a leitura continua usando o perfil da análise e a próxima edição de cada parâmetro os iguala.

### D12 — `D12_CombinedPowerOverride` (ajuste dos fatores por caso)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `IDA` | INTEGER | PK, FK→D07 | S | Análise |
| `IDCase` | INTEGER | PK, FK→D07 | S | Caso |
| `FactorICE` | REAL | — | S | Fator de uso combinado do motor a combustão, de 0 a 1 |
| `FactorEE` | REAL | — | S | Fator de uso combinado do motor elétrico, de 0 a 1 |
| `NotesCPO` | TEXT | — | N | Justificativa |

Só casos de HEV e PHEV aceitam ajuste (I22). A rodada congela os fatores efetivos de cada caso.

### D09 — `D09_Run` (rodada congelada)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `RunID` | TEXT | PK, FK→M01 | S | Execução |
| `IDA` | INTEGER | FK→D06 | S | Análise |
| `RunSeq` | INTEGER | única na análise | S | Número de ordem, a partir de 1 (`S1`, `S2`, …) |
| `FrozenAt` | TEXT | — | S | Data e hora do congelamento |
| `InputSnapshot` | TEXT | — | S | JSON canônico de tudo o que entrou no cálculo |
| `InputHash` | TEXT | — | S | SHA-256 de `InputSnapshot`, em 64 caracteres hexadecimais |
| `ParamBaseHash` | TEXT | — | S | Impressão digital da base |
| `ReferenceWorkbook` | TEXT | — | S | Arquivo de validação |
| `CalculatorVersion` | TEXT | — | S | Versão do programa |
| `Status` | TEXT | — | S | `Frozen` (padrão), `Calculated` ou `Failed` |
| `NotesRun` | TEXT | — | N | Observações |

**JSON canônico:** chaves em ordem alfabética, sem espaços, UTF-8, números com `repr` do Python. Conteúdo: a linha de `D06`; os casos de `D07`, cada um com os parâmetros do veículo (`D03`) e a receita; os valores efetivos dos parâmetros de `P30`; a fórmula efetiva da potência combinada por caso; e as versões.

### R45 — `R45_PowertrainSummary` (resultado da rodada)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `RunID` | TEXT | PK, FK→D09 | S | Rodada |
| `CaseKey` | TEXT | PK | S | Caso, como congelado na rodada |
| `IDVPT` | TEXT | FK→P12 | S | Motorização do caso |
| `IDInd` | TEXT | PK, FK→P51 | S | Indicador |
| `Value` | REAL | — | N | Valor numérico |
| `ValueText` | TEXT | — | N | Valor textual |
| `ValueOrigin` | TEXT | — | S | Selo de origem: `Calculated`, `ExcelReference` ou `Preview` |

Os dois valores nulos significam que o indicador não está disponível para o caso.

### R46 — `R46_RunComparison` (visão)

Junta `R45`, `D09` e `P51`. Colunas: `IDA`, `RunSeq`, `RunID`, `FrozenAt`, `InputHash`, `ParamBaseHash`, `CaseKey`, `IDVPT`, `IDInd`, `DsInd`, `utInd`, `Value`, `ValueText`, `ValueOrigin`. É a fonte da T06.

**Exportação em JSON** (`core/run_export.py`, `format` = `i3et-export`, `format_version` = 1). `kind` = `run`: `project` (linha de `M03`), `run` (linha de `D09` sem o `InputSnapshot`), `inputs` (o `InputSnapshot`), `results` (linhas de `R45` com `DsInd`, `utInd` e `Seal`) e `omitted_previews`. `kind` = `project`: `project`, `param_base_hash`, `configuration` (`D06`, `D07`, `D08`, `D12`), `vehicles` (`D01` a `D03`) e `runs`. Os dois levam `ExportHash`, o SHA-256 do JSON canônico sem esse campo. Linhas com `ValueOrigin` = `Preview` nunca são exportadas.

---

## 5. Metadados do projeto (M) — bloco S7

### M03 — `M03_Project` (identidade do projeto)

| Coluna | Tipo | Chave | Obr. | Descrição |
|---|---|---|---|---|
| `ProjectID` | TEXT | PK | S | `PRJ-` mais oito caracteres. O alfabeto exclui `0`, `O`, `1` e `I`, que se confundem |
| `ProjectName` | TEXT | — | S | Nome dado pelo usuário |
| `Domain` | TEXT | — | S | `LV` |
| `OwnerLabel` | TEXT | — | N | Rótulo de quem criou. Não é credencial |
| `CreatedAt` | TEXT | — | S | Data e hora ISO 8601 |
| `CopiedFromProjectID` | TEXT | — | N | Projeto de origem, quando criado por *Save as* |
| `SchemaVersion` | TEXT | — | S | Versão do esquema (`0.10`) |
| `IsExample` | INTEGER | — | S | 1 para projeto de exemplo, aberto em leitura |

A tabela tem no máximo uma linha, garantida por índice único. A base de referência não tem linha: ela não é um projeto.

---

## 6. Regras de integridade novas

Continuação do Documento 2, §8. As que dependem de mais de uma linha são verificadas em código (`core/validate.py`, no passo 4). As demais já estão no banco.

| Regra | Enunciado | Onde |
|---|---|---|
| I16 | Análise `EC` tem exatamente seis casos, um por motorização, e o primeiro é `REF` | código |
| I17 | Análise `FC` tem de um a sete casos, todos com `CaseRole = FC` | código |
| I18 | `D06.IDEFV` resolve para exatamente uma versão, de `P10` ou de `D04` | código |
| I19 | As versões de `D02` de cada caso (`IDEFV`, `IDMPV`, `IDAPV`, `Boundary`) são as de `D06` | código |
| I20 | Não há linha de `D08` para parâmetro com `P30.IsCalculated = 1` | código |
| I21 | `D06.IDMVRef` é um ICEV do grupo de mercado da categoria, ou o SELEÇÃO dela | código |
| I22 | `D12` só tem linha de caso HEV ou PHEV; ICEV, BEV, FCEV, SHEV e SPHEV têm par fixo | código |
| I23 | `R45.ValueOrigin = Calculated` só para indicador com `P51.CalcStatus = Calculated` | código |
| I24 | Rodadas com o mesmo `InputHash` e o mesmo `ParamBaseHash` têm `R45` igual | teste |
| I25 | `D06`: categoria e referência preenchidas em `EC`, nulas em `FC` | banco |
| I26 | `M03` tem no máximo uma linha, e o `ProjectID` segue o formato | banco |
| I27 | `D08.ValueSource` não é vazio | banco |
| I28 | Se a receita e a lista de fatores são de versões do GREET que dividem o material de forma diferente (`P57`), o fator é adaptado e o aviso é registrado; nunca bloqueia | código |

---

## 7. Migração de um arquivo da 0.9.0

`schema.migrate(conn, project_name=...)`, bloco S8.

1. Confere que o arquivo tem o esquema da 0.9.0. Se não tiver, recusa e não altera nada.
2. Cria as tabelas, os índices e a visão dos blocos S5, S6 e S7 que ainda não existem.
3. Acrescenta `IsCalculable` a `P12_Powertrain` e a `P13_DesignType`, com 1 em todas as linhas.
4. Se recebeu o nome do projeto e `M03` está vazia, cria a linha de identidade com um `ProjectID` novo.
5. Devolve a lista do que fez.

Propriedades, todas testadas:

- **Sem perda.** Nenhuma linha das tabelas `P01` a `P25` e `D01` a `D05` muda.
- **Sem efeito no cálculo.** O núcleo dá os mesmos resultados antes e depois, para os doze veículos da base.
- **Repetível.** A segunda chamada não faz nada e não troca o `ProjectID`.
- **Mesmo destino.** Um arquivo migrado e um banco criado do zero têm as mesmas colunas.

As tabelas de parâmetros novas chegam vazias a um projeto migrado.

### 7.1 Parâmetros da Fase A num projeto antigo — `schema.sync_fase_a()`, bloco S10

Copia da base de referência para o projeto as tabelas de parâmetros da Fase A e as linhas acrescentadas a `P10`, `P11`, `P12`, `P13`, `P15` e `P16` (estas duas, as 56 receitas do GREET 2022 a 2024, desde 17/11). Só acrescenta: nenhuma linha que o projeto já tinha muda, e por isso nenhum resultado existente muda. O `ParamBaseHash` do projeto continua sendo o da base de que ele nasceu; o da base de onde vieram os parâmetros da Fase A fica em `M00_BaseInfo`, na chave `FaseABaseHash`. Pode ser repetida.

### 7.2 Impressão digital — `schema.param_base_hash()`, bloco S9

SHA-256 do conteúdo de todas as tabelas de parâmetros, as da 0.9.0 e as da Fase A, com as linhas na ordem da chave primária. Duas bases com o mesmo conteúdo têm o mesmo hash, qualquer que tenha sido a ordem de carga.

## 8. Verificação

A verificação do passo 2 (107 testes), a do passo 3 (148) e as dos passos 4 e 5 (225 testes, com a base carregada) estão em `docs/08-fase-a-fixtures.md`, §6.
