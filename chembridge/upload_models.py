"""Typed result models and stable codes for the V1 unknown-upload workflow.

The existing package has no error-code convention: it uses plain InputError
messages, CLI exit codes 0/1/2 and manifest statuses complete/partial/failed.
These codes are therefore introduced as a small, self-contained layer and are
mapped to the four V1 statuses by upload_workflow.aggregate_upload_result.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal

UploadStatus = Literal["success", "partial_success", "failed", "requires_user_input"]
V1Format = Literal["mol", "sdf", "csv", "smiles"]
V1_FORMATS: tuple[str, ...] = ("mol", "sdf", "csv", "smiles")


class ErrorCode(str, Enum):
    EMPTY_OR_UNREADABLE_FILE = "EMPTY_OR_UNREADABLE_FILE"
    UNSUPPORTED_OR_UNKNOWN_FORMAT = "UNSUPPORTED_OR_UNKNOWN_FORMAT"
    AMBIGUOUS_FORMAT = "AMBIGUOUS_FORMAT"
    NO_STRUCTURE_FIELD = "NO_STRUCTURE_FIELD"
    MULTIPLE_STRUCTURE_FIELDS = "MULTIPLE_STRUCTURE_FIELDS"
    MOLECULE_PARSE_FAILED = "MOLECULE_PARSE_FAILED"
    NO_VALID_MOLECULES = "NO_VALID_MOLECULES"


class WarningCode(str, Enum):
    EXTENSION_CONTENT_MISMATCH = "EXTENSION_CONTENT_MISMATCH"


@dataclass
class FormatDetectionResult:
    detected_format: str | None = None
    original_filename: str = ""
    original_extension: str = ""
    extension_matches_content: bool = True
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    candidate_formats: list[str] = field(default_factory=list)
    requires_user_input: bool = False
    code: str | None = None
    message: str = ""


@dataclass
class MolecularRecordDraft:
    """One molecular record before parsing; preserves provenance."""

    source_filename: str
    source_record_number: int
    selected_source_field: str | None
    raw_structure_value: str
    inferred_source_format: str
    parser_kind: str = "smiles"
    preparsed_mol: Any | None = None
    preparsed_error: str | None = None


@dataclass
class SuccessfulMolecule:
    source_filename: str
    source_record_number: int
    selected_source_field: str | None
    raw_structure_value: str
    inferred_source_format: str
    canonical_smiles: str
    properties: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass
class FailedRecordDetail:
    source_filename: str
    source_record_number: int
    selected_source_field: str | None
    raw_structure_value: str
    inferred_source_format: str
    code: str = ErrorCode.MOLECULE_PARSE_FAILED.value
    message: str = ""


@dataclass
class UploadResult:
    status: UploadStatus
    code: str | None
    message: str
    original_filename: str = ""
    original_extension: str = ""
    file_size: int | None = None
    detection: FormatDetectionResult | None = None
    detected_format: str | None = None
    selected_structure_field: str | None = None
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    skipped_records: int = 0
    successful_results: list[SuccessfulMolecule] = field(default_factory=list)
    failed_record_details: list[FailedRecordDetail] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    candidate_formats: list[str] = field(default_factory=list)
    candidate_fields: list[str] = field(default_factory=list)
    output_directory: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
