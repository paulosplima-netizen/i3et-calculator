# Data notice — attribution and conditions of use

**The data in this directory is not covered by the MIT licence of the code.**

It has two distinct origins, with different conditions.

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
