# Raw MYH Excel inputs

Place the six original MYH application-round Excel workbooks for **2020–2025** in this folder.

Rules for this folder:
- Keep raw source files unchanged.
- Do not manually edit sheets, headers, values, or filenames after the notebook configuration has been written.
- The notebook will later read from this folder through explicit import metadata/configuration.
- These files are the reproducible input layer for the Part 2 curated dataset workflow.

Expected use:
- `part_2/main.ipynb` reads from this folder.
- The final curated export is written elsewhere, under `part_2/data/processed/`.
