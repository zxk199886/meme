"""Comparison engine: diff two parsed CMLDocument revisions.

Features are matched by Feature No. (balloon number), which Rolls-Royce
keeps stable across CM revisions (deleted balloons leave gaps in the
numbering). The section-G process grid is compared per subtask number so
that inserted/removed subtask columns do not produce false positives.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field

from .parser import CMLDocument, FIELD_NAMES

# Change categories drive the highlight colour in the report.
CATEGORY_DIMENSION = "DIMENSION"
CATEGORY_TOLERANCE = "TOLERANCE"
CATEGORY_TOOLING = "TOOLING / METHOD"
CATEGORY_FVRA = "FVRA / RISK"
CATEGORY_DATUM = "DATUM / THERMAL"
CATEGORY_PROCESS = "PROCESS GRID"
CATEGORY_TEXT = "TEXT / NOTES"

_FIELD_CATEGORY = {
    "B1": CATEGORY_DIMENSION, "B4": CATEGORY_DIMENSION, "B8": CATEGORY_DIMENSION,
    "B2": CATEGORY_TOLERANCE, "B3": CATEGORY_TOLERANCE,
    "B5": CATEGORY_TOLERANCE, "B6": CATEGORY_TOLERANCE,
    "E1": CATEGORY_TOOLING, "E2": CATEGORY_TOOLING, "E3": CATEGORY_TOOLING,
    "E4": CATEGORY_TOOLING, "E5": CATEGORY_TOOLING, "E6": CATEGORY_TOOLING,
    "F1": CATEGORY_TOOLING, "F2": CATEGORY_TOOLING, "F3": CATEGORY_TOOLING,
    "C1": CATEGORY_FVRA, "C2": CATEGORY_FVRA, "C3": CATEGORY_FVRA,
    "C4": CATEGORY_FVRA, "C5": CATEGORY_FVRA, "C6": CATEGORY_FVRA,
    "D1": CATEGORY_DATUM, "D2": CATEGORY_DATUM, "D3": CATEGORY_DATUM,
    "D4": CATEGORY_DATUM, "D5": CATEGORY_DATUM, "D6": CATEGORY_DATUM,
    "D7": CATEGORY_DATUM,
    "G4": CATEGORY_PROCESS,
}


def field_category(ref_code: str) -> str:
    return _FIELD_CATEGORY.get(ref_code, CATEGORY_TEXT)


@dataclass
class FieldChange:
    feature_no: str
    ref_code: str          # e.g. "B2", or "G3:<subtask key>" for grid cells
    field_name: str
    old: str
    new: str
    category: str


@dataclass
class MetadataChange:
    label: str
    old: str
    new: str


@dataclass
class DiffResult:
    old_doc: CMLDocument
    new_doc: CMLDocument
    added_features: list = field(default_factory=list)    # feature_no strings
    removed_features: list = field(default_factory=list)  # feature_no strings
    field_changes: list = field(default_factory=list)     # FieldChange
    metadata_changes: list = field(default_factory=list)  # MetadataChange
    added_subtasks: list = field(default_factory=list)    # Subtask
    removed_subtasks: list = field(default_factory=list)  # Subtask

    @property
    def modified_features(self) -> list:
        seen, out = set(), []
        for ch in self.field_changes:
            if ch.feature_no not in seen:
                seen.add(ch.feature_no)
                out.append(ch.feature_no)
        return out

    @property
    def has_changes(self) -> bool:
        return bool(self.added_features or self.removed_features
                    or self.field_changes or self.metadata_changes
                    or self.added_subtasks or self.removed_subtasks)


def display_value(value) -> str:
    """Human-readable rendering of a raw cell value."""
    if value is None:
        return "(blank)"
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return re.sub(r"[ \t]+", " ", str(value)).strip() or "(blank)"


def _normalise(value) -> str:
    """Canonical form used for equality: whitespace-, case- and
    number-format-insensitive so cosmetic edits don't raise diffs."""
    if value is None:
        return ""
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    text = re.sub(r"\s+", " ", str(value)).strip()
    try:
        num = float(text)
    except ValueError:
        return text.casefold()
    return repr(num)  # 0.40 == 0.4, 5 == 5.0


def values_equal(a, b) -> bool:
    return _normalise(a) == _normalise(b)


def _feature_sort_key(feature_no: str):
    m = re.match(r"^(\d+)", feature_no)
    return (0, int(m.group(1)), feature_no) if m else (1, 0, feature_no)


def compare(old_doc: CMLDocument, new_doc: CMLDocument) -> DiffResult:
    result = DiffResult(old_doc=old_doc, new_doc=new_doc)

    # --- document metadata ------------------------------------------------
    labels = list(old_doc.metadata) + [k for k in new_doc.metadata if k not in old_doc.metadata]
    for label in labels:
        old_v, new_v = old_doc.metadata.get(label), new_doc.metadata.get(label)
        if not values_equal(old_v, new_v):
            result.metadata_changes.append(
                MetadataChange(label, display_value(old_v), display_value(new_v)))
    if old_doc.version and new_doc.version and old_doc.version != new_doc.version:
        result.metadata_changes.append(
            MetadataChange("CM Version", old_doc.version, new_doc.version))

    # --- subtask columns (section G layout) -------------------------------
    for key, st in new_doc.subtasks.items():
        if key not in old_doc.subtasks:
            result.added_subtasks.append(st)
    for key, st in old_doc.subtasks.items():
        if key not in new_doc.subtasks:
            result.removed_subtasks.append(st)

    # --- features ----------------------------------------------------------
    old_keys, new_keys = set(old_doc.features), set(new_doc.features)
    result.added_features = sorted(new_keys - old_keys, key=_feature_sort_key)
    result.removed_features = sorted(old_keys - new_keys, key=_feature_sort_key)

    common_subtasks = [k for k in new_doc.subtasks if k in old_doc.subtasks]
    for key in sorted(old_keys & new_keys, key=_feature_sort_key):
        old_f, new_f = old_doc.features[key], new_doc.features[key]

        ref_codes = list(old_f.fields) + [c for c in new_f.fields if c not in old_f.fields]
        for code in ref_codes:
            if code == "A4":  # the matching key itself
                continue
            old_v, new_v = old_f.fields.get(code), new_f.fields.get(code)
            if not values_equal(old_v, new_v):
                result.field_changes.append(FieldChange(
                    feature_no=key, ref_code=code,
                    field_name=FIELD_NAMES.get(code, code),
                    old=display_value(old_v), new=display_value(new_v),
                    category=field_category(code)))

        for st_key in common_subtasks:
            old_c = old_f.subtask_codes.get(st_key)
            new_c = new_f.subtask_codes.get(st_key)
            if not values_equal(old_c, new_c):
                st = new_doc.subtasks[st_key]
                label = st.number + (f" ({st.description})" if st.description else "")
                result.field_changes.append(FieldChange(
                    feature_no=key, ref_code=f"G3:{st_key}",
                    field_name=f"Process grid @ {label}",
                    old=display_value(old_c), new=display_value(new_c),
                    category=CATEGORY_PROCESS))
    return result
