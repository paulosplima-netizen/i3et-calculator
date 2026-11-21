# B2 — importações e veículos de referência: especificação, implementação e decisões pendentes (21/11/2026)

Estado: **implementado até onde não depende de decisão do autor.** Núcleo, fixtures, esquema, três telas (só leitura e comparação, só para o master), testes (485 passam; lint limpo). Falta fechar as decisões da seção 5 para gravar edições importadas, recalcular os veículos de referência por edição e publicar `v0.12.0`. Commit local feito; o `git push` é seu.

Base: `b2-decisoes-fontes-de-dados` (fontes e termos de uso), `FaseB_Plano_20261121c`, itens do Monday (P47, P48, P60/P59, C33, T39, T40, T42), planilha `LCA_LV_i3ET_20261119.xlsx`, arquivos da pasta Documentação (PBEV INMETRO, FENABRAVE, ANFAVEA).

## 1. Escopo

Já existia (Fase A): `P36`, `P28`, `P55`, `P50` (PBEV), `P26` (154 veículos, `SalesUnits` = licenciamentos de 2025), `P27` (`Avg` nos 6 SELEÇÃO), `P29`, `tools/import_pbev.py`, `tools/import_market_vehicles.py`, `core/vehicle_defaults.py`, T09/T11.
Novo no B2: `P47`, `P48`, `P60`, `P70`, a referência ponderada (C33), leitura dos arquivos de origem, correspondência com o catálogo, telas T39, T40 e T42.

## 2. O que a comparação com os arquivos de origem mostrou

- **PBEV:** mesma edição (24/abr/2026) que a aba da planilha; 717 chaves coincidem sem nenhuma diferença numérica; ~130 chaves diferem só por edição de nome na planilha; 22 chaves duplicadas; 847 registros no PDF contra 843 na planilha. A edição de 25/ago (976 versões) não foi anexada.
- **FENABRAVE:** os volumes de `Most Licensed 2025` coincidem com o informativo Ed. 276 (acumulado até dez/2025) em 82 dos 100 modelos lidos do PDF de forma exata e 9 divididos por motorização (a planilha separa, por exemplo, HR-V e HR-V HEV; a soma das variantes fecha com o PDF: 60.577 + 650 = 61.227); 8 modelos não têm par no catálogo (grafia ou variante: Triton × L200 Triton, Song × Song Pro GL, Yuan × Yuan Plus, Jaecoo 7 × J7, K2500, UK2500, Daily) e 1 difere (BMW X1: 5.367 no PDF, 4.423 no catálogo). As colunas de design, porte, motorização, combustível, massa, MJ/km e montado/importado são manuais e não vêm do PDF.
- **ANFAVEA:** o Anuário 2025 cobre até 2024; o modelo usa o total de 2025 (2.424.281 veículos leves). O arquivo da pasta não basta para esse dado.
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

**Paridade:** `core.market_data.reference_params` reproduz os **60 de 60** valores `Avg` (tolerância relativa 1e-6) e a cobertura dos segmentos, 82,87% do total de 2.424.281 (célula L226 da planilha).

## 4. Implementação

Tabelas (esquema 0.12, bloco S15; `schema.apply_012`; CSV em `data/csv/fase_b`; carga por `tools/load_b2.py`, que não refaz as demais tabelas e portanto não apaga escolhas do master como `P69`):

- `P48_MarketSalesEdition` (IDMSE, fonte FENABRAVE, tipo de período YTD/Month/Range, início, fim, referência do informativo, arquivo, publicada/importada em, nº de registros, `IsAdopted`, nota). Fixture: `FEN2025`, acumulado jan–dez/2025, Ed. 276.
- `P47_MarketSales` (por edição: classe V/CL, posição, marca, modelo, chave, `UnitsSource` do informativo, `UnitsAdopted` usado pelo modelo, `IDMV` do catálogo, nota de ajuste, linha da planilha). Fixture: 111 modelos, todos ligados ao catálogo; `UnitsAdopted` = `P26.SalesUnits` em todos; 9 com unidades redistribuídas pelo autor.
- `P60_FleetLicensingTotal` (ANFAVEA, ano, classe, unidades, fonte, nota). Fixture: 2025, veículos leves, 2.424.281.
- `P70_ReferenceSegment` (categoria, design, porte, grupo de combustível, motorização, linha da planilha). Fixture: 17 segmentos, 12 ligados a categorias.
- As quatro entram em `EDITORIAL_TABLES` (fora do `ParamBaseHash`; hash da base inalterado) e **não são copiadas para os arquivos de projeto** (o dado da FENABRAVE não circula com os projetos).

Módulos: `core/market_data.py` (MD1 nomes e chaves; MD2 informativo da FENABRAVE; MD3 tabela do PBEV; MD4 correspondência com o catálogo, status exact/split/differs/none; MD5 referência ponderada C33; MD6 cobertura; MD7 comparação de uma edição do PBEV com a base), `tools/import_fenabrave.py`, `tools/load_b2.py`, `ui/master.py`.
Telas (menu Auxiliary Data; conteúdo só com a senha do master, sem senha configurada ninguém vê): **T39 PBEV import** (edições da base, vínculo com os veículos, comparação de um PDF novo: adicionados, removidos, consumo alterado), **T40 FENABRAVE import** (edição, 111 modelos, ajustados pelo autor, comparação de um informativo novo com o catálogo), **T42 Weighted references** (segmentos, parâmetros recalculados × modelo Excel, veículos e pesos, cobertura × ANFAVEA). Nenhuma tela grava: a gravação de edições importadas aguarda a decisão 5.
Testes: `tests/test_market_data.py` (11) e `tests/test_telas_012.py` (9).

Divergência registrada: o fator `0,85` da área frontal está como constante em `core/market_data.py` (`FRONTAL_AREA_FACTOR`) e não em `P59`, porque mudar `P59` muda o `ParamBaseHash` (decisão 18).

## 5. Decisões que dependem do autor (por tarefa)

**B2-1 · Dados e termos de uso**
1. Mostrar as tabelas da FENABRAVE e da ANFAVEA a usuários que não são master: depende da sua checagem. Até lá, só master (já decidido).
2. Escrever ao Inmetro (CC BY-ND, "SemDerivações") e à FENABRAVE ("todos os direitos reservados") para confirmar o uso? Sim/não.
3. Os projetos podem levar dados de mercado dentro do arquivo (hoje o PBEV vai; propus não levar P47, P48, P60, P70)? Aceita a regra "dado de mercado só na base de referência"?

**B2-2 · Importação do PBEV (T39)**
4. De onde o aplicativo lê o PBEV: (a) PDF direto, com `pdfplumber` (hoje só opcional; entrar em `requirements.txt` significa instalar no Streamlit Cloud); (b) CSV/Excel que você converte; (c) as duas. Recomendo (a) com (b) de reserva.
5. Onde ficam as edições importadas: (a) na base de referência, gravadas pelo master (como `P69`); (b) arquivo de dados do usuário separado. No Streamlit Cloud o disco é efêmero, então (a) só vale no seu computador até a Fase C.
6. Nomes (M.BENZ etc.) e 22 duplicatas: manter como versões numeradas ou usar a primeira?
7. Ao chegar a edição de 25/ago: refazer os vínculos `P50` e avisar quais veículos mudaram de valor? Qual edição é o padrão de um projeto novo?
8. Registros a mais no PDF (847 × 843): incluir e listar (recomendado) ou ignorar?

**B2-3 · Importação da FENABRAVE (T40)**
9. Divisão de um modelo por motorização numa edição nova: (a) o master digita a participação na T40; (b) repete a participação da edição anterior; (c) estima pelo número de versões do PBEV; (d) outra fonte (ABVE). A planilha só tem valores digitados.
10. Modelos do ranking fora do catálogo de 154 (hoje 8): ignorar, só listar, ou incluir no catálogo (exige parâmetros do veículo a partir do PBEV e das regras de valor padrão)?
11. A aba `+ Vendidos FENABRAVE J24 a M25` (jan/24 a mar/25, com `#REF!`): importar como edição própria ou descartar?
12. Período padrão: acumulado de dezembro e o mensal só para consulta?
13. Ao adotar uma edição nova, recalcular os SELEÇÃO (C33) ou manter os valores da planilha como padrão (recomendado, "a planilha prevalece") e deixar o recálculo como opção do master?

**B2-4 · ANFAVEA (P60)**
14. O total de 2025 só vem da Carta mensal de dezembro/2025 ou do Anuário 2026: você anexa um deles?
15. Indicador de representatividade: soma dos modelos nos segmentos ÷ total ANFAVEA (82,9% hoje; o autor estimava mais de 90%). Mostrar assim, com a ressalva de que licenciamento e emplacamento por modelo têm definições diferentes (é como a T42 mostra hoje)?
16. Numeração: usar `P60`; posso corrigir o nome do item no Monday (`P59`)?

**B2-5 · Veículos de referência (T42 / C33)**
17. Os 17 segmentos e a regra EG/D/X ficam fixos (fixture) ou o master pode editá-los na T42?
18. O fator 0,85 da área frontal: levar para `P59` (muda o `ParamBaseHash`; rodadas congeladas não são afetadas) ou manter no código como divergência?
19. Veículo representativo (`IDMVRepresentative`: ARGO, CRETA, VIRTUS, COMPASS, HILUX, STRADA, escolhidos à mão): regra para edições novas — o de maior venda do segmento principal, ou escolha do master?
20. O resíduo de 17,1% fora dos segmentos (Van, Chassis etc.): mostrar só como cobertura?

**B2-6 · Telas**
21. T39, T40 e T42 ficam no menu Auxiliary Data, visíveis só com a senha master. O usuário comum deve ver alguma coisa (por exemplo só a lista de veículos de referência com a fonte)?
22. As telas só comparam hoje. A gravação ao confirmar depende da decisão 5; até lá, a rota é gerar os CSV e você revisar e commitar. Aceita?

**B2-7 · Publicação**
23. `v0.12.0` ao fechar o B2 (atualizar `.zenodo.json`, `CITATION.cff` e `core.__version__` antes da tag).

## 6. O que falta para fechar o B2 depois das decisões

Gravação de edições importadas (4, 5, 22); correspondência por apelidos mantidos pelo master e divisão por motorização (9, 10); recálculo opcional da C33 por edição e seu efeito nos valores `Avg` de `P27` (13, 18); total da ANFAVEA 2025 (14); regra do veículo representativo (19); roteiro de teste do autor; release.
