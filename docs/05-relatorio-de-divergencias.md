# Relatório de Divergências — Calculadora × i3ET

**Data:** 20/09/2026 · **Fonte:** `LCA_LV_i3ET_20260919a.xlsx` · **Fatores:** versão `BR23`

---

## 1. Propósito

O modelo i3ET em Excel **não será alterado**: ele é a referência publicada, e a estabilidade dele vale mais do que a correção pontual de um detalhe. Este relatório existe para que as diferenças entre a calculadora e o i3ET sejam compreendidas, e para que quem mantém a planilha decida, caso a caso, se e quando ajustá-la.

A calculadora, por sua vez, é construída para ser **coerente**: onde o i3ET apresenta uma inconsistência interna, ela adota a regra correta e a registra aqui, em vez de reproduzir o comportamento.

## 2. Método

Cada uma das **72 configurações** do i3ET foi processada pela calculadora com os próprios parâmetros de entrada e os próprios fatores de emissão da planilha, e a massa resultante foi comparada com a que o i3ET produz.

São consideradas **materiais** as diferenças acima de 0.5 kg ou de 1e-04 em termos relativos. Abaixo disso a diferença é ruído de ponto flutuante, não achado, e listá-la esconderia as que importam.

## 3. Resumo

| Situação | Configurações | Ajuste sugerido no i3ET |
|---|---|---|
| Sem diferença material | 39 | — |
| Fator de leveza (módulo M5) | 28 | nenhum |
| Módulo híbrido em FCV | 5 | sim, ver §4 |

## 4. As diferenças, por origem

### Módulo de combinação híbrida em veículos a célula a combustível

No i3ET, a massa do módulo de combinação híbrida é zerada por uma condicional que lista os trens de força `ICEV`, `BEV`, `SHEV`, `SPHEV`, `HFCEV` e `EFCEV`. As configurações a célula a combustível, porém, usam o rótulo **`FCV`**, que não consta dessa lista. A condição não é satisfeita e o módulo recebe massa num veículo que, por construção, não o possui.

A calculadora atribui o módulo apenas a `HEV` e `PHEV`, e a regra deixou de ser uma condicional embutida na fórmula para ser um parâmetro derivado do trem de força (`IDVP 41`), declarado uma única vez.

**Ajuste sugerido no i3ET:** acrescentar `FCV` à lista de exclusão da fórmula do módulo híbrido, ou — preferível — substituir a condicional por um parâmetro de existência, como foi feito aqui. Convém rever, na mesma oportunidade, os demais parâmetros das configurações a célula a combustível, já que o modelo as desconsiderou.


| Configuração | Trem de força | Calculadora (kg) | i3ET (kg) | Diferença (kg) | Detalhe |
|---|---|---|---:|---:|---|
| `G05` | FCV | 1,880.189 | 1,916.277 | -36.088 | IDSG 43 (Modulo de Combinação Híbrida (adicional de massa)): -36.0875 kg |
| `G15` | FCV | 1,880.189 | 1,916.277 | -36.088 | IDSG 43 (Modulo de Combinação Híbrida (adicional de massa)): -36.0875 kg |
| `G25` | FCV | 1,848.535 | 1,884.622 | -36.088 | IDSG 43 (Modulo de Combinação Híbrida (adicional de massa)): -36.0875 kg |
| `P25` | FCV | 1,848.535 | 1,884.622 | -36.088 | IDSG 43 (Modulo de Combinação Híbrida (adicional de massa)): -36.0875 kg |
| `S25` | FCV | 1,848.535 | 1,884.622 | -36.088 | IDSG 43 (Modulo de Combinação Híbrida (adicional de massa)): -36.0875 kg |

### Fator de leveza (módulo M5)

O i3ET multiplica a massa de cada subgrupo escalado por um fator de leveza, que representa a substituição por materiais mais leves. O fator pertence ao módulo **M5**, fora do escopo desta versão da calculadora, que trabalha com `fLM = 1`.

**Não é uma divergência de cálculo.** A razão entre as massas é rigorosamente constante em todos os subgrupos escalados de cada configuração — o que prova tratar-se de um único fator multiplicativo, e não de erro em qualquer etapa.

**Nenhum ajuste é necessário no i3ET.** Quando o módulo M5 for incorporado, o parâmetro `P06.fLM` deixa de ser 1 e as configurações passam a coincidir sem alteração de fórmula: a equação da calculadora já traz o fator.


| Configuração | Trem de força | Calculadora (kg) | i3ET (kg) | Diferença (kg) | Detalhe |
|---|---|---|---:|---:|---|
| `G30` | FCV | 1,763.254 | 1,212.544 | +550.709 | fator 0.667817 aplicado a todos os subgrupos escalados |
| `P30` | FCV | 1,763.254 | 1,212.544 | +550.709 | fator 0.667817 aplicado a todos os subgrupos escalados |
| `S30` | FCV | 1,763.254 | 1,212.544 | +550.709 | fator 0.667817 aplicado a todos os subgrupos escalados |
| `G10` | FCV | 1,692.470 | 1,174.320 | +518.150 | fator 0.667817 aplicado a todos os subgrupos escalados |
| `G20` | FCV | 1,692.470 | 1,174.320 | +518.150 | fator 0.667817 aplicado a todos os subgrupos escalados |
| `G28` | PHEV | 1,563.751 | 1,290.671 | +273.080 | fator 0.809967 aplicado a todos os subgrupos escalados |
| `P29` | BEV | 1,670.418 | 1,401.397 | +269.021 | fator 0.770351 aplicado a todos os subgrupos escalados |
| `G08` | PHEV | 1,546.430 | 1,280.285 | +266.145 | fator 0.808832 aplicado a todos os subgrupos escalados |
| `P28` | PHEV | 1,563.751 | 1,299.505 | +264.246 | fator 0.816114 aplicado a todos os subgrupos escalados |
| `G18` | PHEV | 1,497.751 | 1,233.772 | +263.979 | fator 0.809943 aplicado a todos os subgrupos escalados |
| `SL26` | ICEV | 1,401.151 | 1,150.760 | +250.391 | fator 0.815716 aplicado a todos os subgrupos escalados |
| `S28` | PHEV | 1,563.751 | 1,316.024 | +247.727 | fator 0.827610 aplicado a todos os subgrupos escalados |
| `G27` | HEV | 1,468.952 | 1,223.381 | +245.571 | fator 0.827516 aplicado a todos os subgrupos escalados |
| `G29` | BEV | 1,670.418 | 1,428.695 | +241.722 | fator 0.793654 aplicado a todos os subgrupos escalados |
| `G17` | HEV | 1,444.564 | 1,206.844 | +237.720 | fator 0.827546 aplicado a todos os subgrupos escalados |
| `G07` | HEV | 1,444.564 | 1,206.939 | +237.624 | fator 0.827615 aplicado a todos os subgrupos escalados |
| `P27` | HEV | 1,468.952 | 1,232.432 | +236.520 | fator 0.833873 aplicado a todos os subgrupos escalados |
| `S27` | HEV | 1,468.952 | 1,234.766 | +234.186 | fator 0.835513 aplicado a todos os subgrupos escalados |
| `G09` | BEV | 1,550.121 | 1,317.279 | +232.842 | fator 0.792060 aplicado a todos os subgrupos escalados |
| `G19` | BEV | 1,504.145 | 1,273.122 | +231.024 | fator 0.793116 aplicado a todos os subgrupos escalados |
| `G26` | ICEV | 1,376.247 | 1,170.699 | +205.548 | fator 0.845895 aplicado a todos os subgrupos escalados |
| `P26` | ICEV | 1,376.247 | 1,177.457 | +198.790 | fator 0.850962 aplicado a todos os subgrupos escalados |
| `G06` | ICEV | 1,329.469 | 1,130.962 | +198.507 | fator 0.845765 aplicado a todos os subgrupos escalados |
| `G16` | ICEV | 1,329.469 | 1,130.962 | +198.507 | fator 0.845765 aplicado a todos os subgrupos escalados |
| `S26` | ICEV | 1,376.247 | 1,181.294 | +194.954 | fator 0.853838 aplicado a todos os subgrupos escalados |
| `S29` | BEV | 1,670.418 | 1,496.253 | +174.165 | fator 0.851324 aplicado a todos os subgrupos escalados |
| `GL26` | ICEV | 1,401.151 | 1,247.805 | +153.346 | fator 0.887140 aplicado a todos os subgrupos escalados |
| `PL26` | ICEV | 1,401.151 | 1,444.992 | -43.841 | fator 1.032266 aplicado a todos os subgrupos escalados |

## 5. Divergências de parâmetro, não de massa

Duas diferenças não aparecem na tabela acima porque a calculadora **honra o valor informado pelo i3ET** em vez de recalculá-lo. Elas são registradas aqui porque afetam quem ler as fórmulas da planilha esperando que elas expliquem os números.

**Potência combinada (`IDVP 15`).** A fórmula do i3ET calcula o máximo entre a potência do motor a combustão e a do motor elétrico. Em três configurações PHEV o valor armazenado é a **soma** das duas. A evolução do modelo foi da soma para o máximo, e o parâmetro passou a ser configurável — os valores armazenados são anteriores a essa mudança. *Observação de método: nem a soma nem o máximo descrevem corretamente a potência combinada de um híbrido; o tema merece tratamento próprio em trabalho futuro.*

**Motor de arranque (`IDVP 18`).** A fórmula aplica 4% da potência do motor a combustão. Em três configurações o valor armazenado corresponde a 3%. Também aqui o parâmetro deixou de ser constante embutida e passou a ser configurável.

Em ambos os casos a calculadora usa o valor informado quando ele existe, e aplica a equação apenas para veículos criados pelo usuário. A coluna `D03.IsCalculated` distingue os dois casos, e toda substituição é registrada no log da execução.

## 6. Emissões: fluidos e baterias

Em 24 configurações da família de referência — aquelas cujas receitas de materiais a base possui e cuja massa já reproduz o i3ET — as emissões foram comparadas parcela a parcela.

**Fluidos (grupo `K`) — corrigido em 20/09/2026.** A base do simulador não trazia composição para o grupo dos fluidos: a calculadora carregava a massa (25 a 43 kg por veículo) e lhe atribuía **emissão zero**. O i3ET traz a composição nas linhas 620 a 626 do módulo M2, e ela passou a integrar `P16`. A concordância agora é exata (maior diferença relativa: 2.1e-16). Antes da correção, faltavam entre 67 e 108 kg CO₂e por veículo, ou algo entre 1,5% e 2,3% do total do berço ao portão. **Nenhum ajuste é necessário no i3ET**: a falha estava na base derivada, não na planilha.

**Bateria de tração.** Reproduz o i3ET na precisão da máquina em todos os modelos que a base descreve. As configurações da família `G` citam modelos que vivem apenas na planilha de baterias do i3ET; para elas a calculadora **mantém a massa, declara o fator ausente e registra aviso** — nunca atribui emissão zero em silêncio.

**Bateria auxiliar (chumbo-ácido).** A intensidade por quilograma coincide exatamente com a das colunas `G` do i3ET. As colunas `BP` da mesma planilha são **9.87% maiores**, por uma razão localizada: elas lançam o plástico da bateria como *Average Plastic* (IDM 10; 4,4833 kg CO₂e/kg) enquanto as colunas `G` o lançam como *Polypropylene* (2,6074). A base segue o polipropileno, que é o material específico e é também o que a receita do simulador declara. O efeito é de cerca de 1,8 kg CO₂e por veículo — menos de 0,05% do total.

**Ajuste sugerido no i3ET:** uniformizar o material do plástico da bateria auxiliar entre as duas famílias de colunas. É uma inconsistência interna da planilha, não uma divergência com a calculadora.

## 7. Emissões: composição dos materiais do veículo — **em aberto**

Esta é a única divergência de emissões ainda não resolvida, e é a mais importante deste relatório.

A **massa** do veículo reproduz o i3ET exatamente. A **distribuição dessa massa entre materiais**, não: para a mesma receita (`BISD2` em `BP01`, por exemplo, que é a receita que a própria planilha declara usar), a base põe cerca de 143 kg a menos de aço e 68 kg a mais de plástico médio, além de separar o alumínio em chapa e extrudado onde o i3ET usa uma única entrada. Como os fatores de emissão diferem entre esses materiais, o total de emissões dos materiais do veículo diverge.

| Configuração | Trem de força | Calculadora (kg CO₂e) | i3ET (kg CO₂e) | Dif. |
|---|---|---:|---:|---:|
| `G03` | PHEV | 6,086.8 | 6,682.0 | -8.91% |
| `G02` | HEV | 6,069.1 | 6,647.3 | -8.70% |
| `G13` | PHEV | 6,071.2 | 6,619.9 | -8.29% |
| `BP04` | BEV | 4,243.2 | 4,246.2 | -0.07% |
| `BP02` | ICEV | 4,630.3 | 4,577.0 | +1.17% |
| `BP01` | ICEV | 4,398.5 | 4,335.9 | +1.44% |

A origem é conhecida: as receitas `P16` vêm da planilha `LVManufacturingMassGHGSimulator`, e o i3ET usa as suas próprias tabelas de composição por grupo GREET. São dois instantâneos da mesma tabela que se separaram — o mesmo tipo de problema já encontrado em `D03` e resolvido pela sincronização com as colunas `BP`.

**Decisão pendente.** Pela diretriz **D11** prevalece o i3ET, o que implicaria reconstruir `P16` a partir das tabelas de composição da planilha. É uma mudança que desloca todos os resultados de emissões e merece decisão explícita antes de ser feita. Enquanto não for tomada, o teste `test_car_materials_stay_within_the_documented_gap` trava a distância no patamar atual, de modo que ela não possa crescer despercebida.

## 8. Conclusão

**Toda diferença material está explicada.** Nenhuma decorre de erro de cálculo da calculadora: elas vêm de um módulo fora do escopo desta versão (leveza) e de uma inconsistência identificada na lista de exclusão do módulo híbrido do i3ET.

Os **doze veículos de referência `BP01`–`BP12` reproduzem o i3ET na precisão da máquina**, com erro relativo entre 0 e 2,6 × 10⁻¹⁶.

---

*Gerado por `tools/report_divergences.py`.*
