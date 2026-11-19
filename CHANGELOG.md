# Changelog

## 0.11.0 - Bloco B1 (M1 and M2 complete)

Added
- Screens T12 Subsystems, T13 Mass parameters, T14 Materials and recipes,
  T15 Emission factors, T16 Maintenance, T17 End of life, T18 Vehicle life,
  T38 Mass validation, T46 Battery and assembly.
- Results tables C15 (replacements), C16 (end of life), C34 (mass validation),
  C35 (vehicle life by stage) and report tables R12 to R15.
- User copies of recipes (U-), batteries (UB-), assemblies (UA-), emission-factor
  versions and mass-parameter sets (UM-), merged in memory at load time; the
  reference data are never altered. Changes to emission factors are logged (D19).
- Mass calibration with the body share of the adjustment; end-of-life methods
  (glider + battery, aggregate vehicle, excluded); maintenance with replacement
  events counted per interval.
- Schema 0.11: `D06_Analysis.EoLMethod` and `D07_AnalysisVehicle` columns
  `DeclaredMassKg`, `MassAdjustmentKg`, `MassBodyShare`, `DeclaredSource`.
- `docs/05c-lista-de-diferencas-b1.md`: differences from the spreadsheet for the
  author to decide.

Changed
- Mass calibration (T38): the difference between declared and estimated mass is split between Body
  and Chassis in proportion to the estimated masses (`s = A_est/(A_est + B_est)`), unless the user sets
  `s`. The GREET Body/Chassis proportion (P63) is only a diagnostic (`C34.BodyShareEstimated`,
  `C34.BodyShareReference`); the T38 warns when the two differ by 5 points or more.
- The 0.9 emission-factor page was superseded by T15 (kept under `_superados/`).
- Runs store the B1 choices and the hashes of user recipes in the snapshot, only
  when they exist, so earlier run hashes do not change.

Known limitations
- UA- and UM- versions cannot yet be chosen in an analysis (foreign keys in D06/D02).
- Frozen emission factors (I53) are not enforced.

## 0.10.0 - Fase A
Project identity, analysis setup, control-panel parameters and frozen runs.
