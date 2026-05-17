# Processed Part 2 exports

This folder contains notebook-generated processed outputs for the final Part 2 MYH curated applications dataset.

## Canonical final Part 2 exports

- `myh_curated_applications_2020_2025.csv`  
  The validated curated longitudinal applications dataset created from the six raw MYH Excel workbooks for application rounds 2020–2025, stored in a transparent text format that is easy to inspect.

- `myh_curated_applications_2020_2025.parquet`  
  The same validated curated longitudinal applications dataset, stored as the typed Parquet companion export for later programmatic reuse.

## Export contract

Both files are written by `part_2/main.ipynb` only after the final quality gate passes.

- Source DataFrame: `curated_applications`
- Grain: one row = one application in one MYH application round
- Scope: 2020–2025
- Schema: locked 32-field curated order
- Index column: not exported in either file

### CSV specifics

- Encoding: UTF-8
- Missing values: empty CSV fields, with structural nulls and later-year source gaps documented in the notebook missingness review

### Parquet specifics

- Engine: PyArrow through pandas `to_parquet(..., engine="pyarrow")`
- Compression: Snappy
- Index: not exported
- Local dependency: PyArrow must be installed for the notebook's Parquet export path; the notebook raises a targeted message if it is missing

## Why both exports are retained

The final Part 2 decision is to retain **both** export formats:
- CSV remains the simplest inspection and exchange artifact,
- Parquet adds a typed, machine-friendly companion output for downstream analytical or loading work.

Both files are generated from the same validated curated table and are checked after writing so the paired exports remain structurally aligned.

## SQL/API handoff

The later SQL/API phase can rely on these paired files as the finished serialized forms of the Part 2 curated dataset. They carry the same table grain, year scope, locked schema, and application-key safety verified in the notebook.

The downstream loader may choose CSV or Parquet based on tooling, but it should preserve:
- the uniqueness rule represented by `(source_year, diarienummer)`,
- source-traceability fields,
- normalized categorical fields,
- derived boolean read-model fields,
- and structural nulls where older workbooks did not contain later-year concepts.

The detailed handoff rationale is recorded in Section 12 of `part_2/main.ipynb`.

## Rules for this folder

- Do not treat processed files as manual inputs.
- Recreate them by rerunning `part_2/main.ipynb` from the unchanged raw Excel files.
- Do not fill structural nulls with artificial values only to make the exports look denser.
