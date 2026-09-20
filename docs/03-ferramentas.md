# Ferramentas do Projeto
## Calculadora da Pegada de Carbono de Veículos Leves — do Berço ao Portão

**Anexo à documentação** · Versão `20260919a` · Projeto NIPE/UNICAMP

Inventário completo das ferramentas do projeto: o que instalar no computador, que contas manter, que bibliotecas o programa usa e o que cada uma faz. Este documento é anexo dos quatro documentos principais, não um quinto documento da especificação.

---

## 1. Para instalar no computador

### 1.1 Essenciais

| # | Ferramenta | Função no projeto | Onde obter | Licença |
|---|---|---|---|---|
| 1 | **Positron** | Editor principal. Escrever o código, rodar o Streamlit, inspecionar DataFrames e o banco SQLite, versionar com Git — tudo na mesma janela | `positron.posit.co/download` | Elastic License 2.0 (*source-available*, gratuito) |
| 2 | **Python 3.12 ou 3.13** | Linguagem do programa. Marcar "Add Python to PATH" na instalação | `python.org/downloads` | PSF (livre) |
| 3 | **Git for Windows** | Controle de versão e publicação. O editor usa, mas não instala | `git-scm.com/download/win` | GPL-2.0 |

**Alternativa ao item 1:** **VS Code** (`code.visualstudio.com`, licença MIT no código-fonte), caso a licença *source-available* do Positron ou a ausência de extensões da Microsoft incomode. Neste caso, instalar as extensões *Python*, *Jupyter*, *SQLite Viewer* e *GitLens*. A diferença é de conforto — o Positron traz painel de variáveis, explorador de dados, navegador de bancos e fluxo integrado para Streamlit; o VS Code não.

### 1.2 Opcionais

| Ferramenta | Quando ajuda | Licença |
|---|---|---|
| **DB Browser for SQLite** (`sqlitebrowser.org`) | Abrir e editar o banco fora do editor, com interface de planilha. O Positron já faz a leitura | GPL / MPL |
| **GitHub Desktop** (`desktop.github.com`) | Se preferir botões a linha de comando para *commit* e *push* | MIT |

### 1.3 Já instalados, e que permanecem

| Ferramenta | Papel daqui em diante |
|---|---|
| **Excel** | Ler os arquivos de origem (`LCA_LV_i3ET`, `LVManufacturingMassGHGSimulator`) e conferir as exportações. **Deixa de ser** a ferramenta de cálculo e de base de dados |
| **Word** | Nenhum papel no projeto. A documentação é Markdown |
| **Navegador** (Chrome ou Edge) | Abrir o aplicativo, local e publicado, e os relatórios HTML |
| **Anaconda / Spyder** | Opcional, para exploração de dados com o *variable explorer*. Não usar como ambiente do projeto — ver §3.1 |

---

## 2. Contas e serviços na nuvem

| Serviço | Função | Custo | Situação |
|---|---|---|---|
| **GitHub** | Repositório público do projeto; origem da publicação | Gratuito | Conta existente |
| **Streamlit Community Cloud** (`share.streamlit.io`) | Hospedagem do aplicativo. Login com a conta do GitHub; publica a cada `push` | Gratuito | A criar |
| **GitHub Actions** | Integração contínua: roda os testes de aderência ao i3ET a cada alteração | Gratuito em repositório público | A configurar |
| **Zenodo** (`zenodo.org`) | DOI para citação acadêmica de cada versão publicada; integra-se ao GitHub | Gratuito | Recomendado |

Nenhum serviço pago, nenhuma chave de API, nenhuma dependência externa em tempo de execução.

---

## 3. Bibliotecas Python

### 3.1 Ambiente

O projeto usa um **ambiente virtual próprio**, em `repo/.venv`, criado com o módulo `venv` da biblioteca padrão. Não usar o ambiente base do Anaconda: o `requirements.txt` precisa listar exatamente o que o aplicativo usa, e num ambiente compartilhado é trabalhoso descobrir isso. Com um ambiente enxuto, a lista é automática.

### 3.2 Bibliotecas de execução — `requirements.txt`

| Biblioteca | Função | Licença |
|---|---|---|
| **streamlit** | Interface web do aplicativo | Apache-2.0 |
| **pandas** | Tabelas em memória e junções relacionais | BSD-3-Clause |
| **numpy** | Aritmética vetorial (dependência do pandas, declarada explicitamente) | BSD-3-Clause |
| **openpyxl** | Leitura das planilhas de origem e escrita das exportações XLSX | MIT |
| **altair** | Gráficos declarativos; acompanha o Streamlit | BSD-3-Clause |
| **jinja2** | Modelo do relatório HTML | BSD-3-Clause |
| **weasyprint** | Conversão do relatório HTML em PDF | BSD-3-Clause |

**Da biblioteca padrão, sem instalar:** `sqlite3` (banco de dados), `csv`, `zipfile`, `hashlib` (impressão digital da base), `uuid`, `datetime`, `pathlib`.

### 3.3 Bibliotecas de desenvolvimento — `requirements-dev.txt`

| Biblioteca | Função | Licença |
|---|---|---|
| **pytest** | Testes: invariantes, aderência ao i3ET, regressão, casos de borda | MIT |
| **pytest-cov** | Cobertura dos testes | MIT |
| **ruff** | Verificação de estilo e formatação automática, em uma ferramenta só | MIT |

### 3.4 Dependências de sistema — `packages.txt`

O WeasyPrint precisa de bibliotecas de sistema, declaradas para o Streamlit Cloud instalar:

```
libpango-1.0-0
libpangoft2-1.0-0
libharfbuzz0b
libcairo2
libgdk-pixbuf-2.0-0
```

Se a instalação falhar no ambiente de publicação, o HTML continua disponível e o PDF sai pelo "imprimir para PDF" do navegador, com o CSS de impressão já previsto. O cálculo nunca é afetado.

### 3.5 Versões fixadas

Todas as bibliotecas entram no `requirements.txt` com versão exata (`==`), não com faixa. Um resultado só é reproduzível se o ambiente também for. As versões são revistas deliberadamente, em uma alteração própria, com os testes de regressão confirmando que nenhum número mudou.

---

## 4. Ferramentas substituídas

| Antes | Agora | Motivo |
|---|---|---|
| Netlify | Streamlit Community Cloud | O Netlify não executa Python |
| Excel como base de dados | SQLite | Integridade relacional verificável, sem fórmulas ocultas |
| Excel como motor de cálculo | Python | Cálculo auditável, testável e reproduzível |
| Word | Markdown | Diferença linha a linha, revisão por *pull request*, gera PDF e site |
| Planilha única de 81 MB | Repositório Git com dados em CSV e SQLite | Histórico, autoria, revisão, tamanho gerenciável |

O Excel permanece como **leitor**: os arquivos de origem continuam sendo dele, e as exportações em XLSX são feitas para serem abertas nele.

---

## 5. Uma ferramenta que não usaremos nesta etapa

Assistentes de escrita de código (Copilot, Codex e semelhantes) ficam de fora enquanto o núcleo de cálculo é escrito. A razão é a diretriz **D3**: a documentação precisa ser necessária e suficiente para recriar o programa, e esse critério só se verifica se o programa for efetivamente escrito a partir dela. Código sugerido por um assistente pode estar correto e ainda assim mascarar uma lacuna na documentação — que é justamente o que o teste de suficiência (§17.3 do Documento 1) existe para encontrar.

Depois de validado o núcleo, não há objeção ao uso desses assistentes nas camadas de interface e relatório.

---

## 6. Ordem de instalação e primeira verificação

```
1. Python 3.12 ou 3.13        (marcar "Add Python to PATH")
2. Git for Windows
3. Positron                   (ou VS Code)
4. reiniciar o terminal
```

Verificação, no terminal do editor:

```bash
python --version      # deve responder 3.12.x ou 3.13.x
git --version         # deve responder git version 2.x
```

Em seguida, dentro de `repo/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

*Documento gerado em 19/09/2026 — versão `a`.*
