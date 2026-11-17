# Especificação Técnica, Arquitetura e Saídas
## Calculadora da Pegada de Carbono de Veículos Leves — do Berço ao Portão

**Documento 4** · Versão `20261116a` · Projeto NIPE/UNICAMP

> **Estado em 16/11/2026.** Este documento descreve a versão 0.9.0, publicada, e as mudanças já feitas para a 0.10.0 (Fase A): o esquema 0.10, a base reconstruída e os scripts de extração. O que mudou está marcado com *(0.10)*. A interface da Fase A (§4) ainda não foi programada; sua especificação está no Documento 6. O estado da Fase A, passo a passo, está no §10.

---

## Sumário

1. [Arquitetura](#1-arquitetura)
2. [Estrutura do repositório](#2-estrutura-do-repositório)
3. [Algoritmo de cálculo](#3-algoritmo-de-cálculo)
4. [Interface do usuário](#4-interface-do-usuário)
5. [Especificação das saídas](#5-especificação-das-saídas)
6. [Exportação](#6-exportação)
7. [Testes e validação](#7-testes-e-validação)
8. [Publicação](#8-publicação)
9. [Evolução modular](#9-evolução-modular)
10. [Fase A — estado em 16/11/2026](#10-fase-a--estado-em-16112026)

---

## 1. Arquitetura

### 1.1 Princípio: núcleo puro, casca substituível

O programa é dividido em três camadas, com dependência em um único sentido:

```
   interface (Streamlit)     ← pode ser trocada sem tocar no resto
        │
   serviços (projeto, exportação, validação)
        │
   núcleo de cálculo (Python puro: entra DataFrame, sai DataFrame)
        │
   persistência (SQLite)
```

O **núcleo** não importa Streamlit, não lê arquivos e não conhece a interface. Ele recebe tabelas e devolve tabelas. Essa disciplina é o que permite:

- rodar os mesmos cálculos em um *notebook*, em testes automatizados e na web;
- trocar o Streamlit por outra interface (ou por uma API) sem reescrever o cálculo;
- validar contra o i3ET com um script, sem abrir a aplicação.

Essa escolha também é a resposta à limitação que motivou o abandono do Netlify: se amanhã a hospedagem mudar, apenas a casca muda.

### 1.2 Pilha tecnológica

| Camada | Escolha | Justificativa |
|---|---|---|
| Linguagem | Python 3.11+ | Diretriz D5 |
| Dados em memória | pandas | Junções relacionais legíveis e verificáveis |
| Persistência | SQLite (biblioteca padrão) | Integridade relacional real, arquivo único, sem servidor |
| Interface | Streamlit | Python nativo, tabelas e gráficos prontos, publicação direta do Git |
| Exportação | `openpyxl` (XLSX) e `csv` (CSV) | Formatos exigidos pela diretriz D4 |
| Gráficos | Altair (já embarcado no Streamlit) | Declarativo, exporta dados junto com a figura |
| Testes | pytest | Testes de invariantes e de aderência ao i3ET |
| Hospedagem | Streamlit Community Cloud | Publicação a partir do repositório Git |

Nenhuma dependência paga, nenhuma chave de API, nenhum serviço externo em tempo de execução.

### 1.3 Os dois bancos

| Banco | Conteúdo | Escrita |
|---|---|---|
| `base_referencia.sqlite` | Tabelas `P` — parâmetros de massa, materiais, fatores de emissão, baterias, montagem. *(0.10)* Também os veículos de mercado, o PBEV, as categorias, o catálogo de parâmetros do Control Panel, as regras de valor padrão, a regra da potência combinada e os valores de referência da planilha | Somente leitura. Distribuído com o programa, versionado no repositório |
| `projeto_<nome>.sqlite` | Tabelas `D` (veículos e cenários do usuário), `C` (resultados da última execução) e `M` (metadados e log) | Leitura e escrita. Baixado e carregado pelo usuário |

Na abertura de um projeto, o programa confere o *hash* da base de referência gravado no projeto contra o da base carregada. Divergência gera aviso explícito: os resultados guardados foram produzidos com outros parâmetros.

*(0.10)* O projeto é uma cópia da base (decisão do passo 2 de setembro: um arquivo, não dois). Um arquivo da 0.9.0 é levado ao esquema novo por `schema.migrate`, que só cria o que falta, e recebe os parâmetros da Fase A por `schema.sync_fase_a`, que só acrescenta linhas. Nenhum dos dois altera resultado existente (Documento 7, §7). O projeto ganha identidade própria na tabela `M03`.

---

## 2. Estrutura do repositório

```
calculadora-berco-portao/
├─ app.py                       # ponto de entrada Streamlit
├─ requirements.txt
├─ README.md
├─ core/                        # nucleo de calculo — Python puro
│  ├─ __init__.py
│  ├─ schema.py                 # DDL (Documento 2, cap. 10) e criacao da base;
│  │                            # (0.10) blocos S5-S10: esquema da Fase A, migracao,
│  │                            # impressao digital e sincronizacao de projeto antigo
│  ├─ loader.py                 # carga de CSV/XLSX/SQLite para DataFrames
│  ├─ params.py                 # calculo dos parametros endogenos (Doc. 1, §7.2)
│  ├─ mass.py                   # C01, C02          (Doc. 1, §8 e §9)
│  ├─ materials.py              # C03, C04, C05     (Doc. 1, §10 e §12)
│  ├─ battery.py                # C06, C07          (Doc. 1, §11)
│  ├─ assembly.py               # C13               (Doc. 1, §13)
│  ├─ totals.py                 # C10, C11, C12, C14 (Doc. 1, §14)
│  ├─ validate.py               # invariantes I1..I13 (Doc. 2, cap. 8)
│  └─ report.py                 # montagem das tabelas R
├─ data/
│  ├─ base_referencia.sqlite
│  ├─ csv/                      # mesma base em CSV, um arquivo por tabela
│  │  └─ fase_a/                # (0.10) fixtures da Fase A, um CSV por tabela;
│  │                            # '<Tabela>.add.csv' sao linhas a acrescentar
│  └─ NOTICE.md                 # origem e condicoes de uso dos dados
├─ tests/
│  ├─ test_invariants.py
│  ├─ test_i3et_reference.py    # aderencia numerica ao i3ET
│  ├─ test_schema_010.py        # (0.10) esquema, restricoes e migracao
│  ├─ test_fixtures_fase_a.py   # (0.10) conteudo da base da Fase A
│  └─ fixtures/                 # inclui base_090.sqlite, um arquivo genuino da 0.9.0
├─ docs/                        # os documentos, glossario PT-EN e interface/ (§4.8)
└─ tools/
   ├─ build_base.py             # gera a base a partir das planilhas de origem
   ├─ extract_i3et.py           # extrai do i3ET os valores de referencia
   ├─ make_db.py                # monta P01-P25 a partir do Documento 3
   ├─ xlsx_cells.py             # (0.10) leitor de uma guia do .xlsx por vez
   ├─ fase_a_common.py          # (0.10) apoio comum aos scripts da Fase A
   ├─ extract_control_panel.py  # (0.10) P29, P30, P51, parte de P52
   ├─ import_market_vehicles.py # (0.10) P54, P26, P27, parte de P52
   ├─ import_pbev.py            # (0.10) P36, P28, P55, P50
   ├─ build_default_rules.py    # (0.10) P49, P35
   ├─ import_ef_versions.py     # (0.10) listas de fatores BR23, GLO23 e variantes
   ├─ build_static_tables.py    # (0.10) P53 e linhas novas de P12 e P13
   ├─ fit_combined_power.py     # (0.10) P56: fatores arbitrados da potência combinada
   ├─ import_recipes.py         # (0.10) receitas do GREET 2024 para P15 e P16
   └─ load_fase_a.py            # (0.10) carrega data/csv/fase_a na base
```

### 2.1 Onde o repositório vive

A árvore acima existe em dois lugares, sempre iguais:

| Lugar | Papel | Sincronizado por |
|---|---|---|
| `C:\Users\<usuário>\Projetos\i3et-calculator\` | **Cópia de trabalho**, clonada do GitHub. Todo arquivo gerado é salvo aqui no momento em que é produzido | Git |
| `github.com/paulosplima-netizen/i3et-calculator` | Repositório público | — |
| `...\_Unicamp\_Calculadora da Pegada de Carbono\Documentação\` | Documentos datados (`_AAAAMMDDx`). A planilha do i3ET fica em `...\Model\`; os pacotes de interface superados, em `Documentação\Versões anteriores\` | OneDrive |

Os **documentos datados** são o instantâneo citável de cada marco e ficam no OneDrive, que é bom nisso. Dentro do repositório, os mesmos documentos têm nomes estáveis (`docs/01-especificacao-funcional.md`) e o histórico fica a cargo do Git — ver diretriz D6.1 do Documento 1. O código nunca leva sufixo datado: quebraria os imports a cada revisão.

A cópia de trabalho precisa ser um **clone** (pasta com `.git`), não um download dos arquivos: sem o `.git` não há vínculo com o GitHub, e nada do que for produzido pode ser enviado.

### 2.2 Por que o repositório fica fora do OneDrive

O repositório **não** pode morar numa pasta sincronizada por armazenamento em nuvem. A razão é estrutural, não de preferência:

1. **O `.git` e o OneDrive disputam os mesmos arquivos.** O `.git` reescreve centenas de arquivos pequenos a cada operação; o OneDrive os trava para enviar. O resultado possível é repositório corrompido ou "cópias em conflito" dentro do `.git`;
2. **Duas máquinas agravam o problema.** Quando a mesma pasta sincroniza para dois computadores em que se trabalha, um `commit` iniciado em um pode chegar pela metade ao outro — índice de uma versão, referências de outra;
3. **O ambiente virtual não sobrevive à sincronização.** O `.venv` tem dezenas de milhares de arquivos, e o `.gitignore` impede que o Git os rastreie mas não impede o OneDrive de sincronizá-los. Pior: um ambiente virtual guarda caminhos absolutos da máquina onde foi criado e não funciona na outra;
4. **O Git já resolve o problema que a sincronização tentaria resolver.** Levar o trabalho de uma máquina a outra é exatamente a função dele — e ele faz isso entendendo o conteúdo, com histórico e resolução de conflitos, enquanto o OneDrive copia bytes sem saber o que são.

**Trabalho em mais de uma máquina:** clonar o repositório em cada uma, a partir do GitHub. `pull` ao começar, `push` ao terminar. Nenhuma pasta de repositório é compartilhada ou sincronizada por nuvem.

**Colaboração:** acontece pelo GitHub, nunca por compartilhamento de pasta. Compartilhar o diretório de documentos com um colaborador é seguro; compartilhar o repositório não é.

O que **permanece** no OneDrive são os documentos, as planilhas de origem e a base — arquivos grandes, poucos e reescritos raramente, que é o caso em que a sincronização ajuda.

**Regra de ouro:** `core/` nunca importa `streamlit`. Se um módulo de `core/` precisar avisar o usuário, ele devolve uma linha de log — não desenha nada.

---

## 3. Algoritmo de cálculo

### 3.1 Sequência

```
1.  carregar base de referencia (P) e projeto (D)
2.  validar integridade estrutural  ......................  I1 a I11
3.  para cada (IDV, IDEA) em D02:
      3.1  resolver versoes: IDMPV, IDVMR, IDEFV, IDAPV, Boundary
      3.2  calcular parametros endogenos de D03      ......  Doc.1 §7.2
      3.3  C01  massa por subgrupo                   ......  Doc.1 §8
      3.4  C02  massa por grupo GREET                ......  Doc.1 §9
      3.5  C03  massa por material e grupo           ......  Doc.1 §10
      3.6  C04  GHG por material e grupo             ......  Doc.1 §12
      3.7  C05  GHG por grupo                        ......  Doc.1 §12
      3.8  C06  massa de bateria por material        ......  Doc.1 §11.3
      3.9  C07  GHG de bateria por material          ......  Doc.1 §11.4
      3.10 C13  GHG da montagem                      ......  Doc.1 §13
      3.11 C10, C11, C12, C14  totalizacoes          ......  Doc.1 §14
4.  validar invariantes de conservacao  .................  I12, I13
5.  gravar C* e M* no projeto; montar R*
```

### 3.2 Núcleo, em pseudocódigo

```python
def calcular(P, D):
    log = Log()
    validar_estrutura(P, D, log)
    C = {}
    for (idv, idea), cen in D["D02"].iterrows():
        gc   = resolver_parametros(D["D03"], P["P07"], idv, cen, log)
        c01  = massa_por_subgrupo(P["P06"], P["P08"], gc, cen, log)
        c02  = massa_por_grupo(c01, gc, log)          # Iprinc vem de gc[35]
        c03  = massa_por_material(c02, P["P16"], cen.IDVMR, log)
        c04  = ghg_por_material(c03, P["P11"], P["P09"], cen.IDEFV, gc, log)
        c06  = massa_bateria(gc, P["P20"], log)
        c07  = ghg_bateria(c06, P["P11"], P["P09"], cen.IDEFV, gc, log)
        c13  = ghg_montagem(P["P21"], P["P22"], P["P23"], P["P25"],
                            cen.IDAPV, cen.IDEFV, log)
        C = acumular(C, totalizar(c01, c02, c03, c04, c06, c07, c13, cen))
    validar_conservacao(C, log)
    return C, log
```

### 3.3 Detalhes que decidem a corretude

**Massa por subgrupo.** A equação é `ME = MR × (GC/GCR)**Beta × fLM`. Calcular em `float` de 64 bits, sem arredondamento intermediário. Arredondamento só na apresentação.

**Exceção `Iprinc`.** Ao montar `C02`, os subgrupos mapeados para `Iprinc` **não** são somados; o valor vem de `GC(IDV, 35)`. Omitir essa regra produz dupla contagem da bateria — o erro mais provável de toda a implementação.

**Base do fator de emissão.** Antes de multiplicar massa por `EF`, consultar `P09.EFBasis`:

```python
if basis == "mass":     ghg = massa * ef
elif basis == "energy": ghg = gc[p09.EFBasisParam] * ef     # ex.: IDM 86 sobre GC(5)
elif basis == "vehicle":ghg = ef                            # ex.: IDM 99 (montagem agregada)
```

**Fechamento das receitas.** Só entram na soma que deve dar 1 os materiais com `P09.ShareRole = 'material'`. Os de papel `process` (montagem de bateria, montagem do veículo, descarte) e `breakdown` (marcadores de química do cátodo, que redetalham o material ativo) ficam fora — somá-los infla a receita e é a causa das somas iguais a 2 ou 3 observadas na base original.

**Montagem.** Três caminhos, conforme `P23.Method`: `from_EF` (padrão) lê o `IDM 99` de `P11` na versão `IDEFV` do cenário; `process` calcula pela decomposição de `P22` e `P25`, considerando apenas os processos com `P21.IncludedInA = 1`; `fixed` usa `P23.FixedGHGPerVehicle`.

**Cobertura de fatores.** Ao montar `C04` e `C07`, acumular a massa cujo `EF` é nulo. Esse total entra em `C14` como `MassNoFactor` e `ShareNoFactor`, e é exibido junto de todo resultado. Um fator ausente não é zero de emissão — é dado que falta, e o relatório precisa dizer isso.

**Divisões.** Toda divisão passa por uma função que devolve `None` e registra log quando o denominador é zero. Em nenhuma circunstância a saída contém `inf` ou `NaN`.

---

## 4. Interface do usuário

**A interface é em inglês.** A documentação permanece em português, e os nomes de tabelas e colunas já eram em inglês — de modo que a tela, o dado e o relatório falam a mesma língua. Um glossário português–inglês dos termos de tela está previsto em `docs/glossario.md` (ainda não escrito — ver §4.9), para que o material didático em português possa apontar para os rótulos que o usuário vê.

Este capítulo descreve a interface com detalhe suficiente para reconstruí-la sem o código e sem ferramentas externas: a ordem dos blocos de cada tela, os controles, os textos, os valores padrão e o sistema visual. As capturas em `docs/interface/telas/` mostram o resultado na versão 0.9.0, no estado de referência (projeto recém-criado, veículo BP01).

### 4.1 Princípios

1. **Didático antes de decorativo.** Cada tela diz em uma frase o que faz, informa em que seção do Documento 1 está especificada e permite abrir um número de volta à equação que o produziu.
2. **Versões sempre à vista.** Dois resultados só são comparáveis se as versões por trás deles estiverem declaradas; por isso a barra de versões aparece no alto de toda tela com projeto aberto.
3. **Tela e arquivo não divergem.** Os gráficos da tela e do relatório exportado saem do mesmo gerador (`core/charts.py`) e da mesma paleta.
4. **Ausência de dado não é zero.** A massa sem fator de emissão publicado é declarada em texto toda vez que um total aparece.

### 4.2 Estrutura e navegação

`app.py` declara a navegação e nada mais; cada tela é um script em `pages/`, na ordem em que a análise acontece. O estado do projeto e os componentes compartilhados ficam em `ui/` (`ui/state.py`, `ui/components.py`), que importa `core` — nunca o contrário.

| # | Tela | Arquivo | Ícone | Doc. 1 | Captura |
|---|---|---|---|---|---|
| 1 | **Home** | `pages/1_Home.py` | 🏠 | §1 | `interface/telas/1_Home.png` |
| 2 | **Vehicles** | `pages/2_Vehicles.py` | 🚗 | §7 | `interface/telas/2_Vehicles.png` |
| 3 | **Vehicle parameters** | `pages/3_Vehicle_parameters.py` | 🔧 | §7.2 | `interface/telas/3_Vehicle_parameters.png` |
| 4 | **Scenario** | `pages/4_Scenario.py` | 🎛 | §3 e §6 | `interface/telas/4_Scenario.png` |
| 5 | **Results** | `pages/5_Results.py` | 📊 | §8 a §14 | `interface/telas/5_Results.png` |
| 6 | **Emission factors** | `pages/6_Emission_factors.py` | 🏭 | §16.4 | `interface/telas/6_Emission_factors.png` |
| 7 | **Export** | `pages/7_Export.py` | 📤 | §6 deste documento | `interface/telas/7_Export.png` |

A navegação fica na barra lateral, com a Home como página padrão. Todas as telas usam `layout="wide"`; o título de aba é `"<Tela> · i3ET Calculator"` (na Home, só `"i3ET Calculator"`).

**Cabeçalho padrão** (`components.page`), nas telas 2 a 7, nesta ordem:

1. `st.title` com o nome da tela;
2. `st.caption` "Specified in docs/01-especificacao-funcional.md, <seção>";
3. a *version bar* (§4.3);
4. o painel de validação compacto (§4.3).

Sem projeto aberto, o cabeçalho mostra só o título, a legenda e o aviso `st.info` "Open or create a project on the **Home** page first." — e a tela para aí.

**Primitivas.** O Streamlit não posiciona elementos livremente: a tela é uma coluna de blocos empilhados. Toda tela desta calculadora é montada só com barra lateral, `st.columns` (com pesos), `st.tabs`, `st.expander`, `st.form`, `st.divider`, controles de entrada, `st.metric`, `st.dataframe`/`st.data_editor` e alertas (`st.info`, `st.success`, `st.warning`, `st.error`). `st.divider` separa blocos de assunto diferente; `st.subheader` abre cada bloco.

### 4.3 Elementos comuns

**Version bar** (`components.version_bar`). Uma linha de texto — não seis caixas, porque os identificadores são longos e uma caixa estreita os cortaria onde está a informação:

> **Mass params** `1` · **Material recipe** `PBP_BISD12, PBP_BISD2 +4` · **Emission factors** `G22` · **Assembly** `A-EF` · **Boundary** `MAT_ASM` · **Project** `meu-projeto`

- cada valor é o conjunto de valores distintos daquela coluna de `D02`, ordenado; com mais de dois, mostra os dois primeiros e conta o resto (`+4`); a lista inteira está na tela Scenario e em `R01`;
- se algum cenário usa uma versão de fatores criada pelo usuário, o valor de *Emission factors* ganha o sufixo "· user-defined";
- segunda linha, em `st.caption`: "Reference base `<16 primeiros caracteres do hash>` · program <versão>".

**Painel de validação** (`components.validation_panel`), logo abaixo da version bar, na forma compacta:

| Situação | Forma compacta (cabeçalho) | Forma completa (Export) |
|---|---|---|
| todos os invariantes passam | nada | `st.success` "Validation passed: every invariant holds." |
| só avisos | `st.expander` "N warning(s)" com até 40 avisos | `st.warning` "Validation passed with N warning(s)." |
| algum erro | `st.error` "**Validation failed** — N error(s). Nothing may be exported until they are resolved." e até 8 regras, cada uma com o identificador em código | idem |

**"How was this calculated?"** (`components.how_was_this_calculated`). Um `st.expander` fechado, colocado logo abaixo do número ou gráfico que explica, com o título "How was this calculated? — <o quê>". Dentro: a equação em bloco de código, uma tabela *Input · Value* com cada insumo e sua tabela de origem, e a seção do Documento 1 em `st.caption`. Aparece em Vehicle parameters (massa de um subgrupo, §8.1) e Results (emissões de um grupo, §12).

**Números.** Formato brasileiro — ponto de milhar, vírgula decimal (`components.number`). Nas métricas (`st.metric`), **uma casa decimal e a unidade no rótulo** ("Cradle to gate (kg CO₂e)" / "4.075,0"), para o valor caber inteiro numa coluna estreita; a precisão completa fica nas tabelas e nas exportações. Nas tabelas, o número é exibido como o `st.dataframe` o formata.

**Nota de cobertura** (`components.coverage_note`), em `st.caption`, sempre logo abaixo de um total: "**7,481 kg** (0,65%) of this vehicle's mass has no published factor in the selected version. That mass is counted in the mass total and contributes nothing to the emissions — absence of data, not zero emissions." Se toda a massa tem fator: "Every kilogram of this vehicle has a published emission factor in the selected version."

**Tabelas.** `st.dataframe` sem índice, na largura da coluna, com a altura padrão do Streamlit (cerca de dez linhas visíveis e rolagem). Editáveis (`st.data_editor`) só para dados do usuário.

**Gráficos.** SVG em linha, gerado por `core/charts.py`, com o estilo de `ESTILO_GRAFICO` (`ui/components.py`) — ver §4.7. Sem dados: `st.caption` "Nothing to plot for this selection."

### 4.4 As sete telas

Em cada tabela abaixo, os blocos estão na ordem em que aparecem, de cima para baixo. "Cabeçalho" é o cabeçalho padrão do §4.2.

#### 4.4.1 Home

Sem o cabeçalho padrão. Título "Light vehicle carbon footprint — cradle to gate"; legenda "Modules M1 (mass) and M2 (manufacturing GHG) of the i3ET model · NIPE/UNICAMP · kg CO₂e, GWP-100, IPCC AR6". Barra lateral expandida ao abrir. Se a base de referência não existe: `st.error` "The reference database is missing. Build it with `python tools/make_db.py`." e a tela para.

| Bloco | Primitiva | Conteúdo |
|---|---|---|
| Duas colunas | `st.columns([1.4, 1])` | esquerda: projeto; direita: base de referência |
| Esquerda — sem projeto | `st.subheader` "Project"; texto; `st.text_input` "Name for a new project" (padrão `meu-projeto`); botão primário "Create project"; `st.file_uploader` "…or open an existing project (.sqlite)" (`.sqlite`, `.db`) | criar copia a base de referência; abrir valida o arquivo e mostra `st.error` se não for um projeto |
| Esquerda — com projeto | texto; `st.success` "**<nome>** is open."; `st.download_button` "Download this project"; `st.caption` "Sessions in the cloud are temporary. Download the project to keep your work."; botão "Close project" | |
| Direita | `st.subheader` "Reference base"; `st.metric` "Parameter hash" (16 caracteres), "Vehicles in the project", "Scenarios", "Program version" | sem projeto: `st.info` "No project open yet." no lugar das três primeiras |
| Com projeto | `st.divider`; version bar; `st.divider`; `st.subheader` "Where to go next"; lista numerada das telas 2 a 7 com uma linha cada | |
| Rodapé | `st.divider`; `st.caption` com a atribuição dos fatores (GREET © UChicago Argonne, LLC; Projeto do Berço ao Portão — FGV/Unicamp para a Fundep, Programa Move) | |

Texto do bloco Project: "A project is one SQLite file: the reference parameters, plus your own vehicles, scenarios and emission factor versions. Creating one copies the reference base — you edit your copy, and the reference is never modified."

#### 4.4.2 Vehicles

| Bloco | Primitiva | Conteúdo |
|---|---|---|
| Cabeçalho | | §7 |
| Explicação | `st.write` | "The twelve reference vehicles come with the base and are never modified. Vehicles you create are marked as yours, and live only in your project file." |
| Lista | `st.dataframe` | `D01` junto com `D02`: IDV, DsV, IDVPT, IDVDT, IDVS, IDLR, Source (`reference`/`yours`), IDMPV, IDVMR, IDEFV, IDAPV, Boundary |
| Criar | `st.divider`; `st.subheader` "Create a vehicle"; texto; `st.form` | ver §4.5 |
| Formulário | duas linhas de `st.columns(3)` e botão primário "Create" | linha 1: "Copy from" (DsV), "Name" (padrão `MEU01`), "Size" (`P14`); linha 2: "Powertrain" (`P12`), "Body" (`P13`), "Material recipe" (`P15`, com ajuda apontando para a tela Scenario). *(0.10)* "Powertrain" e "Body" só listam as linhas com `IsCalculable = 1`; num projeto da 0.9.0, sem a coluna, listam todas |
| Remover | `st.divider`; `st.subheader` "Remove a vehicle of yours"; `st.selectbox` "Vehicle"; botão "Remove" | só aparece se houver veículo do usuário |

Mensagens: `st.error` "There is already a vehicle named <nome>."; `st.success` "<nome> created. Open **Vehicle parameters** to adjust it."

#### 4.4.3 Vehicle parameters

| Bloco | Primitiva | Conteúdo |
|---|---|---|
| Cabeçalho | | §7.2 |
| Veículo | `st.selectbox` "Vehicle" | todos os DsV |
| Explicação | `st.write` | exógenos são do usuário; endógenos são calculados, com a equação ao lado; valor informado não é desfeito pela equação; a coluna `IsCalculated` registra qual é qual |
| Aviso | `st.info` | só para veículo de referência: "This is a reference vehicle: its parameters are read-only. Create a copy on the **Vehicles** screen to change anything." |
| Exógenos | `st.subheader` "Exogenous — what you set"; tabela IDVP, Parameter, Unit, Stored (rotulado "Value" no editor, 6 casas), Text | veículo do usuário: `st.data_editor` com IDVP, Parameter e Unit bloqueados e botão primário "Save values" → `st.success` "Saved. Everything downstream was recalculated." |
| Endógenos | `st.subheader` "Endogenous — computed from the above"; `st.dataframe` IDVP, Parameter, Unit, Computed, Stored, IsCalculated, Equation; `st.caption` explicando Computed × Stored | |
| Massa resultante | `st.divider`; `st.subheader` "Resulting mass"; `st.columns(2)` com as métricas "Vehicle mass (kg)" e "Cradle to gate (kg CO₂e)" | |
| Explicação | "How was this calculated? — Mass of one subgroup": `ME = MR · (GC / GCR)^Beta · fLM`, §8.1 | |
| Subgrupos | `st.dataframe` de `C01`: IDSG, IDVP, GC, Beta, GCR, MR, fLM, ME | |

#### 4.4.4 Scenario

| Bloco | Primitiva | Conteúdo |
|---|---|---|
| Cabeçalho | | §3 e §6 |
| Explicação | `st.write` | "Two results are comparable only if the versions behind them are stated. That is why they are a choice, and why they travel with every exported table." |
| Veículo | `st.selectbox` "Vehicle" | |
| Duas colunas | `st.columns(2)` | |
| Esquerda | `st.subheader` "Material recipe"; `st.radio` "Which composition to apply"; `st.caption` com `P15.DsVMR` da receita marcada; `st.info` "The two families…" | opções: receitas de `P15` compatíveis com o trem de força, cada uma com o sufixo "· consultoria" (`BISD*`) ou "· Berço ao Portão" (`PBP_BISD*`); marcada a do cenário atual. Sem receita compatível: `st.warning` e lista todas |
| Direita | `st.subheader` "Versions"; `st.selectbox` "Emission factors" + `st.caption` "<DsEFV> · <GWPSet>"; "Mass parameters"; "Assembly parameters" + `st.caption` "Method `<Method>` — <DsAPV>"; `st.radio` "Boundary"; `st.caption` sobre `MAT` | opções de fatores: `P10` seguidas de `D04`; fronteira: "materials + assembly (cradle to gate)" (`MAT_ASM`) ou "materials only" (`MAT`) |
| Aplicar | botão primário "Apply to this vehicle" | grava em `D02` → `st.success` "Scenario applied. Everything was recalculated." |
| Visão geral | `st.divider`; `st.subheader` "What each vehicle is set to"; `st.dataframe` IDV, DsV, IDVPT, IDMPV, IDVMR, IDEFV, IDAPV, Boundary | |
| Comparação | `st.divider`; `st.checkbox` "Compare the two recipe families on this vehicle" | marcado: tabela Recipe, Mass (kg), Cradle to gate (kg CO₂e), kg CO₂e / kg, calculada para cada receita compatível, e `st.caption` "Same mass, different emissions…" |

#### 4.4.5 Results

| Bloco | Primitiva | Conteúdo |
|---|---|---|
| Cabeçalho | | §8 a §14 |
| Veículo | `st.selectbox` "Vehicle" | sem cenário: `st.warning` e a tela para |
| Totais | `st.columns(4)` com `st.metric` | "Vehicle mass (kg)", "Materials (kg CO₂e)", "Assembly (kg CO₂e)", "Cradle to gate (kg CO₂e)" (ajuda: a montagem entra quando a fronteira é `MAT_ASM`) |
| Cobertura | nota de cobertura (§4.3) | |
| Cascata | `st.divider`; `st.subheader` "Where the total comes from"; gráfico `charts.waterfall` | passos: grupos GREET com emissão positiva em ordem decrescente e, se a fronteira é `MAT_ASM`, "Assembly"; barra final "Total"; título "<veículo>: contribution of each GREET group" |
| Explicação | "How was this calculated? — Emissions of one group": `GHG_group = Σ_materials Mass_group × MshareGG × EF_material`, §12 | |
| Detalhe | `st.tabs` "By GREET group" · "By material" · "Battery" · "Assembly" | 1: `C10` e legenda; 2: `C11` em ordem decrescente de GEE e `st.checkbox` "Show the material × group detail, with shares and factors" (abre `C03`); 3: `C07` e legenda com o modelo e o método de `P19` — sem bateria de tração: `st.info`; 4: `C13` e legenda com o método de `P23` |
| Comparação | `st.divider`; `st.subheader` "Every vehicle, side by side"; gráfico `charts.bar_chart` "Cradle to gate, every vehicle"; tabela Vehicle, Powertrain, Mass (kg), Cradle to gate (kg CO₂e), kg CO₂e / kg, Mass without factor (kg) | rótulos das barras "<DsV> (<IDVPT>)" |

#### 4.4.6 Emission factors

| Bloco | Primitiva | Conteúdo |
|---|---|---|
| Cabeçalho | | §16.4 |
| Versões | `st.subheader` "Versions in this project"; tabela IDEFV, DsEFV, DateIDEFV, GWPSet, Source (`reference`/`yours`), SourceEFV; `st.caption` sobre a licença (`LicenseEFV` acompanha toda exportação) | |
| Consulta | `st.divider`; `st.subheader` "Browse the factors"; `st.selectbox` "Version"; `st.columns(2)` com as métricas "Materials in this version" e "Without a published factor"; tabela IDM, DsM, EFBasis, EF, IsUserDefined, EFnotes; `st.caption` sobre fator ausente | fatores efetivos (`loader.effective_emission_factors`) |
| Criar versão | `st.divider`; `st.subheader` "Create a version of your own"; texto; `st.form` | ver §4.6 |
| Formulário | `st.columns(2)`: "Identifier" (padrão `MEUS-FATORES`), "Inherit from" (`P10`); "Description" (padrão "Fatores próprios"); `st.text_area` "Where do these values come from?" (com exemplo como *placeholder*); botão primário "Create version" | origem vazia: `st.error` "Provenance is required." |
| Sobrescrever | `st.divider`; `st.subheader` "Override factors in one of your versions"; "Your version"; `st.columns([2, 1])`: "Material" ("<IDM> · <DsM>") e "kg CO₂e per unit"; "Provenance of this value"; botão "Save factor"; tabela dos valores sobrescritos | só aparece se houver versão do usuário |

#### 4.4.7 Export

| Bloco | Primitiva | Conteúdo |
|---|---|---|
| Cabeçalho | | §6 deste documento |
| Explicação | `st.write` | "Every exported set is self-contained: the results, and exactly the parameters that produced them. Whoever receives the file can redo the arithmetic without this program." |
| Formatos | `st.multiselect` "Formats" | XLSX, CSV (zip), HTML, PDF; padrão XLSX e HTML |
| Convenção CSV | `st.radio` horizontal "CSV convention" | "Brazilian — ; separator, , decimal" (padrão) ou "ISO — , separator, . decimal (R, Python, Stata)" |
| Bloqueio | `st.error` e o painel de validação completo | só se houver erro de validação; a tela para |
| Botão | botão primário "Generate and export all tables" | sequência do §6.1, com `st.spinner` "Recalculating and building the tables…" |
| Resultado | `st.success` "N tables, M rows, built at HH:MM:SS." e um `st.download_button` por arquivo | sem WeasyPrint: `st.info` explicando que o HTML imprime o mesmo documento |
| Índice | `st.divider`; `st.subheader` "What comes out"; tabela Tabela, Conteudo, Linhas, Colunas (`R00`…`R44`); `st.caption` sobre tabela vazia | |

### 4.5 Cadastro de veículo pelo usuário

Ao criar um veículo, o programa:

1. pede trem de força, carroceria, porte e classificação (`D01`);
2. pré-preenche `D03` a partir de um veículo existente do mesmo trem de força, marcando os valores herdados;
3. exige que todo `IDVP` exógeno aplicável (`P07.AppliesTo`) seja confirmado;
4. calcula os endógenos e exibe a massa resultante antes de salvar;
5. grava com `IsUserDefined = 1`, o que mantém os doze veículos de referência intactos e distinguíveis.

Na versão 0.9.0, os passos 3 e 4 ainda não estão implementados (§4.9).

### 4.6 Versões de fatores criadas pelo usuário

A tela **Emission factors** implementa o mecanismo do §16.4 do Documento 1:

1. o usuário escolhe uma versão da base como ponto de partida (`BasedOnIDEFV`);
2. dá um nome à sua versão e **declara a origem dos valores** — campo obrigatório;
3. altera apenas os materiais que quer mudar; os demais herdam a versão base;
4. a versão passa a estar disponível em **Scenario**, marcada como definida pelo usuário;
5. tudo fica no arquivo de projeto. A base de referência não é alterada em nenhum momento.

Esse é também o caminho pelo qual os fatores do **Projeto Berço ao Portão (FGV/Unicamp — Fundep / Programa Move)** podem ser usados antes de sua incorporação definitiva à base.

### 4.7 Sistema visual

A tabela completa de *tokens* — cores nos temas claro e escuro, tipografia, espaçamentos, raios e dimensões, cada um com sua nota de uso — está em `docs/interface/sistema-visual/tokens.json`, e as regras de uso em `docs/interface/sistema-visual/README.md`. As cores do Streamlit foram amostradas do aplicativo em execução (0.9.0, Streamlit 1.41.1); as demais vêm do código.

**Cor.**

| Papel | Claro | Escuro | Onde vive |
|---|---|---|---|
| Destaque (`primaryColor`) — botão primário, rádio e caixa marcados, abas, *chips*, links | `#2a78d6` | `#2a78d6` | `.streamlit/config.toml` |
| Fundo da área principal | `#ffffff` | `#0e1117` | padrão do Streamlit |
| Barra lateral e campos | `#f0f2f6` | `#262730` | padrão do Streamlit |
| Texto | `#31333f` | `#fafafa` | padrão do Streamlit |
| Legendas (`st.caption`) | texto a 60% | texto a 60% | padrão do Streamlit |
| Código em linha (identificadores) | `#09ab3b` sobre `#f8f9fb` | `#09ab3b` sobre `#1a1c24` | padrão do Streamlit |
| Série 1 a 7 dos gráficos | `#2a78d6` `#eb6834` `#1baf7a` `#eda100` `#e87ba4` `#008300` `#4a3aa7` | `#3987e5` `#d95926` `#199e70` `#c98500` `#d55181` `#008300` `#9085e9` | `core/export.py` (`PALETA_CLARA`, `PALETA_ESCURA`) |
| Outros; total da cascata | `#898781`; `#52514e` | idem | `core/export.py`; `ui/components.py` |

Regras:

- `primaryColor` é a **única** cor de destaque da interface, e coincide com a série 1 dos gráficos: o controle e a barra falam a mesma cor;
- **vermelho é reservado ao erro de validação**. O Streamlit usa vermelho como cor primária por padrão; a troca é deliberada, porque um botão de rádio não deveria parecer um alarme;
- o verde do código em linha é o estilo do Streamlit para identificadores e não significa sucesso;
- as séries dos gráficos seguem ordem fixa — a ordem é o mecanismo de segurança para daltonismo —, nunca são reordenadas nem cicladas; da oitava categoria em diante, tudo vai para "Outros";
- na tela, grade e eixo dos gráficos são cinzas translúcidos (`rgba(128,128,128,0.25)` e `0.55`), para servir aos dois temas sem troca; o relatório tem neutros próprios e troca de tema por `prefers-color-scheme`.

**Tipografia.** Tela: Source Sans Pro (a fonte que o Streamlit embute com `font = "sans serif"`) e Source Code Pro para código. Relatório: fonte do sistema. Escala da tela: título 44 px (700), subtítulo 28 px (600), texto 16 px, rótulos, legendas e rótulos de métrica 14 px, valor de métrica 36 px, código em linha 12 px.

**Layout.** Barra lateral de 336 px; área principal com margens de 80 px nas laterais e 96 px no alto (layout *wide*); blocos e colunas separados por 16 px; raio de 8 px em campos, botões e alertas. Largura de referência das capturas: 1440 px.

**O que é ajustável sem CSS injetado:** as cores e a fonte do tema (`[theme]` do `.streamlit/config.toml`), as cores dos gráficos (`ESTILO_GRAFICO` e `core/export.py`), e a ordem, as colunas e os textos de cada tela (`pages/`). Raio, altura dos campos e cores dos alertas são do Streamlit; o projeto não injeta CSS.

### 4.8 Como a interface é documentada e alterada

Os arquivos de `docs/interface/`:

| Caminho | O que é |
|---|---|
| `telas/0_Home_sem_projeto.png` e `telas/1_Home.png` … `telas/7_Export.png` | capturas da 0.9.0 a 1440 px de largura, no estado de referência |
| `sistema-visual/tokens.json`, `sistema-visual/README.md` | o sistema visual completo e suas regras |
| `canvas/` | as pranchetas editáveis das sete telas, no formato do Claude Design (`.dc.html` e `canvas.json`) |

**A referência é este capítulo, junto com o código.** As pranchetas de `canvas/` são a superfície de trabalho para propor ajustes visuais — cor, tamanho, ordem, texto — e ficam também publicadas no Claude (artefatos "Telas da Calculadora Berço ao Portão" e "i3ET Calculator"). Elas não são necessárias para reconstruir a interface: tudo o que definem precisa estar dito aqui.

**Fluxo de uma alteração:** ajustar ou comentar a prancheta → levar a mudança ao código (`.streamlit/config.toml`, `ui/components.py`, `core/export.py` ou `pages/`) → atualizar este capítulo, o `tokens.json` e as capturas → atualizar as pranchetas para voltarem a coincidir com o aplicativo.

### 4.9 Divergências entre a especificação anterior e a versão 0.9.0

A revisão deste capítulo, feita em 21/09/2026 a partir do aplicativo em execução, encontrou seis pontos em que o texto anterior e o programa não coincidiam.

| # | Especificação anterior | Versão 0.9.0 | Tratamento |
|---|---|---|---|
| 1 | Painel de validação "lateral" | abaixo da version bar, compacto | texto corrigido (§4.3) |
| 2 | Export com "escolha entre XLSX e CSV" | XLSX, CSV (zip), HTML e PDF | texto corrigido (§4.4.7) |
| 3 | "How was this number calculated?" em qualquer célula de resultado | um expander por bloco (massa de um subgrupo; emissões de um grupo) | **pendência** — decidir entre ampliar o programa e restringir a especificação |
| 4 | Vehicles permite "criar, duplicar e editar" | cria (por cópia) e remove; a edição é feita em Vehicle parameters | texto corrigido (§4.4.2) |
| 5 | Cadastro: confirmar os exógenos aplicáveis e mostrar a massa antes de salvar (§4.5, passos 3 e 4) | não implementado | **pendência** para a 1.0.0 |
| 6 | Glossário `docs/glossario.md` | não existe | **pendência** para a 1.0.0 |

---

## 5. Especificação das saídas

### 5.1 Princípios

1. **Uma aba por tabela**, com a primeira linha de cabeçalho e as colunas na ordem do dicionário;
2. **Autoexplicativa fora do banco**: toda tabela de resultado repete `IDMPV`, `IDVMR`, `IDEFV`, `IDAPV` e `Boundary`;
3. **Insumos junto do resultado**: as tabelas detalhadas trazem `MshareGG`, `EF`, `Beta`, `GCR`, `MR` — quem abrir o arquivo consegue refazer a conta;
4. **Metadados sempre**: a aba `R00` traz data, hora, versão do programa, *hash* da base e situação da validação.

### 5.2 Tabelas de saída

| Tabela | Conteúdo | Origem | Chave |
|---|---|---|---|
| `R00` | Metadados da execução | `M01` | — |
| `R01` | Veículos e cenários | `D01 ⋈ D02` | `IDV`, `IDEA` |
| `R02` | Parâmetros do veículo | `D03 ⋈ P07` | `IDV`, `IDVP` |
| `R03` | Massa por subgrupo, com `Beta`, `GCR`, `MR`, `GC`, `fLM` | `C01 ⋈ P02 ⋈ P06` | `IDV`, `IDEA`, `IDSG` |
| `R04` | Massa por grupo GREET | `C02 ⋈ P04` | `IDV`, `IDEA`, `IDGG` |
| `R05` | Massa e GEE por material e grupo, com `MshareGG` e `EF` | `C03 ⋈ P04 ⋈ P09` | `IDV`, `IDEA`, `IDGG`, `IDM` |
| `R06` | Massa e GEE da bateria por material, com `BMshareGG` e `EF` | `C07 ⋈ P04 ⋈ P09` | `IDV`, `IDEA`, `IDBMd`, `IDGG`, `IDM` |
| `R07` | Massa e GEE por grupo | `C10 ⋈ P04` | `IDV`, `IDEA`, `IDGG` |
| `R08` | Massa e GEE por material | `C11 ⋈ P09` | `IDV`, `IDEA`, `IDM` |
| `R09` | GEE da montagem por processo | `C13 ⋈ P21` | `IDV`, `IDEA`, `IDAP` |
| `R10` | **Total berço ao portão** | `C14` | `IDV`, `IDEA` |
| `R11` | Log de validação | `M02` | — |
| `R20`–`R44` | Fotografia das tabelas de parâmetros efetivamente usadas (`P01` a `P25`) | `P*` | conforme cada tabela |

`C03` e `C07` já trazem massa e emissão na mesma tabela — o que a numeração
original do i3ET separava em `C08`/`C09`. A correspondência está declarada em
`core/report.py`, e as tabelas de montagem completam a faixa: `R39`=`P21`,
`R40`=`P22`, `R41`=`P23`, `R42`=`P24`, `R43`=`P25`.

O corte de "apenas as linhas utilizadas" aplica-se onde o cenário nomeia uma
chave: versão de parâmetros de massa, receita, versão de fatores, versão de
montagem e modelo de bateria. As tabelas de dimensão que nenhum cenário
seleciona — dicionário de dados, lista de materiais, listas de grupos — viajam
inteiras: são pequenas, e cortá-las deixaria descrições órfãs.

`R27` (versões de fatores de emissão) traz `P10` e `D04` na mesma tabela, com uma coluna `IsUserDefined` — quem recebe o arquivo vê imediatamente quais fatores vieram da base e quais foram criados por quem fez a análise.

As tabelas `R20` em diante contêm apenas as linhas utilizadas pelos cenários exportados — não a base inteira. Isso mantém o arquivo pequeno e, mais importante, torna o conjunto exportado **autossuficiente**: quem o recebe tem os resultados e exatamente os parâmetros que os geraram.

### 5.3 Mapeamento em relação ao `Results_ALL_tables` original

O arquivo `Results_ALL_tables_20260919a.xlsx` usa as abas `T01` a `T29`, numeradas sem relação com as tabelas `P`, `D` e `C`, o que obriga quem lê a decorar a correspondência. A tabela abaixo é o mapeamento e fica publicada junto com as saídas.

| Antiga | Conteúdo | Nova |
|---|---|---|
| `T01` | Parâmetros de estimativa de massa | `R21` (= `P06`) |
| `T02` | Versões de parâmetros de massa | `R20` (= `P05`) |
| `T03` | Correlação subgrupo → grupos | `R23` (= `P08`) |
| `T04` | Grupos genéricos | `R22` (= `P03`) |
| `T05` | Grupos GREET | `R24` (= `P04`) |
| `T06` | Lista de parâmetros do veículo | `R25` (= `P07`) |
| `T07` | Lista de veículos | `R01` (= `D01`) |
| `T08` | Valores dos parâmetros | `R02` (= `D03`) |
| `T09` | Massa por subgrupo | `R03` (= `C01`) |
| `T10` | Lista de materiais | `R26` (= `P09`) |
| `T11` | Versões de fatores de emissão | `R27` (= `P10`) |
| `T12` | Fatores de emissão | `R28` (= `P11`) |
| `T13` | Trens de força | `R29` (= `P12`) |
| `T14` | Tipos de carroceria | `R30` (= `P13`) |
| `T15` | Portes | `R31` (= `P14`) |
| `T16` | Receitas de materiais | `R32` (= `P15`) |
| `T17` | Composição por grupo | `R33` (= `P16`) |
| `T18` | Massa e GEE por grupo | `R07` (= `C10`) |
| `T19` | Massa e GEE por material e grupo | `R05` (= `C09`) |
| `T20` | Massa e GEE por veículo | `R10` (= `C12`/`C14`) |
| `T21` | Massa e GEE por material | `R08` (= `C11`) |
| `T22` | Tipos de bateria | `R34` (= `P17`) |
| `T23` | Tecnologias de bateria | `R35` (= `P18`) |
| `T24` | Modelos de bateria | `R36` (= `P19`) |
| `T25` | Composição da bateria | `R37` (= `P20`) |
| `T26` | Dicionário de dados | `R44` (= `P01`) |
| `T27` | Subgrupos | `R38` (= `P02`) |
| `T28` | Veículos e critérios de avaliação | `R01` (= `D01 ⋈ D02`) |
| `T29` | Massa e GEE da bateria por material | `R06` (= `C08`) |
| — | *(novo)* GEE da montagem por processo | `R09` (= `C13`) |
| — | *(novo)* Log de validação | `R11` |
| — | *(novo)* Metadados da execução | `R00` |

Quatro problemas do arquivo original ficam resolvidos: a numeração passa a ser mnemônica; `T26` deixa de ser uma cópia desatualizada do dicionário; `T24` deixa de conter `inf`; e as abas redundantes (`T18` e `T20`, `T19` e `T21`) passam a ter papéis distintos e declarados.

---

## 6. Exportação

### 6.1 O botão

Uma única ação — **"Gerar e exportar todas as tabelas"** — executa:

```
1. recalcular tudo a partir de D (nunca exportar cache)
2. rodar os invariantes I1..I15
3. se houver ERRO: interromper e exibir; nada e exportado
4. montar R00..R44
5. gerar os formatos escolhidos (XLSX, CSV, HTML, PDF)
6. gravar os arquivos e oferecer o download
```

Exportar sempre recalcula. Um arquivo que sai da calculadora corresponde, por construção, ao estado atual dos dados — nunca a um resultado anterior.

### 6.2 Formatos

| Formato | Estrutura | Quando usar |
|---|---|---|
| **XLSX** | Um arquivo, uma aba por tabela `R`, cabeçalhos congelados, colunas dimensionadas, números sem formatação de máscara (valor cheio) | Leitura humana, conferência |
| **CSV** | Um arquivo `.zip` com um `.csv` por tabela, `UTF-8` com BOM, separador `;`, decimal `,` (configurável para `.` e `,`) | Reprocessamento, importação em R/Python/Stata, versionamento |
| **HTML** | Arquivo único autocontido: CSS embutido, gráficos como SVG inline, tabelas navegáveis, sem dependência externa | Circular resultados sem exigir Excel; abre em qualquer navegador |
| **PDF** | Gerado a partir do mesmo HTML, com paginação, cabeçalho, rodapé e numeração | Anexo de artigo e de relatório de política pública |

### 6.2.1 HTML e PDF

Os dois formatos compartilham o mesmo conteúdo e o mesmo gerador, o que evita que divirjam:

```
R00..R44  ──►  modelo HTML (Jinja2)  ──►  relatorio.html  ──►  WeasyPrint  ──►  relatorio.pdf
```

O relatório narrado traz, nesta ordem: identificação da execução e versões usadas; resultado do berço ao portão por veículo; decomposição por grupo GREET e por material; a etapa de montagem; o resultado da validação; e as tabelas completas em anexo. Diferente do XLSX, que é uma coleção de tabelas, o HTML e o PDF são um **documento que se lê** — e por isso cada seção traz a equação aplicada, para manter a função didática fora da aplicação.

**Nota de implementação.** O WeasyPrint depende de bibliotecas de sistema (Pango, Cairo), que no Streamlit Community Cloud são declaradas em `packages.txt`. Se a instalação falhar no ambiente de publicação, o HTML continua disponível e o PDF é gerado sob demanda pelo próprio navegador (imprimir para PDF), com o CSS de impressão já previsto. O núcleo não depende de nenhum dos dois: quem escreve arquivos é `core/export.py` — `core/report.py` só monta tabelas, e `core/charts.py` só devolve SVG como texto — e a ausência da biblioteca degrada o recurso, nunca o cálculo.

**Os gráficos.** São SVG embutido, gerado por `core/charts.py`: sem biblioteca de
plotagem, sem imagem externa, sem requisição. Duas formas, para as duas
perguntas que o relatório responde — barras horizontais de série única para o
total por veículo (rótulo direto em cada barra, sem legenda, porque o título já
nomeia a série) e barras empilhadas para a composição por grupo GREET (legenda
sempre presente, 2 px de superfície entre segmentos, valor de cada segmento ao
passar o cursor). As cores vêm de uma paleta categórica validada para
daltonismo, em ordem fixa, declarada como variáveis CSS uma única vez: a partir
da oitava categoria não há tom novo, o excedente vira “Outros”. Os dois modos,
claro e escuro, são escolhidos — o escuro não é uma inversão automática.

Nome do arquivo: `Resultados_<projeto>_<AAAAMMDD><letra>.xlsx`, seguindo a diretriz D6. A letra avança automaticamente quando já existe um arquivo do mesmo dia.

### 6.3 Precisão

Os números são exportados com a precisão completa do `float64`. Arredondamento é decisão de quem usa o resultado, não da ferramenta — e arredondar na exportação impediria a validação na tolerância de 10⁻⁶ exigida pelo Documento 1.

---

## 7. Testes e validação

### 7.1 Camadas de teste

| Camada | O que verifica | Arquivo |
|---|---|---|
| Unitários | Cada equação isoladamente, com casos de mão | `tests/test_equations.py` |
| Invariantes | I1 a I13 sobre a base de referência | `tests/test_invariants.py` |
| Aderência | Comparação com o i3ET nos doze veículos | `tests/test_i3et_reference.py` |
| Regressão | Resultados congelados: qualquer mudança numérica precisa ser deliberada | `tests/test_regression.py` |
| Aderência (emissões) | Fluidos, baterias e materiais, onde a massa já coincide | `tests/test_ghg_reference.py` |
| Borda | Veículo sem bateria, `GC = 0`, `Beta = 0`, receita incompleta, `EF` ausente | `tests/test_edge_cases.py` |
| Saídas | Tabelas `R`, reconciliação com os totais, XLSX, CSV, HTML e os gráficos | `tests/test_report.py` |
| Telas | Cada tela abre com e sem projeto, e as ações que gravam fazem o que dizem | `tests/test_app.py` |
| Esquema 0.10 | *(0.10)* Banco vazio e arquivo migrado chegam ao mesmo esquema; a migração não muda dado nem resultado; as restrições do banco; o dicionário e o DDL têm as mesmas colunas | `tests/test_schema_010.py` |
| Fixtures da Fase A | *(0.10)* Contagens e valores da base contra o levantamento da planilha; os fatores arbitrados reproduzem as potências gravadas (`tests/test_power_rule.py`); projeto antigo recebe os parâmetros sem mudar resultado | `tests/test_fixtures_fase_a.py` |

Os testes de aderência separam massa de emissões de propósito. A massa é o
módulo M1: 39 configurações exatas, 28 explicadas pelo fator de leveza (M5, fora
de escopo), 5 pela lista de exclusão do módulo híbrido, nenhuma sem explicação.
As emissões são o módulo M2, e reproduzem o i3ET nos doze veículos do projeto —
`ICEV` e `BEV` na precisão da máquina, híbridos com resíduo de 3 × 10⁻⁵, de
origem conhecida e registrada no Documento 5.

A comparação usa a receita de materiais que a planilha nomeia para cada
configuração, e não uma deduzida do trem de força: a *fixture* registra esse
nome, e um teste verifica que os cenários da base o respeitam.

### 7.1.1 Como rodar

```
python -m pytest -q              # a suite inteira, poucos segundos
python tools/validate_core.py    # o quadro de aceitação contra o i3ET
python tools/report_divergences.py   # regenera o Documento 5
python tools/freeze_regression.py    # recongela os resultados (mudança deliberada)
python tools/export_results.py       # gera XLSX, CSV, HTML e PDF em saidas/
```

*(0.10)* Para refazer as fixtures da Fase A a partir da planilha, na ordem: `extract_control_panel`, `extract_m2_inputs`, `import_market_vehicles`, `import_pbev`, `build_default_rules`, `import_ef_versions`, `build_static_tables`, `import_recipes`, `fit_combined_power`, `build_material_equivalence`, `build_generic_battery`, `load_fase_a` e, por fim, `freeze_regression`. O roteiro está no Documento 8, §1. A suíte tem 225 testes. Exportação de rodada e projeto: `python tools/export_run.py projeto.sqlite [--run RUNID]`.

O mesmo conjunto roda a cada `push` no GitHub, por `.github/workflows/tests.yml`.
A aceitação do cálculo é um comando, não a lembrança de ter conferido.

### 7.2 Extração dos valores de referência

`tools/extract_i3et.py` lê `LCA_LV_i3ET_20260919a.xlsx` e grava em `tests/fixtures/` os valores das células listadas em §15.1 do Documento 1. O script é versionado e as *fixtures* também — assim a validação não depende de ter a planilha à mão.

*(0.10)* As fixtures da Fase A vêm de `LCA_LV_i3ET_20261101.xlsx` e ficam na própria base, na tabela `P52_ExcelReferenceValue`, cada valor com a célula de origem. Os scripts leem uma guia por vez (`tools/xlsx_cells.py`), porque a planilha tem 198 guias e mais de 80 MB.

### 7.3 Teste de suficiência da documentação

Conforme §17.3 do Documento 1: implementar o núcleo apenas a partir destes quatro documentos e comparar com o i3ET. Toda lacuna volta para a documentação.

**Quando.** Depois do aplicativo pronto (decisão de 20/09/2026). Fazê-lo agora mediria uma documentação que ainda vai mudar; o valor do teste está em aplicá-lo à versão que será publicada.

---

## 8. Publicação

### 8.1 Passos

```
1. repositorio Git publico no GitHub, com os quatro documentos em docs/
2. LICENSE (MIT), docs/LICENSE (CC BY 4.0) e data/NOTICE.md (termos do GREET)
3. requirements.txt com versoes fixadas
4. Streamlit Community Cloud apontando para app.py na branch main
5. cada push na main republica a aplicacao
6. tags de versao e DOI via Zenodo para citacao academica
```

**Configuração no Streamlit Community Cloud.** Repositório
`paulosplima-netizen/i3et-calculator`, *branch* `main`, arquivo principal
`app.py`, Python **3.12** — a mesma versão da integração contínua, escolhida em
*Advanced settings*. O tema e os limites do servidor ficam em
`.streamlit/config.toml`, versionado junto com o código.

**`packages.txt` contém apenas nomes de pacote**, um por linha, sem
comentários: o arquivo é passado ao `apt-get` da imagem Debian 11 (*bullseye*)
do Community Cloud, e a documentação da plataforma não garante que linhas de
comentário sejam ignoradas. Os quatro pacotes são os que o WeasyPrint 63 pede
(Pango e HarfBuzz) mais uma família de fontes para o PDF. Se falharem, o
cálculo e o HTML não são afetados.

**Versão e DOI.** A primeira *release* registra o DOI. Ela é anterior a `1.0.0`
de propósito: o teste de suficiência da documentação (§7.3), critério de
aceitação da diretriz D3, fica para depois do aplicativo pronto. A `1.0.0` é a
versão que passa nele.

**O repositório é público desde o início.** A decisão não é apenas de conveniência: um repositório público torna verificável a afirmação central do projeto — que a calculadora reproduz o i3ET. Qualquer pessoa pode clonar, rodar os testes de aderência e conferir. Em um repositório privado, a transparência prometida pela diretriz D3 seria uma declaração, não um fato comprovável.

Três cuidados que a abertura impõe:

1. **Nenhum dado não publicável entra no repositório.** Os fatores do Projeto Berço ao Portão só são incorporados depois de confirmada sua condição de publicação;
2. **O `data/NOTICE.md` precisa existir antes do primeiro `push` com dados**, não depois — a condição do Argonne vale desde a primeira redistribuição;
3. **Histórico do Git é permanente.** Um arquivo removido em um *commit* posterior continua acessível no histórico. Na dúvida sobre publicar um dado, ele não entra.

### 8.2 Pendências antes de publicar

| Pendência | Situação |
|---|---|
| Conta GitHub | **resolvida** — conta existente |
| Repositório público ou privado | **resolvido** — público desde o início |
| Licenciamento | **resolvido** — três licenças, ver §8.2.1 |
| Redistribuição dos fatores GREET | **resolvida** — permitida para uso não comercial, sob as quatro condições do §18.3 do Documento 1 |
| Fatores do Projeto Berço ao Portão (FGV/Unicamp — Fundep/Move) | a incorporar como versões `IDEFV` adicionais |
| Conta no Streamlit Community Cloud | **resolvida** — entrada pelo GitHub |
| DOI (Zenodo) para citação | **em andamento** — conta vinculada ao GitHub, repositório listado |
| Aplicativo público ou privado | **decidido em 21/09/2026** — privado, por convite, durante os testes do colaborador; **público a partir da `1.0.0`**, como o repositório |

### 8.2.1 Licenciamento em três camadas

Um único arquivo `LICENSE` não serve a este repositório, porque as três camadas têm origens e restrições diferentes.

| Camada | Arquivo | Licença | Motivo |
|---|---|---|---|
| Código (`core/`, `app.py`, `tools/`, `tests/`) | `LICENSE` | MIT | Autoria própria; permite reúso amplo, inclusive comercial |
| Documentação (`docs/`) | `docs/LICENSE` | CC BY 4.0 | Material didático; exige atribuição, permite adaptação |
| Dados (`data/`) | `data/NOTICE.md` | Termos do GREET — **uso não comercial** | Os fatores derivam do GREET (UChicago Argonne, LLC), que permite redistribuição não comercial mediante aviso, crédito, identificação de versão e declaração de dados modificados |

O `README.md` precisa dizer isso na primeira tela: **o código é livre, os dados não são**. Quem quiser uso comercial troca a versão `IDEFV` — a arquitetura de versões torna isso uma escolha de parâmetro, não uma reescrita.

O `data/NOTICE.md` contém o aviso de direito autoral do GREET, a isenção de responsabilidade, o crédito ao Argonne National Laboratory, as versões utilizadas (`G22`, `G23`, `G24`) e a declaração de que os valores foram **extraídos e processados** a partir do GREET pelo modelo i3ET, não reproduzidos do arquivo original.

### 8.3 Desempenho

Doze veículos, 43 subgrupos e cerca de 100 materiais produzem algumas dezenas de milhares de linhas — irrelevante para pandas e para o SQLite. O limite prático do Streamlit Community Cloud (memória por aplicação) só seria alcançado com milhares de veículos simultâneos, cenário fora do uso previsto. Se ocorrer, o caminho é mover o cálculo para uma API (§1.1 já prevê a separação).

---

## 9. Evolução modular

A calculadora é o primeiro módulo de um caminho que termina no i3ET completo. A ordem proposta segue a dependência de dados, não a numeração dos módulos:

| Etapa | Escopo | O que entra |
|---|---|---|
| **v1** | Berço ao portão | M1 (massa) + M2 (GEE de manufatura) + montagem |
| **v1.1** | Incerteza | Distribuições triangulares do `i3ET Control Panel`; Monte Carlo sobre os parâmetros já existentes |
| **v1.2** | Leveza | Módulo M5: `fLM` deixa de ser 1 e passa a ser calculado |
| **v2** | Uso | Módulos M3 e M4: energia e GEE do berço ao túmulo |
| **v2.1** | Custo | Módulo M6: TCO e LCC |
| **v3** | Frota e política | Cenários de frota, metas, comparações de política pública |

Duas decisões desta versão foram tomadas pensando nessas etapas:

- `fLM` já existe em `P06`, fixado em 1. Quando o módulo M5 entrar, nenhuma equação muda — apenas o parâmetro passa a ser alimentado;
- toda versão de parâmetros (`IDMPV`, `IDVMR`, `IDEFV`, `IDAPV`) é chave. Acrescentar uma dimensão nova — por exemplo, um cenário de rede elétrica — é acrescentar uma versão, não reescrever o modelo.

### 9.1 Recomendações de ferramental para as próximas etapas

| Hoje | Recomendação | Ganho |
|---|---|---|
| Word (`.docx`) | Markdown versionado | Diferença linha a linha, revisão por *pull request*, geração de PDF e site |
| Excel como base de dados | SQLite (já adotado nesta versão) | Integridade relacional verificável, consultas, sem fórmulas ocultas |
| Excel como interface de cálculo | Python + Streamlit | Cálculo auditável, testável e reproduzível |
| Netlify | Streamlit Community Cloud | Executa Python |
| Planilha única de 81 MB | Repositório Git com dados em CSV | Histórico, autoria, revisão, tamanho gerenciável |
| Documentação separada do código | `docs/` no mesmo repositório | A documentação versiona junto com o que ela descreve |
| — | DOI via Zenodo | Citabilidade acadêmica |
| — | Integração contínua (GitHub Actions) | Os testes de aderência ao i3ET rodam a cada alteração |

A migração da planilha para o par SQLite + Python não é uma troca de ferramenta por gosto: é o que torna possível afirmar, com verificação automática, que a calculadora reproduz o i3ET — afirmação que uma planilha de 190 abas não permite sustentar.

---

## 10. Fase A — estado em 16/11/2026

A tabela de evolução do §9 foi escrita em setembro. Em 16/11/2026 o autor adotou as Interfaces Revisadas T01–T46 como especificação-alvo, em três fases: **A** (0.10.0), navegação, projeto e análise; **B**, os demais módulos, um por vez; **C**, contas, projetos no servidor e compartilhamento. O plano de telas e tabelas vive no Monday e tem cópia datada em `PlanoTelasETabelas_i3ETCompleto`.

A arquitetura do §1 não muda nas Fases A e B. A Fase C acrescenta um banco externo e autenticação por provedor (OpenID Connect); o núcleo continua o mesmo, porque não depende da interface nem da persistência.

| Passo | Entrega | Situação | Documento |
|---|---|---|---|
| 1 Documentação | Especificação da Fase A | Concluído | 6 |
| 2 Base e esquema | Esquema 0.10, migração, carregador | Concluído | 7 |
| 3 Fixtures | Scripts de extração, CSV, base reconstruída, receitas do GREET 2024 | Concluído em 17/11 | 8 |
| 4 Núcleo | `power_rule`, `project`, `analysis`, `control_params`, `run`, `provenance`; regras I16 a I23 | Feito em 17/11 | — |
| 5 Testes | Matriz de paridade (Doc. 6, §9) | Feito em 17/11 | 217 testes |
| 6 Saídas e exportação | `R45`, `R46`, exportação das rodadas | Feito em 17/11 | 225 testes |
| 7 Telas | T01 a T11 e T41, quatro menus, glossário | Por fazer | — |
| 8 Publicação | 0.10.0, com DOI | Por fazer | — |

**O que já mudou no código** (nada foi publicado; a versão em produção é a 0.9.0):

- `core/schema.py`: blocos S5 a S10;
- `core/loader.py`: lê as tabelas da 0.10 quando existem;
- `pages/2_Vehicles.py`: só oferece motorizações e carrocerias calculáveis;
- `tools/`: dez arquivos novos (§2);
- `data/base_referencia.sqlite`: reconstruída, com novo `ParamBaseHash`;
- `tests/`: dois arquivos novos e o arquivo de regressão recongelado (mesmos resultados, novo hash).

**O que ainda vale da 0.9.0 e vai mudar no passo 4:** a potência combinada (`IDVP 15`) ainda é fixa quando `core/params.resolve` roda sem `power_factors`. O módulo `core/power_rule.py` (17/11) fornece os fatores, lidos de `P53`, `P56` e `D12`; a ligação ao cálculo dos casos vem com `core/analysis.py` e `core/run.py`.

**Pendências antes de publicar a 0.10.0**, além das do §8.2:

1. modelos de bateria do GREET 2024 em `P19` e `P20`, sem os quais a rodada gravada não é reproduzida (Doc. 5a, D6);
2. termos de uso dos licenciamentos por veículo que a base agora contém (`data/NOTICE.md`, §5);
3. licença de redistribuição das listas `BR23` e `GLO23`;
4. glossário português–inglês (`docs/glossario.md`), ainda não escrito;
5. pacote HTML de revisão das telas gerado a partir das fixtures, para não haver segunda fonte de dados.

---

*Documento gerado em 19/09/2026 — versão `a`. Revisto em 16 e 17/11/2026 (cabeçalho, §1.3, §2, §4.4.2, §7 e §10).*
