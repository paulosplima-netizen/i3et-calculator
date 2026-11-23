# Changelog

## Unreleased - Bloco B2 (imports and reference vehicles; in progress)

## B2c (23/11/2026)

- Decisão 18: o fator da área frontal (0,85) é o parâmetro `FRONTAL_AREA_FACTOR` da P59; o `ParamBaseHash` mudou para `c972269f…` e a regressão congelada foi atualizada.
- Decisão 17: os segmentos da P70 são editáveis pelo Master na T42 (coluna `Origin`); o padrão é o do Excel e pode ser restaurado.
- Decisão 19: a T42 calcula a referência de qualquer motorização e mostra os veículos de mercado mais próximos da referência ponderada (a título de ilustração).
- Decisão 11: uma série FENABRAVE por ano (`save_edition` só aceita acumulado de janeiro, adota a edição mais recente de cada ano e marca parcial); a T42 escolhe o ano.
- Decisão 24: P72 recebe a série 1957–2025 da aba Fleet Characteristics do i3EF (`SourceName = 'i3EF'`; antes de 2016 vale o i3EF, de 2016 em diante fica só para comparação); `tools/import_fleet_characteristics.py`.

### B2b (22/11/2026): divisao por motorizacao, ANFAVEA e FENABRAVE

- P72_FleetLicensingByPowertrain (330 linhas): emplacamento ANFAVEA 2016-2025 por combustivel/tecnologia (2.2.8, 4 classes), eletrificados por tecnologia (2.2.9, automoveis e comerciais leves) e cilindrada (2.2.10, automoveis, sem eletricos); importada por `tools/import_anfavea.py`; formato longo, cada linha confere o total da fonte.
- Decisoes do autor: 4 (leitura direta do PDF; `pdfplumber==0.11.10` entra em `requirements.txt`), 5 (edicoes do master na base de referencia, publicadas por commit; edicoes do usuario por arquivo, Google Drive/OneDrive na Fase C), 9 (uma linha por modelo e motorizacao; candidatas: informativo → edicao anterior → PBEV → master), 13 (recalculo da C33 opcional e exportavel para Excel), 14 (Anuario ANFAVEA 2026; vale a edicao mais recente).
- Esquema: `P47` ganha `UnitsReported`, `UnitsPrevious`, `UnitsPBEV`, `SplitMethod`, `SplitBasis`; `P60` passa a ter `SourceEdition` e `IsAdopted` (ANFAVEA 1957-2025 e total FENABRAVE 2025); nova `P71_FleetEstimate` (frota estimada 2000-2025). `ParamBaseHash` inalterado.
- `core/market_data.py`: MD8 (tabelas do Anuario), MD9 (candidatas de divisao, gravacao da edicao), MD10 (quadro design x motorizacao), MD11 (comparacao e exportacao Excel). `tools/import_anfavea.py`.
- T40: candidatas lado a lado, digitacao do master, gravacao e exportacao; T42: tres niveis de cobertura (6 referencias, 50+50, total FENABRAVE), quadro design x motorizacao e exportacao Excel.
- Correcao: o 2.424.281 e a soma dos rankings 50+50 (inclui van e chassi), nao um total; o total de mercado e 2.549.462 (FENABRAVE Ed. 276).
- 496 testes passam.

Added (21/11/2026)
- Schema 0.12, block S15: `P48_MarketSalesEdition`, `P47_MarketSales` (FENABRAVE licensing by
  model), `P60_FleetLicensingTotal` (ANFAVEA), `P70_ReferenceSegment`; editorial tables (outside
  `ParamBaseHash`), not copied to project files. Loaded by `tools/load_b2.py` from
  `data/csv/fase_b`, built by `tools/import_fenabrave.py`.
- `core/market_data.py`: name normalisation, FENABRAVE bulletin and PBEV table readers,
  catalogue matching (exact, split by powertrain, differs, none), weighted reference vehicles
  (C33: reproduces the 60 averaged values of the Excel model and the 82.9% coverage), PBEV
  edition comparison.
- T39 PBEV import, T40 FENABRAVE import, T42 Weighted references (Auxiliary Data; master user
  only; compare and show, they do not write). Decisions pending: `docs/11`, section 5.

## 0.11.0 - Bloco B1 (M1 and M2 complete)

Changed (21/11/2026)
- Projects are saved in a fixed folder (`ui/storage.py`: `I3ET_PROJECTS_DIR` or `local_settings.json`),
  listed on Home ("Saved projects") and kept after a restart; without a folder the old temporary
  mode stays (cloud). The storage module is the single door for the future server storage.

Changed (20/11/2026)
- T08 Export: new "Prepare Excel, CSV and report" for a frozen run (tables R00-R15 recalculated
  from the snapshot, validated), following the T47 display format; JSON stays full precision.
  T05 and T06 show indicators in the T47 format (`formatting.indicator`). T16 has no quantities
  of the format classes (km intervals), so it is unchanged.
- T15 Emission factors and T17 End of life now follow the display format of T47 (decimal places
  and units); before, they showed the raw values. History and corrections keep full precision.
- T14 Materials and recipes: new "All groups (vehicle bill of materials)" option in the Group
  list. It sums the mass of each material over all GREET groups of one vehicle of a frozen run,
  with a switch to include or leave out the traction battery (`core.materials.vehicle_bill`).
- Mass calibration follows parameter 25: a known mass (market vehicle) is calibrated
  automatically (gap goes to Body and Chassis by the estimated share); a calculated parameter 25
  (theoretical vehicle) is not allocated. New D07.MassCalibrationMode (ON/OFF) and C34.MassBasis
  values; T38 shows the basis and the automatic switch.
- T18 Vehicle life merges the 0.9 Results screen and the 0.11 Vehicle life screen (tabs: life
  stages, initial production, GREET group, material, battery, assembly); the 0.9 page moved to
  `_superados/`. `core.run.recompute` rebuilds the cradle-to-gate detail of a frozen run.
- Reference fixture regenerated from LCA_LV_i3ET_20261119.xlsx: the six PBP_BISD columns
  (CX:DC) now follow the P495 switch and match the replacements of the app (B1-DIV-03 closed).

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

- T47 Display format and table `D22_FormatSetting` (`core/formatting.py`): decimals per quantity,
  kg/t, % or fraction, separators, CSV separator, scientific-notation threshold, profiles default,
  article and audit. It changes only the display (screens T13, T14, T18, T38, T46, the HTML report,
  XLSX cell formats and CSV); calculations and frozen results are never rounded, and the CSV is rounded
  only on request. Without a saved format the exports are as before.
- Emission-factor lists of type Typed can be corrected in the project (decision 11): `D05` no longer
  has a foreign key to `D04`; Published lists are locked and can be copied to a Typed version
  (`ef_edit.copy_to_typed`); results show "Typed, altered"; the corrections can be exported (T15).

- Your own mass-parameter sets (UM-) and assembly versions (UA-), and your emission-factor
  lists, can be chosen in an analysis (T03): `D02` and `D06` no longer have a foreign key on
  `IDMPV` and `IDAPV` (rule I60).

Changed
- I53 also covers UA- and UM- versions (`user_versions` in the snapshot).
- I53: a frozen run stores the hash of the effective emission factors of user or altered lists
  (`emission_factors` in the snapshot); executing it after the factors changed is refused.
- T12: the caption on IDSG 43 no longer calls row 37 of M1 a defect: it is the hybrid combination
  module (additional mass), with its own parameters and GREET group D.
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
