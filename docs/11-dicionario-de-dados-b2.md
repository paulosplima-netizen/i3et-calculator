# B2 — importações e veículos de referência: especificação, implementação e decisões (atualizada em 23/11/2026)

Estado: **implementado; decisões de 22/11 (4, 5, 9, 13, 14) e de 23/11 (todas as demais; ver 4c) tomadas.** Núcleo, fixtures, esquema 0.12 (S15 e S16), telas T39, T40 e T42 (só master; T40 grava a edição importada e exporta; T42 exporta a comparação para Excel), 528 testes passando (inclui contas e papéis), lint limpo. Os commits até `8145508` (B2b, B2c, docs) estão no GitHub; `9bab60e` (decisão 11), `39637ac` e `3fbeff0` (contas e papéis, 4d) e o commit da conferência de totais da T40 são locais, o `git push` é seu. Falta: a parte do usuário comum da decisão 21 (telas T09–T11), teste manual do autor, `v0.12.0`.

Base: `b2-decisoes-fontes-de-dados` (fontes e termos de uso), `FaseB_Plano_20261121c`, itens do Monday (P47, P48, P60/P59, C33, T39, T40, T42), planilha `LCA_LV_i3ET_20261119.xlsx`, arquivos da pasta Documentação (PBEV INMETRO, FENABRAVE, ANFAVEA).

## 1. Escopo

Já existia (Fase A): `P36`, `P28`, `P55`, `P50` (PBEV), `P26` (154 veículos, `SalesUnits` = licenciamentos de 2025), `P27` (`Avg` nos 6 SELEÇÃO), `P29`, `tools/import_pbev.py`, `tools/import_market_vehicles.py`, `core/vehicle_defaults.py`, T09/T11.
Novo no B2: `P47`, `P48`, `P60`, `P70`, a referência ponderada (C33), leitura dos arquivos de origem, correspondência com o catálogo, telas T39, T40 e T42.

## 2. O que a comparação com os arquivos de origem mostrou

- **PBEV:** mesma edição (24/abr/2026) que a aba da planilha; 717 chaves coincidem sem nenhuma diferença numérica; ~130 chaves diferem só por edição de nome na planilha; 22 chaves duplicadas; 847 registros no PDF contra 843 na planilha. A edição de 25/ago (976 versões) não foi anexada.
- **FENABRAVE:** os volumes de `Most Licensed 2025` coincidem com o informativo Ed. 276 (acumulado até dez/2025) em 82 dos 100 modelos lidos do PDF de forma exata e 9 divididos por motorização (a planilha separa, por exemplo, HR-V e HR-V HEV; a soma das variantes fecha com o PDF: 60.577 + 650 = 61.227); 8 modelos não têm par no catálogo (grafia ou variante: Triton × L200 Triton, Song × Song Pro GL, Yuan × Yuan Plus, Jaecoo 7 × J7, K2500, UK2500, Daily) e 1 difere (BMW X1: 5.367 no PDF, 4.423 no catálogo). As colunas de design, porte, motorização, combustível, massa, MJ/km e montado/importado são manuais e não vêm do PDF.
- **Totais (corrigido em 22/11/2026):** o 2.424.281 da planilha **não é um total**: é a soma dos dois rankings da FENABRAVE (50 automóveis + 50 comerciais leves; 1.872.219 + 552.062), que inclui van e chassi (93.768). O total de mercado do modelo é **2.549.462** (FENABRAVE Ed. 276: autos 1.996.531 + comerciais leves 552.931; `Reference Vehicles!P20:R20`). As seis referências somam 2.008.914 (78,8% do mercado; 82,9% do ranking). O Anuário ANFAVEA 2026 (tabela 2.2.1) dá 2.552.201 (1.997.264 + 554.937), 0,11% acima: o modelo usa a FENABRAVE; a ANFAVEA fica para o módulo de frota.
- **Numeração:** o Monday chama a tabela da ANFAVEA de `P59`, que já é `EquationConstant`; usei `P60`. Segmentos: `P70`.

## 3. Como a planilha calcula os veículos de referência (C33) — reproduzido

`Control Panel!AM9:AR16` lê `Market Vehicles!N228:CZ233`. Cada veículo SELEÇÃO é a média ponderada de **segmentos** (linhas 207–223), cada um definido por (grupo de combustível, motorização ICEV, design, porte), com peso = licenciamentos (coluna L):

| Categoria | Segmentos |
|---|---|
| A0 Hatch C | Hatch Subcompact + Hatch Compact (EG) |
| A1 SUV C | SUV Compact (EG) |
| A2 Sedan CM | Sedan Compact + Midsize + Large (EG) |
| A3 SUV ML | SUV Midsize + SUV Large (EG) |
| A4 PUT L | PUT Large (D) |
| A5 PUT C | PUT Subcompact + Compact (EG) + PUT Midsize (D) |

Grupo de combustível: EG = Flex e Gasolina; D = Diesel; X = demais. Os segmentos Chassis e Van (grupo X) não entram em nenhum SELEÇÃO e servem à cobertura. A área frontal (parâmetro 50) não é média: é `0,85 × largura média × altura média`.

**Paridade:** `core.market_data.reference_params` reproduz os **60 de 60** valores `Avg` (tolerância relativa 1e-6) e a cobertura dos segmentos, 82,87% da soma dos rankings 50+50 de 2.424.281 (célula L226 da planilha) e 78,8% do total de mercado de 2.549.462.

## 4. Implementação

Tabelas (esquema 0.12, bloco S15; `schema.apply_012`; CSV em `data/csv/fase_b`; carga por `tools/load_b2.py`, que não refaz as demais tabelas e portanto não apaga escolhas do master como `P69`):

- `P48_MarketSalesEdition` (IDMSE, fonte FENABRAVE, tipo de período YTD/Month/Range, início, fim, referência do informativo, arquivo, publicada/importada em, nº de registros, `IsAdopted`, nota e, desde 23/11, `BulletinUnitsV` e `BulletinUnitsCL`: semitotais do informativo, soma das linhas lidas de automóveis e de comerciais leves). Fixture: `FEN2025`, acumulado jan–dez/2025, Ed. 276.
- `P47_MarketSales` (por edição: classe V/CL, posição, marca, modelo, chave, `UnitsSource` do informativo, `UnitsAdopted` usado pelo modelo, `IDMV` do catálogo, nota de ajuste, linha da planilha). Fixture: 111 modelos, todos ligados ao catálogo; `UnitsAdopted` = `P26.SalesUnits` em todos; 9 com unidades redistribuídas pelo autor.
- `P60_FleetLicensingTotal` (fonte ANFAVEA ou FENABRAVE, edição, ano, classe, unidades, adotada, fonte, nota). Fixture: emplacamento ANFAVEA 1957–2025 (duas edições do Anuário) e total FENABRAVE 2025 (2.549.462). Ver 4b.
- `P70_ReferenceSegment` (categoria, design, porte, grupo de combustível, motorização, linha da planilha). Fixture: 17 segmentos, 12 ligados a categorias.
- As quatro entram em `EDITORIAL_TABLES` (fora do `ParamBaseHash`; hash da base inalterado) e **não são copiadas para os arquivos de projeto** (o dado da FENABRAVE não circula com os projetos).

Módulos: `core/market_data.py` (MD1 nomes e chaves; MD2 informativo da FENABRAVE; MD3 tabela do PBEV; MD4 correspondência com o catálogo, status exact/split/differs/none; MD5 referência ponderada C33; MD6 cobertura; MD7 comparação de uma edição do PBEV com a base), `tools/import_fenabrave.py`, `tools/load_b2.py`, `ui/master.py`.
Telas (menu Auxiliary Data; conteúdo só para quem entrou com conta Master (T01, ver 4d)): **T39 PBEV import** (edições da base, vínculo com os veículos, comparação de um PDF novo: adicionados, removidos, consumo alterado), **T40 FENABRAVE import** (edição, 111 modelos, ajustados pelo autor, comparação de um informativo novo com o catálogo), **T42 Weighted references** (segmentos, parâmetros recalculados × modelo Excel, veículos e pesos, cobertura × ANFAVEA). A T40 grava a edição importada (ver 4b).
Testes: `tests/test_market_data.py` (23) e `tests/test_telas_012.py` (9).

Divergência resolvida em 23/11 (decisão 18): o fator `0,85` da área frontal, que estava como constante no código para não mudar o `ParamBaseHash`, agora é o parâmetro `FRONTAL_AREA_FACTOR` da `P59` (ver 4c).

### 4b. Acréscimos de 22/11/2026 (B2b)
- **P72_FleetLicensingByPowertrain** (commit `7aaaba3`, 330 linhas): emplacamento ANFAVEA 2016–2025 do Anuário 2026 por combustível/tecnologia (2.2.8; automóveis, comerciais leves, caminhões e ônibus), eletrificados por tecnologia (2.2.9; BEV, híbrido flex, híbrido gasolina, híbrido diesel, PHEV; automóveis e comerciais leves) e cilindrada (2.2.10; só automóveis, sem elétricos). Formato longo (`Dimension`, `Category`, `Units`); cada linha confere o total da fonte; `core/market_data.parse_anfavea_columns`, `tools/import_anfavea.py`, carga por `load_b2.py`. Comparação com a aba Fleet Characteristics do i3EF: ver `DivergenciasB2_P72_20261122a.md` (Project: `b2-divergencias-p72`). O Anuário 2025 não traz estas tabelas.
- Esquema S16: `P47` + `UnitsReported`, `UnitsPrevious`, `UnitsPBEV`, `SplitMethod` (Reported, Previous, PBEV, Master, Base, Workbook), `SplitBasis`; `P60` reformulada (`SourceName` ANFAVEA ou FENABRAVE, `SourceEdition`, `IsAdopted`; classes Automobiles, LightCommercials, Trucks, Buses, Total, LightVehicles); nova `P71_FleetEstimate` (frota estimada por classe e edição). Todas editoriais (fora do `ParamBaseHash`, que era `401f68e3…` até 22/11 e passou a `c972269f…` em 23/11 com o parâmetro `FRONTAL_AREA_FACTOR`; carga por `tools/load_b2.py`, fixtures por `tools/import_fenabrave.py` e `tools/import_anfavea.py`). Numeração: P61–P63 pertencem a outras tabelas; P64–P69 ao painel de parâmetros; P70 aos segmentos.
- `core/market_data.py`: MD8 (`parse_anfavea_table`), MD9 (`split_candidates`, `apply_master_units`, `validate_split`, `save_edition`, `largest_remainder`), MD10 (`design_powertrain_pivot`, equivalente à tabela dinâmica `FENABRAVE 2025 Categories!R2:AB11`; soma 2.424.281), MD11 (`reference_comparison`, `export_reference_xlsx`).
- Divisão por motorização (regra): variantes com linha própria no informativo valem como informadas; o total do modelo é repartido entre as demais por maior resto, para fechar exatamente com o informativo; a gravação é recusada se a soma não fechar. Na edição de 2025 valem as divisões manuais da planilha (`SplitMethod = Workbook`, 29 linhas).
- T40: tabela de candidatas, edição de `Units adopted`, `Save edition to the reference base` (só master; no Streamlit Cloud o disco é temporário), exportação da divisão. T42: três níveis de cobertura (seis referências, 50+50, mercado FENABRAVE), quadro design × motorização e exportação Excel da comparação.
- Modelos do ranking sem par no catálogo (decisão 10, 23/11: só listar e corrigir grafias) são listados e não gravados.
- **Conferência de totais na T40 (23/11, pedido do autor):** o quadro "Check: bulletin totals × adopted units" mostra V, CL e V+CL (informativo, adotado, fora do catálogo, diferença) e reage ao que o Master digita; "Check by model" mostra, por modelo dividido, total do informativo × soma adotada; as motorizações de cada modelo ficam uma embaixo da outra. O topo da tela mostra, por edição gravada, o semitotal do informativo (esquerda) × adotado (direita): FEN2025 V 1.872.220 × 1.872.219, CL 552.062 × 552.062, V+CL 2.424.282 × 2.424.281 (diferença de 1 unidade no SONG: 42.181 no informativo, 42.180 no modelo). Não se soma `UnitsSource` da P47, porque o modelo repartido repete o total do informativo na linha principal. `core.market_data`: `sort_split_lines`, `reconcile_totals`, `model_checks`, `edition_totals`.

### 4c. Decisões de 23/11/2026 (autor) e o que foi feito
- **1 e 21 (visibilidade):** as tabelas originais (INMETRO/PBEV, FENABRAVE, ANFAVEA) ficam visíveis só ao Master, que as usa para identificar os veículos referenciais como no Excel. O usuário **não** recebe o cálculo dos referenciais; recebe a lista de veículos de mercado e de referência com todos os parâmetros e um aviso de que se trata de **sugestão do aplicativo**, que pode ser copiada e alterada consultando o site ou o manual do fabricante e as tabelas do INMETRO, da FENABRAVE e da ANFAVEA. O usuário escolhe como padrão os veículos de referência e de mercado do Master e pode criar veículos do zero ou salvar um padrão com outro nome para alterar parâmetros. Os valores do INMETRO que o Master correlacionar e os licenciamentos (FENABRAVE ou ANFAVEA) aparecem ao usuário como informação do Master, sem as tabelas de origem. **Decidido em 23/11 (pontos de implementação):** o veículo copiado pelo usuário fica **independente** do padrão do Master (guarda só a origem da cópia); projetos existentes **não mudam** quando o Master publica edição nova (o aplicativo avisa; o usuário pode copiar o projeto e atualizá-lo com os dados novos); o usuário vê os valores do INMETRO **em MJ/km** (por motorização, combinado para o teste de esteira e calculado a partir do consumo de combustíveis pelo critério da norma), não os campos brutos do PBEV; texto do aviso aprovado: "Parâmetros sugeridos pelo aplicativo a partir de dados do INMETRO, da FENABRAVE e da ANFAVEA, selecionados pelo Master. Copie o veículo e ajuste os valores consultando o site ou o manual do fabricante e as tabelas dessas fontes." **A implementação (telas T09–T11) ainda está por fazer.** Consultar INMETRO, FENABRAVE e ANFAVEA sobre a divulgação das tabelas só depois de o aplicativo estar pronto e testado (decisão 2).
- **2:** não escrever agora; decidir depois do aplicativo pronto e testado.
- **3, 6, 7, 8, 10, 12, 15, 20, 23, 25, 26, 27:** seguem as recomendações (3: dado de mercado só na base de referência; 6: versões numeradas, a primeira como padrão; 7: refazer vínculos da P50 com relatório de mudanças e manter a edição do Excel como padrão até adoção explícita; 8: incluir e listar os 4 registros extras; 10: só listar os modelos fora do catálogo e corrigir grafias; 12: acumulado de dezembro; 15: texto da ressalva aprovado; 20: resíduo só como cobertura; 23: `v0.12.0` após o teste manual; 25: três híbridos na P72, soma para HEV na comparação; 26: cilindrada só para automóveis; 27: ANFAVEA adotada em 2025, valor do Excel como alternativa).
- **11 (período):** uma série por ano: o acumulado de janeiro a dezembro nos anos completos e o acumulado de janeiro ao relatório mais recente no ano corrente (parcial). O mensal não é usado e a aba `+ Vendidos FENABRAVE J24 a M25` é descartada. O primeiro ano de dados é 2025, como no Excel (só o histórico da frota vem desde o início da série da ANFAVEA); anos anteriores só entram se o autor importar o relatório de dezembro deles. **Feito (23/11):** `save_edition` recusa período que não seja YTD, adota a edição de período mais recente de cada ano (as demais ficam com `IsAdopted = 0`) e acrescenta "dados parciais de janeiro a MM/AAAA" quando termina antes de dezembro; `adopted_edition` e `adopted_years`; a T42 escolhe o ano (padrão: último ano completo, com aviso se for parcial) e a T40 não tem mais a caixa "adotar".
- **17 (segmentos):** editáveis pelo Master na T42, com o padrão do Excel (restaurável). Feito (`P70.Origin`, `save_segments`, `restore_workbook_segments`).
- **18 (fator 0,85):** virou o parâmetro `FRONTAL_AREA_FACTOR` da P59. Feito; o `ParamBaseHash` passou de `401f68e3…` para `c972269f…` e a regressão congelada foi atualizada (só mudou o hash).
- **19 (representativo):** o veículo representativo do Excel foi só ilustração (os parâmetros adotados são as médias ponderadas, e só do ICEV; as demais motorizações são calculadas por equivalência). Feito: `closest_vehicles` (veículo de mercado mais próximo da referência ponderada) e `reference_params(powertrain=…)`, na T42. Resultado: ARGO e STRADA coincidem com os escolhidos no Excel; nas demais categorias o mais próximo é outro (PULSE, HB20S, TERRITORY, L200 TRITON). Para as motorizações eletrificadas a opção existe e fica útil quando houver mais veículos.
- **24 (série):** P72 recebe a série 1957–2025 da aba Fleet Characteristics (`SourceName = 'i3EF'`, `SourceEdition = i3EF_20261101`); antes de 2016 vale o i3EF; de 2016 em diante vale o Anuário ANFAVEA mais recente e o i3EF fica só como comparação (`IsAdopted = 0`). Regra geral: manter sempre o conjunto mais recente disponível e documentar linha a linha (`NotesFP`).

### 4d. Contas e papéis, antecipados (23/11/2026)

O autor pediu a entrada por e-mail e senha na T01, com o Master definindo quem é Master, e antecipou o que estava na Fase C. Feito em versão local: `core/accounts.py` (tabela `Account` em `local_accounts.sqlite`, fora do git e fora da base de referência; senha com PBKDF2-SHA256 e sal; papéis Master e User; cadastro aberto sempre como User; bloqueio de 5 min após 5 erros; o último Master não pode ser rebaixado; transferência do papel), `ui/auth.py` (painel da T01 e gestão de usuários) e `require_master` e a T48 passam a olhar o papel da conta, sem campo de senha por tela. O primeiro Master é criado com a senha de instalação (`I3ET_MASTER_PASSWORD` ou `master_password` em `.streamlit/secrets.toml`), pedida uma única vez. Limites assumidos: (a) controla a interface, não protege dados que estejam no repositório público (decisão 2); (b) no Streamlit Cloud o disco é efêmero, então as contas só persistem localmente; (c) para a publicação, a identidade passa a vir de login externo (`st.login`, exige subir o Streamlit além do 1.41.1) mantendo a tabela de papéis por e-mail; recuperação de senha e verificação de e-mail ficam para essa etapa.

## 5. Decisões que dependem do autor (por tarefa)

*As decisões abaixo foram tomadas em 23/11/2026 (ver 4c); o texto original fica como registro.*

**B2-1 · Dados e termos de uso**
1. Mostrar as tabelas da FENABRAVE e da ANFAVEA a usuários que não são master: depende da sua checagem. Até lá, só master (já decidido).
2. Escrever ao Inmetro (CC BY-ND, "SemDerivações") e à FENABRAVE ("todos os direitos reservados") para confirmar o uso? Sim/não.
3. Os projetos podem levar dados de mercado dentro do arquivo (hoje o PBEV vai; propus não levar P47, P48, P60, P70)? Aceita a regra "dado de mercado só na base de referência"?

**B2-2 · Importação do PBEV (T39)**
4. **DECIDIDO (22/11): PDF direto, com CSV/Excel de reserva; `pdfplumber==0.11.9` entra em `requirements.txt` (conferir a instalação no Streamlit Cloud).** [opções originais] De onde o aplicativo lê o PBEV: (a) PDF direto, com `pdfplumber` (hoje só opcional; entrar em `requirements.txt` significa instalar no Streamlit Cloud); (b) CSV/Excel que você converte; (c) as duas. Recomendo (a) com (b) de reserva.
5. **DECIDIDO (22/11): edições do master na base de referência (commit publica para todos; armazenamento em nuvem próprio na Fase C); edições do usuário por arquivo (baixar/carregar) e pasta local; Google Drive/OneDrive na Fase C.** [opções originais] Onde ficam as edições importadas: (a) na base de referência, gravadas pelo master (como `P69`); (b) arquivo de dados do usuário separado. No Streamlit Cloud o disco é efêmero, então (a) só vale no seu computador até a Fase C.
6. Nomes (M.BENZ etc.) e 22 duplicatas: manter como versões numeradas ou usar a primeira?
7. Ao chegar a edição de 25/ago: refazer os vínculos `P50` e avisar quais veículos mudaram de valor? Qual edição é o padrão de um projeto novo?
8. Registros a mais no PDF (847 × 843): incluir e listar (recomendado) ou ignorar?

**B2-3 · Importação da FENABRAVE (T40)**
9. **DECIDIDO (22/11): uma linha por modelo e motorização, nunca agrupada. Candidatas na ordem: informativo FENABRAVE/ANFAVEA → edição anterior → participação de versões no PBEV → ajuste do master; o master vê todas as candidatas lado a lado (T40); a escolha fica em `SplitMethod` e a base em `SplitBasis`/observação.** [opções originais] Divisão de um modelo por motorização numa edição nova: (a) o master digita a participação na T40; (b) repete a participação da edição anterior; (c) estima pelo número de versões do PBEV; (d) outra fonte (ABVE). A planilha só tem valores digitados.
10. Modelos do ranking fora do catálogo de 154 (hoje 8): ignorar, só listar, ou incluir no catálogo (exige parâmetros do veículo a partir do PBEV e das regras de valor padrão)?
11. A aba `+ Vendidos FENABRAVE J24 a M25` (jan/24 a mar/25, com `#REF!`): importar como edição própria ou descartar?
12. Período padrão: acumulado de dezembro e o mensal só para consulta?
13. **DECIDIDO (22/11): planilha prevalece; recálculo da C33 é opção do master; as duas versões são exportáveis para Excel (T42); o teste compara as duas quando usam tabelas do mesmo ano (2025: 60/60).** [opções originais] Ao adotar uma edição nova, recalcular os SELEÇÃO (C33) ou manter os valores da planilha como padrão (recomendado, "a planilha prevalece") e deixar o recálculo como opção do master?

**B2-4 · ANFAVEA (P60)**
14. **DECIDIDO (22/11): Anuário ANFAVEA 2026 anexado e importado; vale a edição mais recente; `P60` (emplacamento 1957–2025) e `P71` (frota estimada 2000–2025) guardam a edição de cada número, para o módulo de frota (LCA_LV_i3EF_20261101). Séries conferidas: 2.2.1 (2026: 2016–2025), 2.3 (2025: 1957–2024, não 1953), 1.11 (2025: 2000–2024; 2026: 2016–2025).** [pergunta original] O total de 2025 só vem da Carta mensal de dezembro/2025 ou do Anuário 2026: você anexa um deles?
15. **Parcialmente decidido (22/11): o total de mercado é o da FENABRAVE (todos os dados do modelo vêm dela); a T42 mostra três níveis (seis referências 78,8%, ranking 50+50 95,1%, mercado 100%) e a ANFAVEA como comparação.** Resta confirmar o texto da ressalva.
16. Numeração: usar `P60`; posso corrigir o nome do item no Monday (`P59`)?

**B2-5 · Veículos de referência (T42 / C33)**
17. Os 17 segmentos e a regra EG/D/X ficam fixos (fixture) ou o master pode editá-los na T42?
18. O fator 0,85 da área frontal: levar para `P59` (muda o `ParamBaseHash`; rodadas congeladas não são afetadas) ou manter no código como divergência?
19. Veículo representativo (`IDMVRepresentative`: ARGO, CRETA, VIRTUS, COMPASS, HILUX, STRADA, escolhidos à mão): regra para edições novas — o de maior venda do segmento principal, ou escolha do master?
20. O resíduo de 17,1% fora dos segmentos (Van, Chassis etc.): mostrar só como cobertura?

**B2-6 · Telas**
21. T39, T40 e T42 ficam no menu Auxiliary Data, visíveis só com a senha master. O usuário comum deve ver alguma coisa (por exemplo só a lista de veículos de referência com a fonte)?
22. **Resolvida pela decisão 5 (22/11): a T40 grava a edição na base de referência (master); a publicação para os demais usuários é o commit da base.**

**B2-8 · Motorização da ANFAVEA (22/11)**
24. (18) Séries de 1957 a 2015 só existem na aba Fleet Characteristics do i3EF: importar para a P72 com `SourceEdition` próprio, ou começar em 2016?
25. (19) Manter os três híbridos da 2.2.9 na P72 e somar para HEV na comparação com o Excel?
26. (20) Cilindrada só para automóveis (a 2.2.10 não cobre comerciais leves nem elétricos)?
27. (21) Em 2025, o módulo de frota adota o valor da ANFAVEA, com o do Excel como alternativa?

**B2-7 · Publicação**
23. `v0.12.0` ao fechar o B2 (atualizar `.zenodo.json`, `CITATION.cff` e `core.__version__` antes da tag).

## 6. O que falta para fechar o B2

Decisões abertas: nenhuma. Por implementar: visibilidade do usuário comum e veículos próprios (decisão 21, junto com T09–T11), refazer vínculos do PBEV quando chegar a edição de 25/ago (decisão 7). Entregas: roteiro de teste do autor (`RoteiroDeTeste_B2_20261123e.md`; comparar Excel × aplicativo com tabelas do mesmo ano, gravar uma edição de teste, exportar), `v0.12.0` (atualizar `.zenodo.json`, `CITATION.cff`, `core.__version__` antes da tag), `git push` dos commits `9bab60e` e `39637ac`, conferir a instalação do `pdfplumber` no Streamlit Cloud, edição de 25/ago do PBEV quando disponível.
