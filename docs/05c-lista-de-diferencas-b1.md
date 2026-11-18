# Lista de diferenças planilha × calculadora ao fim do B1 — para decisão do autor

**Data:** 18/11/2026 · **Base:** `LCA_LV_i3ET_20261101.xlsx` (não alterada) · Complementa `05a-divergencias-fase-a.md` e `05b-divergencias-b1.md`.

Cada linha diz o que a planilha faz, o que a calculadora faz, o peso no resultado e uma sugestão. A coluna **Decisão** fica para você: **manter** a calculadora, **voltar** ao comportamento da planilha, ou **adiar**. Onde a sugestão é "voltar", o caminho de volta já existe no código (indicado) ou é pequeno.

## A. Divergências de cálculo

| # | Assunto | Planilha | Calculadora | Peso no resultado | Sugestão | Decisão |
|---|---|---|---|---|---|---|
| 1 | Calibração de massa (T38), B1-DIV-01 | Com `P69 = "Sim"`, recalcula A e B pela razão `k` e move massa de A para B mesmo sem diferença (SV1: 54,2 kg) | Reparte só a diferença: A recebe `s·Adj`, B recebe `(1−s)·Adj`; `s` por receita (P63) | 0,01 a 0,44% do T511 nas SV1–SV4 | Manter. O método da planilha existe como função de teste (`mass_calibration.sheet_method`) | |
| 2 | `T495` em 28 colunas, B1-DIV-02 | GREET 2023 (AF:AO) e BISD (CD:CI, CK:CV): ignora o seletor, soma sempre a bateria de íon-lítio e soma o fim de vida (`T509`) dentro de `T495`, contando-o duas vezes | Segue o seletor (`Sim`, `Sim Bat`, `Não`) em todas as colunas | Excesso de 1,4% a 32,6% do T511 (mediana 6,6%) | Manter. Corrigir a fórmula na planilha (você informou que fará) | |
| 3 | Colunas PBP_BISD, B1-DIV-03 | 18 colunas têm pneus e bateria auxiliar próprios; fórmula ainda não identificada | Usa os itens de manutenção comuns | 0 a 0,22% do T511 (só DA e DB passam de zero) | Adiar até você identificar a fórmula; se for outra regra, entra como cenário PBP em P31 | |
| 4 | Participações negativas (D8) | Mantém resíduos negativos na linha *Others* | Grava zero e normaliza o grupo; a linha 662 (glider) da planilha soma a mais 0,1% | 0,5 a 0,8 kg de massa; 0,1 a 0,2 kg CO₂e no fim de vida | Manter. Coluna `MshareRaw` em P16 (mostrar "planilha −0,0123; usado 0") não foi criada: depende de você | |
| 5 | Método de fim de vida padrão | Colunas GREET usam o fator por veículo (IDM 100: 177,68 kg CO₂e na BR23); SV1–SV4 já usam glider + bateria | Padrão glider + bateria (0,2 kg CO₂e/kg e 20 kg CO₂e/kWh do painel), decisão 10 | Das 128 colunas de referência, 80 diferem de `T509`: de 0,3% a 15,8% do T511 (mediana 1,6%); BEV chega a +1.745 kg CO₂e | Decisão sua: o padrão da calculadora ou o fator por veículo. Voltar = escolher "Aggregate vehicle factor" na T17 (reproduz `T509` a 1e-9) ou mudar o padrão de `D06.EoLMethod` | |
| 6 | Contagem das reposições | Contagem digitada por configuração | Eventos = número de k ≥ 1 com k·intervalo < vida (sem troca no fim da vida) | Reproduz os totais da planilha nas colunas com o seletor (teste de paridade) | Manter (decisão 13) | |
| 7 | Rotas da BR23 | Lista digitada | Recomposta a partir dos parâmetros X91–X101 e P123–P133; igual à digitada dentro da tolerância do teste | Zero no padrão | Manter (decisão 11) | |
| 8 | Fator ausente (ND) | O Excel trata `ND` como zero (D10 da Fase A) | Dado ausente, nunca zero; na reposição, material sem fator conta 0 com aviso I34 | Só onde há material sem fator | Manter | |
| 9 | Receita ICEV-BISD2 e HEV-PBP_BISD6 (M2 linha 9) | Nome com prefixo da motorização | Mapeado para o ID de P15 (`BISD2`, `PBP_BISD6`) | Nenhum | Manter | |

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
- Corrigir `T495` nas 28 colunas e identificar a fórmula das PBP_BISD.
- Decidir `MshareRaw` (item 4) e os itens 5, 10 e 11.
