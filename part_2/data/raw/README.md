# Raw MYH Excel inputs

This folder contains the unchanged MYH application-round Excel workbooks used by Part 2.

## Expected source workbooks

- `resultat-ansokningsomgang-2020.xlsx`
- `resultat-ansokningsomgang-2021.xlsx`
- `resultat-ansokningsomgang-2022.xlsx`
- `resultat-ansokningsomgang-2023.xlsx`
- `resultat-ansokningsomgang-2024.xlsx`
- `resultat-ansokningsomgang-2025.xlsx`

## Rules for this folder

- Keep raw source files unchanged.
- Do not manually edit sheets, headers, values, or filenames after the notebook configuration has been written.
- `part_2/main.ipynb` reads from this folder.
- These files are the reproducible input layer for the Part 2 curated dataset workflow.
- The final curated export is written elsewhere, under `part_2/data/processed/`.
