# Fase A — fixtures
## Passo 3 do método: os dados extraídos do i3ET

17/11/2026 · versão h · Fonte: `LCA_LV_i3ET_20261101.xlsx` · Destino: `data/base_referencia.sqlite`

Este documento diz de onde veio cada tabela de parâmetros da Fase A, como refazê-la e o que a extração revelou. As colunas estão no dicionário (`docs/07`); as regras de uso, na especificação (`docs/06`).

Versão g (17/11, passo 5): `P58` (bateria paramétrica) e as entradas do M2 (`P52`, conjunto `M2_IN`) entram na base; a paridade do núcleo com a rodada gravada fecha em 0,2% na massa e 0,1% no GEE (§4, item 14). Novos roteiros: `tools/build_generic_battery.py` e `tools/extract_m2_inputs.py`.

Versão de 17/11 (potência combinada): `P53` passa a ser o par de fatores padrão por motorização, e `P56` (nova, 40 linhas) guarda os fatores arbitrados para igualar a planilha, gerada por `tools/fit_combined_power.py`, que roda depois de `extract_control_panel.py` e `import_market_vehicles.py` e antes de `load_fase_a.py`.

Versão de 17/11 (alumínio): `G22` corrigido em `P11` e `P57` (nova, 2 linhas) criada por `tools/build_material_equivalence.py`, que roda depois de `import_recipes.py`. Os totais dos doze veículos de referência mudaram (§4, item 13).

Versão de 17/11 (receitas e licença): todas as 56 receitas do bloco T:CA do M2 (GREET 2022, 2023 e 2024, com Fuel Cell) estão na base (§4, item 12); a licença de `BR23` e `GLO23` foi esclarecida (§4, item 1).

Versão de 17/11: importadas as 30 receitas da família GREET 2024 (§3, §4 item 12, §5 item 1); o passo 3 deixa de ter complemento pendente. A primeira conta com elas mostrou o que falta para a paridade (§5, item 9).

Versão c: registra três respostas do autor de 16/11 — GWP das listas `BR23` e `GLO23` confirmado, descrições de `P12` mantidas, receita de materiais escolhida pelo usuário (§4, itens 1 e 8; §7).

Versão b: corrige o item 1 do §5 (as receitas da rodada gravada são uma terceira família, ausente da base, e não nomes diferentes das que a base tem) e leva as constatações ao anexo do relatório de divergências.

Situação: **passo 3 concluído; passo 5 (paridade) fechado em 17/11.** A base de referência foi reconstruída e tem novo `ParamBaseHash`. Os totais dos doze veículos da base mudaram só por causa do alumínio de `G22` (§4, item 13).

---

## 1. Como refazer

Com a planilha em `Model/`, na raiz do repositório:

```
python tools/extract_control_panel.py
python tools/extract_m2_inputs.py
python tools/import_market_vehicles.py
python tools/import_pbev.py
python tools/build_default_rules.py
python tools/import_ef_versions.py
python tools/build_static_tables.py
python tools/import_recipes.py
python tools/fit_combined_power.py
python tools/build_material_equivalence.py
python tools/build_generic_battery.py
python tools/load_fase_a.py
python tools/freeze_regression.py
python -m pytest -q
```

Os nove primeiros gravam CSV em `data/csv/fase_a/`. O décimo migra a base, carrega os CSV, regrava o dicionário em dados e recalcula o hash. Todos aceitam o caminho da planilha (ou da base) como argumento. Podem ser repetidos: o resultado é o mesmo.

`tools/load_fase_a.py` roda **depois** de `tools/make_db.py`, que continua montando `P01` a `P25` a partir do Documento 3.

## 2. Scripts e blocos

| Arquivo | Blocos | Gera |
|---|---|---|
| `tools/xlsx_cells.py` | XL1 textos compartilhados · XL2 guia → arquivo · XL3 grade da guia · XL4 colunas e endereços | Leitor de uma guia por vez, com a marca de fórmula de cada célula |
| `tools/fase_a_common.py` | FA1 planilha de referência · FA2 escrita dos CSV · FA3 normalização de rótulos | Apoio comum |
| `tools/extract_control_panel.py` | CP1 parâmetros · CP2 categorias · CP3 indicadores e saídas · CP4 gravação | `P30`, `P29`, `P51`, parte de `P52` |
| `tools/import_market_vehicles.py` | MV1 catálogo de parâmetros · MV2 veículos · MV3 valores e classe · MV4 bloco auxiliar · MV5 gravação | `P54`, `P26`, `P27`, parte de `P52` |
| `tools/import_pbev.py` | PB1 edição · PB2 registros e campos · PB3 vínculos · PB4 gravação | `P36`, `P28`, `P55`, `P50` |
| `tools/build_default_rules.py` | DR1 colunas → critérios · DR2 células → regras · DR3 porte pela área · DR4 gravação | `P49`, `P35` |
| `tools/import_ef_versions.py` | EF1 conferência · EF2 versões · EF3 fatores · EF4 gravação | linhas novas de `P10` e `P11` |
| `tools/build_static_tables.py` | ST1 motorizações · ST2 carrocerias · ST3 fatores de uso combinado · ST4 gravação | linhas de `P12` e `P13`; `P53` |
| `tools/import_recipes.py` | RC1 leiaute do bloco · RC2 colunas da família · RC3 participações, normalização e fluidos · RC4 conferência · RC5 gravação | linhas novas de `P15` e `P16` |
| `tools/build_material_equivalence.py` | ME1 fatores de `G22` · ME2 pesos · ME3 gravação | correção de `P11` (`G22`); `P57` |
| `tools/load_fase_a.py` | LD1 migração · LD2 acréscimos · LD3 tabelas novas · LD4 dicionário em dados · LD5 verificação e hash | a base |
| `core/schema.py` | S9 impressão digital · S10 parâmetros da Fase A num projeto antigo | — |

O leitor da planilha existe porque o arquivo tem 198 guias e mais de 80 MB: abrir tudo para ler uma guia custa minutos. Ele lê só o XML da guia pedida e traz o valor que o Excel gravou na última vez em que calculou.

## 3. O que a base passou a conter

| Tabela | Linhas | Origem na planilha |
|---|---:|---|
| `P54_MarketParam` | 58 | Market Vehicles N4:BS6 |
| `P26_MarketVehicle` | 154 | Market Vehicles, linhas 7–161 (a 113 é separador) |
| `P27_MarketVehicleParam` | 8.324 | Market Vehicles N7:BS161 |
| `P36_PBEVEdition` | 1 | — (`PBEV2026`) |
| `P28_PBEVRecord` | 843 | PBEV - INMETRO - 2026, B22:AD864 |
| `P55_PBEVRecordValue` | 15.593 | idem, 25 campos por registro |
| `P50_MarketVehiclePBEV` | 350 | cruzamento por marca e modelo |
| `P29_VehicleCategory` | 6 | Control Panel X12:Z17 e AM7:AR8 |
| `P30_ControlParam` | 205 | Control Panel, blocos Expert, Expanded e Basic |
| `P49_DefaultRuleVersion` | 2 | — |
| `P35_VehicleParamDefaultRule` | 91 | Market Vehicles M257:AW299 |
| `P51_OutputIndicator` | 47 | Control Panel BN9:BV55 |
| `P52_ExcelReferenceValue` | 2.492 | Control Panel BF9:BU55 (378) e Market Vehicles B165:DC204 (2.114) |
| `P53_CombinedPowerRule` | 6 | decisão de 17/11: fator de uso combinado padrão por motorização |
| `P56_CombinedPowerFit` | 40 | `tools/fit_combined_power.py`, a partir de `P52` (BP10:BU12, BF10:BI12 e o bloco auxiliar) |
| `P57_MaterialEquivalence` | 2 | `tools/build_material_equivalence.py`: alumínio único = chapa + extrudado; pesos das 30 receitas da família GREET 2024 |
| `P10_EFVersion` | +7 | Emission Factors GREET and BR, AH:AN |
| `P11_EmissionFactor` | +728 e 3 corrigidas | idem, 104 materiais por versão; as 3 são o alumínio de `G22` (§4, item 13) |
| `P15_VehicleMaterialRecipe` | +56 | M2 GHG Mfg Module, bloco de receitas, colunas T:AC (GREET 2022), AF:AO (2023) e AR:CA (2024) |
| `P16_MaterialShare` | +6.888 | idem, linhas 83–281, e massas de fluidos nas linhas 620–626 |
| `P12_Powertrain` | +2 e 6 descrições | Market Vehicles (MHEV, FCEV) |
| `P13_DesignType` | +2 | Market Vehicles (Van, Chassis) |
| `P01_DataDictionary` | +187 | colunas das tabelas da 0.10, com a descrição de `docs/07` |

`IDMV` e `IDPBR` são o número da linha na planilha. Isso torna cada registro rastreável sem tabela de correspondência.

**Conferência com os levantamentos anteriores.** Os números batem com os de 10 e 11/11: 154 veículos e seis SELEÇÃO; 843 registros do PBEV, 92 veículos com registro e 64 com mais de um; 205 parâmetros (12 Basic, 108 Expert, 85 Expanded; 66 calculados); 47 linhas de saída. Os 205 parâmetros foram comparados um a um com a extração de 11/11 (valor, faixa, nível, seção, distribuição e referência): iguais.

## 4. Decisões tomadas na extração

1. **Sete listas de fatores, não duas.** A planilha tem `GLO23`, `BR23` e mais cinco variantes de `BR23` (`BR23_100%`, `BR23_ICEV_SUV`, `BR23_HEV`, `BR23_PHEV`, `BR23_BEV`). Entraram todas, porque a rodada gravada pode usar a variante da motorização. O `%` saiu do identificador: `BR23_100`. O conjunto de GWP, `AR6-100`, igual ao das demais listas, foi confirmado pelo autor em 16/11. Licença esclarecida pelo autor em 17/11: as listas foram publicadas com o relatório *Pegada de Carbono do Berço ao Portão* e disponibilizadas à AEA e ao governo federal, sem restrição de uso declarada e com a ressalva de como foram calculadas; o autor participou da elaboração e as usa conforme as recomendações do relatório. `P10.LicenseEFV` registra isso.
2. **Classe do valor em `P27`.** Vem da marca de fórmula da célula: digitado é `Man`; fórmula num parâmetro com regra de valor padrão é `Def`; fórmula de cálculo é `Calc`; busca no PBEV é `PBEV`; no SELEÇÃO, média é `Avg` e o resto é `Rep`. A planilha não distingue estimativa de engenharia de dado do fabricante: a classe `Eng` ficou sem uso.
3. **Regras de valor padrão.** Cada célula preenchida da matriz virou uma regra. A matriz não declara precedência; adotei luxo, motorização, carroceria, faixa de potência, porte, carroceria × porte, que é a ordem que reproduz as descrições do autor para o ar-condicionado e a instrumentação. A versão `FML` não tem linhas: o que as fórmulas gravaram está em `P27`, classe `Def`.
4. **Campos do PBEV.** O cabeçalho da guia ocupa quatro linhas com células mescladas. Os 25 nomes de campo (`Km_l_Etanol_Cidade`, `ConsumoEnergetico_MJ_km`, …) estão em `tools/import_pbev.py`. A marca `\\` (não se aplica) não é gravada; `ND` é gravado como texto.
5. **Módulo de cada parâmetro (`UsedByModule`).** Atribuído pela seção do painel: UPP, LMP e FEF → M4; PET → M3; MEF → M1–M2; AUC → M6; LWP → M5; as três escolhas da análise (combustível, curva, ciclo) → `UI`. É uma primeira atribuição, a refinar quando o núcleo de cada módulo passar a ler os parâmetros.
6. **Indicadores já calculados.** `P51.CalcStatus` vale `Calculated` nas 14 linhas cuja origem na planilha é o M2 (parâmetros do veículo, massa, receita e GEE de fabricação) e `ExcelReference` nas demais.
7. **Catálogo sem cálculo.** MHEV, FCEV, Van e Chassis entraram em `P12` e `P13` com `IsCalculable = 0`, para que os 29 veículos de mercado que os usam caibam no catálogo. A tela de veículos da 0.9.0 passou a filtrar por essa coluna.
8. **Descrições de `P12`.** As seis motorizações tinham um marcador provisório. As descrições novas são redação desta etapa. O autor decidiu mantê-las (16/11).
9. **`ParamBaseHash`.** Passou a cobrir também as tabelas da Fase A, com as linhas na ordem da chave primária. O valor mudou de `ccba9488…` para `26971e5d…` no passo 3, para `310f285d…` com as receitas e para `63217eeb…` com os fatores de uso combinado (`P53` e `P56`, 17/11) e para `163fb8cc…` com o alumínio (`P11` corrigida e `P57`, 17/11), para `c6fe7580…` com as receitas de 2022, 2023 e as de Fuel Cell para `53ab7aa7…` com o texto de licença das listas `BR23` e `GLO23`, para `f7d0e15b…` com `P58` e para `dc2b90bc…` com as entradas do M2 (`P52`, conjunto `M2_IN`, 17/11). O arquivo de regressão foi recongelado em cada passo; no último os totais mudaram (item 13).
10. **Projeto antigo.** `schema.sync_fase_a()` leva os parâmetros da Fase A a um projeto migrado da 0.9.0, só acrescentando linhas.
11. **Arquivo da 0.9.0 nos testes.** `tests/fixtures/base_090.sqlite` é a base como publicada na 0.9.0. É contra ela que a migração é testada.
12. **Receitas das famílias GREET 2022, 2023 e 2024 (todas as do bloco T:CA).** Por decisão do autor, entram todas as receitas do M2 cuja coluna define a própria receita, usadas ou não e incluindo Fuel Cell (`FCV-*`, motorização `FCEV`, que a base não calcula): 10 de 2022 (T:AC), 10 de 2023 (AF:AO) e 36 de 2024 (AR:CA), 56 ao todo. A edição vem do rótulo da linha 7. Nas de FCEV, como nas demais, o grupo `Iprinc` não é importado, porque a bateria de tração vem de `P20`; o conjunto de pilha e tanque, se houver, ficará para quando a base calcular FCEV. Os pesos de `P57` continuam sendo os das 30 receitas do GREET 2024 que a base calcula. O método é o da primeira importação, de 30 colunas do bloco `GREET 2024` (ICEV, HEV, PHEV e BEV, as que a base calcula), descrita a seguir: séries `G` (carro de passeio), `S` (SUV) e `P` (picape), nas numerações 21–24 e 26–29, mais as seis variantes `L` do ICEV. O identificador é o nome da planilha (`ICEV-G21`), que é o que o bloco auxiliar cita. A série dá a carroceria em `P15` (`S` → SUV, `P` → PUT; a série `G` fica sem carroceria, porque serve a sedã e a hatch). As participações são normalizadas por grupo, como em setembro; 28 participações negativas (16 nas receitas de 2024 e 12 nas de 2022 e 2023), resíduo de fechamento da linha *Others*, entraram como zero. Os fluidos (grupo K) vêm das massas de cada fluido na própria coluna. **Conferência do método:** aplicado às receitas que a base já tinha, reproduz as 584 participações comparadas, sem divergência. A variante `L` é *Large*: receita para veículos grandes (esclarecido pelo autor em 17/11). As numerações 26 a 30 são as versões mais leves, com mais fibra de carbono, fibra de vidro e alumínio no lugar de aço (esclarecido pelo autor em 17/11): colunas AW:BA (série G, `ICEV-G26` a `FCV-G30`, mais `ICEV-GL26` em BC), BI:BM (série S) e BU:BY (série P); todas já estão na base, inclusive as de Fuel Cell (`FCV-G30`, `FCV-S30`, `FCV-P30`).
13. **Alumínio de `G22` e equivalência entre versões (17/11, divergência D2).** O i3ET tem na lista `G22` um só alumínio (IDM 4, 15,7407) e `ND` para chapa e extrudado (4a, 4b); a 0.9.0 trazia em `G22` os valores do G23 (11,94; 11,94; 4,77). `G22` foi corrigido. `P57` guarda a equivalência, com os pesos 0,6206 (chapa) e 0,3794 (extrudado), média das 30 receitas da família GREET 2024, e `core/ef_equivalence.py` aplica o critério do autor: receita nova com lista antiga usa o fator único nos dois tipos; receita antiga com lista nova usa a média ponderada; os dois casos geram o aviso I28. Os doze veículos de referência usam `G22` com receitas `BISD` (só chapa): o GEE do berço ao portão subiu de 1,2% (BP05) a 3,5% (BP03) e a massa não mudou. O i3ET, nesse caso, aloca zero aos dois tipos (divergência D10).
14. **Bateria de tração paramétrica e referência da rodada gravada (17/11, passo 5).** O i3ET tem três modelos `PB-HEV-indefinido`, `PB-PHEV-indefinido` e `PB-BEV-indefinido` (guia `GREET Batteries Material List`, colunas ID:IF) sem composição: a massa é um parâmetro do Control Panel vezes a potência elétrica (HEV) ou a energia da bateria (PHEV, BEV), e a pegada é a massa vezes a intensidade de carbono (X66:Z72 e X83:Z89). `P58_GenericBatteryModel` guarda o vínculo; os valores ficam em `P30`/`D08`. A tabela de saídas da rodada gravada (Control Panel BP:BU, que lê o M2 ET:EY) usa `PB-HEV-indefinido` no HEV e no SHEV e `PB-BEV-indefinido` no PHEV, no SPHEV e no BEV; o bloco auxiliar (`MV_AUX`) guarda outro estado, com modelos `G24-*` e outro dimensionamento. `analysis.create_ec` toma o dimensionamento e a bateria da tabela de saídas. `ParamBaseHash` passou para `f7d0e15b…`; a regressão dos doze veículos só mudou no hash.
    **Entradas do M2 e módulo de combinação híbrida (17/11).** O M2 (ET:EY) usa valores diferentes do bloco auxiliar em ar-condicionado (14.000 contra 20.000 no ICEV), motor de partida, fator de utilidades e área de vidros. `tools/extract_m2_inputs.py` grava as 228 entradas em `P52` (`M2_IN`), e `analysis._recorded_params` as aplica entre `MV_AUX` e `CP_OUT_EC`. Além disso, `D03` passou a gravar `IDVP 41` (existência do módulo de combinação híbrida) como 1 em HEV e PHEV; antes ficava 0 e o subgrupo `IDSG 43` (26,6 kg no HEV, 47,7 kg no PHEV) sumia. Resultado contra o Control Panel: potência combinada e energia da bateria exatas; massa dentro de 0,2% (A06 exata) e pegada do berço ao portão dentro de 0,1%. Resíduo no ICEV (1,5 kg): fator do motor de partida do M2. Os testes de paridade passaram a tolerar 0,3% na massa e 0,2% na pegada.

## 5. Constatações para o relatório de divergências

Levadas ao anexo `docs/05a-divergencias-fase-a.md`, junto com as dos levantamentos de 10 e 11/11.

1. **Receitas da rodada gravada.** As 40 configurações do bloco auxiliar usam receitas com o nome da configuração do GREET: `ICEV-G21`, `HEV-G22`, `PHEV-G23`, `BEV-G24`, e as séries `S`, `P`, `GL` e `PL`. No M2 da planilha, a linha 9 de cada configuração nomeia a receita, e essas colunas trazem a própria composição. A base tem só as duas famílias importadas em setembro, `BISD*` (consultoria) e `PBP_BISD*` (Projeto do Berço ao Portão). Não estavam na base. **Importadas em 17/11** (§4, item 12).
2. **Alumínio na lista `G22`.** Em três materiais (IDM 4, 4a e 4b) a base difere da planilha: a planilha traz 15,74 para o alumínio forjado e `ND` para chapa e extrudado; a base traz 11,94, 11,94 e 4,77. Os outros 309 fatores de `G22`, `G23` e `G24` são iguais. Resolvido em 17/11, com o critério de equivalência entre versões (§4, item 13; divergências D2, D10 e D11 do anexo `05a`).
3. **Categoria e porte do SELEÇÃO.** O nome da categoria e o porte do veículo SELEÇÃO não coincidem em três casos: A0 "Hatch Compact" tem SELEÇÃO `Subcompact`; A2 "Sedan Midsize" tem `Compact`; A3 "SUV Large" tem `Midsize`. `P29` guarda o porte do veículo.
4. **BEV-A06.** Confirmado: 83,6 kW na tabela de saídas e 79,6 kW no bloco auxiliar. As duas estão em `P52`.
5. **Faixas.** Três parâmetros têm mínimo maior que máximo, e dois digitáveis (`X64`, `X65`) têm valor zero abaixo do mínimo. Gravados como estão.
6. **Rótulos.** `Hatch` e `Extralarge` na planilha, `Hatchback` e `ExtraLarge` na base (normalizados na extração). `Electricity` e `Eletricidade` convivem na coluna de combustível.
7. **Fatores ausentes.** Cada lista nova tem 5 materiais sem fator (`ND`), gravados como ausentes, não como zero.
8. **Rótulo com erro na planilha.** A célula AX17 do bloco Basic mostra `#REF!`.
9. **Primeira conta com as receitas novas.** Com os parâmetros do bloco auxiliar, a receita nomeada e a lista `BR23`, o núcleo dá para o ICEV da rodada gravada (A01) 1.087,25 kg e 4.527,4 kg CO₂e, contra 1.083,03 kg e 4.513,84 kg CO₂e gravados: 0,4% e 0,3% de diferença. (Superado pelo item 14: com as entradas do M2, a bateria paramétrica e o módulo de combinação híbrida, as seis motorizações fecham.) Para as outras cinco motorizações a conta ainda não fecha, por duas razões já identificadas: (a) a planilha usa modelos de bateria do GREET 2024 (`G24-HEV-Ni-MH`, `G24-PHEV50-NMC111`, `G24-BEV300-NMC111`) que não estão em `P19` e `P20`, de modo que a bateria de tração entra com massa zero; (b) a lista de fatores que a planilha aplica a cada motorização (`BR23` ou a variante `BR23_HEV`, `BR23_PHEV`, `BR23_BEV`) precisa ser confirmada na leitura do M2. O resíduo do ICEV pede a comparação dos parâmetros de massa de `P06` com o M1 da planilha de 01/11.

## 6. Verificação

| Verificação | Resultado |
|---|---|
| Suíte completa (`python -m pytest -q`) | 225 de 225 passam |
| — testes da 0.9.0, incluindo as telas | 108 |
| — esquema e migração (passo 2) | 20 |
| — fixtures (passo 3) | 25 |
| — potência combinada (passo 4, `tests/test_power_rule.py`) | 7 |
| — equivalência de materiais (passo 4, `tests/test_ef_equivalence.py`) | 13 |
| — valores padrão, projeto, análise e rodada, parâmetros de controle e selo (passo 4) | 5 + 8 + 8 |
| — bateria paramétrica e paridade da rodada gravada (passo 5, `tests/test_generic_battery.py`) | 17 |
| — matriz de paridade: livre escolha com 7 casos, caso `Pending`, fatores (1; 1), FCEV, mesma entrada (passo 5, `tests/test_paridade_matriz.py`) | 5 |
| — exportação em JSON e `R46` (passo 6, `tests/test_run_export.py`) | 8 |
| Validação contra o i3ET (`tools/validate_core.py`) | aprovado, 0 divergências sem explicação |
| Regressão dos doze veículos | massa idêntica à da 0.9.0; GEE do berço ao portão de 1,2% a 3,5% maior, por causa do alumínio de `G22` (§4, item 13), e recongelado |
| `integrity_check` e `foreign_key_check` na base | `ok` e 0 violações |
| Potência combinada com `ExcelParity` | reproduz as dez potências gravadas (BP12:BU12 e BF12:BI12) e as 40 de `P56` |
| Paridade da rodada gravada (BP20:BU20 e BP29:BU29) | massa e GEE de fabricação das seis motorizações dentro de 0,2% (A06 exata); potência combinada e energia da bateria exatas |
| Carga repetida | mesmo hash |
| Estilo (`ruff`) | sem apontamentos |

## 7. O que fica para os passos seguintes

1. **Feito no passo 5 (17/11):** a paridade das seis motorizações da rodada gravada (item 14 do §4); a comparação de `P06` com o M1, que achou o módulo de combinação híbrida (`IDVP 41`) e as entradas do M2; a receita como escolha do usuário, com `SHEV` e `SPHEV` usando as do HEV e do PHEV. A importação dos modelos `G24-*` para `P19` e `P20` deixou de ser condição, porque a tabela de saídas da rodada usa os modelos paramétricos (`P58`); ela volta quando houver uma referência que os use.
2. **Pendências da paridade:** o resíduo de 1,5 kg no ICEV (fator do motor de partida do M2, que o núcleo ainda calcula com 0,04 fixo) e a escolha final dos fatores de HEV e PHEV (A2 do anexo `05a`), depois da validação. `HP_PER_KW` (1,34102) ainda está no código e passa para uma tabela de parâmetros na próxima reconstrução da base.
3. **Passo 6 (saídas e exportação): feito em 17/11** (`core/run_export.py`). **Passo 7 (telas):** T01 a T11 e T41, navegação, glossário e a frase-resumo da T03, que a matriz de §9 do doc. 6 compara com o título do Control Panel; `tools/build_review_data.py` mantém `model-data.js` igual à base.
4. **Decidido pelo autor em 17/11:** FENABRAVE citada como fonte, com as quantidades importadas (a participação se calcula quando for preciso); licença de `BR23` e `GLO23` esclarecida; D11 aceito. Numerações 26 a 30 = versões mais leves (AW:BA, BI:BM, BU:BY), confirmado.

## 8. Nota de ambiente

O SQLite não conseguiu gravar direto em `data/` a partir do ambiente desta sessão, que não permite apagar arquivos: ele cria e apaga um arquivo de diário a cada transação. A base foi montada numa pasta temporária e copiada por cima. Sobrou um diário vazio, movido para `_to_delete/` na raiz do repositório. Pode ser apagado; o Git já o ignora. No Windows, fora desta sessão, `tools/load_fase_a.py` grava direto, sem esse cuidado.
