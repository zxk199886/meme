"""Command-line interface.

Usage:
    python -m cml_compare OLD.xlsx NEW.xlsx [-o marked_up.xlsx]
"""

from __future__ import annotations

import argparse
import os
import sys

from .diff import compare
from .parser import parse_cml
from .report import write_marked_up_report


def default_output_name(new_path: str) -> str:
    stem = os.path.splitext(os.path.basename(new_path))[0]
    return f"{stem}_COMPARED.xlsx"


def print_summary(diff) -> None:
    old_doc, new_doc = diff.old_doc, diff.new_doc
    print(f"Old: {os.path.basename(old_doc.path)}  ({old_doc.version or 'version n/a'}, "
          f"{len(old_doc.features)} features)")
    print(f"New: {os.path.basename(new_doc.path)}  ({new_doc.version or 'version n/a'}, "
          f"{len(new_doc.features)} features)")
    print("-" * 72)
    if not diff.has_changes:
        print("NO DIFFERENCES FOUND")
        return
    print(f"Added features    : {len(diff.added_features)}"
          + (f"  -> {', '.join(diff.added_features)}" if diff.added_features else ""))
    print(f"Removed features  : {len(diff.removed_features)}"
          + (f"  -> {', '.join(diff.removed_features)}" if diff.removed_features else ""))
    print(f"Modified features : {len(diff.modified_features)}"
          + (f"  -> {', '.join(diff.modified_features)}" if diff.modified_features else ""))
    print(f"Cell changes      : {len(diff.field_changes)}")
    print(f"Metadata changes  : {len(diff.metadata_changes)}")
    print(f"Subtask columns   : +{len(diff.added_subtasks)} / -{len(diff.removed_subtasks)}")
    if diff.field_changes:
        print("-" * 72)
        for ch in diff.field_changes:
            print(f"  Feature {ch.feature_no:>5}  {ch.field_name}: "
                  f"{ch.old}  ->  {ch.new}   [{ch.category}]")
    for mc in diff.metadata_changes:
        print(f"  Metadata  {mc.label}: {mc.old}  ->  {mc.new}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="cml_compare",
        description="Compare two revisions of a Characteristics Matrix (CML) "
                    "workbook and produce a marked-up copy of the new revision "
                    "with all differences highlighted.")
    ap.add_argument("old", help="Path to the OLD CML revision (.xlsx)")
    ap.add_argument("new", help="Path to the NEW CML revision (.xlsx)")
    ap.add_argument("-o", "--output",
                    help="Output path for the marked-up workbook "
                         "(default: <new file>_COMPARED.xlsx)")
    ap.add_argument("--no-report", action="store_true",
                    help="Only print the console summary, do not write a workbook")
    args = ap.parse_args(argv)

    for path in (args.old, args.new):
        if not os.path.isfile(path):
            ap.error(f"File not found: {path}")

    print("Parsing old revision ...")
    old_doc = parse_cml(args.old)
    print("Parsing new revision ...")
    new_doc = parse_cml(args.new)
    diff = compare(old_doc, new_doc)
    print()
    print_summary(diff)

    if not args.no_report:
        output = args.output or default_output_name(args.new)
        print()
        print("Writing marked-up report ...")
        write_marked_up_report(diff, output)
        print(f"Report written to: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
