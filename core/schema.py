"""Relational schema of the i3ET Calculator.

This module is the normative definition of the database. It mirrors chapter 10
of Documento 2 (Dicionário de Dados e Modelo Relacional).

Naming: table and column names follow the i3ET and GREET conventions and are
kept in English, even though the project documentation is in Portuguese.

Layers
------
P*  parameters, read-only reference base
D*  scenario data, owned by the user's project file
C*  calculated tables, rebuilt on every run
M*  run metadata and validation log

Schema 0.10 (Fase A) is appended at the end of the module, in blocks S5 to S8.
"""

from __future__ import annotations

import sqlite3

# --------------------------------------------------------------------------
# Parameters (P) — reference base, read-only
# --------------------------------------------------------------------------
DDL_PARAMS = """
CREATE TABLE P01_DataDictionary (
  IDTable                  TEXT    NOT NULL,
  ColumnName               TEXT    NOT NULL,
  ColumnOrder              INTEGER NOT NULL,
  SQLType                  TEXT    NOT NULL CHECK (SQLType IN ('INTEGER','REAL','TEXT','DATE')),
  KeyRole                  TEXT    NOT NULL CHECK (KeyRole IN ('PK','FK','-')),
  FKTarget                 TEXT,
  Unit                     TEXT,
  ParamClass               TEXT    NOT NULL,
  Required                 INTEGER NOT NULL CHECK (Required IN (0,1)),
  Domain                   TEXT,
  DsColumnName             TEXT,
  ColumnCalculationFormula TEXT,
  TableName                TEXT    NOT NULL,
  PRIMARY KEY (IDTable, ColumnName)
);

CREATE TABLE P02_VehicleSubgroup (
  IDSG INTEGER PRIMARY KEY,
  DsSG TEXT NOT NULL
);

CREATE TABLE P03_GenericGroup (
  IDG INTEGER PRIMARY KEY,
  DsG TEXT NOT NULL
);

CREATE TABLE P04_GreetGroup (
  IDGG      TEXT PRIMARY KEY,
  DsGG      TEXT NOT NULL,
  IsBattery INTEGER NOT NULL DEFAULT 0 CHECK (IsBattery IN (0,1))
);

CREATE TABLE P05_MassParamVersion (
  IDMPV     INTEGER PRIMARY KEY,
  DsMPV     TEXT NOT NULL,
  DateIDMPV DATE NOT NULL,
  SourceMPV TEXT
);

CREATE TABLE P07_VehicleParam (
  IDVP       INTEGER PRIMARY KEY,
  DsVP       TEXT NOT NULL,
  utVP       TEXT,
  ParamClass TEXT NOT NULL CHECK (ParamClass IN ('Exo','End','Res')),
  GCEquation TEXT,
  AppliesTo  TEXT
);

CREATE TABLE P06_MassEstimationParam (
  IDMPV     INTEGER NOT NULL REFERENCES P05_MassParamVersion(IDMPV),
  IDSG      INTEGER NOT NULL REFERENCES P02_VehicleSubgroup(IDSG),
  Beta      REAL NOT NULL CHECK (Beta >= 0),
  GCR       REAL NOT NULL CHECK (GCR  >  0),
  utGCR     TEXT,
  MR        REAL NOT NULL CHECK (MR   >= 0),
  fLM       REAL NOT NULL DEFAULT 1.0 CHECK (fLM > 0),
  Reference TEXT,
  PRIMARY KEY (IDMPV, IDSG)
);

CREATE TABLE P08_SubgroupCorrelation (
  IDSG        INTEGER PRIMARY KEY REFERENCES P02_VehicleSubgroup(IDSG),
  IDVP        INTEGER NOT NULL REFERENCES P07_VehicleParam(IDVP),
  IDG         INTEGER NOT NULL REFERENCES P03_GenericGroup(IDG),
  IDGG        TEXT    NOT NULL REFERENCES P04_GreetGroup(IDGG),
  ExcludedVPT TEXT
);

CREATE TABLE P09_Material (
  IDM          TEXT PRIMARY KEY,
  DsM          TEXT NOT NULL,
  Mspec        TEXT,
  EFBasis      TEXT NOT NULL DEFAULT 'mass' CHECK (EFBasis IN ('mass','energy','vehicle')),
  EFBasisParam INTEGER REFERENCES P07_VehicleParam(IDVP),
  IsProcess    INTEGER NOT NULL DEFAULT 0 CHECK (IsProcess IN (0,1)),
  ShareRole    TEXT NOT NULL DEFAULT 'material'
               CHECK (ShareRole IN ('material','process','breakdown'))
);

CREATE TABLE P10_EFVersion (
  IDEFV      TEXT PRIMARY KEY,
  DsEFV      TEXT NOT NULL,
  DateIDEFV  DATE NOT NULL,
  GWPSet     TEXT NOT NULL DEFAULT 'AR6-100',
  SourceEFV  TEXT NOT NULL,
  LicenseEFV TEXT
);

CREATE TABLE P11_EmissionFactor (
  IDM     TEXT NOT NULL REFERENCES P09_Material(IDM),
  IDEFV   TEXT NOT NULL REFERENCES P10_EFVersion(IDEFV),
  -- EF is nullable on purpose: NULL means "no factor published for this
  -- material in this version" (the source shows 'ND'), which is NOT the same
  -- as zero emissions. The calculation contributes 0 for it but counts the
  -- mass in C14.MassNoFactor, so a result never presents missing data as if
  -- it were good news. See Documento 1, secao 16.5.
  EF      REAL CHECK (EF IS NULL OR EF >= 0),
  EFnotes TEXT NOT NULL,
  PRIMARY KEY (IDM, IDEFV)
);

CREATE TABLE P12_Powertrain (
  IDVPT TEXT PRIMARY KEY,
  DsVPT TEXT NOT NULL
);

CREATE TABLE P13_DesignType (
  IDVDT TEXT PRIMARY KEY,
  DsVDT TEXT NOT NULL
);

CREATE TABLE P14_VehicleSize (
  IDVS TEXT PRIMARY KEY,
  DsVS TEXT NOT NULL
);

CREATE TABLE P15_VehicleMaterialRecipe (
  IDVMR TEXT PRIMARY KEY,
  IDVPT TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDVDT TEXT REFERENCES P13_DesignType(IDVDT),
  IDVS  TEXT REFERENCES P14_VehicleSize(IDVS),
  DsVMR TEXT
);

CREATE TABLE P16_MaterialShare (
  IDVMR    TEXT NOT NULL REFERENCES P15_VehicleMaterialRecipe(IDVMR),
  IDGG     TEXT NOT NULL REFERENCES P04_GreetGroup(IDGG),
  IDM      TEXT NOT NULL REFERENCES P09_Material(IDM),
  -- Only rows whose material has ShareRole = 'material' are mass fractions
  -- that must add up to 1 (invariant I1, checked in validate.py). Rows for
  -- process pseudo-materials carry a conversion coefficient instead, so the
  -- column constraint here is only non-negativity.
  MshareGG REAL NOT NULL CHECK (MshareGG >= 0),
  PRIMARY KEY (IDVMR, IDGG, IDM)
);

CREATE TABLE P17_BatteryType (
  IDBTy TEXT PRIMARY KEY,
  DsBTy TEXT NOT NULL
);

CREATE TABLE P18_BatteryTechnology (
  IDBTe TEXT PRIMARY KEY,
  IDBTy TEXT NOT NULL REFERENCES P17_BatteryType(IDBTy),
  DsBTe TEXT
);

CREATE TABLE P19_BatteryModel (
  IDBMd                    TEXT PRIMARY KEY,
  IDEFV                    TEXT REFERENCES P10_EFVersion(IDEFV),
  IDVPT                    TEXT REFERENCES P12_Powertrain(IDVPT),
  IDBTe                    TEXT REFERENCES P18_BatteryTechnology(IDBTe),
  -- These are nullable because a battery model is dimensioned either by
  -- energy (BEV, PHEV: RefEnergy set, RefPower absent) or by power (HEV: the
  -- reverse). NULL means "does not apply to this chemistry", which the mass
  -- rule of Documento 1 secao 7.3 reads as the 'ND' of the source.
  RefRange                 REAL CHECK (RefRange    IS NULL OR RefRange    >= 0),
  RefEnergy                REAL CHECK (RefEnergy   IS NULL OR RefEnergy   >= 0),
  RefPower                 REAL CHECK (RefPower    IS NULL OR RefPower    >= 0),
  RefWeight                REAL CHECK (RefWeight   IS NULL OR RefWeight   >= 0),
  RefGHGIDBMd              REAL CHECK (RefGHGIDBMd IS NULL OR RefGHGIDBMd >= 0),
  EnergyDensity            REAL,
  PowerDensity             REAL,
  GravimetricEnergyDensity REAL,
  GravimetricPowerDensity  REAL,
  GravimetricGHGDensity    REAL,
  EnergyGHGDensity         REAL,
  -- How this battery's emissions are obtained. The i3ET decides by the prefix
  -- of the identifier ("PB..."); here the choice is explicit and follows what
  -- the data actually supports: 'composition' sums the materials of P20,
  -- 'gravimetric' multiplies the battery mass by GravimetricGHGDensity,
  -- 'none' is the row for vehicles without a traction battery.
  GHGMethod                TEXT NOT NULL DEFAULT 'composition'
                           CHECK (GHGMethod IN ('composition','gravimetric','none')),
  DsBMd                    TEXT,
  CHECK (GHGMethod <> 'gravimetric' OR GravimetricGHGDensity IS NOT NULL)
);

CREATE TABLE P20_BatteryMaterialShare (
  IDBMd     TEXT NOT NULL REFERENCES P19_BatteryModel(IDBMd),
  IDGG      TEXT NOT NULL REFERENCES P04_GreetGroup(IDGG),
  IDM       TEXT NOT NULL REFERENCES P09_Material(IDM),
  -- Same as P16: a mass fraction for 'material' rows, a conversion
  -- coefficient for process rows. IDM 86 (Lithium Ion Battery Assembly) uses
  -- values between 1.1 and 2.3, which are not fractions -- its factor is in
  -- kg CO2e/kWh. Invariant I2 sums only the 'material' rows.
  BMshareGG REAL NOT NULL CHECK (BMshareGG >= 0),
  PRIMARY KEY (IDBMd, IDGG, IDM)
);

CREATE TABLE P21_AssemblyProcess (
  IDAP        INTEGER PRIMARY KEY,
  DsAP        TEXT NOT NULL,
  IncludedInA INTEGER NOT NULL DEFAULT 1 CHECK (IncludedInA IN (0,1)),
  NotesAP     TEXT
);

CREATE TABLE P23_AssemblyParamVersion (
  IDAPV              TEXT PRIMARY KEY,
  DsAPV              TEXT NOT NULL,
  DateIDAPV          DATE NOT NULL,
  Method             TEXT NOT NULL DEFAULT 'from_EF'
                     CHECK (Method IN ('from_EF','process','fixed')),
  FixedGHGPerVehicle REAL CHECK (FixedGHGPerVehicle IS NULL OR FixedGHGPerVehicle >= 0),
  Status             TEXT NOT NULL DEFAULT 'recommended'
                     CHECK (Status IN ('recommended','legacy')),
  IDEFVdefault       TEXT REFERENCES P10_EFVersion(IDEFV),
  SourceAPV          TEXT NOT NULL,
  CHECK (Method <> 'fixed' OR FixedGHGPerVehicle IS NOT NULL)
);

CREATE TABLE P24_EnergyCarrier (
  IDFuel TEXT PRIMARY KEY,
  DsFuel TEXT NOT NULL
);

CREATE TABLE P22_AssemblyEnergy (
  IDAPV            TEXT    NOT NULL REFERENCES P23_AssemblyParamVersion(IDAPV),
  IDAP             INTEGER NOT NULL REFERENCES P21_AssemblyProcess(IDAP),
  IDFuel           TEXT    NOT NULL REFERENCES P24_EnergyCarrier(IDFuel),
  EnergyPerVehicle REAL    NOT NULL CHECK (EnergyPerVehicle >= 0),
  FuelShare        REAL    NOT NULL CHECK (FuelShare BETWEEN 0 AND 1),
  PRIMARY KEY (IDAPV, IDAP, IDFuel)
);

CREATE TABLE P25_FuelEmissionFactor (
  IDFuel      TEXT NOT NULL REFERENCES P24_EnergyCarrier(IDFuel),
  IDEFV       TEXT NOT NULL REFERENCES P10_EFVersion(IDEFV),
  EFfuel      REAL NOT NULL,
  EFfuelNotes TEXT,
  PRIMARY KEY (IDFuel, IDEFV)
);
"""

# --------------------------------------------------------------------------
# Scenario data (D) — the user's project file
# --------------------------------------------------------------------------
DDL_SCENARIO = """
CREATE TABLE D01_Vehicle (
  IDV           INTEGER PRIMARY KEY,
  DsV           TEXT NOT NULL,
  IDVPT         TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDVDT         TEXT NOT NULL REFERENCES P13_DesignType(IDVDT),
  IDVS          TEXT NOT NULL REFERENCES P14_VehicleSize(IDVS),
  IDLR          TEXT NOT NULL CHECK (IDLR IN ('Regular','Luxury')),
  IsUserDefined INTEGER NOT NULL DEFAULT 0 CHECK (IsUserDefined IN (0,1)),
  NotesIDV      TEXT
);

CREATE TABLE D02_EvaluationAlternative (
  IDV       INTEGER NOT NULL REFERENCES D01_Vehicle(IDV),
  IDEA      INTEGER NOT NULL,
  IDMPV     INTEGER NOT NULL REFERENCES P05_MassParamVersion(IDMPV),
  IDVMR     TEXT    NOT NULL REFERENCES P15_VehicleMaterialRecipe(IDVMR),
  IDEFV     TEXT    NOT NULL,
  IDAPV     TEXT    NOT NULL REFERENCES P23_AssemblyParamVersion(IDAPV),
  Boundary  TEXT    NOT NULL DEFAULT 'MAT_ASM' CHECK (Boundary IN ('MAT','MAT_ASM')),
  NotesIDEA TEXT,
  PRIMARY KEY (IDV, IDEA)
);

CREATE TABLE D03_VehicleParamValue (
  IDV          INTEGER NOT NULL REFERENCES D01_Vehicle(IDV),
  IDVP         INTEGER NOT NULL REFERENCES P07_VehicleParam(IDVP),
  GC           REAL    NOT NULL DEFAULT 0,
  GCText       TEXT,
  IsCalculated INTEGER NOT NULL DEFAULT 0 CHECK (IsCalculated IN (0,1)),
  PRIMARY KEY (IDV, IDVP)
);

CREATE TABLE D04_UserEFVersion (
  IDEFV        TEXT PRIMARY KEY,
  DsEFV        TEXT NOT NULL,
  DateIDEFV    DATE NOT NULL,
  GWPSet       TEXT NOT NULL DEFAULT 'AR6-100',
  SourceEFV    TEXT NOT NULL,
  LicenseEFV   TEXT,
  BasedOnIDEFV TEXT REFERENCES P10_EFVersion(IDEFV)
);

CREATE TABLE D05_UserEmissionFactor (
  IDM     TEXT NOT NULL REFERENCES P09_Material(IDM),
  IDEFV   TEXT NOT NULL REFERENCES D04_UserEFVersion(IDEFV),
  EF      REAL NOT NULL CHECK (EF >= 0),
  EFnotes TEXT,
  PRIMARY KEY (IDM, IDEFV)
);
"""

# D02.IDEFV has no FOREIGN KEY on purpose: it may name a version of the
# reference base (P10) or one the user created (D04). Rule I14 forbids the two
# from colliding, and validate.py checks that every IDEFV used resolves to
# exactly one of them. A FK to a single table would make user versions
# impossible; a FK to both is not expressible in SQL.

# --------------------------------------------------------------------------
# Effective emission factors: base + user versions, user takes precedence
# --------------------------------------------------------------------------
DDL_VIEWS = """
CREATE VIEW EF_Effective AS
  SELECT IDM, IDEFV, EF, EFnotes, 0 AS IsUserDefined
    FROM P11_EmissionFactor
  UNION ALL
  SELECT IDM, IDEFV, EF, EFnotes, 1
    FROM D05_UserEmissionFactor
  UNION ALL
  SELECT p.IDM, v.IDEFV, p.EF, p.EFnotes, 1
    FROM D04_UserEFVersion v
    JOIN P11_EmissionFactor p ON p.IDEFV = v.BasedOnIDEFV
   WHERE NOT EXISTS (SELECT 1 FROM D05_UserEmissionFactor d
                      WHERE d.IDEFV = v.IDEFV AND d.IDM = p.IDM);
"""

# --------------------------------------------------------------------------
# Calculated tables (C) and run metadata (M)
# --------------------------------------------------------------------------
DDL_CALC = """
CREATE TABLE C01_MassBySubgroup (
  IDV  INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDSG INTEGER NOT NULL,
  IDGG TEXT NOT NULL, IDVP INTEGER NOT NULL,
  GC   REAL NOT NULL, Beta REAL NOT NULL, GCR REAL NOT NULL,
  MR   REAL NOT NULL, fLM  REAL NOT NULL, ME  REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDSG)
);

CREATE TABLE C02_MassByGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL,
  MassIDGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG)
);

CREATE TABLE C03_MassByMaterialGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  MshareGG REAL NOT NULL, MassIDMpGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG, IDM)
);

CREATE TABLE C04_GHGByMaterialGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  EF REAL, GHGIDMpGG REAL NOT NULL, HasFactor INTEGER NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG, IDM)
);

CREATE TABLE C05_GHGByGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL,
  GHGIDGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG)
);

CREATE TABLE C06_BatteryMassByMaterial (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDBMd TEXT NOT NULL,
  IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  BMshareGG REAL NOT NULL, MassIDMpGGB REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDBMd, IDGG, IDM)
);

CREATE TABLE C07_BatteryGHGByMaterial (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDBMd TEXT NOT NULL,
  IDGG TEXT NOT NULL, IDM TEXT NOT NULL,
  EF REAL, GHGIDMpGGB REAL NOT NULL, HasFactor INTEGER NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDBMd, IDGG, IDM)
);

CREATE TABLE C10_MassGHGByGroup (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDGG TEXT NOT NULL,
  MassIDGG REAL NOT NULL, GHGIDGG REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDGG)
);

CREATE TABLE C11_MassGHGByMaterial (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDM TEXT NOT NULL,
  MassIDM REAL NOT NULL, GHGIDM REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDM)
);

CREATE TABLE C12_MassGHGByVehicle (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL,
  MassIDV REAL NOT NULL, GHGIDV REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA)
);

CREATE TABLE C13_AssemblyGHG (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL, IDAP INTEGER NOT NULL,
  EnergyPerVehicle REAL NOT NULL, GHGAssembly REAL NOT NULL,
  PRIMARY KEY (IDV, IDEA, IDAP)
);

CREATE TABLE C14_CradleToGate (
  IDV INTEGER NOT NULL, IDEA INTEGER NOT NULL,
  MassIDV         REAL NOT NULL,
  GHGMaterials    REAL NOT NULL,
  GHGAssembly     REAL NOT NULL,
  GHGCradleToGate REAL NOT NULL,
  GHGperKg        REAL,
  MassNoFactor    REAL NOT NULL DEFAULT 0,
  ShareNoFactor   REAL NOT NULL DEFAULT 0,
  PRIMARY KEY (IDV, IDEA)
);

CREATE TABLE M01_RunMetadata (
  RunID             TEXT PRIMARY KEY,
  RunTimestamp      TEXT NOT NULL,
  CalculatorVersion TEXT NOT NULL,
  ParamBaseHash     TEXT NOT NULL,
  ProjectName       TEXT,
  ValidationStatus  TEXT NOT NULL
);

CREATE TABLE M02_ValidationLog (
  RunID    TEXT NOT NULL REFERENCES M01_RunMetadata(RunID),
  Severity TEXT NOT NULL CHECK (Severity IN ('INFO','AVISO','ERRO')),
  RuleID   TEXT NOT NULL,
  Message  TEXT NOT NULL,
  Context  TEXT
);
"""

DDL_INDEXES = """
CREATE INDEX ix_P11_EFV ON P11_EmissionFactor (IDEFV);
CREATE INDEX ix_P16_GG  ON P16_MaterialShare  (IDGG, IDM);
CREATE INDEX ix_P20_GG  ON P20_BatteryMaterialShare (IDGG, IDM);
CREATE INDEX ix_D03_VP  ON D03_VehicleParamValue (IDVP);
"""

#: Tables of the reference base, in dependency order (parents first).
PARAM_TABLES = [
    "P01_DataDictionary", "P02_VehicleSubgroup", "P03_GenericGroup",
    "P04_GreetGroup", "P05_MassParamVersion", "P07_VehicleParam",
    "P06_MassEstimationParam", "P08_SubgroupCorrelation", "P09_Material",
    "P10_EFVersion", "P11_EmissionFactor", "P12_Powertrain", "P13_DesignType",
    "P14_VehicleSize", "P15_VehicleMaterialRecipe", "P16_MaterialShare",
    "P17_BatteryType", "P18_BatteryTechnology", "P19_BatteryModel",
    "P20_BatteryMaterialShare", "P21_AssemblyProcess",
    "P23_AssemblyParamVersion", "P24_EnergyCarrier", "P22_AssemblyEnergy",
    "P25_FuelEmissionFactor",
]

#: Tables of the user's project file, in dependency order.
SCENARIO_TABLES = [
    "D01_Vehicle", "D02_EvaluationAlternative", "D03_VehicleParamValue",
    "D04_UserEFVersion", "D05_UserEmissionFactor",
]

#: Sheet name in the source workbook -> table name in the database.
SHEET_TO_TABLE = {t.split("_")[0]: t for t in PARAM_TABLES + SCENARIO_TABLES}


def create_schema(conn: sqlite3.Connection, *, with_calc: bool = True) -> None:
    """Create every table, view and index on an empty connection."""
    conn.executescript("PRAGMA foreign_keys = ON;")
    conn.executescript(DDL_PARAMS)
    conn.executescript(DDL_SCENARIO)
    if with_calc:
        conn.executescript(DDL_CALC)
    conn.executescript(DDL_VIEWS)
    conn.executescript(DDL_INDEXES)
    if with_calc:
        # Os blocos S5 a S7 dependem de M01, que so existe com as tabelas C e M.
        apply_010(conn)
        apply_011(conn)
    conn.commit()


# ==========================================================================
# SCHEMA 0.10 -- Fase A: navegacao, projeto e analise
# ==========================================================================
# Documento de referencia: docs/07-dicionario-de-dados-fase-a.md, que detalha
# docs/06-fase-a-navegacao-projeto-e-analise.md.
#
# Os blocos S1 a S4 sao os da 0.9.0, acima, e nao mudam:
#   S1 parametros (DDL_PARAMS)      S3 visoes e indices (DDL_VIEWS, DDL_INDEXES)
#   S2 cenario (DDL_SCENARIO)       S4 calculo e metadados (DDL_CALC)
# Os blocos novos sao:
#   S5 parametros da Fase A         S7 identidade do projeto
#   S6 analise, rodada e resultado  S8 migracao 0.9 -> 0.10
#
# Todo CREATE dos blocos S5 a S7 usa IF NOT EXISTS. E o que permite aplicar os
# mesmos blocos a um banco vazio e a um projeto da 0.9.0 ja preenchido.

#: Versao do esquema do arquivo de projeto, gravada em M03_Project.
SCHEMA_VERSION = "0.11"

# --------------------------------------------------------------------------
# BLOCO S5 -- Parametros da Fase A (P26 a P30, P35, P36, P49 a P55)
#   O que faz : cria as tabelas de parametros novas, vazias.
#   Le        : nada. Os dados entram no passo 3 (fixtures).
#   Devolve   : DDL_PARAMS_010, executado por create_schema() e migrate().
# --------------------------------------------------------------------------
DDL_PARAMS_010 = """
CREATE TABLE IF NOT EXISTS P54_MarketParam (
  IDMP        INTEGER PRIMARY KEY CHECK (IDMP BETWEEN 1 AND 99),
  DsMP        TEXT NOT NULL,
  utMP        TEXT,
  SheetColumn TEXT NOT NULL,
  IDVP        INTEGER REFERENCES P07_VehicleParam(IDVP),
  ValueKind   TEXT NOT NULL DEFAULT 'Num' CHECK (ValueKind IN ('Num','Text'))
);

CREATE TABLE IF NOT EXISTS P26_MarketVehicle (
  IDMV               INTEGER PRIMARY KEY,
  DsMV               TEXT NOT NULL UNIQUE,
  Brand              TEXT,
  Model              TEXT,
  IDVPT              TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDVDT              TEXT NOT NULL REFERENCES P13_DesignType(IDVDT),
  IDVS               TEXT NOT NULL REFERENCES P14_VehicleSize(IDVS),
  IDLR               TEXT NOT NULL CHECK (IDLR IN ('Regular','Luxury')),
  Fuel               TEXT,
  MarketGroup        TEXT,
  SalesClass         TEXT NOT NULL DEFAULT 'ND' CHECK (SalesClass IN ('V','CL','ND')),
  SalesRefYear       INTEGER,
  SalesUnits         INTEGER CHECK (SalesUnits IS NULL OR SalesUnits >= 0),
  IsSelecao          INTEGER NOT NULL DEFAULT 0 CHECK (IsSelecao IN (0,1)),
  IDMVRepresentative INTEGER REFERENCES P26_MarketVehicle(IDMV),
  SheetRow           INTEGER,
  NotesMV            TEXT,
  SourceMV           TEXT
);

CREATE TABLE IF NOT EXISTS P27_MarketVehicleParam (
  IDMV       INTEGER NOT NULL REFERENCES P26_MarketVehicle(IDMV),
  IDMP       INTEGER NOT NULL REFERENCES P54_MarketParam(IDMP),
  Value      REAL,
  ValueText  TEXT,
  ValueClass TEXT NOT NULL
             CHECK (ValueClass IN ('Man','Def','Calc','Eng','PBEV','Avg','Rep')),
  PRIMARY KEY (IDMV, IDMP),
  CHECK ((Value IS NULL) <> (ValueText IS NULL))
);

CREATE TABLE IF NOT EXISTS P36_PBEVEdition (
  IDPBE          TEXT PRIMARY KEY,
  EditionYear    INTEGER NOT NULL,
  EditionVersion TEXT,
  SourcePBE      TEXT NOT NULL,
  PublishedAt    DATE,
  ImportedAt     TEXT,
  RecordCount    INTEGER,
  NotesPBE       TEXT
);

CREATE TABLE IF NOT EXISTS P28_PBEVRecord (
  IDPBR    INTEGER PRIMARY KEY,
  IDPBE    TEXT NOT NULL REFERENCES P36_PBEVEdition(IDPBE),
  MatchKey TEXT NOT NULL,
  Brand    TEXT NOT NULL,
  Model    TEXT NOT NULL,
  Version  TEXT,
  SheetRow INTEGER
);

CREATE TABLE IF NOT EXISTS P55_PBEVRecordValue (
  IDPBR     INTEGER NOT NULL REFERENCES P28_PBEVRecord(IDPBR),
  FieldName TEXT    NOT NULL,
  Value     REAL,
  ValueText TEXT,
  PRIMARY KEY (IDPBR, FieldName),
  CHECK ((Value IS NULL) <> (ValueText IS NULL))
);

CREATE TABLE IF NOT EXISTS P50_MarketVehiclePBEV (
  IDMV         INTEGER NOT NULL REFERENCES P26_MarketVehicle(IDMV),
  IDPBR        INTEGER NOT NULL REFERENCES P28_PBEVRecord(IDPBR),
  IDPBE        TEXT    NOT NULL REFERENCES P36_PBEVEdition(IDPBE),
  IsFirstMatch INTEGER NOT NULL DEFAULT 0 CHECK (IsFirstMatch IN (0,1)),
  PRIMARY KEY (IDMV, IDPBR)
);

CREATE TABLE IF NOT EXISTS P29_VehicleCategory (
  IDVC               TEXT PRIMARY KEY,
  DsVC               TEXT NOT NULL,
  CaseDigit          INTEGER NOT NULL UNIQUE CHECK (CaseDigit BETWEEN 0 AND 9),
  IDVDT              TEXT NOT NULL REFERENCES P13_DesignType(IDVDT),
  IDVS               TEXT NOT NULL REFERENCES P14_VehicleSize(IDVS),
  IDLR               TEXT NOT NULL CHECK (IDLR IN ('Regular','Luxury')),
  MarketGroup        TEXT,
  IDMVSelecao        INTEGER NOT NULL REFERENCES P26_MarketVehicle(IDMV),
  IDMVRepresentative INTEGER REFERENCES P26_MarketVehicle(IDMV)
);

CREATE TABLE IF NOT EXISTS P30_ControlParam (
  IDCP         TEXT PRIMARY KEY,
  Cell         TEXT NOT NULL,
  Section      TEXT NOT NULL,
  Level        TEXT NOT NULL CHECK (Level IN ('B','E','X')),
  DsCP         TEXT NOT NULL,
  utCP         TEXT,
  IsCalculated INTEGER NOT NULL DEFAULT 0 CHECK (IsCalculated IN (0,1)),
  DefaultValue REAL,
  DefaultText  TEXT,
  BasicValue   REAL,
  BasicCell    TEXT,
  MinValue     REAL,
  MostFrequent REAL,
  MaxValue     REAL,
  Distribution TEXT,
  StdDev       REAL,
  Reference    TEXT,
  UsedByModule TEXT CHECK (UsedByModule IS NULL
                           OR UsedByModule IN ('M1M2','M3','M4','M5','M6','UI')),
  CHECK (DefaultValue IS NULL OR DefaultText IS NULL)
);

CREATE TABLE IF NOT EXISTS P49_DefaultRuleVersion (
  IDDRV     TEXT PRIMARY KEY,
  DsDRV     TEXT NOT NULL,
  IsDefault INTEGER NOT NULL DEFAULT 0 CHECK (IsDefault IN (0,1)),
  NotesDRV  TEXT
);

CREATE TABLE IF NOT EXISTS P35_VehicleParamDefaultRule (
  IDDRV        TEXT    NOT NULL REFERENCES P49_DefaultRuleVersion(IDDRV),
  IDMP         INTEGER NOT NULL REFERENCES P54_MarketParam(IDMP),
  RuleSeq      INTEGER NOT NULL,
  IDVPT        TEXT REFERENCES P12_Powertrain(IDVPT),
  IDVDT        TEXT REFERENCES P13_DesignType(IDVDT),
  IDVS         TEXT REFERENCES P14_VehicleSize(IDVS),
  IDLR         TEXT CHECK (IDLR IS NULL OR IDLR IN ('Regular','Luxury')),
  PowerMinHP   REAL,
  PowerMaxHP   REAL,
  AreaMin      REAL,
  AreaMax      REAL,
  Value        REAL,
  ValueText    TEXT,
  FactorOfIDMP INTEGER REFERENCES P54_MarketParam(IDMP),
  SourceCell   TEXT,
  PRIMARY KEY (IDDRV, IDMP, RuleSeq),
  CHECK ((Value IS NULL) <> (ValueText IS NULL))
);

CREATE TABLE IF NOT EXISTS P51_OutputIndicator (
  IDInd        TEXT PRIMARY KEY,
  DsInd        TEXT NOT NULL,
  utInd        TEXT,
  SourceModule TEXT,
  PanelRow     INTEGER,
  IsHeader     INTEGER NOT NULL DEFAULT 0 CHECK (IsHeader IN (0,1)),
  ValueKind    TEXT NOT NULL DEFAULT 'Num' CHECK (ValueKind IN ('Num','Text')),
  FuelScenario TEXT,
  CalcStatus   TEXT NOT NULL DEFAULT 'ExcelReference'
               CHECK (CalcStatus IN ('Calculated','ExcelReference'))
);

CREATE TABLE IF NOT EXISTS P52_ExcelReferenceValue (
  IDXR      INTEGER PRIMARY KEY,
  RefSet    TEXT NOT NULL CHECK (RefSet IN ('CP_OUT_EC','CP_OUT_FC','MV_AUX','M2_IN')),
  CaseKey   TEXT NOT NULL,
  IDInd     TEXT    REFERENCES P51_OutputIndicator(IDInd),
  IDMP      INTEGER REFERENCES P54_MarketParam(IDMP),
  Value     REAL,
  ValueText TEXT,
  Workbook  TEXT NOT NULL,
  Sheet     TEXT NOT NULL,
  Cell      TEXT NOT NULL,
  CHECK ((IDInd IS NULL) <> (IDMP IS NULL)),
  CHECK (Value IS NULL OR ValueText IS NULL)
);

CREATE TABLE IF NOT EXISTS P53_CombinedPowerRule (
  IDVPT         TEXT PRIMARY KEY REFERENCES P12_Powertrain(IDVPT),
  FactorICE     REAL NOT NULL CHECK (FactorICE BETWEEN 0 AND 1),
  FactorEE      REAL NOT NULL CHECK (FactorEE  BETWEEN 0 AND 1),
  IsProvisional INTEGER NOT NULL CHECK (IsProvisional IN (0,1)),
  NotesCPR      TEXT
);

CREATE TABLE IF NOT EXISTS P56_CombinedPowerFit (
  CaseKey       TEXT PRIMARY KEY,
  IDVPT         TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  RefSet        TEXT NOT NULL,
  PowerICE      REAL NOT NULL,
  PowerEE       REAL NOT NULL,
  PowerCombined REAL NOT NULL,
  FactorICE     REAL NOT NULL CHECK (FactorICE BETWEEN 0 AND 1),
  FactorEE      REAL NOT NULL CHECK (FactorEE  BETWEEN 0 AND 1),
  FitKind       TEXT NOT NULL CHECK (FitKind IN ('Fixed','Sum','ICE','EE','Tie','NoFit')),
  IsProvisional INTEGER NOT NULL CHECK (IsProvisional IN (0,1)),
  NotesCPF      TEXT
);

-- Equivalencia entre materiais de versoes diferentes do GREET (aluminio unico ate
-- o G22; chapa e extrudado do G23 em diante). Divergencia D2.
CREATE TABLE IF NOT EXISTS P57_MaterialEquivalence (
  IDMParent    TEXT NOT NULL REFERENCES P09_Material(IDM),
  IDMChild     TEXT NOT NULL REFERENCES P09_Material(IDM),
  Weight       REAL NOT NULL CHECK (Weight > 0 AND Weight <= 1),
  WeightSource TEXT NOT NULL,
  NotesME      TEXT,
  PRIMARY KEY (IDMParent, IDMChild),
  CHECK (IDMParent <> IDMChild)
);

-- Bateria de tracao parametrica: modelos genericos do i3ET (`PB-<tipo>-indefinido`)
-- cuja massa e intensidade de carbono vem de parametros do Control Panel, nao de
-- uma composicao. Massa = parametro de massa por unidade x potencia (Power) ou
-- energia (Energy) da bateria. Os valores ficam em P30/D08, editaveis.
CREATE TABLE IF NOT EXISTS P58_GenericBatteryModel (
  IDBMd         TEXT PRIMARY KEY,
  IDVPT         TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  SizingBasis   TEXT NOT NULL CHECK (SizingBasis IN ('Power','Energy')),
  IDCPMass      TEXT NOT NULL REFERENCES P30_ControlParam(IDCP),
  IDCPCarbon    TEXT NOT NULL REFERENCES P30_ControlParam(IDCP),
  SourceGBM     TEXT NOT NULL,
  NotesGBM      TEXT
);

-- Constantes de equacao como parametros (bloco B0): fator do motor de partida
-- (IDVP 18) e hp por kW. Nada disso fica embutido no codigo.
CREATE TABLE IF NOT EXISTS P59_EquationConstant (
  IDEC          TEXT PRIMARY KEY,
  ValueEC       REAL NOT NULL,
  UnitEC        TEXT,
  SourceEC      TEXT NOT NULL,
  NotesEC       TEXT,
  IsProvisional INTEGER NOT NULL DEFAULT 0 CHECK (IsProvisional IN (0,1))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_P52_ref
  ON P52_ExcelReferenceValue (RefSet, CaseKey, IFNULL(IDInd, ''), IFNULL(IDMP, 0));
CREATE INDEX IF NOT EXISTS ix_P27_MP    ON P27_MarketVehicleParam (IDMP);
CREATE INDEX IF NOT EXISTS ix_P28_key   ON P28_PBEVRecord (IDPBE, MatchKey);
CREATE INDEX IF NOT EXISTS ix_P30_level ON P30_ControlParam (Level, Section);
"""

# --------------------------------------------------------------------------
# BLOCO S6 -- Analise, rodada e resultado (D06 a D09, D12, R45, R46)
#   O que faz : cria as tabelas do usuario que guardam a configuracao da
#               analise, os casos, os parametros alterados, o ajuste da regra
#               de potencia, a rodada congelada e o resultado da rodada.
#   Le        : nada.
#   Devolve   : DDL_ANALYSIS_010.
#   Nota      : R45 fica gravada no arquivo de projeto. E a excecao deliberada
#               a regra de que tabelas R sao derivadas: a rodada congelada tem
#               de sobreviver a uma troca de base.
# --------------------------------------------------------------------------
DDL_ANALYSIS_010 = """
CREATE TABLE IF NOT EXISTS D06_Analysis (
  IDA               INTEGER PRIMARY KEY,
  DsA               TEXT NOT NULL,
  Mode              TEXT NOT NULL CHECK (Mode IN ('EC','FC')),
  AnalysisType      TEXT NOT NULL DEFAULT 'GHG_LCA_LCC'
                    CHECK (AnalysisType IN ('GHG_LCA_LCC','SENSITIVITY',
                                            'MONTE_CARLO','LIGHTWEIGHTING')),
  IDVC              TEXT    REFERENCES P29_VehicleCategory(IDVC),
  IDMVRef           INTEGER REFERENCES P26_MarketVehicle(IDMV),
  FuelScenario      TEXT NOT NULL,
  TestNorm          TEXT NOT NULL CHECK (TestNorm IN ('NBR','EPA','NEDC','WLTC')),
  DistanceCurve     TEXT NOT NULL,
  IDEFV             TEXT NOT NULL,
  IDMPV             INTEGER NOT NULL REFERENCES P05_MassParamVersion(IDMPV),
  IDAPV             TEXT NOT NULL REFERENCES P23_AssemblyParamVersion(IDAPV),
  Boundary          TEXT NOT NULL DEFAULT 'MAT_ASM' CHECK (Boundary IN ('MAT','MAT_ASM')),
  SPHEVEco          INTEGER NOT NULL DEFAULT 0 CHECK (SPHEVEco IN (0,1)),
  LightweightingOn  INTEGER NOT NULL DEFAULT 0 CHECK (LightweightingOn IN (0,1)),
  ParamProfile      TEXT NOT NULL DEFAULT 'Expert'
                    CHECK (ParamProfile IN ('Basic','Expert','Expanded')),
  CombinedPowerRule TEXT NOT NULL DEFAULT 'Default'
                    CHECK (CombinedPowerRule IN ('Default','ExcelParity')),
  NotesIDA          TEXT,
  CHECK ((Mode = 'EC' AND IDVC IS NOT NULL AND IDMVRef IS NOT NULL)
      OR (Mode = 'FC' AND IDVC IS NULL     AND IDMVRef IS NULL))
);

CREATE TABLE IF NOT EXISTS D07_AnalysisVehicle (
  IDA          INTEGER NOT NULL REFERENCES D06_Analysis(IDA),
  IDCase       INTEGER NOT NULL CHECK (IDCase BETWEEN 1 AND 7),
  CaseKey      TEXT    NOT NULL,
  CaseRole     TEXT    NOT NULL CHECK (CaseRole IN ('REF','EQ','FC')),
  IDVPT        TEXT    NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDMV         INTEGER REFERENCES P26_MarketVehicle(IDMV),
  IDV          INTEGER NOT NULL,
  IDEA         INTEGER NOT NULL,
  FuelBlend    TEXT,
  IDPBE        TEXT REFERENCES P36_PBEVEdition(IDPBE),
  SizingOrigin TEXT NOT NULL
               CHECK (SizingOrigin IN ('Manufacturer','ExcelReference',
                                       'Calculated','Pending')),
  PRIMARY KEY (IDA, IDCase),
  UNIQUE (IDA, CaseKey),
  FOREIGN KEY (IDV, IDEA) REFERENCES D02_EvaluationAlternative(IDV, IDEA)
);

CREATE TABLE IF NOT EXISTS D08_ControlParamValue (
  IDA         INTEGER NOT NULL REFERENCES D06_Analysis(IDA),
  IDCP        TEXT    NOT NULL REFERENCES P30_ControlParam(IDCP),
  Profile     TEXT    NOT NULL CHECK (Profile IN ('Basic','Expert','Expanded')),
  Value       REAL,
  ValueText   TEXT,
  ValueSource TEXT NOT NULL CHECK (length(trim(ValueSource)) > 0),
  UpdatedAt   TEXT NOT NULL,
  PRIMARY KEY (IDA, IDCP, Profile),
  CHECK ((Value IS NULL) <> (ValueText IS NULL))
);

CREATE TABLE IF NOT EXISTS D12_CombinedPowerOverride (
  IDA       INTEGER NOT NULL,
  IDCase    INTEGER NOT NULL,
  FactorICE REAL NOT NULL CHECK (FactorICE BETWEEN 0 AND 1),
  FactorEE  REAL NOT NULL CHECK (FactorEE  BETWEEN 0 AND 1),
  NotesCPO  TEXT,
  PRIMARY KEY (IDA, IDCase),
  FOREIGN KEY (IDA, IDCase) REFERENCES D07_AnalysisVehicle(IDA, IDCase)
);

CREATE TABLE IF NOT EXISTS D09_Run (
  RunID             TEXT PRIMARY KEY REFERENCES M01_RunMetadata(RunID),
  IDA               INTEGER NOT NULL REFERENCES D06_Analysis(IDA),
  RunSeq            INTEGER NOT NULL CHECK (RunSeq >= 1),
  FrozenAt          TEXT NOT NULL,
  InputSnapshot     TEXT NOT NULL,
  InputHash         TEXT NOT NULL CHECK (length(InputHash) = 64),
  ParamBaseHash     TEXT NOT NULL,
  ReferenceWorkbook TEXT NOT NULL,
  CalculatorVersion TEXT NOT NULL,
  Status            TEXT NOT NULL DEFAULT 'Frozen'
                    CHECK (Status IN ('Frozen','Calculated','Failed')),
  NotesRun          TEXT,
  UNIQUE (IDA, RunSeq)
);

CREATE TABLE IF NOT EXISTS R45_PowertrainSummary (
  RunID       TEXT NOT NULL REFERENCES D09_Run(RunID),
  CaseKey     TEXT NOT NULL,
  IDVPT       TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDInd       TEXT NOT NULL REFERENCES P51_OutputIndicator(IDInd),
  Value       REAL,
  ValueText   TEXT,
  ValueOrigin TEXT NOT NULL
              CHECK (ValueOrigin IN ('Calculated','ExcelReference','Preview')),
  PRIMARY KEY (RunID, CaseKey, IDInd),
  CHECK (Value IS NULL OR ValueText IS NULL)
);

CREATE INDEX IF NOT EXISTS ix_D09_IDA ON D09_Run (IDA, RunSeq);
CREATE INDEX IF NOT EXISTS ix_R45_Ind ON R45_PowertrainSummary (IDInd, CaseKey);

CREATE VIEW IF NOT EXISTS R46_RunComparison AS
  SELECT d.IDA, d.RunSeq, r.RunID, d.FrozenAt, d.InputHash, d.ParamBaseHash,
         r.CaseKey, r.IDVPT, r.IDInd, i.DsInd, i.utInd,
         r.Value, r.ValueText, r.ValueOrigin
    FROM R45_PowertrainSummary r
    JOIN D09_Run d             ON d.RunID = r.RunID
    JOIN P51_OutputIndicator i ON i.IDInd = r.IDInd;
"""

# --------------------------------------------------------------------------
# BLOCO S7 -- Identidade do projeto (M03)
#   O que faz : cria a tabela de uma linha so que identifica o arquivo de
#               projeto. O indice sobre a constante 1 e o que impede a
#               segunda linha.
#   Le        : nada.
#   Devolve   : DDL_PROJECT_010.
# --------------------------------------------------------------------------
DDL_PROJECT_010 = """
CREATE TABLE IF NOT EXISTS M03_Project (
  ProjectID           TEXT PRIMARY KEY
                      CHECK (length(ProjectID) = 12 AND ProjectID GLOB 'PRJ-*'
                             AND substr(ProjectID, 5) NOT GLOB '*[^A-Z0-9]*'),
  ProjectName         TEXT NOT NULL CHECK (length(trim(ProjectName)) > 0),
  Domain              TEXT NOT NULL DEFAULT 'LV' CHECK (Domain IN ('LV')),
  OwnerLabel          TEXT,
  CreatedAt           TEXT NOT NULL,
  CopiedFromProjectID TEXT,
  SchemaVersion       TEXT NOT NULL,
  IsExample           INTEGER NOT NULL DEFAULT 0 CHECK (IsExample IN (0,1))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_M03_single ON M03_Project ((1));
"""

#: Tabelas de parametros da Fase A, em ordem de dependencia (pais primeiro).
PARAM_TABLES_010 = [
    "P54_MarketParam", "P26_MarketVehicle", "P27_MarketVehicleParam",
    "P36_PBEVEdition", "P28_PBEVRecord", "P55_PBEVRecordValue",
    "P50_MarketVehiclePBEV", "P29_VehicleCategory", "P30_ControlParam",
    "P49_DefaultRuleVersion", "P35_VehicleParamDefaultRule",
    "P51_OutputIndicator", "P52_ExcelReferenceValue", "P53_CombinedPowerRule",
    "P56_CombinedPowerFit", "P57_MaterialEquivalence", "P58_GenericBatteryModel",
    "P59_EquationConstant",
]

#: Tabelas do usuario da Fase A, em ordem de dependencia.
ANALYSIS_TABLES = [
    "D06_Analysis", "D07_AnalysisVehicle", "D08_ControlParamValue",
    "D12_CombinedPowerOverride", "D09_Run", "R45_PowertrainSummary",
]

#: Tabelas de metadados do projeto.
PROJECT_TABLES = ["M03_Project"]

#: Tudo o que a 0.10 acrescenta. O carregador le estas tabelas quando existem.
TABLES_010 = PARAM_TABLES_010 + ANALYSIS_TABLES + PROJECT_TABLES

#: Tabelas da 0.9.0 que ganham a coluna IsCalculable.
CALCULABLE_TABLES = ["P12_Powertrain", "P13_DesignType"]

#: Alfabeto do ProjectID: maiusculas e digitos, sem 0/O e 1/I, que se confundem.
_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


# --------------------------------------------------------------------------
# BLOCO S8 -- Migracao 0.9 -> 0.10
#   O que faz : leva um arquivo da 0.9.0 ao esquema 0.10 sem tocar em nenhum
#               dado existente. Pode ser chamada mais de uma vez.
#   Le        : uma conexao aberta; opcionalmente o nome do projeto.
#   Devolve   : a lista do que foi feito, para o log.
# --------------------------------------------------------------------------
def new_project_id() -> str:
    """S8.1 -- identificador neutro: nao carrega login, nome nem data."""
    import secrets
    return "PRJ-" + "".join(secrets.choice(_ID_ALPHABET) for _ in range(8))


def table_names(conn: sqlite3.Connection) -> set[str]:
    """S8.2 -- tabelas e visoes presentes no arquivo."""
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}


def apply_010(conn: sqlite3.Connection) -> None:
    """S8.3 -- aplica os blocos S5, S6 e S7. Nao altera o que ja existe."""
    conn.executescript(DDL_PARAMS_010)
    conn.executescript(DDL_ANALYSIS_010)
    conn.executescript(DDL_PROJECT_010)
    # P12 ganha a marca das motorizacoes que o nucleo sabe calcular. As seis da
    # 0.9.0 valem 1; MHEV e FCEV entram no catalogo, no passo 3, com 0.
    # P13 ganha a mesma marca: Van e Chassis estao no catalogo de mercado, mas
    # a estimativa de massa nao tem parametros para elas.
    for tabela in CALCULABLE_TABLES:
        colunas = {r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        if "IsCalculable" not in colunas:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN IsCalculable "
                         "INTEGER NOT NULL DEFAULT 1 CHECK (IsCalculable IN (0,1))")


def migrate(conn: sqlite3.Connection, *, project_name: str | None = None,
            copied_from: str | None = None, is_example: bool = False) -> list[str]:
    """S8.4 -- migra o arquivo e, se `project_name` vier, da-lhe identidade.

    A base de referencia nao e um projeto: migra-se sem `project_name` e ela
    fica sem linha em M03. Um arquivo de projeto recebe exatamente uma linha,
    e uma segunda chamada nao a troca -- o ProjectID e estavel.
    """
    import datetime as dt

    antes = table_names(conn)
    if "P12_Powertrain" not in antes or "D02_EvaluationAlternative" not in antes:
        raise ValueError("o arquivo nao tem o esquema da 0.9.0; nada foi alterado")

    feito: list[str] = []
    conn.execute("PRAGMA foreign_keys = ON")
    sem_marca = [t for t in CALCULABLE_TABLES if "IsCalculable" not in {
        r[1] for r in conn.execute(f"PRAGMA table_info({t})")}]
    apply_010(conn)
    for nome in sorted(table_names(conn) - antes):
        feito.append(f"criada {nome}")
    for tabela in sem_marca:
        feito.append(f"{tabela}: coluna IsCalculable")
    feito.extend(apply_011(conn))

    if project_name is not None:
        if conn.execute("SELECT COUNT(*) FROM M03_Project").fetchone()[0] == 0:
            pid = new_project_id()
            conn.execute(
                "INSERT INTO M03_Project (ProjectID, ProjectName, Domain, CreatedAt, "
                "CopiedFromProjectID, SchemaVersion, IsExample) VALUES (?,?,?,?,?,?,?)",
                (pid, project_name.strip(), "LV",
                 dt.datetime.now().isoformat(timespec="seconds"),
                 copied_from, SCHEMA_VERSION, int(is_example)))
            feito.append(f"M03_Project: {pid}")
        else:
            conn.execute("UPDATE M03_Project SET SchemaVersion = ?", (SCHEMA_VERSION,))
    conn.commit()
    return feito


# ==========================================================================
# SCHEMA 0.11 -- Bloco B1: completar M1 e M2
# ==========================================================================
# Documento de referencia: docs/09-dicionario-de-dados-b1.md.
# Blocos:
#   S11 parametros do B1 (P31, P31b, P32, P61, P62, P63)
#   S12 tabelas do usuario do B1 (D10, D13 a D21)
#   S13 resultados do B1 (C15, C16, C34, C35)
#   S14 colunas acrescentadas a tabelas existentes e migracao 0.10 -> 0.11
# Tudo e CREATE IF NOT EXISTS ou ADD COLUMN condicional: pode ser repetido.
# --------------------------------------------------------------------------
DDL_PARAMS_011 = """
CREATE TABLE IF NOT EXISTS P31_MaintenanceItem (
  IDMI           TEXT PRIMARY KEY,
  DsMI           TEXT NOT NULL,
  ItemKind       TEXT NOT NULL CHECK (ItemKind IN ('PART','BATTERY','FLUID')),
  IDGG           TEXT REFERENCES P04_GreetGroup(IDGG),
  IDM            TEXT REFERENCES P09_Material(IDM),
  IntervalKm     REAL CHECK (IntervalKm IS NULL OR IntervalKm > 0),
  IntervalSource TEXT NOT NULL CHECK (IntervalSource IN ('i3ET-compatible','Entered')),
  RefCount       REAL,
  MassPerUnitKg  REAL CHECK (MassPerUnitKg IS NULL OR MassPerUnitKg >= 0),
  NotesMI        TEXT
);

CREATE TABLE IF NOT EXISTS P31b_MaintenancePartShare (
  IDMI   TEXT NOT NULL REFERENCES P31_MaintenanceItem(IDMI),
  IDM    TEXT NOT NULL REFERENCES P09_Material(IDM),
  Share  REAL NOT NULL CHECK (Share >= 0 AND Share <= 1),
  NotesMPS TEXT,
  PRIMARY KEY (IDMI, IDM)
);

CREATE TABLE IF NOT EXISTS P32_CorrectiveMaintenance (
  IDCM          INTEGER PRIMARY KEY,
  CorrectivePct REAL NOT NULL DEFAULT 0 CHECK (CorrectivePct >= 0),
  Basis         TEXT NOT NULL DEFAULT 'PART_MASS_SHARE'
                CHECK (Basis IN ('PART_MASS_SHARE','PRODUCTION_GHG_SHARE')),
  SourceCM      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS P61_BRRouteFactor (
  IDM                 TEXT NOT NULL REFERENCES P09_Material(IDM),
  Route               TEXT NOT NULL
                      CHECK (Route IN ('RECYCLED','VIRGIN_MAIN','VIRGIN_ALT','GREEN')),
  EFRoute             REAL,
  EFGlobal            REAL,
  LossGlobalAdjusted  REAL,
  LossGlobalAdopted   REAL,
  LossNationalAdjusted REAL,
  LossNationalAdjIDCP TEXT REFERENCES P30_ControlParam(IDCP),
  LossNationalAdopted REAL,
  Origin              TEXT NOT NULL DEFAULT 'Typed',
  SourceRF            TEXT,
  PRIMARY KEY (IDM, Route)
);

CREATE TABLE IF NOT EXISTS P62_BRRouteShare (
  IDM        TEXT NOT NULL REFERENCES P09_Material(IDM),
  Route      TEXT NOT NULL
             CHECK (Route IN ('RECYCLED','VIRGIN_MAIN','VIRGIN_ALT','GREEN',
                              'IMP_ICEV','IMP_ICEV_SUV','IMP_HEV','IMP_PHEV','IMP_BEV')),
  ShareRule  TEXT NOT NULL CHECK (ShareRule IN ('CONSTANT','PARAM','FORMULA')),
  IDCP       TEXT REFERENCES P30_ControlParam(IDCP),
  ShareValue REAL,
  RuleExpr   TEXT,
  SourceRS   TEXT,
  PRIMARY KEY (IDM, Route),
  CHECK ((ShareRule = 'PARAM' AND IDCP IS NOT NULL)
      OR (ShareRule = 'CONSTANT' AND ShareValue IS NOT NULL)
      OR (ShareRule = 'FORMULA' AND RuleExpr IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS P63_RecipeBodyChassisMass (
  IDVMR              TEXT PRIMARY KEY REFERENCES P15_VehicleMaterialRecipe(IDVMR),
  ColumnM2           TEXT NOT NULL,
  BodyMassRefKg      REAL NOT NULL CHECK (BodyMassRefKg > 0),
  ChassisMassRefKg   REAL NOT NULL CHECK (ChassisMassRefKg > 0),
  ChassisBodyRatio   REAL NOT NULL CHECK (ChassisBodyRatio > 0),
  BodyShareOfMassAdj REAL NOT NULL CHECK (BodyShareOfMassAdj BETWEEN 0 AND 1),
  SourceNote         TEXT
);
"""

DDL_USER_011 = """
CREATE TABLE IF NOT EXISTS D10_MaintenanceScenario (
  IDMS            INTEGER PRIMARY KEY,
  IDA             INTEGER NOT NULL UNIQUE REFERENCES D06_Analysis(IDA),
  MaintenanceMode TEXT NOT NULL DEFAULT 'Sim'
                  CHECK (MaintenanceMode IN ('Sim','Sim Bat','Não')),
  Scenario        TEXT NOT NULL DEFAULT 'REFERENCE' CHECK (Scenario IN ('REFERENCE','USER')),
  VehicleLifeKm   REAL CHECK (VehicleLifeKm IS NULL OR VehicleLifeKm > 0),
  BatteryLifeKm   REAL CHECK (BatteryLifeKm IS NULL OR BatteryLifeKm > 0),
  Author          TEXT,
  ChangedAt       TEXT
);

CREATE TABLE IF NOT EXISTS D10_Item (
  IDMS       INTEGER NOT NULL REFERENCES D10_MaintenanceScenario(IDMS),
  IDMI       TEXT NOT NULL REFERENCES P31_MaintenanceItem(IDMI),
  IntervalKm REAL CHECK (IntervalKm IS NULL OR IntervalKm > 0),
  Active     INTEGER NOT NULL DEFAULT 1 CHECK (Active IN (0,1)),
  PRIMARY KEY (IDMS, IDMI)
);

CREATE TABLE IF NOT EXISTS D13_UserRecipe (
  IDVMRU     TEXT PRIMARY KEY,
  DsVMRU     TEXT NOT NULL,
  IDVMRBase  TEXT NOT NULL REFERENCES P15_VehicleMaterialRecipe(IDVMR),
  IDVPT      TEXT NOT NULL REFERENCES P12_Powertrain(IDVPT),
  IDVDT      TEXT NOT NULL,
  IDVS       TEXT NOT NULL,
  Author     TEXT,
  CreatedAt  TEXT,
  UpdatedAt  TEXT NOT NULL,
  NotesU     TEXT
);

CREATE TABLE IF NOT EXISTS D14_UserMaterialShare (
  IDVMRU    TEXT NOT NULL REFERENCES D13_UserRecipe(IDVMRU),
  IDGG      TEXT NOT NULL REFERENCES P04_GreetGroup(IDGG),
  IDM       TEXT NOT NULL REFERENCES P09_Material(IDM),
  MshareGG  REAL NOT NULL CHECK (MshareGG >= 0),
  SourceU   TEXT,
  ChangedBy TEXT,
  ChangedAt TEXT,
  PRIMARY KEY (IDVMRU, IDGG, IDM)
);

CREATE TABLE IF NOT EXISTS D15_UserBatteryModel (
  IDBMdU    TEXT PRIMARY KEY,
  DsBMdU    TEXT NOT NULL,
  IDBMdBase TEXT NOT NULL REFERENCES P19_BatteryModel(IDBMd),
  IDVPT     TEXT REFERENCES P12_Powertrain(IDVPT),
  IDBTe     TEXT REFERENCES P18_BatteryTechnology(IDBTe),
  RefEnergy REAL,
  RefPower  REAL,
  RefWeight REAL,
  Origin    TEXT NOT NULL DEFAULT 'Own',
  Author    TEXT,
  CreatedAt TEXT,
  UpdatedAt TEXT
);

CREATE TABLE IF NOT EXISTS D16_UserBatteryShare (
  IDBMdU     TEXT NOT NULL REFERENCES D15_UserBatteryModel(IDBMdU),
  IDGG       TEXT NOT NULL REFERENCES P04_GreetGroup(IDGG),
  IDM        TEXT NOT NULL REFERENCES P09_Material(IDM),
  BMshareGG  REAL NOT NULL CHECK (BMshareGG >= 0),
  PRIMARY KEY (IDBMdU, IDGG, IDM)
);

CREATE TABLE IF NOT EXISTS D17_UserAssemblyVersion (
  IDAPVU             TEXT PRIMARY KEY,
  DsAPVU             TEXT NOT NULL,
  Method             TEXT NOT NULL CHECK (Method IN ('fixed','from_EF','process')),
  FixedGHGPerVehicle REAL CHECK (FixedGHGPerVehicle IS NULL OR FixedGHGPerVehicle >= 0),
  Origin             TEXT NOT NULL DEFAULT 'Own',
  Author             TEXT,
  CreatedAt          TEXT,
  UpdatedAt          TEXT,
  CHECK (Method <> 'fixed' OR FixedGHGPerVehicle IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS D18_UserAssemblyEnergy (
  IDAPVU           TEXT    NOT NULL REFERENCES D17_UserAssemblyVersion(IDAPVU),
  IDAP             INTEGER NOT NULL REFERENCES P21_AssemblyProcess(IDAP),
  IDFuel           TEXT    NOT NULL REFERENCES P24_EnergyCarrier(IDFuel),
  EnergyPerVehicle REAL    NOT NULL CHECK (EnergyPerVehicle >= 0),
  FuelShare        REAL    NOT NULL CHECK (FuelShare BETWEEN 0 AND 1),
  PRIMARY KEY (IDAPVU, IDAP, IDFuel)
);

CREATE TABLE IF NOT EXISTS D19_EFChangeLog (
  IDLog     INTEGER PRIMARY KEY AUTOINCREMENT,
  IDEFV     TEXT NOT NULL,
  IDM       TEXT NOT NULL,
  Action    TEXT NOT NULL CHECK (Action IN ('edit','override','restore','remove','import')),
  OldEF     REAL,
  NewEF     REAL,
  Author    TEXT,
  ChangedAt TEXT NOT NULL,
  Reason    TEXT
);

CREATE TABLE IF NOT EXISTS D20_UserMassParamVersion (
  IDMPVU    TEXT PRIMARY KEY,
  DsMPVU    TEXT NOT NULL,
  IDMPVBase INTEGER NOT NULL REFERENCES P05_MassParamVersion(IDMPV),
  Origin    TEXT NOT NULL DEFAULT 'Own',
  Author    TEXT,
  CreatedAt TEXT,
  NotesMPV  TEXT
);

CREATE TABLE IF NOT EXISTS D21_UserMassParam (
  IDMPVU    TEXT    NOT NULL REFERENCES D20_UserMassParamVersion(IDMPVU),
  IDSG      INTEGER NOT NULL REFERENCES P02_VehicleSubgroup(IDSG),
  Beta      REAL,
  GCR       REAL CHECK (GCR IS NULL OR GCR > 0),
  utGCR     TEXT,
  MR        REAL CHECK (MR IS NULL OR MR >= 0),
  fLM       REAL CHECK (fLM IS NULL OR fLM >= 0),
  Reference TEXT,
  ChangedBy TEXT,
  ChangedAt TEXT,
  PRIMARY KEY (IDMPVU, IDSG)
);
"""

DDL_CALC_011 = """
CREATE TABLE IF NOT EXISTS C15_Replacement (
  RunID      TEXT    NOT NULL REFERENCES D09_Run(RunID),
  IDA        INTEGER NOT NULL,
  IDCase     INTEGER NOT NULL,
  IDMI       TEXT    NOT NULL REFERENCES P31_MaintenanceItem(IDMI),
  EventIndex INTEGER NOT NULL CHECK (EventIndex >= 1),
  EventKm    REAL    NOT NULL,
  GHGkg      REAL    NOT NULL,
  PRIMARY KEY (RunID, IDCase, IDMI, EventIndex),
  FOREIGN KEY (IDA, IDCase) REFERENCES D07_AnalysisVehicle(IDA, IDCase)
);

CREATE TABLE IF NOT EXISTS C16_EndOfLife (
  RunID         TEXT    NOT NULL REFERENCES D09_Run(RunID),
  IDA           INTEGER NOT NULL,
  IDCase        INTEGER NOT NULL,
  EoLMethod     TEXT    NOT NULL
                CHECK (EoLMethod IN ('GLIDER_BATTERY','AGGREGATE_VEHICLE','EXCLUDED')),
  GliderMassKg  REAL,
  BatteryKWh    REAL,
  FactorGlider  REAL,
  FactorBattery REAL,
  FactorVehicle REAL,
  GHGEoL        REAL    NOT NULL,
  PRIMARY KEY (RunID, IDCase),
  FOREIGN KEY (IDA, IDCase) REFERENCES D07_AnalysisVehicle(IDA, IDCase)
);

CREATE TABLE IF NOT EXISTS C34_MassValidation (
  RunID                 TEXT    NOT NULL REFERENCES D09_Run(RunID),
  IDA                   INTEGER NOT NULL,
  IDCase                INTEGER NOT NULL,
  IDV                   INTEGER NOT NULL,
  IDEA                  INTEGER NOT NULL,
  MassBasis             TEXT,
  DeclaredMassKg        REAL,
  CalculatedMassKg      REAL    NOT NULL,
  DiffKg                REAL,
  DiffPct               REAL,
  AdjustmentKg          REAL    NOT NULL DEFAULT 0,
  ResidualKg            REAL,
  DeclaredSource        TEXT,
  BodyShare             REAL CHECK (BodyShare IS NULL OR BodyShare BETWEEN 0 AND 1),
  BodyChassisMassBefore REAL,
  BodyChassisMassAfter  REAL,
  PRIMARY KEY (RunID, IDCase),
  FOREIGN KEY (IDA, IDCase) REFERENCES D07_AnalysisVehicle(IDA, IDCase)
);

CREATE TABLE IF NOT EXISTS C35_VehicleLifeStage (
  RunID      TEXT    NOT NULL REFERENCES D09_Run(RunID),
  IDA        INTEGER NOT NULL,
  IDCase     INTEGER NOT NULL,
  IDV        INTEGER NOT NULL,
  Stage      TEXT    NOT NULL
             CHECK (Stage IN ('INITIAL_PRODUCTION','LIFETIME_REPLACEMENTS','END_OF_LIFE')),
  SubStage   TEXT    NOT NULL DEFAULT '',
  GHGkg      REAL    NOT NULL,
  SourceCell TEXT,
  Method     TEXT,
  Note       TEXT,
  PRIMARY KEY (RunID, IDCase, Stage, SubStage),
  FOREIGN KEY (IDA, IDCase) REFERENCES D07_AnalysisVehicle(IDA, IDCase)
);
"""

#: Tabelas de parametros do B1, pais primeiro.
PARAM_TABLES_011 = ["P31_MaintenanceItem", "P31b_MaintenancePartShare",
                    "P32_CorrectiveMaintenance", "P61_BRRouteFactor",
                    "P62_BRRouteShare", "P63_RecipeBodyChassisMass"]

#: Tabelas do usuario do B1, pais primeiro.
USER_TABLES_011 = ["D10_MaintenanceScenario", "D10_Item", "D13_UserRecipe",
                   "D14_UserMaterialShare", "D15_UserBatteryModel",
                   "D16_UserBatteryShare", "D17_UserAssemblyVersion",
                   "D18_UserAssemblyEnergy", "D19_EFChangeLog",
                   "D20_UserMassParamVersion", "D21_UserMassParam"]

#: Tabelas de resultado do B1.
CALC_TABLES_011 = ["C15_Replacement", "C16_EndOfLife", "C34_MassValidation",
                   "C35_VehicleLifeStage"]

#: Tudo o que a 0.11 cria.
TABLES_011 = PARAM_TABLES_011 + USER_TABLES_011 + CALC_TABLES_011

_ORIGIN = "CHECK (Origin IN ('Typed','Published','Own'))"
_EFV_SOURCE = [("SourceDocTitle", "TEXT"), ("SourceInstitution", "TEXT"),
               ("SourceEdition", "TEXT"), ("SourceURL", "TEXT"),
               ("SourceAccessDate", "TEXT"), ("ImportFile", "TEXT"),
               ("ImportHash", "TEXT"), ("ImportedBy", "TEXT"), ("ImportedAt", "TEXT")]

#: Colunas que a 0.11 acrescenta a tabelas ja existentes: (tabela, coluna, declaracao).
COLUMNS_011 = (
    [("P02_VehicleSubgroup", "IDVPGC", "INTEGER REFERENCES P54_MarketParam(IDMP)"),
     ("P02_VehicleSubgroup", "SourceRow", "INTEGER"),
     ("P02_VehicleSubgroup", "NotesSG", "TEXT"),
     ("P10_EFVersion", "Origin", f"TEXT NOT NULL DEFAULT 'Typed' {_ORIGIN}")]
    + [("P10_EFVersion", c, d) for c, d in _EFV_SOURCE]
    + [("D04_UserEFVersion", "Origin", f"TEXT NOT NULL DEFAULT 'Own' {_ORIGIN}")]
    + [("D04_UserEFVersion", c, d) for c, d in _EFV_SOURCE]
    + [("P11_EmissionFactor", "Route", "TEXT"), ("P11_EmissionFactor", "Region", "TEXT"),
       ("P11_EmissionFactor", "RefYear", "INTEGER"), ("P11_EmissionFactor", "EFLow", "REAL"),
       ("P11_EmissionFactor", "EFHigh", "REAL"),
       ("P16_MaterialShare", "MshareRaw", "REAL"),
       ("D05_UserEmissionFactor", "Author", "TEXT"),
       ("D05_UserEmissionFactor", "ChangedAt", "TEXT"),
       ("D05_UserEmissionFactor", "Reason", "TEXT"),
       ("C02_MassByGroup", "EstimatedMassKg", "REAL"),
       ("C02_MassByGroup", "CalibrationKg", "REAL NOT NULL DEFAULT 0"),
       ("C02_MassByGroup", "FinalMassKg", "REAL"),
       ("D07_AnalysisVehicle", "DeclaredMassKg", "REAL CHECK (DeclaredMassKg IS NULL OR "
        "DeclaredMassKg > 0)"),
       ("D07_AnalysisVehicle", "MassAdjustmentKg", "REAL NOT NULL DEFAULT 0"),
       ("D07_AnalysisVehicle", "MassBodyShare", "REAL CHECK (MassBodyShare IS NULL OR "
        "MassBodyShare BETWEEN 0 AND 1)"),
       ("D07_AnalysisVehicle", "DeclaredSource", "TEXT"),
       ("D06_Analysis", "EoLMethod", "TEXT NOT NULL DEFAULT 'GLIDER_BATTERY' "
        "CHECK (EoLMethod IN ('GLIDER_BATTERY','AGGREGATE_VEHICLE','EXCLUDED'))")]
)


def apply_011(conn: sqlite3.Connection) -> list[str]:
    """S14 -- aplica os blocos S11 a S13 e as colunas novas. Nao altera dados.

    Devolve o que foi feito, para o log da migracao.
    """
    feito: list[str] = []
    antes = table_names(conn)
    conn.executescript(DDL_PARAMS_011)
    conn.executescript(DDL_USER_011)
    conn.executescript(DDL_CALC_011)
    for nome in TABLES_011:
        if nome not in antes:
            feito.append(f"criada {nome}")
    for tabela, coluna, decl in COLUMNS_011:
        if tabela not in antes:
            continue
        existentes = {r[1] for r in conn.execute(f"PRAGMA table_info({tabela})")}
        if coluna not in existentes:
            conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {decl}")
            feito.append(f"{tabela}: coluna {coluna}")
    return feito


# --------------------------------------------------------------------------
# BLOCO S9 -- Impressao digital da base (ParamBaseHash)
#   O que faz : calcula o SHA-256 do conteudo das tabelas de parametros. E a
#               mesma conta de tools/make_db.py, estendida as tabelas da 0.10.
#   Le        : uma conexao aberta.
#   Devolve   : o hash, em 64 caracteres hexadecimais.
#   Nota      : a ordem das linhas e a da chave primaria, para que duas bases
#               com o mesmo conteudo tenham o mesmo hash, qualquer que tenha
#               sido a ordem de insercao.
# --------------------------------------------------------------------------
def param_base_hash(conn: sqlite3.Connection) -> str:
    import hashlib

    presentes = table_names(conn)
    h = hashlib.sha256()
    for tabela in PARAM_TABLES + PARAM_TABLES_010 + PARAM_TABLES_011:
        if tabela not in presentes:
            continue
        h.update(tabela.encode("utf-8"))
        chave = [r[1] for r in sorted(conn.execute(f"PRAGMA table_info({tabela})"),
                                      key=lambda r: r[5]) if r[5] > 0]
        ordem = ", ".join(chave) if chave else "rowid"
        for row in conn.execute(f"SELECT * FROM {tabela} ORDER BY {ordem}"):
            h.update(repr(row).encode("utf-8"))
    return h.hexdigest()


# --------------------------------------------------------------------------
# BLOCO S10 -- Parametros da Fase A num projeto que veio da 0.9.0
#   O que faz : um projeto migrado tem as tabelas da 0.10 vazias. Este bloco
#               copia para ele, da base de referencia, as tabelas de
#               parametros da Fase A e as linhas acrescentadas a P10, P11, P12,
#               P13, P15 e P16. So acrescenta: nenhuma linha que o projeto ja tinha e
#               alterada, e por isso nenhum resultado existente muda.
#   Le        : a conexao do projeto (ja migrado) e o caminho da base.
#   Devolve   : {tabela: linhas copiadas}.
#   Nota      : o ParamBaseHash do projeto continua sendo o da base de que
#               ele nasceu; o da base de onde vieram os parametros da Fase A
#               fica em M00_BaseInfo, chave FaseABaseHash.
# --------------------------------------------------------------------------
def sync_fase_a(conn: sqlite3.Connection, reference_db: str) -> dict[str, int]:
    feito: dict[str, int] = {}
    conn.commit()
    conn.execute("ATTACH DATABASE ? AS ref", (reference_db,))
    try:
        conn.execute("BEGIN")
        conn.execute("PRAGMA defer_foreign_keys = ON")
        for tabela in (["P10_EFVersion", "P11_EmissionFactor"] + CALCULABLE_TABLES
                       + ["P15_VehicleMaterialRecipe", "P16_MaterialShare"]):
            cols = ", ".join(r[1] for r in conn.execute(f"PRAGMA table_info({tabela})"))
            cur = conn.execute(
                f"INSERT OR IGNORE INTO {tabela} ({cols}) SELECT {cols} FROM ref.{tabela}")
            feito[tabela] = cur.rowcount
        todas = PARAM_TABLES_010 + PARAM_TABLES_011
        for tabela in reversed(todas):
            conn.execute(f"DELETE FROM {tabela}")
        for tabela in todas:
            cols = ", ".join(r[1] for r in conn.execute(f"PRAGMA table_info({tabela})"))
            cur = conn.execute(
                f"INSERT INTO {tabela} ({cols}) SELECT {cols} FROM ref.{tabela}")
            feito[tabela] = cur.rowcount
        origem = conn.execute(
            "SELECT Value FROM ref.M00_BaseInfo WHERE Key = 'ParamBaseHash'").fetchone()
        conn.execute("INSERT OR REPLACE INTO M00_BaseInfo VALUES ('FaseABaseHash', ?)",
                     (origem[0] if origem else None,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("DETACH DATABASE ref")
    return feito
