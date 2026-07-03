# CML Revision Compare

Compares two revisions of a Rolls-Royce MRO **Characteristics Matrix (CML/CM)**
workbook and produces a **marked-up copy of the new revision** in which every
difference is colour-highlighted, plus a prepended *Comparison Summary* sheet.

Built for the First Article Inspection workflow: when a new CM revision is
released (manual / repair scheme update), run the comparison to instantly see
which balloons were added or removed and which dimensions, tolerances,
measurement tools or methods changed.

## What is compared

| Area | Detail |
|---|---|
| Features (balloons) | Added / removed / modified, matched by **Feature No.** (stable across revisions) |
| Section A | Drawing/definition details (manual ref, subtasks, figure ref, sub-features) |
| Section B | Nominal dimension, **lower/upper tolerance**, control limits, description, feature code |
| Section C | FVRA: Severity, Occurrence, Detection, RPN, S/L/F/P/W, inspection category |
| Section D | Datums, thermal sensitivity data |
| Section E | **Verification method, equipment type/id**, MSA method/report/result |
| Section F | Independent verification (over-check) method and equipment |
| Section G | Process grid (X/M/P/IC/IM/IO/IV/ID codes) compared **per subtask number**, so inserted/removed subtask columns don't create false positives; final verification method; notes |
| Metadata | Part name, part numbers, repair scheme, issue date, CM version |

Comparison is whitespace-, case- and number-format-insensitive (`0.40` = `0.4`),
so cosmetic edits are not reported.

## Output: the marked-up workbook

A copy of the **new** CML with:

- changed cells **colour-filled by category** (tolerance, dimension,
  tooling/method, FVRA, process grid, datum, text) and a **cell comment**
  stating the old value,
- added features: whole row green,
- added subtask columns: header green,
- a **Comparison Summary** sheet (first tab): counts, colour legend, metadata
  changes, added features, **removed features** (with their key data — they no
  longer exist in the new file), subtask column changes, and a table of every
  cell change with its CM cell reference.

## Install

```bash
pip install -r cml_compare/requirements.txt   # openpyxl, flask
```

## Command line

```bash
python -m cml_compare OLD_CML.xlsx NEW_CML.xlsx [-o marked_up.xlsx]
python -m cml_compare OLD_CML.xlsx NEW_CML.xlsx --no-report   # console summary only
```

Default output name: `<new file>_COMPARED.xlsx`.

## Web app

```bash
python -m cml_compare.webapp     # then open http://127.0.0.1:5000
```

Drag-drop the old and new CML, view the differences in the browser, download
the marked-up workbook. Files are processed in a temporary directory and are
not persisted. Set `CML_COMPARE_PORT` to change the port.

## Notes and limitations

- Both files must be **Excel-saved** `.xlsx` workbooks. The CM sheet contains
  formulas (RPN, inspection category, metadata links); Excel stores their
  cached values, which this tool reads. Files re-saved by other tools without
  cached values will read those cells as blank.
- The marked-up copy is a **review aid, not a controlled document**. Embedded
  images / OLE objects (e.g. balloon diagram attachments) are not carried
  over by openpyxl — refer to the controlled CML for those. Excel
  re-calculates the formula cells when the marked-up copy is opened.
- The parser locates the header row and every column by their reference codes
  (`(A1)`…`(G5)`), not fixed cell addresses, so it tolerates template drift
  between CM template versions.
- If a balloon is renumbered between revisions it will be reported as
  removed + added (Feature No. is the matching key).

## Tests

```bash
python -m unittest tests.test_cml_compare -v
```

Tests use small synthetic workbooks that mimic the CM template layout —
no proprietary data is included in this repository.
