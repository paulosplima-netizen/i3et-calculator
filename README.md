# i3ET Calculator

**Light Vehicle Cradle-to-Gate Carbon Footprint**

A calculator for the mass and the cradle-to-gate greenhouse gas emissions of light
passenger vehicles. It reimplements modules M1 (mass) and M2 (manufacturing GHG) of
the **i3ET** model — *Integrated Economic, Energy and Environment Transport Model* —
as an auditable, testable program.

Developed at **NIPE/UNICAMP**.

---

## ⚠️ Licensing: the code is open, the data is not

This repository carries three different licences. Please read before reusing anything.

| Layer | Path | Licence |
|---|---|---|
| Code | `core/`, `ui/`, `pages/`, `app.py`, `tools/`, `tests/` | **MIT** — see `LICENSE` |
| Documentation | `docs/` | **CC BY 4.0** — see `docs/LICENSE` |
| Data | `data/` | **Not open.** GREET-derived factors are restricted to **non-commercial use** — see `data/NOTICE.md` |

A single `LICENSE` file at the root would suggest MIT covers everything. It does not.
The emission factors derived from GREET (UChicago Argonne, LLC) may be redistributed
for non-commercial use only, and carry attribution requirements. If you need
commercial use, replace the emission factor version — the architecture makes that a
parameter choice, not a rewrite.

---

## What it calculates

For a given vehicle and scenario:

- **Mass**, broken down by subgroup, by GREET group and by material (kg);
- **Cradle-to-gate GHG emissions**, broken down the same way (kg CO₂e, GWP-100, IPCC AR6);
- **Vehicle assembly** emissions, either read from the emission factor table or
  computed process by process;
- A **coverage figure**: how much of the vehicle's mass has no published emission
  factor in the chosen version. A missing factor is absence of data, not zero
  emissions, and every result says so.

System boundary: raw material extraction through the factory gate. The use phase,
end-of-life and lifetime replacements are out of scope — they belong to modules M3
to M6 of the i3ET and to later versions of this tool.

---

## Design principles

**The core is pure.** `core/` never imports the user interface, never reads files on
its own and never prints. Tables in, tables out. The same code runs in the web app,
in a notebook and in the test suite.

**Every join is declared.** No positional matching. Every relationship between tables
goes through an explicit foreign key that the database enforces.

**Version is a key, not a footnote.** The mass parameter version, material recipe,
emission factor version and assembly parameter version are part of the key of every
result. Two results are comparable only if the versions are stated.

**The reference base is immutable.** Users create scenarios and vehicles, and may add
their own emission factor versions in their project file. The reference parameters are
never modified — which is what makes results reproducible.

**Nothing is presented that cannot be reconciled.** Mass and emissions must close
across subgroups, groups, materials and totals to within 1e-9 relative. A failed
invariant blocks export.

---

## Status

Under development. The reference database is built and validated, the calculation
core reproduces the i3ET — mass on all 72 configurations of the spreadsheet (39 exact,
33 explained by a module that is out of scope) and cradle-to-gate emissions on the
twelve project vehicles — and the seven screens of the web interface run. What is
left is publication.

## Running it

```
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

streamlit run app.py                 # the web interface, seven screens

python -m pytest -q                  # the test suite
python tools/validate_core.py        # the acceptance table against the i3ET
python tools/report_divergences.py   # regenerates docs/05
python tools/export_results.py       # XLSX, CSV, HTML and PDF into saidas/
```

The same three commands run on every push, in `.github/workflows/tests.yml`.
`data/csv/` carries the whole reference base as CSV, and `data/base_referencia.sqlite`
opens in any SQLite viewer — neither needs Python to be read.

## Documentation

Full specification, in Portuguese, in `docs/`:

| File | Contents |
|---|---|
| `01-especificacao-funcional.md` | Scope, glossary, every equation, reconciliation with the i3ET, resolved divergences, validation criteria |
| `02-dicionario-de-dados.md` | Column-by-column dictionary, keys, domains, integrity rules, full SQL DDL |
| `03-ferramentas.md` | Tooling inventory |
| `04-especificacao-tecnica.md` | Architecture, algorithm, interface, output tables, export, tests, publication |
| `05-relatorio-de-divergencias.md` | Where and why the calculator differs from the i3ET spreadsheet, and what to adjust there |

The specification is written to be sufficient on its own: someone should be able to
rebuild this program from `docs/` alone, without reading the source. That claim is
tested, not assumed.

## How to cite

Lima, P. S. P. (2026). *i3ET Calculator: Light Vehicle Cradle-to-Gate Carbon
Footprint* (version 0.9.0). NIPE/UNICAMP.
https://github.com/paulosplima-netizen/i3et-calculator

The citation metadata live in `CITATION.cff` (GitHub's *Cite this repository*)
and `.zenodo.json` (the archived record and its DOI). Each release on GitHub is
archived by Zenodo with its own DOI.

## Data sources

- **GREET** (Argonne National Laboratory), versions 2022, 2023 and 2024 — material
  emission factors, battery composition, vehicle assembly energy;
- **Projeto do Berço ao Portão** — FGV/Unicamp for Fundep, under the Programa Move of
  the Brazilian federal government — Brazilian emission factors;
- **i3ET** (`LCA_LV_i3ET`) — the reference model this tool reimplements.
