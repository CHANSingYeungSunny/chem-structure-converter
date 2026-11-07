"""V1 unknown-upload workflow: MOL / SDF / CSV / plain SMILES only.

Deliberately layered: format detection, table inspection, record parsing and
result aggregation are separate functions. Chemistry parsing, properties,
images and format conversion are reused from chembridge.io / chembridge.pipeline;
this module does not implement a second chemistry engine.
"""
from __future__ import annotations

import csv
import io as _io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rdkit import Chem, rdBase

from .io import (Detection, InputError, _lines, _parse_value, _valid,
                 decode_bytes, normalize_header, parse_records)
from .pipeline import convert_file, properties
from .upload_models import (ErrorCode, FailedRecordDetail, FormatDetectionResult,
                            MolecularRecordDraft, SuccessfulMolecule, UploadResult,
                            V1_FORMATS, WarningCode)

# Case-insensitive comparison is done through io.normalize_header.
CANDIDATE_FIELD_KINDS: dict[str, str] = {
    "smiles": "smiles",
    "canonicalsmiles": "smiles",
    "isomericsmiles": "smiles",
    "inchi": "inchi",
    "mol": "mol",
    "molblock": "mol",
    "structure": "auto",
}
EXPECTED_EXTENSIONS: dict[str, set[str]] = {
    "mol": {"mol"},
    "sdf": {"sdf", "sd"},
    "csv": {"csv"},
    "smiles": {"smi", "smiles"},
}
NEUTRAL_EXTENSIONS = {"", "txt", "text", "dat"}
SAMPLE_LIMIT = 20
V1_OUTPUTS = "csv,json,smi,sdf,mol,png,svg,inchi,selfies"


def _concise(exc: BaseException) -> str:
    """User-readable one-line message; never expose a stack trace."""
    text = str(exc).strip() or type(exc).__name__
    return text.splitlines()[0][:200]


def original_extension(filename: str) -> str:
    name = Path(filename.replace("\\", "/")).name
    suffix = Path(name).suffix.lstrip(".").lower()
    if suffix == "gz":
        suffix = Path(name).with_suffix("").suffix.lstrip(".").lower()
    return suffix


def _safe_basename(filename: str) -> str:
    """Never let an uploaded name become a trusted server-side path."""
    name = Path(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", name).lstrip(".")[:120]
    return cleaned if cleaned and cleaned not in {".", ".."} else "upload.bin"


def _base_result(data: bytes, filename: str, file_size: int | None) -> UploadResult:
    return UploadResult(
        status="failed", code=None, message="",
        original_filename=Path(filename.replace("\\", "/")).name,
        original_extension=original_extension(filename),
        file_size=file_size if file_size is not None else len(data),
    )


def _failure(base: UploadResult, code: ErrorCode, message: str,
             detection: FormatDetectionResult | None = None) -> UploadResult:
    base.status = "failed"
    base.code = code.value
    base.message = message
    if detection is not None:
        base.detection = detection
        base.detected_format = detection.detected_format
        base.warnings = list(detection.warnings)
        base.candidate_formats = list(detection.candidate_formats)
    return base


def _requires_input(base: UploadResult, code: ErrorCode, message: str,
                    detection: FormatDetectionResult, *,
                    candidate_fields: list[str] | None = None,
                    selected_structure_field: str | None = None) -> UploadResult:
    base.status = "requires_user_input"
    base.code = code.value
    base.message = message
    base.detection = detection
    base.detected_format = detection.detected_format
    base.warnings = list(detection.warnings)
    base.candidate_formats = list(detection.candidate_formats)
    base.candidate_fields = list(candidate_fields or [])
    base.selected_structure_field = selected_structure_field
    return base


# ---------------------------------------------------------------------------
# 1. Readability + format detection
# ---------------------------------------------------------------------------

def decode_upload(data: bytes) -> str:
    """Return decoded text or raise InputError for empty/unreadable uploads."""
    if not data or not data.strip():
        raise InputError("The uploaded file is empty.")
    text = decode_bytes(data)
    if not text.strip():
        raise InputError("The uploaded file contains no readable text.")
    return text


def _mol_markers(text: str) -> bool:
    return bool(re.search(r"V(?:2000|3000)\s*$", text, re.M)) and "M  END" in text


def _sdf_blocks(text: str) -> list[str]:
    return [b for b in re.split(r"^\$\$\$\$[^\S\n]*$", text, flags=re.M) if b.strip()]


def _sdf_sample_ok(text: str) -> bool:
    with rdBase.BlockLogs():
        supplier = Chem.ForwardSDMolSupplier(
            _io.BytesIO(text.encode("utf-8")), sanitize=True,
            removeHs=True, strictParsing=True)
        return any(mol is not None for mol in supplier)


def _mol_block_ok(text: str, first_block: str) -> bool:
    with rdBase.BlockLogs():
        for candidate in (text, first_block):
            if Chem.MolFromMolBlock(candidate, sanitize=True, removeHs=True,
                                    strictParsing=True) is not None:
                return True
    return False


def _delimited_rows(text: str) -> tuple[str, list[tuple[int, list[str]]]] | None:
    """Return (delimiter, [(physical line number, cells)]) for non-blank rows."""
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    try:
        delimiter = csv.Sniffer().sniff(text[:16384], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    try:
        raw_rows = list(csv.reader(_io.StringIO(text), delimiter=delimiter, strict=True))
    except csv.Error:
        return None
    rows = [(number, row) for number, row in enumerate(raw_rows, 1)
            if any(cell.strip() for cell in row)]
    if len(rows) < 2:
        return None
    header = [cell.strip() for cell in rows[0][1]]
    if not header or any(not h for h in header):
        return None
    if len({h.lower() for h in header}) != len(header):
        return None
    # A header must look like column names, not like a molecular record.
    if any(_valid(header_cell, "smiles") for header_cell in header):
        return None
    # A one-column table whose header is a known structure field is a valid CSV
    # interpretation even without a delimiter character in the first line; the
    # same bytes are also a plain-SMILES file with an optional header, which is
    # a genuine ambiguity handled by detect_upload_format.
    single_column_header_table = len(header) == 1 and _field_kind(header[0]) is not None
    if delimiter not in first and not single_column_header_table:
        return None
    # Width mismatches are NOT rejected here: they become per-record errors in
    # build_csv_records, matching the existing converter's behaviour.
    return delimiter, rows


def _field_kind(name: str) -> str | None:
    return CANDIDATE_FIELD_KINDS.get(normalize_header(name))


def _values_parse(values: list[str], kind: str) -> str | None:
    """Return the parser kind that validates at least one sampled value."""
    kinds = ("smiles", "mol", "inchi") if kind == "auto" else (kind,)
    for candidate in kinds:
        if any(_valid(value, candidate) for value in values[:SAMPLE_LIMIT]):
            return candidate
    return None


def _csv_evidence(text: str) -> tuple[bool, list[str]]:
    parsed = _delimited_rows(text)
    if parsed is None:
        return False, []
    _, rows = parsed
    header = [c.strip() for c in rows[0][1]]
    candidates = [h for h in header if _field_kind(h) is not None]
    if not candidates:
        # Still a readable table; NO_STRUCTURE_FIELD is decided during inspection.
        return True, ["Consistently readable delimited table with identifiable columns."]
    sample = [row for _, row in rows[1:]]
    for name in candidates:
        values = [r[header.index(name)].strip() for r in sample
                  if len(r) > header.index(name) and r[header.index(name)].strip()]
        if values and _values_parse(values, _field_kind(name) or "smiles"):
            return True, ["Delimited table with a candidate molecular structure column "
                          f"'{name}' whose sampled values parse with RDKit."]
    return True, ["Delimited table with candidate column names; sampled values need user review."]


def _smiles_evidence(text: str) -> tuple[bool, list[str]]:
    lines = _lines(text)
    if not lines:
        return False, []
    considered = lines
    if considered and len(considered[0][1].split()) == 1 \
            and considered[0][1].lower() in {"smiles", "inchi", "selfies"}:
        considered = considered[1:]
    parsed = sum(1 for _, line in considered
                 if _valid(line.split(maxsplit=1)[0], "smiles"))
    if parsed == 0:
        return False, []
    return True, [f"{parsed} of {len(considered)} sampled non-empty text records "
                  "parse as SMILES with RDKit."]


def detect_upload_format(text: str, filename: str, *,
                         selected_format: str | None = None) -> FormatDetectionResult:
    """Content-evidence detection limited to the four V1 formats."""
    ext = original_extension(filename)
    result = FormatDetectionResult(
        original_filename=Path(filename.replace("\\", "/")).name,
        original_extension=ext,
    )

    if selected_format is not None:
        if selected_format not in V1_FORMATS:
            result.code = ErrorCode.UNSUPPORTED_OR_UNKNOWN_FORMAT.value
            result.message = f"Unsupported V1 format selection: {selected_format!r}."
            return result
        result.detected_format = selected_format
        result.evidence = [f"User selected {selected_format} after an ambiguous result."]
        result.message = f"Format selected by user: {selected_format}."
        _apply_extension_check(result)
        return result

    separators = re.findall(r"^\$\$\$\$[^\S\n]*$", text, re.M)
    blocks = _sdf_blocks(text)
    markers = _mol_markers(text)
    sdf_strong = bool(separators) and markers and _sdf_sample_ok(text)
    mol_strong = markers and _mol_block_ok(text, blocks[0] if blocks else text)
    if sdf_strong:
        # Stronger-content precedence: a valid $$$$ separator plus a parseable
        # MOL-block record always means SDF, even for a single record whose body
        # also parses as one MOL. A lone MOL block is only used without $$$$.
        mol_strong = False
    csv_strong, csv_notes = _csv_evidence(text)
    csv_columns = 0
    parsed_table = _delimited_rows(text)
    if parsed_table is not None:
        csv_columns = len(parsed_table[1][0][1])
    smiles_strong, smiles_notes = (False, [])
    if not markers and not separators:
        smiles_strong, smiles_notes = _smiles_evidence(text)

    strong: dict[str, list[str]] = {}
    if sdf_strong:
        strong["sdf"] = ["Found $$$$ record separators.", "Found MOL block markers.",
                         "Sampled SDF records parse with RDKit (SDF outranks MOL)."]
    if mol_strong:
        strong["mol"] = ["Found M  END.", "Found V2000/V3000 marker.",
                         "No $$$$ separator; content parses as a MOL block with RDKit."]
    if csv_strong:
        strong["csv"] = csv_notes
        if csv_columns > 1:
            smiles_strong = False  # a real multi-column table outranks plain text
    if smiles_strong:
        strong["smiles"] = smiles_notes

    if len(strong) > 1:
        result.requires_user_input = True
        result.candidate_formats = sorted(strong)
        result.evidence = [note for notes in strong.values() for note in notes]
        result.code = ErrorCode.AMBIGUOUS_FORMAT.value
        result.message = "Several V1 formats fit the content; choose one explicitly."
        return result
    if not strong:
        result.code = ErrorCode.UNSUPPORTED_OR_UNKNOWN_FORMAT.value
        result.message = "No V1 format (MOL/SDF/CSV/plain SMILES) fits the file content."
        return result

    result.detected_format = next(iter(strong))
    result.evidence = strong[result.detected_format]
    result.message = f"Detected {result.detected_format} from content evidence."
    _apply_extension_check(result)
    return result


def _apply_extension_check(result: FormatDetectionResult) -> None:
    if result.detected_format is None:
        return
    ext = result.original_extension
    expected = EXPECTED_EXTENSIONS.get(result.detected_format, set())
    matches = ext in NEUTRAL_EXTENSIONS or ext in expected
    result.extension_matches_content = matches
    if not matches:
        result.warnings.append(WarningCode.EXTENSION_CONTENT_MISMATCH.value)
        result.evidence.append(
            f"Extension '.{ext}' disagrees with detected content "
            f"'{result.detected_format}'; content takes priority, filename preserved."
        )


# ---------------------------------------------------------------------------
# 2. Table inspection (CSV)
# ---------------------------------------------------------------------------

@dataclass
class CsvInspection:
    header: list[str] = field(default_factory=list)
    rows: list[tuple[int, list[str]]] = field(default_factory=list)
    delimiter: str = ","
    usable_fields: list[tuple[str, str]] = field(default_factory=list)
    candidate_fields: list[str] = field(default_factory=list)
    skipped_blank_rows: int = 0
    error_code: str | None = None
    message: str = ""


def inspect_csv_fields(text: str, *, selected_field: str | None = None) -> CsvInspection:
    """Find usable molecular structure columns; never choose between several."""
    parsed = _delimited_rows(text)
    if parsed is None:
        return CsvInspection(
            error_code=ErrorCode.NO_STRUCTURE_FIELD.value,
            message="The file is not a consistently readable delimited table.")
    delimiter, rows = parsed
    inspection = CsvInspection(
        header=[cell.strip() for cell in rows[0][1]],
        rows=rows[1:],
        delimiter=delimiter,
        skipped_blank_rows=sum(1 for line in text.splitlines() if not line.strip()),
    )
    named = [(h, _field_kind(h)) for h in inspection.header if _field_kind(h) is not None]
    inspection.candidate_fields = [h for h, _ in named]
    if not named:
        inspection.error_code = ErrorCode.NO_STRUCTURE_FIELD.value
        inspection.message = "No candidate molecular structure column was found."
        return inspection

    if selected_field is not None:
        exact = next((h for h, _ in named if h.lower() == selected_field.lower()), None)
        if exact is None:
            inspection.error_code = ErrorCode.NO_STRUCTURE_FIELD.value
            inspection.message = f"Selected field {selected_field!r} is not a structure column."
            return inspection
        kind = _field_kind(exact) or "smiles"
        values = [row[inspection.header.index(exact)].strip()
                  for _, row in inspection.rows
                  if len(row) > inspection.header.index(exact)]
        resolved = _values_parse([v for v in values if v], kind) or kind
        inspection.usable_fields = [(exact, resolved)]
        return inspection

    for name, kind in named:
        index = inspection.header.index(name)
        values = [row[index].strip() for _, row in inspection.rows if len(row) > index]
        values = [v for v in values if v][:SAMPLE_LIMIT]
        resolved = _values_parse(values, kind or "smiles") if values else None
        if resolved:
            inspection.usable_fields.append((name, resolved))
    if not inspection.usable_fields:
        inspection.error_code = ErrorCode.NO_STRUCTURE_FIELD.value
        inspection.message = ("Candidate column names exist but no sampled value "
                              "could be parsed as a molecule.")
    return inspection


# ---------------------------------------------------------------------------
# 3. Record building + independent parsing
# ---------------------------------------------------------------------------

def build_csv_records(inspection: CsvInspection, field_name: str, parser_kind: str,
                      filename: str) -> tuple[list[MolecularRecordDraft], int]:
    """Preserve original data row numbers (header is row 1)."""
    index = inspection.header.index(field_name)
    drafts: list[MolecularRecordDraft] = []
    for row_number, row in inspection.rows:
        raw = row[index] if len(row) > index else ""
        draft = MolecularRecordDraft(
            source_filename=Path(filename.replace("\\", "/")).name,
            source_record_number=row_number,
            selected_source_field=field_name,
            raw_structure_value=raw,
            inferred_source_format="csv",
            parser_kind=parser_kind,
        )
        if len(row) != len(inspection.header):
            draft.preparsed_error = "Column count does not match the header."
        drafts.append(draft)
    return drafts, inspection.skipped_blank_rows


def build_nontabular_records(text: str, fmt: str,
                             filename: str) -> tuple[list[MolecularRecordDraft], int, str | None]:
    """Reuse io.parse_records for MOL / SDF / plain SMILES splitting and parsing."""
    detection = Detection(fmt, "V1 content evidence", "signature",
                          original_extension(filename))
    try:
        records = parse_records(text, detection)
    except (InputError, OSError, ValueError) as exc:
        return [], 0, _concise(exc)
    drafts = [
        MolecularRecordDraft(
            source_filename=Path(filename.replace("\\", "/")).name,
            source_record_number=record.index,
            selected_source_field=None,
            raw_structure_value=record.raw if isinstance(record.raw, str) else str(record.raw),
            inferred_source_format=fmt,
            parser_kind=record.representation or fmt,
            preparsed_mol=record.mol if not record.error else None,
            preparsed_error=record.error or None,
        )
        for record in records
    ]
    skipped = max(0, len(text.splitlines()) - len(records))
    return drafts, skipped, None


def _parse_auto(raw: str) -> Any:
    last: Exception | None = None
    for kind in ("smiles", "mol", "inchi"):
        try:
            return _parse_value(raw, kind)
        except Exception as exc:  # expected RDKit/parse failures at record level
            last = exc
    raise InputError(_concise(last) if last else "Cannot parse molecular structure.")


def parse_molecular_record(draft: MolecularRecordDraft) -> SuccessfulMolecule | FailedRecordDetail:
    """Parse one record independently; a failure never affects other records."""
    common = dict(
        source_filename=draft.source_filename,
        source_record_number=draft.source_record_number,
        selected_source_field=draft.selected_source_field,
        raw_structure_value=draft.raw_structure_value,
        inferred_source_format=draft.inferred_source_format,
    )
    try:
        if draft.preparsed_error:
            raise InputError(draft.preparsed_error)
        mol = draft.preparsed_mol
        if mol is None:
            if not draft.raw_structure_value.strip():
                raise InputError("Missing or non-text molecular structure.")
            mol = (_parse_auto(draft.raw_structure_value) if draft.parser_kind == "auto"
                   else _parse_value(draft.raw_structure_value, draft.parser_kind))
        if mol is None or mol.GetNumAtoms() == 0:
            raise InputError("RDKit could not build a molecule from this record.")
        if mol.GetNumAtoms() > 1000:
            raise InputError("Molecule exceeds 1000 atoms.")
        if any(atom.GetAtomicNum() == 0 for atom in mol.GetAtoms()):
            raise InputError("Wildcard/query atoms are out of scope.")
        smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
    except Exception as exc:
        return FailedRecordDetail(**common,
                                  code=ErrorCode.MOLECULE_PARSE_FAILED.value,
                                  message=_concise(exc))

    warnings: list[str] = []
    try:
        props = properties(mol)
    except Exception as exc:
        props = {}
        warnings.append(f"Property calculation failed: {_concise(exc)}")
    return SuccessfulMolecule(**common, canonical_smiles=smiles,
                              properties=props, warnings=warnings)


# ---------------------------------------------------------------------------
# 4. Aggregation + existing output capabilities
# ---------------------------------------------------------------------------

def aggregate_upload_result(
    *, base: UploadResult, detection: FormatDetectionResult,
    successes: list[SuccessfulMolecule], failures: list[FailedRecordDetail],
    skipped_records: int, selected_structure_field: str | None,
) -> UploadResult:
    base.detection = detection
    base.detected_format = detection.detected_format
    base.selected_structure_field = selected_structure_field
    base.warnings = list(detection.warnings)
    base.total_records = len(successes) + len(failures) + skipped_records
    base.successful_records = len(successes)
    base.failed_records = len(failures)
    base.skipped_records = skipped_records
    base.successful_results = successes
    base.failed_record_details = failures

    if not successes:
        base.status = "failed"
        base.code = ErrorCode.NO_VALID_MOLECULES.value
        base.message = "No molecular record could be parsed."
    elif failures:
        base.status = "partial_success"
        base.code = None
        base.message = (f"{len(successes)} record(s) parsed, {len(failures)} failed; "
                        "valid results were preserved.")
    else:
        base.status = "success"
        base.code = None
        base.message = f"All {len(successes)} molecular record(s) parsed successfully."
    return base


def _attach_outputs(result: UploadResult, data: bytes, filename: str, fmt: str,
                    field_name: str | None, parser_kind: str | None,
                    output_dir: Path) -> None:
    """Reuse convert_file for images / conversion / properties; never replace it."""
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        source = output_dir / _safe_basename(filename)
        source.write_bytes(data)
        converted = output_dir / "converted"
        if converted.exists():
            result.warnings.append(
                "Optional output generation skipped: output directory already exists.")
            return
        kwargs: dict[str, Any] = {"input_format": fmt, "outputs": V1_OUTPUTS}
        if fmt == "csv" and field_name:
            kwargs["column"] = field_name
            kwargs["column_format"] = parser_kind if parser_kind != "auto" else "auto"
        convert_file(source, converted, **kwargs)
    except Exception as exc:
        # Reported, never silent: parsed molecules and their properties remain.
        result.warnings.append(f"Optional output generation failed: {_concise(exc)}")
        return
    result.output_directory = str(converted)
    molecules_path = converted / "molecules.json"
    if molecules_path.exists():
        generated = json.loads(molecules_path.read_text(encoding="utf-8"))["molecules"]
        by_row = {item["record_index"]: item for item in generated}
        for molecule in result.successful_results:
            item = by_row.get(molecule.source_record_number)
            if item:
                molecule.outputs = {key: f"converted/{value}"
                                    for key, value in item["outputs"].items()}
    export_path = converted / "export_errors.json"
    if export_path.exists():
        for error in json.loads(export_path.read_text(encoding="utf-8")):
            result.warnings.append(
                f"Optional output '{error.get('output')}' failed for record "
                f"{error.get('record_index')}: {_concise(Exception(error.get('error', '')))}")


# ---------------------------------------------------------------------------
# 5. Orchestrator (thin; all work is delegated to the functions above)
# ---------------------------------------------------------------------------

def process_upload(
    data: bytes, filename: str, *, selected_format: str | None = None,
    selected_field: str | None = None, file_size: int | None = None,
    output_dir: str | Path | None = None,
) -> UploadResult:
    """Inspect an unknown upload and return a structured, typed result.

    No network, no model, no new job system. Resuming an ambiguous result only
    requires passing selected_format / selected_field with the same bytes.
    """
    base = _base_result(data, filename, file_size)
    try:
        text = decode_upload(data)
    except (InputError, OSError, UnicodeError, ValueError) as exc:
        return _failure(base, ErrorCode.EMPTY_OR_UNREADABLE_FILE, _concise(exc))

    detection = detect_upload_format(text, filename, selected_format=selected_format)
    if detection.requires_user_input:
        return _requires_input(base, ErrorCode.AMBIGUOUS_FORMAT,
                               detection.message, detection)
    if detection.detected_format is None:
        return _failure(base, ErrorCode.UNSUPPORTED_OR_UNKNOWN_FORMAT,
                        detection.message, detection)
    fmt = detection.detected_format

    field_name: str | None = None
    parser_kind: str | None = None
    if fmt == "csv":
        inspection = inspect_csv_fields(text, selected_field=selected_field)
        if inspection.error_code:
            return _failure(base, ErrorCode.NO_STRUCTURE_FIELD,
                            inspection.message, detection)
        if len(inspection.usable_fields) > 1 and selected_field is None:
            fields = [name for name, _ in inspection.usable_fields]
            result = _requires_input(base, ErrorCode.MULTIPLE_STRUCTURE_FIELDS,
                                     "Several usable structure columns exist; choose one.",
                                     detection, candidate_fields=fields)
            return result
        field_name, parser_kind = inspection.usable_fields[0]
        drafts, skipped = build_csv_records(inspection, field_name, parser_kind, filename)
        build_error: str | None = None
    else:
        drafts, skipped, build_error = build_nontabular_records(text, fmt, filename)

    successes: list[SuccessfulMolecule] = []
    failures: list[FailedRecordDetail] = []
    if build_error:
        failures.append(FailedRecordDetail(
            source_filename=base.original_filename, source_record_number=0,
            selected_source_field=field_name, raw_structure_value="",
            inferred_source_format=fmt, message=build_error))
    for draft in drafts:
        parsed = parse_molecular_record(draft)
        if isinstance(parsed, SuccessfulMolecule):
            successes.append(parsed)
        else:
            failures.append(parsed)

    result = aggregate_upload_result(
        base=base, detection=detection, successes=successes,
        failures=failures, skipped_records=skipped,
        selected_structure_field=field_name)
    if output_dir is not None and successes:
        _attach_outputs(result, data, filename, fmt, field_name, parser_kind,
                        Path(output_dir))
    return result
