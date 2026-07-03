"""CML (Characteristics Matrix) revision comparison tool.

Parses Rolls-Royce MRO Characteristics Matrix workbooks, compares two
revisions feature-by-feature, and produces a marked-up copy of the new
revision with every difference highlighted.
"""

__version__ = "1.0.0"

from .parser import CMLDocument, Feature, parse_cml  # noqa: F401
from .diff import DiffResult, compare  # noqa: F401
from .report import write_marked_up_report  # noqa: F401
