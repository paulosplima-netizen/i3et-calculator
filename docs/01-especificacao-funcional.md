# Especificação Funcional e Metodológica
## Calculadora da Pegada de Carbono de Veículos Leves — do Berço ao Portão

**Documento 1 de 4** · Versão `20260919a` · Projeto NIPE/UNICAMP

---

## Sumário

1. [Diretrizes do Projeto](#1-diretrizes-do-projeto)
2. [Objetivo e uso pretendido](#2-objetivo-e-uso-pretendido)
3. [Escopo e fronteiras do sistema](#3-escopo-e-fronteiras-do-sistema)
4. [Glossário e convenções de nomenclatura](#4-glossário-e-convenções-de-nomenclatura)
5. [Visão geral do encadeamento de cálculo](#5-visão-geral-do-encadeamento-de-cálculo)
6. [Classificação dos parâmetros](#6-classificação-dos-parâmetros)
7. [Etapa 1 — Parâmetros do veículo (GC)](#7-etapa-1--parâmetros-do-veículo-gc)
8. [Etapa 2 — Estimativa de massa por subgrupo](#8-etapa-2--estimativa-de-massa-por-subgrupo)
9. [Etapa 3 — Agregação de massa por grupo GREET](#9-etapa-3--agregação-de-massa-por-grupo-greet)
10. [Etapa 4 — Massa por material](#10-etapa-4--massa-por-material)
11. [Etapa 5 — Bateria de tração](#11-etapa-5--bateria-de-tração)
12. [Etapa 6 — Emissões de GEE dos materiais](#12-etapa-6--emissões-de-gee-dos-materiais)
13. [Etapa 7 — Montagem do veículo](#13-etapa-7--montagem-do-veículo)
14. [Etapa 8 — Totalizações](#14-etapa-8--totalizações)
15. [Reconciliação com o modelo i3ET](#15-reconciliação-com-o-modelo-i3et)
16. [Divergências encontradas na documentação inicial](#16-divergências-encontradas-na-documentação-inicial)
17. [Critérios de validação e aceitação](#17-critérios-de-validação-e-aceitação)
18. [Referências](#18-referências)

---

## 1. Diretrizes do Projeto

Este capítulo registra, em forma revisada e normativa, as instruções que originaram o projeto. Ele é a fonte de autoridade sobre *o que* deve ser construído; os demais capítulos tratam de *como*.

**D1 — Objeto.** Construir uma calculadora da pegada de carbono de um veículo leve, na perspectiva da Avaliação de Ciclo de Vida (ACV) do berço ao portão da montadora, reproduzindo o que hoje é feito pelos módulos **M1 Mass Module** e **M2 GHG Mfg Module** da planilha `LCA_LV_i3ET`, cujos insumos e resultados são hoje operados pela aba `i3ET Control Panel`.

**D2 — Recorte.** O i3ET realiza análise do berço ao túmulo. Este exercício restringe-se às etapas do berço ao portão da montadora. Os módulos M3 a M6 (energia, uso, leveza, TCO/LCC) estão fora desta etapa e serão incorporados modularmente em trabalhos futuros.

**D3 — Finalidade da documentação.** Documentar de forma didática e transparente a construção e o funcionamento da calculadora, de modo que ela sirva como material didático e de formulação de políticas públicas.
**Critério de suficiência:** a documentação gerada deve ser necessária e suficiente para recriar o programa sem nenhum auxílio adicional.

**D4 — Dados.** Parâmetros exógenos, parâmetros endógenos e resultados são armazenados em tabelas com integridade relacional declarada e verificável, exportáveis em CSV e XLSX.

**D5 — Programa.** A calculadora é programada em Python e acessível pela internet.

**D6 — Padrão de nomes de documentos.** Todo documento termina com o padrão `_AAAAMMDD` + letra de versão do dia, onde `a` designa a primeira versão gerada no dia, `b` a segunda, e assim por diante. Exemplo: `_20260919a`.

**D6.1 — Alcance do padrão.** O sufixo datado aplica-se aos **documentos entregues**, que ficam na raiz do diretório compartilhado e constituem o instantâneo citável de cada marco. **Não** se aplica ao conteúdo do repositório: ali os arquivos têm nomes estáveis (`core/mass.py`, `docs/01-especificacao-funcional.md`) e o histórico é responsabilidade do Git, que registra cada alteração linha a linha, com autoria e data — precisão que o sufixo não alcança. Um `core/mass_20260920a.py` quebraria os imports a cada revisão; um documento renomeado quebraria os links internos. As duas convenções convivem: o Git versiona o trabalho, o sufixo datado marca as entregas.

**D7 — Repositório de trabalho.** O diretório `_Calculadora da Pegada de Carbono do Berço ao Portão` é simultaneamente a fonte e o destino do trabalho. Nele residem o simulador `LCA_LV_i3ET` e os documentos iniciais, e nele são salvos os documentos revisados.

**D8 — Papel dos documentos iniciais.**

| Arquivo | Papel |
|---|---|
| `MassGHGSimulator_Instructions` | Descritivo textual do encadeamento de cálculo |
| `LVManufacturingMassGHGSimulator` | Dados e parâmetros iniciais, ainda sem parâmetros endógenos nem resultados |
| `Results_ALL_tables` | Exemplo do formato de saída; sua estrutura precisa ser revista e sua geração deve ser acionada por um botão no programa |
| `LCA_LV_i3ET` | Simulador completo de referência (berço ao túmulo) |

**D9 — Etapa atual.** Revisar a documentação inicialmente proposta e produzir quatro novos arquivos adequados à execução da programação.

**D10 — Evolução.** Uma vez estabilizados o ferramental e a documentação, avançar de forma modular até abranger todos os módulos do i3ET e, em seguida, evoluir para outros modelos. Recomendações de substituição das ferramentas em uso são parte esperada do trabalho.

**D11 — Precedência (regra de conflito).** Quando a documentação inicial e o comportamento do modelo `LCA_LV_i3ET` divergirem, **prevalece o modelo i3ET**. Toda divergência resolvida por esta regra é registrada no [Capítulo 16](#16-divergências-encontradas-na-documentação-inicial), com a redação original, o comportamento observado no i3ET e a regra adotada.

**D12 — Métrica.** As emissões são expressas em kg CO₂e, com fatores de aquecimento global de horizonte 100 anos (GWP-100) do **IPCC AR6**. A versão do conjunto de fatores usada em cada cálculo é sempre registrada junto ao resultado (índice `IDEFV`).

**D13 — Parametrização dos fatores de emissão.** **Todos** os fatores de emissão são parâmetros da base, nunca constantes no código — inclusive o fator de montagem. A base é preparada para receber, além das versões do GREET, os fatores obtidos e publicados pelo **Projeto do Berço ao Portão (FGV/Unicamp para a Fundep, Programa Move do Governo Federal)**.

**D14 — Decisões de ferramental (etapa atual).**

| Decisão | Escolha | Motivo |
|---|---|---|
| Linguagem | Python | Diretriz D5 |
| Hospedagem | Streamlit Community Cloud | O Netlify não executa Python: suas *Functions* rodam JavaScript/TypeScript e Go. O Streamlit publica diretamente de um repositório Git, é Python nativo e já oferece download de CSV/XLSX |
| Persistência | Arquivo de projeto SQLite | Integridade relacional real, sem contas nem servidor; o arquivo é o registro auditável da análise |
| Base de parâmetros | Imutável | O usuário cria cenários e veículos; as tabelas de parâmetros de referência são somente leitura, garantindo reprodutibilidade |
| Formato da documentação | Markdown + CSV | Versionável, difere linha a linha, converte para PDF e site |
| Idioma da documentação | Português | Público-alvo imediato |
| Idioma da interface | **Inglês** | Alcance internacional da ferramenta; nomes de tabelas e colunas já são em inglês |
| Repositório | GitHub público | Torna verificável a aderência ao i3ET |
| Cópia de trabalho | `repo/` no diretório compartilhado | Espelha o repositório; tudo que é gerado é salvo ali no momento em que é produzido |
| Formatos de exportação | XLSX, CSV, **HTML e PDF** | Planilha para conferência, CSV para reprocessamento, HTML para circular sem Excel, PDF para anexo de artigo e de relatório de política pública |

---

## 2. Objetivo e uso pretendido

A calculadora estima, para um veículo leve de passageiros, duas grandezas:

- **Massa do veículo**, decomposta em subgrupos, grupos e materiais (kg);
- **Emissões de gases de efeito estufa do berço ao portão da montadora** (kg CO₂e), decompostas por grupo e por material.

O uso pretendido é duplo:

- **Didático** — cada número apresentado deve poder ser rastreado até a equação, o parâmetro e a fonte que o produziram. A calculadora expõe a cadeia inteira, não apenas o total.
- **Formulação de políticas públicas** — a comparação entre trens de força (ICEV, HEV, PHEV, BEV, FCEV) e entre versões de fatores de emissão (GREET, Brasil) é o objeto de interesse. Por isso toda saída carrega, obrigatoriamente, a identificação das versões de parâmetros usadas.

A calculadora **não** é um substituto do i3ET: é a reimplementação auditável de dois de seus módulos, com a mesma base numérica.

---

## 3. Escopo e fronteiras do sistema

### 3.1 O que está dentro

A fronteira "berço ao portão da montadora" compreende:

1. **Produção dos materiais** que compõem o veículo, do berço (extração) até o portão do fornecedor — os fatores de emissão `EF` são dados em kg CO₂e/kg de material;
2. **Produção da bateria de tração** (quando houver) e da bateria auxiliar, incluindo a etapa de montagem da bateria;
3. **Produção dos fluidos** embarcados;
4. **Montagem do veículo na planta** — pintura, climatização e iluminação da planta, aquecimento, movimentação de materiais, soldagem e ar comprimido.

### 3.2 O que está fora

| Etapa | Situação |
|---|---|
| Uso do veículo (combustível, eletricidade) | Fora — módulos M3/M4 do i3ET |
| Reposições ao longo da vida (pneus, baterias, fluidos) | Fora — é etapa de uso |
| Descarte e reciclagem (DR) | Fora — é o "portão ao túmulo" |
| Transporte do veículo pronto até o cliente | Fora — não modelado no i3ET |
| Leveza (*lightweighting*) | Fora da v1 — ver §15.3 |
| Veículos a célula a combustível (`FCV`) | Fora da v1 — decisão de 20/09/2026 |

**Célula a combustível.** Os `FCV` têm massa no i3ET, mas nenhuma receita de
materiais: as famílias `BISD` e `PBP_BISD` não trazem coluna para esse trem de
força, e o grupo `H` (sistema auxiliar da célula) fica sem composição. Calcular
massa sem emissões seria oferecer meia resposta, então a v1 não os inclui. A
divergência do módulo híbrido em `FCV`, registrada no Documento 5, continua
valendo para quando forem incorporados.

### 3.3 Unidade funcional

**Um veículo produzido**, caracterizado por seu trem de força, tipo de carroceria, porte e conjunto de parâmetros de projeto. Resultados derivados em kg CO₂e/kg de veículo são apresentados como indicador secundário.

---

## 4. Glossário e convenções de nomenclatura

### 4.1 Convenção dos índices

Toda coluna cujo nome começa por `ID` é um índice. A tabela em que um índice é declarado **primário** (`IDprimary`) não admite repetição da combinação de seus índices primários; nas demais tabelas o mesmo índice aparece como **secundário** (`IDsecondary`) e pode repetir-se.

Os nomes de tabelas e de colunas permanecem **em inglês**, ainda que a documentação seja em português, para manter compatibilidade com o i3ET, com o GREET e com os artigos publicados.

### 4.2 Índices do modelo

| Índice | Significado | Tabela de origem |
|---|---|---|
| `IDV` | Veículo analisado | `D01` |
| `IDEA` | Alternativa de avaliação (cenário) | `D02` |
| `IDVP` | Parâmetro do veículo | `P07` |
| `IDSG` | Subgrupo do veículo (nível mais fino) | `P02` |
| `IDG` | Grupo genérico | `P03` |
| `IDGG` | Grupo GREET (nível de agregação usado no cálculo de GEE) | `P04` |
| `IDM` | Material | `P09` |
| `IDMPV` | Versão dos parâmetros de massa | `P05` |
| `IDVMR` | Receita de materiais do veículo | `P15` |
| `IDEFV` | Versão dos fatores de emissão | `P10` |
| `IDVPT` | Trem de força (*powertrain*) | `P12` |
| `IDVDT` | Tipo de carroceria (*design*) | `P13` |
| `IDVS` | Porte (*size*) | `P14` |
| `IDBTy` | Tipo de bateria | `P17` |
| `IDBTe` | Tecnologia de bateria | `P18` |
| `IDBMd` | Modelo de bateria | `P19` |
| `IDAP` | Processo de montagem | `P21` (novo) |
| `IDAPV` | Versão dos parâmetros de montagem | `P23` (novo) |

### 4.3 Grandezas

| Símbolo | Significado | Unidade |
|---|---|---|
| `GC` | Valor do parâmetro de um veículo (*General Characteristic*) | conforme `P07.utVP` |
| `Beta` | Expoente da lei de escala de massa | adimensional |
| `GCR` | Valor de referência do parâmetro | idem `GC` |
| `MR` | Massa de referência do subgrupo | kg |
| `ME` | Massa estimada do subgrupo | kg |
| `MassIDGG` | Massa do grupo GREET | kg |
| `MshareGG` | Fração mássica de um material dentro de um grupo | adimensional (0–1) |
| `BMshareGG` | Fração mássica de um material dentro de um grupo da bateria | adimensional (0–1) |
| `EF` | Fator de emissão do material | kg CO₂e/kg |
| `MassIDMpGG` | Massa de um material dentro de um grupo | kg |
| `GHGIDMpGG` | Emissão de um material dentro de um grupo | kg CO₂e |

### 4.4 Prefixos das tabelas

| Prefixo | Natureza | Escrita |
|---|---|---|
| `P` | Parâmetros de referência | Somente leitura para o usuário |
| `D` | Dados do cenário (veículos e suas escolhas) | Editável pelo usuário |
| `C` | Tabelas calculadas | Escritas pelo programa |
| `R` | Tabelas de relatório (exportação) | Escritas pelo programa |

---

## 5. Visão geral do encadeamento de cálculo

```
D01/D02  veículos e cenários
   │
   ├─► D03  parâmetros GC do veículo ──► (endógenos calculados por P07.GCEquation)
   │            │
   │            ▼
   │      P06  Beta, GCR, MR  ──►  C01  ME por subgrupo      ME = MR·(GC/GCR)^Beta
   │                                  │
   │                                  ▼
   │                            C02  MassIDGG por grupo GREET
   │                                  │
   │            P16 MshareGG ────────►│
   │                                  ▼
   │                            C03  MassIDMpGG (massa por material e grupo)
   │                                  │
   │            P11 EF ──────────────►│
   │                                  ▼
   │                            C04  GHGIDMpGG
   │
   ├─► P19/P20  bateria de tração
   │                            C06  MassIDMpGGB  ──►  C07  GHGIDMpGGB
   │
   ├─► P21..P23  montagem
   │                            C13  GHG da montagem
   │
   └────────────────────────────►  C10 (por grupo) ─► C11 (por material) ─► C12 (por veículo)
                                                                             │
                                                                             ▼
                                                                    C14  total berço-portão
```

Cada seta é uma junção relacional explícita; nenhuma etapa usa correspondência posicional.

---

## 6. Classificação dos parâmetros

A diretriz D4 exige distinguir parâmetros exógenos de endógenos. Adotamos três classes, registradas na coluna `ParamClass` do dicionário de dados (Documento 2):

| Classe | Definição | Quem preenche | Exemplos |
|---|---|---|---|
| **Exógeno** | Valor informado de fora do modelo: medição, literatura, escolha do analista | Base de referência ou usuário | `Beta`, `GCR`, `MR`, `EF`, `MshareGG`, potência do motor, comprimento do veículo |
| **Endógeno** | Valor calculado a partir de outros parâmetros, **antes** do cálculo de massa | Programa | `fA`, `fR`, `fB`, potência combinada, massa da bateria |
| **Resultado** | Saída do encadeamento de cálculo | Programa | `ME`, `MassIDGG`, `GHGIDM`, `GHGIDV` |

A fronteira entre endógeno e resultado é operacional: endógenos são insumos das equações de massa; resultados são produto delas. Um parâmetro endógeno nunca é digitado pelo usuário — se o usuário informar um valor para ele, o programa avisa e recalcula.

> **Regra de transparência.** Toda célula apresentada na interface exibe, sob demanda, sua classe, sua equação (se endógena ou resultado), seus insumos com os respectivos índices e sua referência bibliográfica.

---

## 7. Etapa 1 — Parâmetros do veículo (GC)

Cada veículo `IDV` é descrito por um conjunto de parâmetros `IDVP` listados em `P07`, cujos valores `GC` residem em `D03` com chave (`IDV`, `IDVP`).

### 7.1 Parâmetros exógenos

São informados pelo usuário ou herdados do veículo de referência. Exemplos: `IDVP 2` (potência do motor a combustão, kW), `IDVP 3` (potência do motor elétrico, kW), `IDVP 5` (capacidade da bateria de energia, kWh), `IDVP 7` (comprimento, m), `IDVP 8` (largura, m), `IDVP 27` (altura, m), `IDVP 6` (aro da roda, pol), `IDVP 11` (nº de airbags e cintos), `IDVP 12` (nº de assentos), `IDVP 14` (`fT`: 1,0 para tração 2WD e 1,2 para 4WD), `IDVP 17` (ar-condicionado, BTU), `IDVP 19` (tanque de combustível, L), `IDVP 22` (complexidade de instrumentação, 1 a 5), `IDVP 32` (`IDBMd`, modelo de bateria).

### 7.2 Parâmetros endógenos e suas equações

As equações abaixo são as **efetivamente aplicadas pelo i3ET** (aba `M2 GHG Mfg Module`, linhas 11 a 51) e substituem, por força da diretriz D11, a redação abreviada de `P07.GCEquation`.

| `IDVP` | Nome | Equação | Unidade |
|---|---|---|---|
| 9 | `fA` — área do veículo | `GC(9) = GC(7) × GC(8)` | m² |
| 15 | Combined Power | `GC(15) = GC(3)` se `IDVPT ∈ {SHEV, SPHEV}`; caso contrário `GC(15) = MAX(GC(2), GC(3))` | kW |
| 16 | `fR` — robustez | `GC(16) = GC(15) × GC(9) × GC(14) × GC(29)` | kW·m² |
| 18 | Electric Starter Engine | `GC(18) = 0,04 × GC(2)` | kW |
| 28 | `fB` — volume de carroceria | `GC(28) = GC(9) × GC(27)` | m³ |
| 30 | Combined Power with Hybrid Complexity | `GC(30) = GC(25) × GC(29)` | kW |
| 33 | Battery Power Density | `GC(33) = P19.PowerDensity(GC(32))`; `ND` se ausente | kg/kW |
| 34 | Battery Energy Density | `GC(34) = P19.EnergyDensity(GC(32))`; `ND` se ausente | kg/kWh |
| 35 | Battery Weight | ver §7.3 | kg |
| 36 | Battery Reference Energy Capacity | `GC(36) = P19.RefEnergy(GC(32))` | kWh |
| 37 | ICE Power / `fH` | `GC(37) = GC(2) / GC(29)` | kW |
| 42 | Hybrid Combination Parameter | `GC(42) = GC(41) × GC(15)` | kW |

`GC(29)` (`fH`, complexidade híbrida) é **exógeno por veículo** e reside em `D03`. No i3ET, a linha 39 do módulo M2 vale **1 em todas as 57 configurações**, e é esse o valor adotado: `fH = 1` para todos os veículos da base de referência. O parâmetro permanece na estrutura — a equação do i3ET continua sendo `GC(15) × GC(9) × GC(14) × GC(29)` — mas sem efeito sobre os resultados, e disponível para quem queira explorá-lo. Não é atributo do trem de força: dois veículos do mesmo trem de força podem ter complexidades diferentes.

`GC(4)` (bateria de serviço) também é exógeno por veículo: a base traz 0,72 kWh ou 0,96 kWh conforme o veículo, enquanto o i3ET usa a constante 0,864 kWh (12 V × 72 Ah). Prevalece o dado da base, por ser mais específico; a constante do i3ET fica como valor padrão para veículos novos.

`GC(25)` (massa do veículo) **é resultado**, não entrada: no i3ET a célula correspondente lê o total do módulo M1. Ele aparece em `P07` por herança da estrutura da planilha e é marcado como `Resultado` no dicionário de dados.

### 7.3 Massa da bateria de tração — `IDVP 35`

O i3ET aplica a regra em cascata:

```
se GC(33) = "ND":
    se GC(34) = "ND":  GC(35) = 0
    senão:             GC(35) = GC(34) × GC(5)        # densidade de energia × capacidade
senão:
    se GC(24) > 0:     GC(35) = GC(33) × GC(24)       # densidade de potência × potência da bateria
    senão:             GC(35) = GC(33) × GC(3)        # densidade de potência × potência do motor elétrico
```

A redação de `P07.GCEquation` (`GC(35) = GC(5) × GC(34)`) cobre apenas o segundo ramo e é insuficiente para híbridos com bateria de potência. Prevalece a regra acima (D11).

### 7.4 Regra de completude

Antes de qualquer cálculo, o programa verifica que `D03` contém um valor para cada par (`IDV`, `IDVP`) exigido pelo trem de força do veículo. Parâmetros não aplicáveis (ex.: `IDVP 20` e `21`, célula a combustível, em um ICEV) recebem `0` explicitamente — nunca vazio. A ausência de valor é erro de validação, não zero implícito.

---

## 8. Etapa 2 — Estimativa de massa por subgrupo

### 8.1 A lei de escala

A massa de cada subgrupo `IDSG` é estimada por uma lei de potência sobre um parâmetro dimensionador:

$$ME = MR \times \left(\frac{GC}{GCR}\right)^{\beta}$$

onde, para a versão de parâmetros `IDMPV` e o subgrupo `IDSG`, a tabela `P06` fornece:

- `MR` — massa do subgrupo no veículo de referência (kg);
- `GCR` — valor do parâmetro dimensionador no veículo de referência;
- `Beta` — elasticidade da massa em relação ao parâmetro.

O parâmetro dimensionador de cada subgrupo é definido por `P08`, que associa `IDSG` ao `IDVP` correspondente (e também aos grupos `IDG` e `IDGG`). O valor `GC` vem de `D03` para o par (`IDV`, `IDVP`).

**Interpretação didática.** `Beta = 1` significa proporcionalidade direta (dobrar o parâmetro dobra a massa); `Beta < 1` significa ganho de escala (a massa cresce menos que proporcionalmente); `Beta = 0` significa massa fixa, independente do porte.

### 8.2 Montagem da tabela `C01`

`C01` é preenchida na seguinte sequência, para cada linha de `D02` (isto é, para cada combinação `IDV`, `IDMPV`, `IDVMR`, `IDEFV`):

1. Replicar, para essa combinação, todas as linhas de `P06` correspondentes ao `IDMPV` — uma linha de `C01` por `IDSG`;
2. Preencher `IDGG` e `IDVP` a partir de `P08`, pela chave `IDSG`;
3. Preencher `GC` a partir de `D03`, pela chave (`IDV`, `IDVP`);
4. Tomar `Beta`, `GCR` e `MR` de `P06`, pela chave (`IDMPV`, `IDSG`);
5. Calcular `ME = MR × (GC/GCR)^Beta`.

Se `GC = 0`, a potência resulta em `0` para `Beta > 0` — o subgrupo não existe no veículo (ex.: motor de combustão em um BEV). Se `Beta = 0`, `ME = MR` independentemente de `GC`; o programa emite aviso quando isso ocorre com `GC = 0`, porque significa massa atribuída a um componente inexistente.

### 8.3 Aplicabilidade do subgrupo ao trem de força

Nem todo subgrupo existe em todo veículo. O i3ET trata isso com condicionais embutidas na fórmula de cada linha; o modelo aqui torna a regra um dado, na coluna `P08.ExcludedVPT`:

| Subgrupo | Não existe em | Como o i3ET trata |
|---|---|---|
| Caixa de Câmbio e Embreagem | `SHEV`, `SPHEV` | `=IF(IDVPT="SHEV",0,IF(IDVPT="SPHEV",0, ...))` na coluna de `Tamanho` de M1 |
| Módulo de Combinação Híbrida | `ICEV`, `BEV`, `SHEV`, `SPHEV`, células a combustível | Resolvido por parâmetro: o subgrupo é dimensionado por `IDVP 42 = GC(41) × GC(15)`, que vale 0 quando `GC(41) = 0` |

O segundo caso mostra o padrão preferível: quando a condição pode ser expressa como parâmetro, ela vira parâmetro. `ExcludedVPT` existe para os casos em que isso não é possível.

> **Erro tratado.** Qualquer indeterminação (`0^0`, `GCR = 0`, `GC` ausente) produz `ME = 0` e registra uma entrada no log de validação, reproduzindo o `IFERROR` do i3ET. O log é parte do relatório, não um efeito colateral silencioso.

---

## 9. Etapa 3 — Agregação de massa por grupo GREET

`C02` soma as massas dos subgrupos dentro de cada grupo GREET, para cada combinação (`IDV`, `IDMPV`, `IDVMR`, `IDEFV`):

$$MassIDGG_{IDGG} = \sum_{IDSG \,\in\, IDGG} ME_{IDSG}$$

com a associação `IDSG → IDGG` dada por `P08`.

**Exceção `Iprinc`.** O grupo `Iprinc` (bateria de tração) não é somado a partir de `C01`: sua massa é lida diretamente de `D03` no par (`IDV`, `IDVP = 35`), resultado da regra de §7.3. Isso evita dupla contagem, já que a massa da bateria é obtida por densidade energética e não por lei de escala.

Os doze grupos GREET (`P04`) são:

| `IDGG` | Descrição |
|---|---|
| `A` | Body: including BIW, interior, exterior, and glass |
| `B` | Chassis (w/o battery) |
| `C` | Traction Motor |
| `D` | Powertrain System (including BOP) |
| `E` | Transmission System / Gearbox |
| `F` | Generator |
| `G` | Electronic Controller |
| `H` | Fuel Cell Auxiliary System |
| `Iaux` | Battery Lead Acid (bateria auxiliar) |
| `Iprinc` | Battery Ion Lithium (bateria de tração) |
| `J` | Onboard Charger |
| `K` | Fluids |

---

## 10. Etapa 4 — Massa por material

`C03` distribui a massa de cada grupo entre os materiais que o compõem, segundo a receita `IDVMR`:

$$MassIDMpGG_{IDM,IDGG} = MassIDGG_{IDGG} \times MshareGG_{IDVMR,IDGG,IDM}$$

com `MshareGG` vindo de `P16`, pela chave (`IDVMR`, `IDGG`, `IDM`).

Aplica-se a **todos os grupos exceto `Iprinc`**, cuja composição é tratada em §11.

**Duas famílias de receitas.** O i3ET guarda as receitas em colunas nomeadas do
módulo M2 (bloco `T8:DD281`), e a linha 9 de cada configuração nomeia a que ela
usa. São duas famílias, e não duas versões do mesmo dado: `<PT>-BISD<n>` é a
receita original, de consultoria, e `<PT>-PBP_BISD<n>` é a do Projeto do Berço
ao Portão, que partiu da anterior e ajustou a participação de alguns materiais
com informação das montadoras brasileiras. A base traz as duas, com a
procedência declarada em `P15.DsVMR`, e cada cenário de `D02` aponta para a que
a planilha nomeia. Deduzir a receita pelo trem de força não serve: há mais de
uma por trem de força, e o veículo `BP02` usa uma variante — `PBP_BISD2s` — que
o seu nome não revela.

**Participação mássica negativa.** Algumas colunas do i3ET fecham a soma do
grupo com um resíduo negativo na linha `Others`, da ordem de 1 × 10⁻⁴. Fração
mássica negativa não existe: essas linhas entram como zero e a normalização
redistribui a diferença, o que introduz um desvio de 3 × 10⁻⁵ no resultado dos
híbridos. Está registrado no Documento 5.

**Grupo `K` (Fluidos).** A base do simulador não trazia receita para os fluidos. O
grupo carregava massa — de 25 a 43 kg por veículo — e, sem materiais, recebia
emissão zero. Não era uma decisão: era uma ausência de dado que se comportava
como um valor. A composição existe no i3ET (módulo M2, linhas 620 a 626: óleo de
motor, fluido de direção, fluido de freio, fluido de transmissão, arrefecimento,
lavador de para-brisa e adesivos) e foi incorporada a `P16` por trem de força,
pela diretriz **D11**. Com ela, a emissão dos fluidos reproduz o i3ET
exatamente. A correção acrescentou entre 67 e 108 kg CO₂e por veículo, entre
1,5% e 2,3% do total do berço ao portão. A receita do `SHEV` adota a do `HEV`,
por não haver configuração `SHEV` com fluidos preenchidos na planilha; o registro
está no Documento 5.

**Fechamento e grupo ausente.** Um par (`IDVMR`, `IDGG`) cujas participações
somam exatamente zero é um grupo que aquela receita não usa — uma ausência, não
uma violação de fechamento. A verificação ignora esses pares e exige o
fechamento em 1 apenas dos grupos presentes. Confundir os dois casos foi o que
inicialmente fez a base parecer inválida.

**Invariante de fechamento.** Para todo par (`IDVMR`, `IDGG`) com massa não nula, exige-se:

$$\left|\sum_{IDM \,:\, ShareRole = material} MshareGG_{IDVMR,IDGG,IDM} - 1\right| \le 10^{-6}$$

A soma percorre **apenas** os `IDM` cujo `P09.ShareRole` é `material`. As receitas da base trazem, no mesmo grupo, três tipos de item:

| `ShareRole` | O que é | Entra na soma? |
|---|---|---|
| `material` | Material propriamente dito (aço, alumínio, vidro, plástico…) | Sim |
| `process` | Pseudo-material de processo: montagem da bateria, montagem do veículo, descarte. Aparece com participação 1 | Não |
| `breakdown` | Redetalhamento do material ativo da bateria por química do cátodo (`IDM 87` a `97`), que repete massa já contada em `IDM 41` | Não |

Ignorar essa distinção é o que faz as receitas da base original fecharem em 2 ou em 3.

O programa verifica o invariante na carga da base e bloqueia o cálculo se ele falhar, exibindo o grupo e a soma encontrada.

---

## 11. Etapa 5 — Bateria de tração

A bateria de tração tem estrutura própria porque sua massa não segue lei de escala e sua composição depende da tecnologia, não da receita do veículo.

### 11.1 Identificação e massa

O veículo indica em `D03` (`IDVP = 32`) o modelo de bateria `IDBMd`, que aponta para `P19`. A massa vem de `IDVP 35` (§7.3). Veículos sem bateria de tração usam `IDBMd = 'NA'`, cuja linha em `P19` tem todos os campos iguais a zero; nesse caso a massa e as emissões do grupo `Iprinc` são zero, sem divisão por zero em nenhuma derivação.

### 11.2 Relações internas de `P19`

`P19` mistura parâmetros informados e derivados. As derivações são:

**Se `IDVPT = HEV`** (bateria dimensionada por potência), respeitando `IDBMd`:

```
RefWeight              = RefPower × PowerDensity
RefGHGIDBMd            = RefWeight × GravimetricGHGDensity
EnergyDensity          = RefWeight / RefEnergy
GravimetricEnergyDensity = 1 / EnergyDensity
GravimetricPowerDensity  = 1 / PowerDensity
EnergyGHGDensity       = RefGHGIDBMd / RefEnergy
```

**Se `IDVPT ≠ HEV`** (bateria dimensionada por energia), respeitando `IDBMd`:

```
RefWeight              = RefEnergy × EnergyDensity
RefGHGIDBMd            = RefEnergy × EnergyGHGDensity
GravimetricEnergyDensity = 1 / EnergyDensity
GravimetricGHGDensity  = RefGHGIDBMd / RefWeight
```

Cada divisão é protegida: denominador nulo produz campo vazio e entrada no log, nunca `inf`.

### 11.3 Massa por material da bateria

`C06` distribui a massa da bateria entre seus materiais:

$$MassIDMpGGB_{IDM} = GC(IDV, 35) \times BMshareGG_{IDBMd,IDGG,IDM}$$

com `BMshareGG` de `P20`, pela chave (`IDBMd`, `IDGG`, `IDM`). `C06` é construída replicando, para cada linha de `D02` e seu `IDBMd` correspondente, o conjunto de materiais presentes em `P11` para o `IDEFV` daquela linha. Combinações de `IDEFV` presentes em `P11` mas ausentes de `D02` não geram linhas.

### 11.4 Emissões da bateria

$$GHGIDMpGGB_{IDM} = MassIDMpGGB_{IDM} \times EF_{IDM,IDEFV}$$

**Exceção `IDM = 86` (Lithium Ion Battery Assembly).** Esse "material" é, na verdade, a montagem da bateria, cujo fator é dado em **kg CO₂e/kWh** e não em kg CO₂e/kg. Sua emissão é calculada sobre a capacidade da bateria:

$$GHGIDMpGGB_{86} = GC(IDV, 5) \times EF_{86,IDEFV}$$

A mesma lógica vale para o item de montagem da bateria de chumbo-ácido no grupo `Iaux`, cujo fator é aplicado sobre a massa da bateria auxiliar.

> **Regra geral.** Todo `IDM` cuja unidade de `EF` não seja kg CO₂e/kg é um **pseudo-material de processo** e precisa de uma base de aplicação declarada. Essa base passa a ser um campo explícito da tabela de materiais (`P09.EFBasis`), eliminando exceções codificadas.

### 11.5 Dois caminhos para a emissão da bateria

Nem toda bateria tem composição de materiais publicada. O i3ET trata os dois casos com uma condicional sobre o identificador do modelo — se ele começa por `PB`, usa uma intensidade de carbono mássica; caso contrário, soma os materiais. A calculadora adota a mesma regra, mas torna a escolha um **dado** e não uma convenção de nomenclatura, na coluna `P19.GHGMethod`:

| `GHGMethod` | Quando se aplica | Cálculo |
|---|---|---|
| `composition` | O modelo tem composição em `P20` | $GHG = \sum_{IDM} MassIDMpGGB_{IDM} \times EF_{IDM,IDEFV}$ |
| `gravimetric` | O modelo não tem composição, e sim uma intensidade de carbono | $GHG = massa_{bateria} \times GravimetricGHGDensity$ |
| `none` | `IDBMd = 'NA'`: veículo sem bateria de tração | $GHG = 0$ |

Amarrar a regra ao prefixo do identificador seria frágil: bastaria renomear um modelo para mudar o resultado. Amarrá-la à existência do dado é verificável — e é o que a coluna faz.

**Os dois modelos gravimétricos da base de referência**, importados do i3ET e originários do Projeto do Berço ao Portão:

| `IDBMd` | Trem de força | kg/kWh | kg/kW | Tecnologia | Intensidade (kg CO₂e/kg) |
|---|---|---|---|---|---|
| `PBP-BEV-LFP` | BEV | 8,6383 | — | LFP | 11,17856 |
| `PBP-HEV-NMC811` | HEV | 6,7234 | 0,38660 | NMC811 | 15,5975 |

A reprodução foi verificada nos nove veículos com bateria: massa e emissão coincidem com o i3ET até a precisão da máquina.

---

## 12. Etapa 6 — Emissões de GEE dos materiais

`C04` calcula a emissão de cada material dentro de cada grupo:

$$GHGIDMpGG_{IDM,IDGG} = MassIDMpGG_{IDM,IDGG} \times EF_{IDM,IDEFV}$$

com `EF` de `P11`, pela chave (`IDM`, `IDEFV`).

`C05` agrega por grupo:

$$GHGIDGG_{IDGG} = \sum_{IDM} GHGIDMpGG_{IDM,IDGG}, \quad IDGG \ne Iprinc$$

`C08` e `C09` são junções de conveniência (massa e emissão lado a lado) para leitura e auditoria: `C08 = C06 ⋈ C07`, `C09 = C03 ⋈ C04`, ambas pelos índices completos.

---

## 13. Etapa 7 — Montagem do veículo

Esta etapa **não existia** na documentação inicial e foi incorporada porque a fronteira "portão da montadora" a inclui por definição. A formulação segue a aba `ADR-Assembling Disposal Recycling` do i3ET, da qual se aproveita **apenas a parcela A (Assembling)**; a parcela DR (*Disposal and Recycling*) fica fora do escopo.

### 13.1 Estrutura

A montagem é decomposta em processos (`P21`), cada um com um consumo de energia por veículo e uma repartição entre combustíveis (`P22`):

| `IDAP` | Processo | Energia (MJ/veículo) | Entra em **A** |
|---|---|---|---|
| 1 | Paint Production | 302,80 | **não** |
| 2 | Vehicle Assembly — Painting | 2 910,90 | sim |
| 3 | Vehicle Assembly — HVAC & Lighting | 1 044,51 | sim |
| 4 | Vehicle Assembly — Heating | 3 146,18 | sim |
| 5 | Vehicle Assembly — Material Handling | 216,29 | sim |
| 6 | Vehicle Assembly — Welding | 288,03 | sim |
| 7 | Vehicle Assembly — Compressed Air | 431,52 | sim |

*(valores da versão de referência derivada do GREET; são parâmetros, não constantes)*

**Por que `Paint Production` fica fora.** A produção da tinta é energia de produção de **material**, já contabilizada pelo `IDM` correspondente na composição do veículo. O agregado `A` do i3ET soma apenas os processos 2 a 7 — e essa é a razão de `A` valer 705,46 kg CO₂e/veículo e não 744,70 kg, que é a soma dos sete.

Cada processo reparte sua energia entre óleo residual, diesel, gás natural, carvão e eletricidade (`P22.FuelShare`, com soma igual a 1 por processo). Os fatores de emissão dos combustíveis e da eletricidade vêm de `P25`, indexados por `IDEFV` — é por aqui que entram os fatores brasileiros.

### 13.2 Equação

$$GHG_{A} = \sum_{IDAP} \sum_{IDFuel} E_{IDAP} \times FuelShare_{IDAP,IDFuel} \times EF^{fuel}_{IDFuel,IDEFV}$$

somando apenas os processos com `P21.IncludedInA = 1`. O resultado é gravado em `C13`, por (`IDV`, `IDEA`, `IDAP`).

**Dois métodos, uma mesma tabela.** A versão de parâmetros de montagem (`P23`) declara seu método:

| `Method` | Cálculo | Versão de referência |
|---|---|---|
| `process` | Decomposição por processo e combustível (equação acima) | `ADR-GREET22` — reproduz os 705,46 kg CO₂e/veículo da aba ADR |
| `fixed` | Valor agregado em `P23.FixedGHGPerVehicle` | `i3ET-BR23` — 227,28 kg CO₂e/veículo, valor adotado pelo i3ET |

No i3ET, a montagem aparece como um pseudo-material (`IDM 99`, "A — Assembling") na própria tabela de fatores de emissão, com valor por veículo que muda conforme a versão `IDEFV`. O método `fixed` reproduz esse comportamento; o método `process` abre a caixa-preta.

### 13.3 Por que parametrizar

A montagem é o caso que melhor mostra por que nenhum fator de emissão pode ser constante de código (diretriz D13). Os números abaixo saem todos da **mesma estrutura de cálculo**, mudando apenas os parâmetros: com a repartição energética do GREET e seus fatores, 705,46 kg CO₂e/veículo; trocando só a eletricidade pela rede brasileira (25,64 g CO₂e/MJ), 449,39; com o valor agregado que o i3ET adota, 227,28. Uma faixa de mais de três vezes, inteiramente explicada por escolhas de parâmetro — e é justamente essa faixa que uma calculadora de política pública precisa tornar visível, e não esconder atrás de uma constante. Por isso a versão de parâmetros de montagem acompanha cada resultado.

**A montagem já é um parâmetro da tabela de fatores.** O `IDM 99` ("A — Assembling") tem `EFBasis = vehicle` e um valor por versão `IDEFV` — é assim que o i3ET faz, e é o que a calculadora adota por padrão:

| `IDEFV` | Montagem (kg CO₂e/veículo) |
|---|---|
| `G22`, `G23` | 705,462 |
| `G24` | 697,92 |
| `BR25BR`, `BR25m` | 318,91 |
| `BR25GLO` | 756,496 |

As quatro versões de parâmetros de montagem (`P23`) diferem apenas em **de onde** o valor vem:

| `IDAPV` | `Method` | O que faz | Situação |
|---|---|---|---|
| `A-EF` | `from_EF` | Lê o `IDM 99` da versão `IDEFV` do cenário. Cobre todas as versões automaticamente | **padrão** |
| `A-G22` | `process` | Decomposição por processo e combustível, GREET 2022. Reconcilia com o `IDM 99` de `G22` | recomendada |
| `A-G23` | `process` | Idem, GREET 2023 | recomendada |
| `i3ET-BR23` | `fixed` | 227,28 | **legado** |

O valor de 227,28 kg CO₂e/veículo que o i3ET traz na linha 510 do módulo M2 é uma **constante da planilha**: não consta do `IDM 99` em nenhuma versão de `P11` e não é reproduzível pela decomposição por processo — com a repartição energética do GREET e o fator da rede brasileira (25,64 g CO₂e/MJ), o resultado seria 449,39 kg CO₂e/veículo, ainda o dobro. Permanece na base apenas para reproduzir resultados anteriores, marcado como legado e fora da seleção padrão.

Esta é a única exceção deliberada à diretriz D11: aqui **não** prevalece o i3ET, porque o valor em questão é um dado de entrada de origem não reconstituível, e a diretriz existe para resolver conflitos de *regra de cálculo*, não para preservar um dado divergente da sua própria fonte declarada.

**Por que manter `A-G22` e `A-G23` se `A-EF` já resolve.** Porque a decomposição é o que torna o número auditável: ela mostra que os 705,46 kg vêm de seis processos, com energia e combustíveis declarados, e permite responder o que aconteceria com outra matriz elétrica. `A-EF` dá o número certo; `process` explica de onde ele vem. A reconciliação entre os dois é um teste automático.

### 13.4 Chave de escopo

O programa expõe um seletor de fronteira com três posições — `Materiais`, `Materiais + Montagem` (padrão) e `Personalizado` — e o valor escolhido é gravado junto com o resultado. Nenhum total é apresentado sem a indicação da fronteira que o gerou.

---

## 14. Etapa 8 — Totalizações

| Tabela | Conteúdo | Regra |
|---|---|---|
| `C10` | Massa e GEE por grupo GREET | `GHGIDGG` = soma de `C04` por `IDGG` (exceto `Iprinc`); para `Iprinc`, soma de `C07`. Se a soma de `C07` for zero, usar `P19.RefGHGIDBMd × GC(IDV, 35)` |
| `C11` | Massa e GEE por material | `MassIDM` = soma de `C03` + soma de `C06` por `IDM`; `GHGIDM` = soma de `C04` + soma de `C07` por `IDM` |
| `C12` | Massa e GEE por veículo (materiais) | Somas de `C10` |
| `C13` | GEE da montagem | §13.2 |
| `C14` | **Total berço ao portão** | `GHGIDV` de `C12` + `GHG_A` de `C13`, conforme a fronteira selecionada |

**Invariantes de consistência**, verificados a cada execução e publicados no relatório:

1. `Σ C01.ME` (exceto `Iprinc`) + massa da bateria = `C12.MassIDV`, com tolerância relativa de 10⁻⁹;
2. `Σ C11.MassIDM` = `C12.MassIDV`, mesma tolerância;
3. `Σ C11.GHGIDM` = `C12.GHGIDV`, mesma tolerância;
4. `Σ C10.GHGIDGG` = `C12.GHGIDV`, mesma tolerância.

Falha de invariante interrompe a exportação e exibe a discrepância — a calculadora nunca entrega um número que ela própria não consegue reconciliar.

---

## 15. Reconciliação com o modelo i3ET

Esta seção documenta onde o i3ET está, célula a célula, para que qualquer pessoa possa auditar a reimplementação.

### 15.1 Correspondência estrutural

| Conceito da calculadora | Localização no `LCA_LV_i3ET` |
|---|---|
| Parâmetros `GC` do veículo (`D03`) | `M2 GHG Mfg Module`, linhas 11 a 51, colunas T em diante (uma coluna por configuração) |
| `Beta`, `GCR`, `MR` (`P06`) | `M1 Mass Module`, colunas U, V e X, linhas 8 a 59 |
| Associação `IDSG → IDVP` (`P08`) | `M1 Mass Module`, coluna G (`ID conf`) |
| Associação `IDSG → IDGG` (`P08`) | `M1 Mass Module`, coluna T |
| `ME` por subgrupo (`C01`) | `M1 Mass Module`, coluna AC e homólogas: `=IFERROR($X·((AB/$V)^$U)·AE, 0)` |
| Massa por grupo (`C02`) | `M1 Mass Module`, linhas 68 a 79; lidas em `M2`, linhas 69 a 81 |
| Composição de materiais (`P16`) | `M2 GHG Mfg Module`, linhas 83 a 280 |
| Massa e GEE por material e grupo (`C03`/`C04`) | `M2 GHG Mfg Module`, linhas 282 a 493 |
| Fatores de emissão (`P11`) | aba `Emission Factors GREET and BR`, intervalo `AC6:AO201`; a coluna é escolhida por `M2!$P$67` (a versão `IDEFV`) |
| Total por material (`C11`) | `M2 GHG Mfg Module`, linhas 519 a 559 |
| Montagem (`C13`) | `M2 GHG Mfg Module`, linha 510, alimentada pela aba `ADR-Assembling Disposal Recycling` |
| Total berço-portão (`C14`) | soma das parcelas de `M2!T511` indicadas em §15.2 |

### 15.2 Decomposição do total do i3ET

A célula `M2!T511` ("SIMULADOR: TOTAL GHG") é a soma de sete parcelas:

```
T511 = T495  (reposições ao longo da vida)
     + T509  (DR — descarte e reciclagem)
     + T510  (A — montagem)
     + T516  (materiais do veículo, sem baterias e sem fluidos)
     + T560  (bateria auxiliar, chumbo-ácido)
     + T571  (baterias de potência/energia)
     + T617  (fluidos)
```

O total **do berço ao portão** é, portanto:

$$GHG_{berço\to portão} = T516 + T560 + T571 + T617 + T510$$

isto é, o total do i3ET **menos** as reposições (`T495`) e menos o descarte e reciclagem (`T509`). Essa é a definição operacional que a calculadora implementa, e a razão pela qual seus números não coincidem com o "TOTAL GHG" exibido pelo i3ET.

Observe-se ainda que, dentro do bloco de baterias, o i3ET carrega dois pseudo-materiais de processo — `IDM 99` (A — Assembling) e `IDM 100` (DR — Disposal and Recycling). O primeiro entra no escopo; o segundo não.

### 15.3 O fator de leveza (`fator LM`)

No i3ET, a massa calculada de cada subgrupo é multiplicada por um **fator de leveza** (coluna AE em `M1`), uniforme para todos os subgrupos de uma configuração:

$$ME = MR \times \left(\frac{GC}{GCR}\right)^{\beta} \times f_{LM}$$

Nas configurações de referência (G01 a G05) `f_LM = 1`; nas configurações com aplicação de materiais leves, `f_LM < 1` (por exemplo 0,8458). O fator pertence ao módulo M5 (*Lightweighting*), fora do escopo desta versão.

**Decisão:** a calculadora implementa a equação **com** o fator, fixado em `f_LM = 1` na v1 e exposto no dicionário de dados como parâmetro `P06.fLM` com valor padrão 1. Assim a equação fica idêntica à do i3ET, a validação numérica é exata, e a incorporação do módulo M5 no futuro não exigirá alterar a fórmula — apenas alimentar o parâmetro.

### 15.4 Universo de veículos

`D01` contém doze veículos, `BP01` a `BP12`, todos de porte *Midsize*: três ICEV, três BEV, três HEV e três PHEV, distribuídos entre Hatchback, Sedan e SUV. `D02` associa cada um a `IDMPV = 1`, `IDEFV = G22` e a uma das seis receitas de `P15`.

O i3ET trabalha com um conjunto maior de configurações (`G01` a `G30`, mais variantes `GL` e `S`), organizadas por trem de força e porte. A validação usa o subconjunto correspondente aos doze veículos de `D01`; o mapeamento veículo → configuração do i3ET é registrado na tabela `R00_Mapeamento` do relatório de validação.

---

## 16. Divergências encontradas na documentação inicial

Aplicando a diretriz D11 (prevalece o i3ET), registram-se as seguintes divergências e as regras adotadas.

| # | Onde | Redação/estado original | Comportamento no i3ET | Regra adotada |
|---|---|---|---|---|
| 1 | `P20` | Coluna nomeada `BMshare`; instruções citam `BMshareGG`; três colunas sem cabeçalho com resíduos de `IDM` | — | Coluna renomeada `BMshareGG`; colunas residuais eliminadas |
| 2 | `C05` | "GHGIDGG = MassIDGG × EF correlacionado a `IDM`, `IDEFV`" — mas `C05` não possui `IDM` | Soma das emissões dos materiais do grupo | `C05.GHGIDGG = Σ C04.GHGIDMpGG` por `IDGG` |
| 3 | `C11` | "GHGIDM = soma de `GHGIDMpGG` da tabela `C06`" — `C06` contém massa, não emissão | Soma de `C04` e `C07` | `GHGIDM = Σ C04 + Σ C07`, por `IDM` |
| 4 | Instruções | Citam tabelas `P22` (correlação de índices do veículo) e `P23` (valores `GC`), inexistentes na planilha | — | `P22` ≡ `D01` + `D02`; `P23` ≡ `D03`. Nomes unificados; `P21` a `P23` ficam livres e passam a designar as tabelas de montagem |
| 5 | Instruções | "Os `IDVP` 9, 16, 18, 28 e 37 podem ser preenchidos por cálculo" | São calculados também os `IDVP` 4, 15, 30, 33, 34, 35, 36 e 42 | Lista completa em §7.2 |
| 6 | `P07` (`IDVP 35`) | `GC(35) = GC(5) × GC(34)` | Regra em cascata com quatro ramos | Regra de §7.3 |
| 7 | `P07` (`IDVP 25`) | Listado como parâmetro do veículo | É lido do total de massa de M1 | Reclassificado como `Resultado` |
| 8 | `P19` | Linhas com zeros e `NA`; `Results_ALL_tables` (`T24`) exibe `inf` em `GravimetricEnergyDensity` | — | Divisões protegidas; `IDBMd = 'NA'` ⇒ bateria nula (§11.1) |
| 9 | `P15` × `D02` | `P15` define `IDVMR` por (`IDVPT`, `IDVDT`, `IDVS`), todas *Sedan Midsize*; `D02` atribui `IDVMR` diretamente, inclusive a Hatchbacks e SUVs | `D02` é quem manda | `D02` prevalece; `P15` vira regra de consistência com aviso, não erro |
| 10 | `Results_ALL_tables` (`T26`) | Cópia de `P01` com `IDTable` numérico e 138 linhas, contra 183 de `P01` | — | Dicionário único, em uma só tabela, sempre com `IDTable` textual |
| 11 | `Results_ALL_tables` | Abas `T01` a `T29`, sem correspondência com `P/D/C` e com conteúdo redundante | — | Renomeadas `R01` a `Rnn`, com tabela de mapeamento `T → R` publicada (Documento 4) |
| 12 | Instruções | `IDGG = 'Iprinc'` tratado por exceção em quatro pontos distintos do texto | Coerente | Regra única e explícita: a massa de `Iprinc` vem de `GC(IDV, 35)` (§9) |
| 13 | Instruções | `IDM = 86` tratado por exceção pontual | Fator em kg CO₂e/kWh | Generalizado por `P09.EFBasis` (§11.4) |
| 14 | Escopo | Documentação inicial cobre apenas materiais | i3ET calcula a montagem (`M2!T510`) | Montagem incorporada ao escopo (§13) |
| 15 | `D03_Auto` | Aba em rascunho: "ainda falta desmembrar e criar a instrução" | Lógica reside em `M2`, linhas 11 a 51 | Substituída pelas equações de §7.2; a aba é descontinuada |
| 16 | `IDM` | Declarado `Text` em `P01` mas tratado como número | A base usa `4a`, `4b`, `46a`, `46b` além de códigos numéricos | `IDM` é **TEXT** em todo o modelo |
| 17 | `P16`/`P20` | Receitas que somam 2 ou 3 | Mistura materiais, processos e redetalhamentos no mesmo grupo | Coluna `P09.ShareRole`; o fechamento soma apenas `material` (§10) |
| 18 | Montagem | Inexistente | `A` soma os processos 2 a 7 da aba ADR, excluindo `Paint Production` | `P21.IncludedInA`; reprodução exata dos 705,46 kg CO₂e/veículo |
| 19 | `P16`, grupo `Iaux` | Item com `IDM = 'ND'` e participação 1 | É a montagem da bateria de chumbo-ácido | Reatribuído a `IDM 84`, marcado como `process` |

| 20 | `P20.BMshareGG` do `IDM 86` | Valores entre 1,1 e 2,3, tratados como participação mássica | É `GravimetricEnergyDensity` (kWh/kg) × `EF(86)` — a emissão de montagem por quilo de bateria, com o fator já embutido, e **de versão trocada**: modelos `G22` trazem o fator da `G24`, modelos `G23` trazem o da `G22` | Zerado na base; a montagem da bateria é calculada por `GC(IDV, 5) × EF(86, IDEFV do cenário)`. Valores originais preservados na aba `BMshare86_original` |

| 21 | `D03` × i3ET | Os veículos `BP01`–`BP12` da base do simulador e as colunas homônimas do i3ET divergiam em 12 a 19 dos 33 parâmetros comparáveis: comprimento, largura, altura, aro, potência, tanque, capacidade de bateria | Dois instantâneos que se separaram | `D03` sincronizada a partir do i3ET (§16.6). Valores anteriores na aba `D03_antes_da_sincronizacao` |
| 22 | Emissão da bateria | Um único caminho, por composição de materiais | Dois caminhos, escolhidos por condicional sobre o prefixo do identificador | Coluna `P19.GHGMethod`, com a escolha ancorada na existência do dado (§11.5) |

| 23 | Módulo híbrido em FCV | — | A condicional do i3ET zera o módulo para `ICEV`, `BEV`, `SHEV`, `SPHEV`, `HFCEV` e `EFCEV`, mas as configurações usam o rótulo `FCV`, ausente da lista: o módulo recebe massa num veículo que não o possui | A calculadora atribui o módulo apenas a `HEV` e `PHEV`. Divergência de 36,09 kg em cinco configurações, registrada no Relatório de Divergências |
| 24 | `IDVP 15` e `IDVP 18` | Equações fixas | Valores armazenados divergem das próprias fórmulas: a potência combinada foi da soma para o máximo, e o arranque de constante embutida para parâmetro configurável | O valor informado prevalece sobre a equação; a equação vale para veículos criados pelo usuário (§16.7) |

### 16.1 Divergências que exigem decisão sua

As três abaixo **não** foram resolvidas pela regra D11 sem ressalva, porque aplicá-la muda resultados. Foram implementadas conforme o i3ET e estão sinalizadas na aba `Verificacao` do Documento 3.

| # | Assunto | Situação |
|---|---|---|
| A | **`fR` (`IDVP 16`)** | **Resolvida.** Adotada a equação do i3ET com `fH = 1`, como na linha 39 do módulo M2 em todas as 57 configurações. O parâmetro permanece na estrutura sem efeito sobre os resultados, e `fR` coincide com a base original |
| A2 | **`IDVP 15` (Combined Power)** | O i3ET usa `MAX(GC(2), GC(3))`, salvo `SHEV`/`SPHEV`. A base diverge em dois veículos: `IDV 1` traz 85,300 contra 85,318 (arredondamento) e `IDV 11` traz 110,536 contra 173,992 — nele a base usa a potência do motor a combustão, não a maior das duas. **Adotada a regra do i3ET**; confirmar `IDV 11` |
| B | **`IDVP 42`** | A base traz 0 para todos os veículos, embora `GC(41) = 1` nos híbridos. Com 0, o subgrupo "Módulo de Combinação Híbrida" recebe massa nula em todos os veículos — o módulo desaparece do modelo. A equação `GC(41) × GC(15)` reproduz exatamente a condicional do i3ET. **Adotada a equação**; confirmar |
| C | **`IDVP 36`** | A base traz 0 para os veículos 7 a 9, mas o modelo de bateria `G22-HEV-NMC111` tem `RefEnergy = 2 kWh`. **Adotado o valor de `P19`** |

### 16.2 Pequenos desvios de fechamento

Dezesseis das 54 combinações (`IDVMR`, `IDGG`) de `P16` e três das nove de `P20` fechavam em 0,9999 em vez de 1, com desvios entre 10⁻⁵ e 1,3 × 10⁻³ — arredondamentos herdados da origem dos dados, não erros de estrutura.

**Decisão: normalizar.** Cada participação foi dividida pela soma dos itens de papel `material` do seu grupo. Cinquenta grupos foram ajustados; o maior desvio original era de 1 300 ppm, na receita `BISD6`, grupo `C` (motor de tração). Depois da normalização, todas as 54 combinações de `P16` e as nove de `P20` fecham dentro de 10⁻⁶.

O fator aplicado a cada grupo, a soma original e o desvio em ppm ficam registrados na aba **`Normalizacao`** do Documento 3. Nenhum ajuste é silencioso: quem quiser reverter tem o fator exato.

### 16.2.1 A montagem da bateria e o fator embutido

Este caso merece registro detalhado porque a estrutura da base escondia um erro que nenhuma verificação de integridade apanharia.

A coluna `P20.BMshareGG` é, para todo material, uma participação mássica entre 0 e 1. Para o `IDM 86` (Lithium Ion Battery Assembly) ela trazia valores entre 1,1 e 2,3. A explicação está na unidade do fator desse pseudo-material, que é kg CO₂e/**kWh** e não kg CO₂e/kg: o coeficiente converte massa em energia. Mas ele não é o inverso da densidade energética — é esse inverso **já multiplicado por um fator de emissão**:

| Modelo | kWh/kg (`P19`) | `BMshareGG(86)` | razão | corresponde ao `EF(86)` da versão |
|---|---|---|---|---|
| `G22-BEV200-NMC111` | 0,13505 | 1,748324 | 12,945751 | `G24` |
| `G22-BEV200-LFP` | 0,11523 | 1,491739 | 12,945751 | `G24` |
| `G22-SPHEV20-LFP` | 0,08583 | 1,111134 | 12,945751 | `G24` |
| `G23-BEV150-NMC111` | 0,15229 | 2,072629 | 13,609752 | `G22` |
| `G23-BEV200-NMC111` | 0,16033 | 2,182051 | 13,609752 | `G22` |
| `G23-PHEV50-NMC111` | 0,17126 | 2,330806 | 13,609752 | `G22` |

A razão coincide até a sexta casa decimal, o que não deixa dúvida sobre a composição do número. E a última coluna mostra o problema: **as versões estão trocadas**. Os modelos da versão 2022 carregam o fator de 2024; os de 2023 carregam o de 2022.

Duas consequências, ambas verificadas numericamente com o veículo `IDV 4`:

1. Usar o coeficiente **subestima a montagem da bateria em 5,129%** — 595,5 contra 626,0 kg CO₂e. A diferença é exatamente a razão entre os fatores das duas versões, 1,051291;
2. Se o programa aplicasse `EF(86)` sobre esse resultado, como a regra genérica de `C07` faria, o total seria 8.104 kg CO₂e — **treze vezes** o correto, porque o fator entraria duas vezes.

**Regra adotada.** O `BMshareGG` do `IDM 86` foi zerado na base, e a emissão de montagem da bateria é calculada pela regra que a documentação já previa:

$$GHG_{86} = GC(IDV, 5) \times EF_{86,IDEFV}$$

com o `IDEFV` do cenário. Isso mantém a versão consistente com o resto do cálculo e elimina a possibilidade de dupla contagem. Os valores originais ficam preservados na aba `BMshare86_original` do Documento 3, para auditoria.

**Lição de projeto.** Um número pré-calculado guardado numa coluna cuja semântica é outra não é detectável por chave, por tipo nem por restrição — só por conferência dimensional. É a razão pela qual `P09.EFBasis` e `P09.ShareRole` existem: eles tornam explícito o que cada valor é, e é isso que permitiu encontrar este caso.

### 16.3 Efeito das decisões sobre a massa

As equações adotadas alteram a massa de dez subgrupos em relação à base original, todos em veículos eletrificados:

| Veículo | Variação total (kg) | Principal origem |
|---|---|---|
| `IDV 7` (HEV) | +28,57 | `IDVP 42` — módulo de combinação híbrida deixa de ser nulo |
| `IDV 8` (HEV) | +46,27 | `IDVP 42` |
| `IDV 9` (HEV) | +25,45 | `IDVP 42` |
| `IDV 10` (PHEV) | +28,57 | `IDVP 42` |
| `IDV 11` (PHEV) | +94,02 | `IDVP 42` (+46,54) e `IDVP 15`/`16` (+47,47) |
| `IDV 12` (PHEV) | +38,52 | `IDVP 42` |

Os veículos ICEV e BEV não mudam. O grosso da variação vem de um único fato: na base original, `IDVP 42` era zero em todos os veículos, o que fazia o subgrupo "Módulo de Combinação Híbrida" **desaparecer** dos híbridos. Ele agora tem massa — o que é o comportamento do i3ET.

---

## 16.4 Fatores de emissão definidos pelo usuário

A base de referência é imutável, mas o usuário precisa poder usar seus próprios fatores — para testar uma hipótese, para aplicar dados de um fornecedor, ou para incorporar um estudo que ainda não entrou na base. Isso é feito **sem tocar na base**: o arquivo de projeto pode conter versões próprias de fatores, nas tabelas `D04` e `D05`.

| Aspecto | Regra |
|---|---|
| **Onde vivem** | No arquivo de projeto do usuário (`.sqlite`), nunca na base de referência |
| **Identificação** | `D04.IDEFV` não pode colidir com nenhum `IDEFV` de `P10`; a colisão é erro de validação |
| **Herança** | `D04.BasedOnIDEFV` aponta para uma versão da base; os materiais não informados em `D05` herdam o fator dessa versão. Assim, alterar um único material não exige redigitar 104 fatores |
| **Resolução** | Na carga, o programa monta a tabela efetiva de fatores como a união de `P11` com `D05`, com `D05` tendo precedência |
| **Nas saídas** | Toda linha exportada com uma versão do usuário é marcada como tal, e `R27` traz `D04` junto de `P10`, com a fonte e a licença declaradas pelo usuário |
| **Procedência** | `D04.SourceEFV` é obrigatório. A calculadora não aceita um fator sem origem declarada — a transparência vale também para o dado de quem a usa |

O mesmo mecanismo recebe, quando disponíveis, os fatores do **Projeto Berço ao Portão (FGV/Unicamp — Fundep / Programa Move)** antes de sua incorporação definitiva à base de referência.

---

## 16.5 Cobertura dos fatores de emissão

Nem todo material usado nas receitas tem fator de emissão em todas as versões. Na fonte (i3ET) esses casos aparecem como `ND`, e são somados como zero — comportamento que a calculadora reproduz. O efeito, porém, precisa ficar visível:

| Versão | Materiais usados sem fator |
|---|---|
| `G22` | 10 |
| `G23`, `G24`, `BR25m`, `BR25GLO` | 11 |
| `BR25BR` | 14 |

de um total de 50 materiais com participação maior que zero. Os casos de maior alcance:

| `IDM` | Material | Grupos afetados |
|---|---|---|
| 14 | Glass Fiber-Reinforced Plastic | 18 |
| 40 | Others | 14 |
| 41 | Active Material | 8 |
| 59 | Coolant: Glycol | 8 |

> **Consequência que precisa ser dita.** Comparar o total de uma versão GREET com o de uma versão brasileira pode refletir, em parte, **ausência de dado** e não diferença de desempenho ambiental. O `IDM 40` ("Others"), presente em 14 grupos, não tem fator nas versões GREET e tem nas brasileiras.

Por isso:

1. A tabela `P11.EFnotes` registra, em cada fator ausente, que a emissão é contabilizada como zero por falta de dado;
2. A aba `CoberturaEF` do Documento 3 lista todos os casos, por versão;
3. O relatório exportado traz uma **seção de cobertura**, com a massa total cujo fator é nulo em cada cenário;
4. A interface exibe esse percentual junto ao total — um resultado com 8% da massa sem fator não pode ser apresentado como se fosse completo.

---

## 16.6 Sincronização dos veículos de referência com o i3ET

Ao extrair as configurações do i3ET para os testes, descobriu-se que os doze veículos `BP01`–`BP12` existem **nos dois lugares** — o mapeamento que se supunha inexistente é a identidade — e que os parâmetros divergem substancialmente:

| Parâmetro divergente | Nº de veículos |
|---|---|
| Comprimento, largura, altura | 10 |
| Aro da roda | 9 |
| Potência do motor a combustão | 9 |
| Arranque elétrico | 9 |

Os parâmetros endógenos divergiam em todos os doze, mas por consequência: derivam das dimensões.

**Decisão: sincronizar a partir do i3ET**, conforme a diretriz D11. Foram alterados **104 valores** e confirmados 184 já iguais. Os anteriores ficam na aba `D03_antes_da_sincronizacao` do Documento 3, com o valor antigo e o novo lado a lado.

A sincronização trouxe consigo dois modelos de bateria que a base não tinha — `PBP-BEV-LFP` e `PBP-HEV-NMC811` — e com eles o segundo caminho de cálculo descrito em §11.5.

**Verificação após a sincronização:** 276 parâmetros exógenos conferem com o i3ET sem uma única diferença; a massa da bateria e a emissão pelo caminho gravimétrico coincidem nos nove veículos até a precisão da máquina.

---

## 16.7 Política de divergência com o i3ET

**O i3ET em Excel não será alterado.** Ele é a referência publicada, e a estabilidade dele vale mais do que a correção pontual de um detalhe. Isso cria uma tensão com a diretriz D11, que manda o i3ET prevalecer, e a resolução é a seguinte:

| Situação | Conduta |
|---|---|
| O i3ET e a documentação inicial divergem numa **regra de cálculo** | Prevalece o i3ET (D11) |
| O i3ET apresenta **inconsistência interna** — uma fórmula que contradiz a si mesma ou um caso não previsto | A calculadora adota a regra coerente e registra a divergência |
| O i3ET traz um **valor informado** que difere da sua própria fórmula | O valor informado prevalece; a equação fica como padrão para veículos novos |

O terceiro caso não é anomalia, é evolução: parâmetros que começaram como constante embutida na fórmula tornaram-se configuráveis, e os valores armazenados refletem o estado do modelo no momento em que foram lançados. A calculadora respeita o dado e documenta a diferença.

**Toda divergência material é publicada** no *Relatório de Divergências — Calculadora × i3ET*, gerado por `tools/report_divergences.py`, que explica a origem de cada uma e sugere, quando cabe, o ajuste correspondente na planilha. Diferenças da ordem do ruído de ponto flutuante não são relatadas: listá-las esconderia as que importam.

> **Tema em aberto.** A potência combinada (`IDVP 15`) não é nem a soma nem o máximo das potências do motor a combustão e do motor elétrico. O i3ET passou de uma para a outra, e nenhuma das duas descreve corretamente o comportamento de um híbrido. O tratamento adequado é trabalho futuro, registrado aqui para não se perder.

---

## 17. Critérios de validação e aceitação

### 17.1 Validação numérica contra o i3ET

Para cada um dos doze veículos de `D01`, compara-se a saída da calculadora com a do i3ET nas seguintes grandezas:

| Grandeza | Origem no i3ET | Tolerância relativa |
|---|---|---|
| `ME` por subgrupo | `M1`, coluna `Peso Calc.` | 10⁻⁶ |
| `MassIDGG` por grupo | `M2`, linhas 70 a 81 | 10⁻⁶ |
| `MassIDV` | `M2`, linha 69 | 10⁻⁶ |
| `MassIDM` por material | `M2`, linhas 519 a 559 | 10⁻⁶ |
| `GHGIDM` por material | `M2`, linhas 519 a 559 | 10⁻⁶ |
| GEE dos materiais | `M2!T516` | 10⁻⁶ |
| GEE das baterias | `M2!T560` + `M2!T571` | 10⁻⁶ |
| GEE dos fluidos | `M2!T617` | 10⁻⁶ |
| GEE da montagem | `M2!T510` | 10⁻⁶ |
| Total berço-portão | soma de §15.2 | 10⁻⁶ |

A comparação é automatizada: um script lê a planilha i3ET, extrai as células indicadas e produz um relatório de aderência que acompanha cada versão da calculadora. Divergência acima da tolerância é falha de aceitação.

### 17.2 Validação estrutural

1. Todas as chaves primárias declaradas são únicas;
2. Toda chave estrangeira aponta para uma linha existente;
3. Nenhuma tabela `C` contém linha com índice nulo;
4. Os invariantes de §14 são satisfeitos;
5. O invariante de fechamento das receitas (§10) é satisfeito para todo (`IDVMR`, `IDGG`) com massa não nula;
6. Toda combinação (`IDM`, `IDEFV`) referenciada por alguma receita existe em `P11`.

### 17.3 Teste de suficiência da documentação

O critério da diretriz D3 é verificado por reconstrução: o núcleo de cálculo é implementado usando **somente** estes quatro documentos, sem consultar o i3ET nem a documentação inicial, e seus resultados são comparados aos do i3ET pelos critérios de §17.1. Qualquer lacuna encontrada nesse exercício é corrigida na documentação, não contornada no código.

---

## 18. Referências

### 18.1 Documentos do projeto

| Documento | Arquivo |
|---|---|
| 1 — Especificação Funcional e Metodológica | `EspecificacaoFuncional_CalculadoraBP_20260919a.md` (este) |
| 2 — Dicionário de Dados e Modelo Relacional | `DicionarioDeDados_ModeloRelacional_20260919a.md` |
| 3 — Base de Dados da Calculadora | `BaseDeDados_CalculadoraBP_20260919a.xlsx` |
| 4 — Especificação Técnica, Arquitetura e Saídas | `EspecificacaoTecnica_ArquiteturaESaidas_20260919a.md` |

### 18.2 Fontes de dados

- **GREET** (Argonne National Laboratory) — versões 2022, 2023 e 2024; fatores de emissão de materiais, composição de baterias e energia de montagem;
- **Projeto do Berço ao Portão** — FGV/Unicamp para a Fundep, no âmbito do Programa Move (Governo Federal); fatores de emissão brasileiros, a serem incorporados como versões `IDEFV` adicionais;
- **EPE, ANEEL, ONS** — intensidade de carbono da rede elétrica brasileira;
- **`LCA_LV_i3ET`** — modelo de referência, cujas abas `M1 Mass Module`, `M2 GHG Mfg Module` e `ADR-Assembling Disposal Recycling` são a base desta reimplementação;
- Referências bibliográficas dos parâmetros de massa: preservadas em `P06.Reference` e detalhadas na aba de referências do módulo M1.

### 18.3 Redistribuição dos fatores de emissão do GREET

Os termos de direito autoral do GREET (UChicago Argonne, LLC) **permitem** a reprodução e a redistribuição para **uso não comercial**, sob quatro condições que este projeto assume integralmente:

1. **Manter os avisos de direito autoral e a isenção de responsabilidade** do GREET junto aos dados redistribuídos;
2. **Creditar o Argonne National Laboratory** como desenvolvedor do GREET;
3. **Identificar a versão** do GREET em toda publicação de resultados — exigência já atendida pela estrutura de versões `IDEFV`, que acompanha cada linha exportada;
4. **Declarar quando os dados de entrada foram modificados.** É o caso aqui: os fatores desta base não são o arquivo GREET original, e sim valores extraídos e processados pelo i3ET. A tabela `P11` traz a rastreabilidade em `EFnotes`, e `P10.SourceEFV` registra a origem de cada versão.

Duas consequências práticas:

- **A base de dados não pode ser licenciada como software livre irrestrito.** O código pode (MIT); a documentação pode (CC BY 4.0); os fatores derivados do GREET ficam sob os termos do Argonne, restritos a uso não comercial. O repositório precisa, portanto, de três licenças distintas e de um arquivo `data/NOTICE.md` com os avisos exigidos.
- **A modificação do código-fonte do GREET não é permitida**, o que não afeta este projeto: a calculadora não modifica nem recompila o GREET — ela consome valores publicados, documentando a extração.

Os fatores do **Projeto do Berço ao Portão (FGV/Unicamp para a Fundep — Programa Move, Governo Federal)** **já estão na base**, nas versões `BR25BR` (produção 100% nacional), `BR25m` (mercado brasileiro) e `BR25GLO` (internacional), sem restrição herdada do GREET. As condições de redistribuição desses fatores ainda precisam ser registradas em `P10.LicenseEFV` antes da publicação.

Fontes: [Argonne GREET — Copyright](https://greet.anl.gov/copyright); [Argonne GREET R&D Model](https://greet.anl.gov/).

---

*Documento gerado em 19/09/2026 — versão `a`.*
