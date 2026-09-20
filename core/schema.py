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
  DsBMd                    TEXT
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
    conn.commit()
