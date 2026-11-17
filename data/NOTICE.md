# Data notice — attribution and conditions of use

**The data in this directory is not covered by the MIT licence of the code.**

It has several distinct origins, with different conditions. Sections 1 and 2 cover the
data of version 0.9.0; section 5 covers what version 0.10 (Fase A) added.

---

## 1. Emission factors derived from GREET

Versions `G22`, `G23` and `G24` of table `P10_EFVersion`, and the corresponding rows of
`P11_EmissionFactor`, `P19_BatteryModel`, `P20_BatteryMaterialShare`,
`P22_AssemblyEnergy` and `P25_FuelEmissionFactor`, derive from the **GREET model**
(Greenhouse gases, Regulated Emissions, and Energy use in Technologies).

> Copyright © UChicago Argonne, LLC. All rights reserved.
>
> GREET was developed by **Argonne National Laboratory**.
>
> Redistribution is permitted for **non-commercial use only**.

**Conditions we are bound by, and that anyone redistributing this data is bound by:**

1. This copyright notice and the disclaimer below must be kept with the data;
2. Argonne National Laboratory must be credited as the developer of GREET;
3. The GREET version must be identified in any publication of results. This repository
   satisfies that structurally: the version identifier `IDEFV` is part of the key of
   every result and is restated in every exported table;
4. **Modified input data must be declared.** It applies here. These values are **not**
   the original GREET files: they were extracted and processed through the `LCA_LV_i3ET`
   spreadsheet model. The column `P11_EmissionFactor.EFnotes` records the provenance of
   every single factor, including which ones have no published value in a given version.

Modification or reverse compilation of the GREET source code is not permitted. This
project does neither: it consumes published values and documents the extraction.

Licence terms: https://greet.anl.gov/copyright
GREET model: https://greet.anl.gov/

**Disclaimer.** The GREET model and its data are provided "as is". Neither the United
States Government, nor UChicago Argonne, LLC, nor any of their employees makes any
warranty, express or implied, or assumes any legal liability for the accuracy,
completeness, or usefulness of the information disclosed.

---

## 2. Brazilian emission factors

Versions `BR25BR` (100% domestic production), `BR25m` (Brazilian market mix) and
`BR25GLO` (international) derive from the **Projeto do Berço ao Portão**, carried out by
**FGV and Unicamp** for **Fundep**, under the **Programa Move** of the Brazilian federal
government.

These factors carry no restriction inherited from GREET. Their own conditions of
redistribution are to be registered in `P10_EFVersion.LicenseEFV` before wider
publication.

---

## 3. What this means in practice

| If you want to | Then |
|---|---|
| Use this tool for research, teaching or public policy | Go ahead. Cite GREET and its version, and this repository |
| Use it commercially | Do not use the `G22`, `G23` or `G24` versions. Supply your own factors — the interface supports user-defined emission factor versions, stored in your project file |
| Redistribute the data | Keep this notice intact, with the attribution and the declaration of processing |

---

## 4. A note on missing factors

Some materials have no published factor in some versions — the source shows `ND`. In
the database these appear as `NULL`, never as zero, and the calculation reports the
mass affected. **A missing factor is absence of data, not zero emissions**, and results
that compare versions may be comparing data coverage as much as environmental
performance. See section 16.5 of `docs/01-especificacao-funcional.md`.

---

## 5. Data added in version 0.10 (Fase A)

All of it was read from the i3ET spreadsheet `LCA_LV_i3ET_20261101.xlsx` (NIPE/UNICAMP)
by the scripts in `tools/`, and each table records the sheet and cell it came from.
**The conditions below must be settled before version 0.10.0 is published.**

| Data | Tables | Original source | Conditions of redistribution |
|---|---|---|---|
| Emission factor lists `GLO23`, `BR23` and its five variants | `P10`, `P11` | i3ET, sheet *Emission Factors GREET and BR* | Published with the report *Pegada de Carbono do Berço ao Portão* and made available to AEA and to the federal government with no restriction on use declared, with a caveat on how the factors were calculated. The i3ET author took part in preparing both and uses them as the report recommends (confirmed 17 Nov 2026); `P10.LicenseEFV` says so. GWP set `AR6-100`, the same as the other lists |
| PBEV records, edition 2026 | `P28`, `P36`, `P50`, `P55` | Programa Brasileiro de Etiquetagem Veicular, INMETRO | Public labelling data published by INMETRO. Credit INMETRO/PBEV and the edition. The copy here is the one kept in the i3ET spreadsheet, not a fresh download |
| Market vehicles and their parameters | `P26`, `P27`, `P54` | i3ET, sheet *Market Vehicles*: manufacturer data, PBEV data and the authors' own estimates | Compiled by the i3ET authors. `P27.ValueClass` separates typed values from defaults and calculated ones |
| Units licensed per vehicle (the 50 most licensed passenger cars and the 50 most licensed light commercials; cumulative January to December), reference year in `P26.SalesRefYear` | `P26.SalesUnits`, `P26.SalesClass`, `P26.SalesRefYear` | **FENABRAVE** (Federação Nacional da Distribuição de Veículos Automotores), public licensing reports, read through the i3ET sheets *Most Licensed 2025* | Published openly by FENABRAVE; the author found no restriction on use (17 Nov 2026). **Cite FENABRAVE as the source** in the documentation and in the app (report, reference year, access date, address). The figures are used only as weights among these vehicles; they are not the whole market (see ANFAVEA below). The author may also notify FENABRAVE of the academic, non-profit use. Option kept open: store only the normalized shares instead of the units |
| Total licensing by year (passenger cars, light commercials, trucks, buses) — **planned, Phase B**, with the FENABRAVE import (T40) | planned table `P59` (`P58` is the generic battery model) | **ANFAVEA** (Associação Nacional dos Fabricantes de Veículos Automotores), monthly bulletin (*Carta da Anfavea*) and yearly *Anuário*, source Renavam/Denatran | To be imported. Same criterion as FENABRAVE and the INMETRO PBEV (decided by the author on 17 Nov 2026): cite ANFAVEA as the source (report, year, access date, address), keep the published units, and record that no restriction on use was found when the publications are read before loading. Purpose: coverage of the FENABRAVE top 50 against the ANFAVEA total, and later the fleet analysis
| Control-panel parameters, categories, outputs, reference values | `P29`, `P30`, `P51`, `P52` | i3ET, sheet *i3ET Control Panel* | Part of the i3ET model. The bibliographic source of each parameter is in `P30.Reference` |
| Default rules and combined-power factors | `P35`, `P49`, `P53`, `P56` | i3ET, sheets *Market Vehicles* and *Control Panel*; project decisions of 16–17 Nov 2026 | Part of this project |
| Vehicle material recipes (56 from the i3ET sheet *M2 GHG Mfg Module*, columns T:CA: GREET 2022, 2023 and 2024 vehicle compositions, including fuel cell, plus the 12 recipes from version 0.9.0) | `P15`, `P16` | i3ET, sheet *M2 GHG Mfg Module*; the GREET compositions come from Argonne National Laboratory's GREET model, normalised by the i3ET authors | The GREET conditions of section 1 apply (credit Argonne and the GREET version). The normalisation is part of the i3ET model |
| Material equivalence (single aluminium to sheet and extrusion) | `P57` | Weights from the 30 GREET 2024 recipes of this project that the base calculates; project decision of 17 Nov 2026 | Part of this project |

