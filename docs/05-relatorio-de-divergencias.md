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

Em 12 configurações da família de referência — aquelas cujas receitas de materiais a base possui e cuja massa já reproduz o i3ET — as emissões foram comparadas parcela a parcela.

**Fluidos (grupo `K`) — corrigido em 20/09/2026.** A base do simulador não trazia composição para o grupo dos fluidos: a calculadora carregava a massa (25 a 43 kg por veículo) e lhe atribuía **emissão zero**. O i3ET traz a composição nas linhas 620 a 626 do módulo M2, e ela passou a integrar `P16`. A concordância agora é exata (maior diferença relativa: 2.1e-16). Antes da correção, faltavam entre 67 e 108 kg CO₂e por veículo, ou algo entre 1,5% e 2,3% do total do berço ao portão. **Nenhum ajuste é necessário no i3ET**: a falha estava na base derivada, não na planilha.

**Bateria de tração.** Reproduz o i3ET na precisão da máquina em todos os modelos que a base descreve. As configurações da família `G` citam modelos que vivem apenas na planilha de baterias do i3ET; para elas a calculadora **mantém a massa, declara o fator ausente e registra aviso** — nunca atribui emissão zero em silêncio.

**Bateria auxiliar (chumbo-ácido).** Reproduz o i3ET exatamente, nas duas famílias de configurações. Até 20/09/2026 havia aqui uma diferença fixa de 9,87% nas colunas `BP`, atribuída a uma inconsistência interna da planilha: elas lançam o plástico da bateria como *Average Plastic* e as colunas `G` como *Polypropylene*. Não era inconsistência — eram duas receitas diferentes, e a base passou a ter as duas (§7).

## 7. Emissões: composição dos materiais do veículo — **resolvido**

Este foi o item em aberto de 20/09/2026, e está fechado. A massa do veículo já reproduzia o i3ET; a distribuição dessa massa entre materiais não. A investigação mostrou que não era deriva entre cópias de uma mesma tabela, e sim **duas receitas distintas**.

### 7.1 Duas famílias de receitas, e não duas versões

O i3ET guarda as receitas em colunas nomeadas do próprio módulo M2 (bloco `T8:DD281`), e a linha 9 de cada configuração nomeia a que ela usa. Há duas famílias:

| Família | Origem |
|---|---|
| `<PT>-BISD<n>` | receita original, de consultoria |
| `<PT>-PBP_BISD<n>` | receita do Projeto do Berço ao Portão, que partiu da anterior e ajustou a participação de alguns materiais com informação das montadoras brasileiras |

No grupo A, por exemplo:

| Grupo A (carroceria) | `ICEV-BISD2` | `ICEV-PBP_BISD2` |
|---|---:|---:|
| Aço | 0,652777058 | 0,802318776 |
| Plástico médio | 0,216746989 | 0,110750895 |
| Cobre/latão | 0,018986306 | 0,000000000 |
| Alumínio forjado | 0,030699147 | 0,006139829 |

A base trazia apenas a primeira, e os veículos do projeto usavam-na — daí uma diferença de 126,8 kg de aço em `BP01`, 90,4 no grupo A e 36,4 no grupo B, com a massa total inalterada. **As duas famílias passam a existir na base**, com a procedência declarada em `P15.DsVMR`, e cada cenário usa a receita que a planilha nomeia na sua coluna. Deduzir pelo trem de força não serviria: há mais de uma receita por trem de força, e `BP02` usa uma variante própria, `ICEV-PBP_BISD2s`, que o nome do veículo não revela. Por isso a *fixture* de validação passou a registrar o nome da receita de cada configuração.

### 7.2 Participações que a base trazia como zero

A importação também restaurou 36 participações não nulas que a base arredondara para zero — entre 2 × 10⁻⁵ e 4 × 10⁻⁴: platina no grupo D, níquel, náilon, resina fenólica, mica, zinco e óxido de zinco nos grupos C e G.

Uma delas não é pequena no resultado: **a platina** do catalisador. Com o fator da versão BR23, de 69.670 kg CO₂e/kg, a participação de 2 × 10⁻⁵ vale 265 kg CO₂e em `BP01` e 152 kg em `BP07` — de 3% a 6% do veículo, vindos de um número arredondado para zero. É o caso exemplar do princípio da diretriz **D13**: numa tabela de fatores com cinco ordens de grandeza de amplitude, não existe participação desprezível a priori.

*Discrepância conhecida e mantida:* a platina tem fator **126,5** kg CO₂e/kg nas versões G22, G23 e G24 e **69.670** na BR23 — 550 vezes maior. A diferença decide alguns pontos percentuais do resultado de qualquer veículo com catalisador. **Decisão de 20/09/2026: manter como está**, por ser discrepância já conhecida na tabela de fatores. A calculadora usa o fator da versão que o cenário escolher, e a escolha fica visível no resultado.

### 7.3 Onde isso deixou a aderência

| Configuração | Receita | Calculadora (kg CO₂e) | i3ET (kg CO₂e) | Dif. relativa |
|---|---|---:|---:|---:|
| `BP01` | `PBP_BISD2` | 4,335.866 | 4,335.866 | -4.2e-16 |
| `BP02` | `PBP_BISD2s` | 4,576.990 | 4,576.990 | -2.0e-16 |
| `BP03` | `PBP_BISD3` | 4,957.472 | 4,957.472 | +0.0e+00 |
| `BP04` | `PBP_BISD12` | 4,246.159 | 4,246.159 | -2.1e-16 |
| `BP05` | `PBP_BISD12` | 7,987.797 | 7,987.797 | +1.1e-16 |
| `BP06` | `PBP_BISD12` | 5,275.162 | 5,275.162 | -1.7e-16 |
| `BP07` | `PBP_BISD6` | 5,002.423 | 5,002.354 | +1.4e-05 |
| `BP08` | `PBP_BISD6` | 5,783.730 | 5,783.652 | +1.3e-05 |
| `BP09` | `PBP_BISD6` | 5,758.226 | 5,758.144 | +1.4e-05 |
| `BP10` | `PBP_BISD8` | 5,652.015 | 5,651.853 | +2.9e-05 |
| `BP11` | `PBP_BISD8` | 7,739.735 | 7,739.489 | +3.2e-05 |
| `BP12` | `PBP_BISD8` | 7,410.679 | 7,410.485 | +2.6e-05 |

Os `ICEV` e os `BEV` reproduzem o i3ET na precisão da máquina. O resíduo de 3 × 10⁻⁵ dos híbridos vem de uma decisão declarada: algumas colunas do i3ET fecham a soma do grupo com um resíduo **negativo** na linha `Others`, da ordem de 1 × 10⁻⁴. Participação mássica negativa não existe; essas oito linhas entram como zero e a normalização redistribui a diferença.

**Decisão de 20/09/2026: normalizar.** Uma participação negativa num vetor de frações mássicas é um artifício de planilha que não sobrevive à passagem para um modelo relacional — o invariante I1 existe justamente para impedir que ele passe despercebido. As oito linhas entram como zero, a normalização redistribui, e o resíduo de 3 × 10⁻⁵ nos híbridos é o preço declarado dessa decisão.

## 8. Conclusão

**Toda diferença material está explicada.** Nenhuma decorre de erro de cálculo da calculadora: elas vêm de um módulo fora do escopo desta versão (leveza) e de uma inconsistência identificada na lista de exclusão do módulo híbrido do i3ET.

Os **doze veículos de referência `BP01`–`BP12` reproduzem o i3ET em massa na precisão da máquina**, com erro relativo entre 0 e 2,6 × 10⁻¹⁶.

Em **emissões**, os mesmos doze veículos também reproduzem o i3ET: a maior diferença relativa é de 3e-05, e vem de uma decisão declarada — a normalização das participações negativas (§7.3). Fluidos, bateria de tração e bateria auxiliar coincidem exatamente.

---

*Gerado por `tools/report_divergences.py`.*
