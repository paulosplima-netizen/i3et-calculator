# i3ET Calculator

Sistema visual da Calculadora da Pegada de Carbono de Veículos Leves do Berço ao Portão (módulos M1 e M2 do i3ET, NIPE/UNICAMP). Ele cobre três superfícies que precisam contar a mesma história: **a tela** (Streamlit), **os gráficos** (SVG gerado por `core/charts.py`) e **o relatório exportado** (HTML e PDF gerados por `core/export.py`).

Os valores vêm do repositório `paulosplima-netizen/i3et-calculator` (commit `825b581`, programa 0.9.0) e, no caso das cores do Streamlit, de amostras do app rodando nos temas claro e escuro. As pranchetas das sete telas estão no canvas **Telas da Calculadora Berço ao Portão**, que usa estes tokens.

## Princípios

- **Didático antes de decorativo.** Cada tela explica o que faz em uma frase (`body`), diz onde está especificada (`caption`: "Specified in docs/01-especificacao-funcional.md, §…") e abre qualquer número de volta à equação que o produziu (expander *How was this calculated?*).
- **Versões sempre à vista.** A barra de versões aparece no alto de toda tela com projeto aberto. Dois resultados só são comparáveis se as versões estiverem declaradas.
- **Tela e arquivo não divergem.** Os gráficos da tela e do relatório saem do mesmo gerador e da mesma paleta. Uma mudança de cor vale para os dois lugares ou para nenhum.
- **Ausência de dado não é zero.** Massa sem fator de emissão publicado é dita em texto toda vez (`caption`), nunca escondida.

## Cor

- `primary` (#2a78d6) é a **única** cor de destaque da interface: botão primário, rádio e caixa marcados, links, foco. É também o slot 1 dos gráficos (`series-1`), então o controle e a barra falam a mesma cor.
- **Vermelho é reservado ao erro de validação** (`alert-error-*`, `report-critico`). O Streamlit usa vermelho como cor primária por padrão; foi trocado de propósito, porque um botão de rádio não deveria parecer um alarme.
- Verde em código (`app-code-text`) é o estilo do Streamlit para identificadores e **não** significa sucesso. Sucesso é `alert-success-*`.
- Alertas por papel: `info` orienta (abra um projeto; veículo de referência é somente leitura), `success` confirma uma ação que gravou, `warning` avisa sem bloquear, `error` bloqueia a exportação.
- Gráficos: `series-1` … `series-7` em ordem fixa, nunca reordenados nem ciclados; a oitava categoria em diante vai para **Outros** em `chart-other`. O total da cascata usa `chart-total`. Grade e eixo na tela são cinzas translúcidos (`chart-grid`, `chart-axis`) para servir aos dois temas sem troca.
- O relatório tem neutros próprios, levemente quentes (`report-*`), e troca para escuro por `prefers-color-scheme`.

## Tipografia

- Tela: **Source Sans Pro** (a fonte que o Streamlit embute com `font = "sans serif"`), **Source Code Pro** para código. Relatório: fonte do sistema, para abrir igual de um pen drive daqui a dez anos.
- Uma escala, sem tamanhos avulsos: `screen-title` 44 · `screen-subheader` 28 · `body` 16 · `widget-label`/`caption`/`metric-label` 14 · `code-inline` 12. Métrica em `metric-value` 36.
- Números em formato brasileiro: ponto de milhar, vírgula decimal (`1.157,7`). Nas métricas, **uma casa decimal e a unidade no rótulo** — "Cradle to gate (kg CO₂e)" / "4.075,0" — para o valor caber inteiro numa coluna estreita. A precisão completa fica nas tabelas e nas exportações.
- Idioma: interface em inglês; documentação, relatório e este sistema em português.

## Layout

A tela é Streamlit: **não há posicionamento livre**. Toda prancheta deve ser montável só com estas primitivas, em ordem vertical:

| Primitiva | Uso nesta calculadora |
|---|---|
| Barra lateral (`st.navigation`) | as sete telas, na ordem da análise |
| `st.title` + `st.caption` | nome da tela e seção do Documento 1 |
| Barra de versões | ver componente VersionBar |
| `st.columns([pesos])` | Home 1,4 : 1; Scenario 1 : 1; métricas 4 × 1; formulários 3 × 1 |
| `st.tabs` | Results: By GREET group · By material · Battery · Assembly |
| `st.expander` | How was this calculated?; avisos de validação |
| `st.form` | Create a vehicle; Create a version of your own |
| `st.divider` | separa blocos de assunto diferente |
| `st.dataframe` / `st.data_editor` | toda tabela; editável só para veículos do usuário |

- Layout `wide`: barra lateral de `sidebar-width` (336px), área principal com margem `space-main-x` (80px) e `space-main-top` (96px). Prancheta de referência: `screen-width` 1440px.
- Blocos empilhados com `space-4` (16px) entre si; colunas com o mesmo intervalo.
- Raio único de `radius-widget` (8px) em campos, botões e alertas — é o do Streamlit e não se muda pela tela.

## O que dá para mudar, e onde

| Ajuste | Onde vira código |
|---|---|
| Cor de destaque, fundo, texto, fonte | `.streamlit/config.toml`, seção `[theme]` (`primaryColor`, `backgroundColor`, `secondaryBackgroundColor`, `textColor`, `font`) |
| Cores e traços dos gráficos na tela | `ESTILO_GRAFICO` em `ui/components.py` |
| Paleta e neutros do relatório | `PALETA_CLARA`, `PALETA_ESCURA` e `TEMPLATE` em `core/export.py` |
| Ordem, colunas, textos de cada tela | `pages/<n>_<Tela>.py` |
| Cabeçalho, barra de versões, painel de validação | `ui/components.py` |

Cores de alerta, raio de 8px e altura dos campos são do próprio Streamlit: mudá-las exige CSS injetado, o que o projeto evita.

## Não sincronizado

- Cores de `warning` e `error` do Streamlit: valores padrão da versão 1.41, não amostrados (nenhuma tela os mostrava no estado de referência).
- Arquivos de fonte não copiados: o Streamlit embute Source Sans Pro; nas pranchetas a fonte vem do Google Fonts como Source Sans 3, a sucessora.
- Componentes: não há biblioteca de componentes no código (é Streamlit). Os cartões abaixo são renderizações estáticas, escritas à mão a partir de `ui/components.py` e `core/charts.py`.
