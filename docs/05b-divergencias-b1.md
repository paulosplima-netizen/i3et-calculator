# Relatório de Divergências — anexo do bloco B1

**Data:** 18/11/2026 · **Fonte:** `LCA_LV_i3ET_20261101.xlsx` · Gerado por `tools/report_b1_divergences.py` · Complementa `05-relatorio-de-divergencias.md` e `05a-divergencias-fase-a.md`

O i3ET em Excel não é alterado e prevalece; este anexo mede o que o aplicativo faz de diferente nas partes que o B1 completa (M1 e M2) e quanto isso pesa no resultado.

## B1-DIV-01 — Calibração de massa: o método da planilha move massa de A para B

Com `P69 = "Sim"` o M2 calcula `A = (declarada − Σ demais grupos)/(1 + k)` e `B = k·A`, com `k` a razão chassi/carroceria digitada por receita. Isso redistribui a massa entre carroceria e chassi **mesmo quando a massa declarada é igual à calculada**. O aplicativo (decisão do autor, 18/11/2026) reparte só a diferença: `A_final = A_est + s·Adj`, `B_final = B_est + (1 − s)·Adj`, com `s = 1/(1 + k)` por receita (P63); sem diferença, nada muda. Os fatores de GEE por kg vêm das receitas e da lista BR23.

| Coluna | Receita | k | Massa movida de A para B (kg) | GEE/kg de A | GEE/kg de B | Efeito no GEE (kg CO₂e) | % do T511 |
|---|---|---|---|---|---|---|---|
| FD | ICEV-G21 | 0,4802 | 54,2 | 3,73 | 4,16 | 22,9 | 0,44 |
| FE | HEV-G22 | 0,4929 | 40,9 | 3,73 | 4,16 | 17,3 | 0,25 |
| FF | PHEV-G23 | 0,4802 | 1,7 | 3,73 | 4,16 | 0,7 | 0,01 |
| FG | BEV-G24 | 0,4929 | 49,4 | 3,73 | 4,16 | 20,9 | 0,28 |

Sinal: o efeito é o que a planilha soma a mais (positivo) ou a menos (negativo) por mover massa para o chassi, em relação ao aplicativo. Em 6 receitas o chassi pesa mais que a carroceria nos valores digitados (`k` > 1: FCV-P25, HEV-P27, PHEV-P28, BEV-P29, FCV-P30, PHEV-S28); conferir a digitação. **Sugestão para o i3ET:** aplicar só a diferença entre massa declarada e calculada.

## B1-DIV-02 — T495 antigo em 28 colunas do M2

Em 94 colunas `T495 = I × (T496 + T499 + J × T500 + T501)` segue o seletor `P495`. Em 28 (GREET 2023, `AF:AO`, e as BISD, `CD:CI`, `CK:CV`) a fórmula é `R495 × (… + T500 + T509)`: ignora o seletor, inclui sempre a bateria de tração e soma o fim de vida (`T509`), que `T511` soma de novo. O aplicativo reproduz a forma com seletor. O que a planilha soma a mais nessas colunas:

| Coluna | Receita | Seletor | Excesso em T495 (kg CO₂e) | T509 | T500 | % do T511 |
|---|---|---|---|---|---|---|
| AF | ICEV-G11 | Sim | 177,7 | 177,7 | 0,0 | 2,49 |
| AG | HEV-G12 | Sim | 602,5 | 177,7 | 424,8 | 7,01 |
| AH | PHEV-G13 | Sim | 1.279,5 | 177,7 | 1.101,9 | 12,84 |
| AI | BEV-G14 | Sim | 5.486,1 | 177,7 | 5.308,4 | 32,60 |
| AJ | FCV-G15 | Sim | 682,1 | 177,7 | 504,5 | 3,30 |
| AK | ICEV-G16 | Sim | 177,7 | 177,7 | 0,0 | 1,37 |
| AL | HEV-G17 | Sim | 536,1 | 177,7 | 358,4 | 3,84 |
| AM | PHEV-G18 | Sim | 1.059,2 | 177,7 | 881,5 | 7,10 |
| AN | BEV-G19 | Sim | 4.222,2 | 177,7 | 4.044,5 | 21,28 |
| AO | FCV-G20 | Sim | 629,0 | 177,7 | 451,4 | 3,32 |
| CD | ICEV-BISD2 | Sim | 177,7 | 177,7 | 0,0 | 3,20 |
| CE | ICEV-BISD2 | Sim | 177,7 | 177,7 | 0,0 | 3,20 |
| CF | ICEV-BISD3 | Sim | 177,7 | 177,7 | 0,0 | 3,01 |
| CG | HEV-BISD6 | Sim | 618,7 | 177,7 | 441,0 | 7,50 |
| CH | PHEV-BISD8 | Sim | 2.837,5 | 177,7 | 2.659,8 | 21,58 |
| CI | BEV-BISD12 | Sim | 6.059,7 | 177,7 | 5.882,0 | 30,59 |
| CK | ICEV-BISD2 | Sim | 177,7 | 177,7 | 0,0 | 3,16 |
| CL | ICEV-BISD2 | Sim | 177,7 | 177,7 | 0,0 | 2,93 |
| CM | ICEV-BISD3 | Sim | 177,7 | 177,7 | 0,0 | 2,86 |
| CN | HEV-BISD6 | Sim | 194,5 | 177,7 | 16,8 | 3,05 |
| CO | HEV-BISD6 | Sim | 194,5 | 177,7 | 16,8 | 3,05 |
| CP | HEV-BISD6 | Sim | 446,7 | 177,7 | 269,0 | 6,20 |
| CQ | SHEV-BISD7 | Sim | 656,2 | 177,7 | 478,5 | 9,10 |
| CR | PHEV-BISD8 | Sim | 827,0 | 177,7 | 649,3 | 8,90 |
| CS | PHEV-BISD8 | Sim | 803,5 | 177,7 | 625,8 | 8,77 |
| CT | PHEV-BISD8 | Sim | 803,5 | 177,7 | 625,8 | 8,77 |
| CU | BEV-BISD12 | Sim | 747,4 | 177,7 | 569,7 | 9,20 |
| CV | BEV-BISD12 | Sim | 3.951,8 | 177,7 | 3.774,2 | 29,40 |

Entre as 28 colunas, o excesso vai de 1,37% a 32,60% do T511 (mediana 6,60%). **Sugestão para o i3ET:** usar a fórmula com seletor nas 28 colunas (o autor informou que corrigirá).

## B1-DIV-03 — Colunas PBP_BISD

As 18 colunas do Projeto do Berço ao Portão (`CX:DC` e outras) têm pneus e bateria auxiliar próprios na planilha (jogo de pneus e reposição da bateria auxiliar diferentes dos demais). O aplicativo usa os mesmos itens de reposição (P31) para todas as receitas. Diferença planilha − aplicativo na vida de 200 mil km:

| Coluna | Receita | Pneus | Bateria auxiliar | Fluidos | Total | % do T511 |
|---|---|---|---|---|---|---|
| CX | ICEV-PBP_BISD2 | 0,0 | -0,0 | 0,00 | 0,0 | 0,00 |
| CY | ICEV-PBP_BISD2s | 0,0 | -0,0 | 0,00 | 0,0 | 0,00 |
| CZ | ICEV-PBP_BISD3 | 0,0 | -0,0 | 0,00 | 0,0 | 0,00 |
| DA | HEV-PBP_BISD6 | 7,0 | 9,2 | 0,01 | 16,2 | 0,22 |
| DB | PHEV-PBP_BISD8 | 7,0 | 9,2 | 0,01 | 16,2 | 0,18 |
| DC | BEV-PBP_BISD12 | 0,0 | -0,0 | 0,00 | 0,0 | 0,00 |
| EF | ICEV-PBP_BISD2 | 0,0 | 0,0 | 0,00 | 0,0 | 0,00 |
| EG | ICEV-PBP_BISD2s | 0,0 | 0,0 | 0,00 | 0,0 | 0,00 |
| EH | ICEV-PBP_BISD3 | 0,0 | 0,0 | 0,00 | 0,0 | 0,00 |
| EI | BEV-PBP_BISD12 | 0,0 | 0,0 | 0,00 | 0,0 | 0,00 |
| EJ | BEV-PBP_BISD12 | 0,0 | 0,0 | 0,00 | 0,0 | 0,00 |
| EK | BEV-PBP_BISD12 | 0,0 | 0,0 | 0,00 | 0,0 | 0,00 |
| EL | HEV-PBP_BISD6 | 0,0 | 0,0 | -0,00 | -0,0 | -0,00 |
| EM | HEV-PBP_BISD6 | 0,0 | 0,0 | -0,00 | -0,0 | -0,00 |
| EN | HEV-PBP_BISD6 | 0,0 | 0,0 | -0,00 | -0,0 | -0,00 |
| EO | PHEV-PBP_BISD8 | 0,0 | 0,0 | -0,00 | -0,0 | -0,00 |
| EP | PHEV-PBP_BISD8 | 0,0 | 0,0 | -0,00 | -0,0 | -0,00 |
| EQ | PHEV-PBP_BISD8 | 0,0 | 0,0 | -0,00 | -0,0 | -0,00 |

**Pendência:** identificar a fórmula própria dessas colunas (autor) antes de decidir se P31 ganha um cenário PBP.

## Efeito por ordem de grandeza

- Massa da glider no fim de vida: a linha 662 do M2 soma as massas de material e passa 0,1% da massa por grupo nas receitas com participação negativa zerada (divergência D8, já registrada): 0,5 a 0,8 kg, ou 0,1 a 0,2 kg CO₂e no fim de vida.

**Atualização de 19/11/2026 (B1-DIV-02).** O autor corrigiu a fórmula de `T495` nas 28 colunas em `LCA_LV_i3ET_20261119.xlsx`. A fixture `tests/fixtures/b1_reference.json` foi regerada dessa planilha: 122 colunas seguem o seletor e nenhuma é "antiga"; as 6 colunas PBP_BISD (`CX:DC`) ainda têm `T495` digitado (0), o que fica registrado como B1-DIV-03.
