# Lista de diferenças planilha × calculadora ao fim do B1 — decisões do autor (19/11/2026)

**Data:** 18/11/2026; decisões de 19/11/2026 · **Base:** `LCA_LV_i3ET_20261101.xlsx`; fixture regerada em 19/11 a partir de `LCA_LV_i3ET_20261119.xlsx` (a planilha é do autor e não é alterada por nós) · Complementa `05a-divergencias-fase-a.md` e `05b-divergencias-b1.md`.

Cada linha traz a decisão do autor, a justificativa e o cuidado para os testes que comparam planilha e aplicativo. A descrição completa de cada diferença (o que a planilha faz, o que a calculadora faz, peso no resultado) está na versão anterior desta lista (`B1_ListaDeDiferencas_20261119a.md`, em `Versões anteriores` na pasta Documentação, e no histórico do git).

## A. Divergências de cálculo

| # | Assunto | Decisão do autor | Justificativa | Impacto nos testes e ajustes combinados |
|---|---|---|---|---|
| 1 | Calibração de massa (T38), B1-DIV-01. Planilha: com `P69 = "Sim"` recalcula A e B pela razão `k` e move massa mesmo sem diferença (SV1: 54,2 kg). Calculadora: reparte só a diferença. Peso: 0,01 a 0,44% do `T511` | **Em debate (19/11).** Valem os princípios: a diferença entre a massa total informada pelo fabricante e a estimada é lançada em carroceria e chassi, e a soma não muda | A estimativa (betas e massas de referência) deveria ficar próxima da proporção do GREET; se não fica, os parâmetros devem ser recalibrados, usando o GREET como referência | Paridade exata só com `P69 = "Não"` ou ajuste zero; com "Sim", a diferença é de 0,01 a 0,44% do `T511` e o teste compara com `mass_calibration.sheet_method` com essa tolerância declarada |
| 2 | `T495` em 28 colunas, B1-DIV-02 | Manter o método da calculadora (regra única, com o seletor); corrigir a planilha | Evita a dupla contagem do fim de vida | **Planilha corrigida** em `LCA_LV_i3ET_20261119.xlsx` (`AF495`, `CD495`, `CK495` e as demais). Fixture regerada: 122 colunas seguem o seletor e nenhuma é "antiga"; a paridade de `T495` e `T511` passa a valer em todas elas |
| 3 | Colunas PBP_BISD, B1-DIV-03 | Reconstruir as fórmulas no Excel como nas demais colunas | As colunas foram coladas de outra planilha só para trazer as receitas de materiais | Na planilha de 19/11 as 6 colunas `CX:DC` ainda têm `T495` digitado (0), e o teste as exclui explicitamente. Após a reconstrução, regerar a fixture e exigir a paridade nelas. **A conferir:** esta lista falava em 18 colunas PBP_BISD e a B1-DIV-02 em 6 (`CX:DC`) |
| 4 | Participações negativas (D8) | Normalizar as alocações para que cada grupo some 100% | As receitas atuais garantiram a soma 100% jogando a diferença para a linha *Others*, e isso pode ter acontecido em vários grupos | Os resultados diferem da planilha. Teste proposto: com `MshareRaw` (valores brutos), calcular como a planilha e exigir paridade exata; o cálculo normalizado leva tolerância declarada. **A reconciliar:** a base conta 28 linhas negativas; a varredura da planilha achou 45 células negativas (linhas 132 e 155 do M2; massas nas linhas 337 e 362), com resíduos de até cerca de −1×10⁻⁴ |
| 5 | Método de fim de vida padrão | Manter glider + bateria como padrão (fator por kg do glider e por kWh da bateria) | Diferencia as emissões pela massa do glider e pela capacidade da bateria, no lugar de um valor fixo | Os testes de paridade de `T509` e `T511` usam o método "Aggregate vehicle factor" (reproduz `T509` a 1e-9); o padrão tem teste próprio por conta manual. O fim de vida chega a 15,8% do `T511` (BEV: +1.745 kg CO₂e), então o valor de `X77` (20 kg CO₂e/kWh) deve ter fonte registrada. Opção do lado da planilha: `T509` ler `X76` e `X77` |
| 6 | Contagem das reposições | Manter a troca por quilometragem informada, sem trocas previstas para o fim da vida | Permite alterar a vida do veículo de forma coerente e alocar as emissões ao longo do tempo | A paridade exata vale só com vida de 200.000 km (a planilha usa contagens digitadas); em outras vidas o teste compara com a conta manual |
| 7 | Rotas da BR23 | Manter a recomposição dos fatores por sucata, rotas de produção e perdas de processo (aço e alumínio) | Funcionalidade já existente no modelo em Excel | Com os parâmetros do i3ET reproduz a lista digitada. Teste que varia parâmetros: na planilha é preciso alterar também `P124` a `P133`, pois só `P123` é ligado a `Z91`. Opção do lado da planilha: ligar `P124:P133` a `Z92:Z101` |
| 8 | Fator ausente (ND) | Manter o alerta para materiais sem fator correlacionável | Não impede o cálculo, mas indica a necessidade de ajustes | Teste: a lista de materiais sem fator avisada pelo aplicativo é igual ao conjunto de ND da planilha; os totais coincidem (ND soma como zero nos dois lados) |
| 9 | Receita `ICEV-BISD2` e `HEV-PBP_BISD6` (M2 linha 9) | Manter | O resultado é igual | Nenhum |

## B. Diferenças de projeto (a calculadora faz algo que a planilha não faz)

| # | Assunto | Calculadora | Sugestão | Decisão |
|---|---|---|---|---|
| 10 | Massa declarada, ajuste e `s` por caso | Guardados em colunas novas de D07 (`DeclaredMassKg`, `MassAdjustmentKg`, `MassBodyShare`, `DeclaredSource`); você decidiu `MassAdjBodyChassisKg` em P54/D03 | Manter em D07 (valor é por caso e já entra no congelamento) ou mover para P54/D03 | |
| 11 | Fatores de emissão do usuário | Versão própria herdada de uma da base (D04/D05) com histórico (D19); lista Digitada da base não é editada no lugar (a D05 só aceita versões de D04) | Manter, ou relaxar a chave de D05 para editar listas Digitadas diretamente | |
| 12 | Exibição | kg e kg CO₂e com 1 casa decimal nas telas; CSV sem arredondar | Manter (decisão 1) | |
| 13 | M1 linha 37 | IDSG 43 (a planilha repete o ID 23) | Manter; corrigir a planilha | |

## C. Limitações técnicas abertas (não são divergências com a planilha)

1. **Versão do usuário de montagem (`UA-`) e de parâmetros de massa (`UM-`) não podem ser escolhidas numa análise:** `D06.IDAPV` e `D06/D02.IDMPV` têm chave estrangeira para P23/P05. As cópias já valem no cálculo. Solução: recriar D06 e D02 sem a chave (migração), ou tabela de escolha própria.
2. **Modelo de bateria do usuário (`UB-`):** vale quando o parâmetro 32 do veículo traz o identificador; a T10 ainda não oferece a escolha.
3. **I53 (fatores efetivos congelados):** a rodada lê fatores, receitas e cópias do arquivo do projeto no momento de executar; editar depois de congelar ainda não é impedido. Só as receitas do usuário guardam hash (I30).
4. **C02 por grupo (Estimated/Calibration/Final) não é gravado por rodada:** a T38 não avisa antes da rodada que A ou B ficaria negativo (I40); a rodada para com o valor mínimo.
5. **Telas T18 e "Vehicle life" (T18L)** coexistem; falta decidir se uma absorve a outra.

## D. Pendências suas, que não bloqueiam

- Conferir a digitação das linhas 54 e 55 do M2 nas 6 receitas com `k` > 1 (FCV-P25, HEV-P27, PHEV-P28, BEV-P29, FCV-P30, PHEV-S28).
- ~~Corrigir `T495` nas 28 colunas~~ (feito na planilha de 19/11). Reconstruir as fórmulas das PBP_BISD (`CX:DC`, item 3).
- Decidir o item 1 (em debate), `MshareRaw` e a reconciliação 28 × 45 (item 4) e os itens 10 e 11.
- Opcional, do lado da planilha: ligar `P124:P133` a `Z92:Z101` (item 7) e fazer `T509` ler `X76` e `X77` (item 5).
