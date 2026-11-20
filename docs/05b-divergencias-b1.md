# Relatório de Divergências — anexo do bloco B1

**Data:** 20/11/2026 · **Fonte:** `LCA_LV_i3ET_20261101.xlsx` · Gerado por `tools/report_b1_divergences.py` · Complementa `05-relatorio-de-divergencias.md` e `05a-divergencias-fase-a.md`

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
## B1-DIV-03 — Colunas PBP_BISD (resolvida em 20/11/2026)

As colunas `CX:DC` e as demais do Projeto do Berço ao Portão traziam `T495` digitado (0) e, na comparação, pneus e bateria auxiliar aparentemente próprios. O autor reconstruiu as fórmulas em `LCA_LV_i3ET_20261119.xlsx`: as 128 colunas completas do M2 seguem agora o seletor `P495`, e as 18 colunas PBP_BISD passam a reproduzir as reposições do aplicativo (P31) no teste de paridade. Não é necessário um cenário PBP em P31.

## Efeito por ordem de grandeza

- Massa da glider no fim de vida: a linha 662 do M2 soma as massas de material e passa 0,1% da massa por grupo nas receitas com participação negativa zerada (divergência D8, já registrada): 0,5 a 0,8 kg, ou 0,1 a 0,2 kg CO₂e no fim de vida.

