"""Shared enumerations for patent records."""

from enum import Enum


class SourceType(str, Enum):
    """Known patent record sources."""

    EPO = "EPO"
    USPTO = "USPTO"
    TURKPATENT = "TURKPATENT"
    CSV_IMPORT = "CSV_IMPORT"
    JSON_IMPORT = "JSON_IMPORT"
