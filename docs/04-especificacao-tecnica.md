# Especificação Técnica, Arquitetura e Saídas
## Calculadora da Pegada de Carbono de Veículos Leves — do Berço ao Portão

**Documento 4 de 4** · Versão `20260919a` · Projeto NIPE/UNICAMP

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
| `base_referencia.sqlite` | Tabelas `P` — parâmetros de massa, materiais, fatores de emissão, baterias, montagem | Somente leitura. Distribuído com o programa, versionado no repositório |
| `projeto_<nome>.sqlite` | Tabelas `D` (veículos e cenários do usuário), `C` (resultados da última execução) e `M` (metadados e log) | Leitura e escrita. Baixado e carregado pelo usuário |

Na abertura de um projeto, o programa confere o *hash* da base de referência gravado no projeto contra o da base carregada. Divergência gera aviso explícito: os resultados guardados foram produzidos com outros parâmetros.

---

## 2. Estrutura do repositório

```
calculadora-berco-portao/
├─ app.py                       # ponto de entrada Streamlit
├─ requirements.txt
├─ README.md
├─ core/                        # nucleo de calculo — Python puro
│  ├─ __init__.py
│  ├─ schema.py                 # DDL (Documento 2, cap. 10) e criacao da base
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
│  └─ csv/                      # mesma base em CSV, um arquivo por tabela
├─ tests/
│  ├─ test_invariants.py
│  ├─ test_i3et_reference.py    # aderencia numerica ao i3ET
│  └─ fixtures/
├─ docs/                        # os quatro documentos + glossario PT-EN
└─ tools/
   ├─ build_base.py             # gera a base a partir das planilhas de origem
   └─ extract_i3et.py           # extrai do i3ET os valores de referencia
```

### 2.1 Onde o repositório vive

A árvore acima existe em dois lugares, sempre iguais:

| Lugar | Papel | Sincronizado por |
|---|---|---|
| `C:\Users\<usuário>\Projetos\i3et-calculator\` | **Cópia de trabalho**, clonada do GitHub. Todo arquivo gerado é salvo aqui no momento em que é produzido | Git |
| `github.com/paulosplima-netizen/i3et-calculator` | Repositório público | — |
| `...\_Calculadora da Pegada de Carbono do Berço ao Portão\Documentação\` | Documentos datados (`_AAAAMMDDx`), planilhas de origem e a base | OneDrive |

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

**A interface é em inglês.** A documentação permanece em português, e os nomes de tabelas e colunas já eram em inglês — de modo que a tela, o dado e o relatório falam a mesma língua. Um glossário português–inglês dos termos de tela fica em `docs/glossario.md`, para que o material didático em português possa apontar para os rótulos que o usuário vê.

Sete telas, na ordem em que a análise acontece. Cada uma corresponde a um capítulo da especificação funcional, e o link para esse capítulo fica visível na própria tela — é assim que o material didático e o programa ficam amarrados.

| # | Tela | O que faz | Doc. 1 |
|---|---|---|---|
| 1 | **Home** | Abre um projeto existente (`.sqlite`) ou cria um novo; mostra a versão da base e seu *hash* | §1 |
| 2 | **Vehicles** | Lista `D01`; permite criar, duplicar e editar veículos do usuário | §7 |
| 3 | **Vehicle parameters** | Edita `D03`. Campos exógenos editáveis; endógenos exibidos em cinza, com a equação ao lado e recálculo imediato | §7.2 |
| 4 | **Scenario** | Escolhe `IDMPV`, `IDVMR`, `IDEFV`, `IDAPV` e a fronteira (`MAT` ou `MAT_ASM`); explica cada escolha | §3, §6 |
| 5 | **Results** | Massa e GEE por grupo, por material e total; gráfico de cascata do total; tabela detalhada com a conta linha a linha | §8 a §14 |
| 6 | **Emission factors** | Consulta as versões da base e permite criar versões próprias (`D04`/`D05`), herdando de uma versão existente e alterando apenas os materiais desejados | §16.4 |
| 7 | **Export** | Botão único **"Generate and export all tables"**; escolha entre XLSX e CSV | §6 deste documento |

**A receita de materiais é escolha do usuário** (decisão de 20/09/2026). A base
traz as duas famílias que o i3ET traz — a receita original de consultoria
(`BISD*`) e a do Projeto do Berço ao Portão (`PBP_BISD*`), construída sobre a
primeira com informação das montadoras brasileiras. A tela **Scenario** lista as
duas, mostra a procedência de `P15.DsVMR` ao lado de cada uma e traz
pré-selecionada a que o i3ET usa para aquele veículo. Trocar a receita muda o
resultado, então a escolha aparece na *version bar* e em toda exportação.

**Estrutura.** `app.py` declara a navegação e nada mais; cada tela é um script
em `pages/`, na ordem em que a análise acontece. O estado do projeto e os
componentes compartilhados ficam em `ui/`, que importa `core` — nunca o
contrário. Os gráficos da tela saem do mesmo `core/charts.py` que desenha o
relatório exportado, de modo que tela e arquivo não possam divergir.

Elementos presentes em todas as telas:

- **Version bar** no alto: as quatro versões em uso e a fronteira selecionada, sempre visíveis; versões criadas pelo usuário aparecem marcadas;
- **Validation panel** lateral: verde quando todos os invariantes passam; vermelho com a lista de falhas quando não;
- **"How was this number calculated?"**: em qualquer célula de resultado, abre a equação, os insumos com seus índices e a referência bibliográfica.

### 4.2 Versões de fatores criadas pelo usuário

A tela **Emission factors** implementa o mecanismo do §16.4 do Documento 1:

1. o usuário escolhe uma versão da base como ponto de partida (`BasedOnIDEFV`);
2. dá um nome à sua versão e **declara a origem dos valores** — campo obrigatório;
3. altera apenas os materiais que quer mudar; os demais herdam a versão base;
4. a versão passa a estar disponível em **Scenario**, marcada como definida pelo usuário;
5. tudo fica no arquivo de projeto. A base de referência não é alterada em nenhum momento.

Esse é também o caminho pelo qual os fatores do **Projeto Berço ao Portão (FGV/Unicamp — Fundep / Programa Move)** podem ser usados antes de sua incorporação definitiva à base.

### 4.1 Cadastro de veículo pelo usuário

Ao criar um veículo, o programa:

1. pede trem de força, carroceria, porte e classificação (`D01`);
2. pré-preenche `D03` a partir de um veículo existente do mesmo trem de força, marcando os valores herdados;
3. exige que todo `IDVP` exógeno aplicável (`P07.AppliesTo`) seja confirmado;
4. calcula os endógenos e exibe a massa resultante antes de salvar;
5. grava com `IsUserDefined = 1`, o que mantém os doze veículos de referência intactos e distinguíveis.

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

O mesmo conjunto roda a cada `push` no GitHub, por `.github/workflows/tests.yml`.
A aceitação do cálculo é um comando, não a lembrança de ter conferido.

### 7.2 Extração dos valores de referência

`tools/extract_i3et.py` lê `LCA_LV_i3ET_20260919a.xlsx` e grava em `tests/fixtures/` os valores das células listadas em §15.1 do Documento 1. O script é versionado e as *fixtures* também — assim a validação não depende de ter a planilha à mão.

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

*Documento gerado em 19/09/2026 — versão `a`.*
