"""Deterministic, offline tests for the V1 unknown-upload workflow.

All fixtures are tiny local strings/bytes created in this file; no downloads,
no public datasets, no network access.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from chembridge.upload_models import ErrorCode, WarningCode
from chembridge.upload_workflow import process_upload

ETHANOL_MOL = """ethanol
     RDKit          2D

  3  2  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.2990    0.7500    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.5981   -0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  2  3  1  0
M  END
"""
WATER_MOL = """water
     RDKit          2D

  1  0  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
M  END
"""
TWO_RECORD_SDF = ETHANOL_MOL + "$$$$\n" + WATER_MOL + "$$$$\n"
ONE_RECORD_WITH_SEPARATOR = ETHANOL_MOL + "$$$$\n"
INCHI_ETHANOL = "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"
# Genuine ambiguity after SDF/MOL precedence: one-column CSV with a `smiles`
# header is also a plain-SMILES text file with an optional single-token header.
AMBIGUOUS_SINGLE_COLUMN = b"smiles\nCCO\n"


def run(data: bytes, name: str, **kwargs):
    return process_upload(data, name, **kwargs)


def test_valid_mol_returns_success():
    result = run(ETHANOL_MOL.encode(), "ethanol.mol")
    assert result.status == "success"
    assert result.code is None
    assert result.detected_format == "mol"
    assert result.successful_records == 1 and result.failed_records == 0
    assert result.successful_results[0].canonical_smiles == "CCO"
    assert result.successful_results[0].properties["formula"] == "C2H6O"


def test_valid_multi_record_sdf_returns_success():
    result = run(TWO_RECORD_SDF.encode(), "two.sdf")
    assert result.status == "success"
    assert result.detected_format == "sdf"
    assert result.successful_records == 2
    assert {m.canonical_smiles for m in result.successful_results} == {"CCO", "O"}


def test_single_record_sdf_with_separator_prefers_sdf():
    assert "$$$$" in ONE_RECORD_WITH_SEPARATOR
    result = run(ONE_RECORD_WITH_SEPARATOR.encode(), "one.sdf")
    assert result.status == "success"
    assert result.detected_format == "sdf"
    assert result.code != ErrorCode.AMBIGUOUS_FORMAT.value
    assert result.successful_records == 1
    assert result.successful_results[0].canonical_smiles == "CCO"


def test_mol_without_separator_detects_mol():
    assert "$$$$" not in ETHANOL_MOL
    result = run(ETHANOL_MOL.encode(), "ethanol.mol")
    assert result.status == "success"
    assert result.detected_format == "mol"


@pytest.mark.parametrize("name", ["renamed.mol", "renamed.csv"])
def test_sdf_with_wrong_extension_detects_sdf_and_warns(name):
    result = run(TWO_RECORD_SDF.encode(), name)
    assert result.status == "success"
    assert result.detected_format == "sdf"
    assert result.original_extension == Path(name).suffix.lstrip(".")
    assert result.original_filename == name
    assert WarningCode.EXTENSION_CONTENT_MISMATCH.value in result.warnings
    assert result.detection.extension_matches_content is False


def test_valid_csv_with_one_smiles_column_returns_success():
    data = b"id,smiles\n1,CCO\n2,CCN\n"
    result = run(data, "molecules.csv")
    assert result.status == "success"
    assert result.detected_format == "csv"
    assert result.selected_structure_field == "smiles"
    assert result.successful_records == 2
    assert [m.source_record_number for m in result.successful_results] == [2, 3]


def test_csv_mixed_valid_and_invalid_rows_returns_partial_and_preserves_rows():
    data = b"id,smiles\n1,CCO\n\n2,INVALID\n3,\n"
    result = run(data, "mixed.csv")
    assert result.status == "partial_success"
    assert result.successful_records == 1 and result.failed_records == 2
    assert result.skipped_records == 1
    assert result.total_records == 4
    # Physical file line numbers are preserved (blank line 3 is skipped).
    assert [d.source_record_number for d in result.failed_record_details] == [4, 5]
    assert [d.raw_structure_value for d in result.failed_record_details] == ["INVALID", ""]
    assert all(d.code == ErrorCode.MOLECULE_PARSE_FAILED.value
               for d in result.failed_record_details)
    assert result.successful_results[0].canonical_smiles == "CCO"


def test_csv_without_molecular_structure_column_returns_no_structure_field():
    data = b"id,name,note\n1,ethanol,ok\n2,water,pure\n"
    result = run(data, "names.csv")
    assert result.status == "failed"
    assert result.code == ErrorCode.NO_STRUCTURE_FIELD.value
    assert result.detected_format == "csv"


def test_csv_with_two_usable_columns_requires_user_input_and_can_resume():
    data = f'name,smiles,inchi\nethanol,CCO,"{INCHI_ETHANOL}"\n'.encode()
    result = run(data, "two_columns.csv")
    assert result.status == "requires_user_input"
    assert result.code == ErrorCode.MULTIPLE_STRUCTURE_FIELDS.value
    assert set(result.candidate_fields) == {"smiles", "inchi"}

    resumed = run(data, "two_columns.csv", selected_field="smiles")
    assert resumed.status == "success"
    assert resumed.selected_structure_field == "smiles"
    assert resumed.successful_records == 1


def test_extension_mismatch_is_reported_and_original_extension_preserved():
    result = run(ETHANOL_MOL.encode(), "mislabelled.csv")
    assert result.status == "success"
    assert result.detected_format == "mol"
    assert result.original_extension == "csv"
    assert result.detection.extension_matches_content is False
    assert WarningCode.EXTENSION_CONTENT_MISMATCH.value in result.warnings
    assert result.original_filename == "mislabelled.csv"


def test_empty_file_returns_empty_or_unreadable():
    result = run(b"", "empty.csv")
    assert result.status == "failed"
    assert result.code == ErrorCode.EMPTY_OR_UNREADABLE_FILE.value
    assert result.total_records == 0


def test_unreadable_binary_returns_empty_or_unreadable():
    result = run(b"\x89PNG\r\n\x1a\n\x00\x01\x02", "picture.png")
    assert result.status == "failed"
    assert result.code == ErrorCode.EMPTY_OR_UNREADABLE_FILE.value


def test_valid_plain_smiles_text_returns_success_and_counts_skipped():
    result = run(b"CCO ethanol\n\nCCN ethylamine\n", "structures.smi")
    assert result.status == "success"
    assert result.detected_format == "smiles"
    assert result.successful_records == 2
    assert result.skipped_records == 1
    assert {m.canonical_smiles for m in result.successful_results} == {"CCO", "CCN"}


def test_plain_smiles_with_valid_and_invalid_records_returns_partial():
    result = run(b"CCO\nNOT_A_SMILES\n", "mixed.smi")
    assert result.status == "partial_success"
    assert result.successful_records == 1 and result.failed_records == 1
    assert result.failed_record_details[0].source_record_number == 2
    assert result.failed_record_details[0].raw_structure_value == "NOT_A_SMILES"
    assert result.failed_record_details[0].code == ErrorCode.MOLECULE_PARSE_FAILED.value


def test_completely_invalid_plain_text_returns_unsupported():
    result = run(b"this is not chemistry at all\n", "notes.txt")
    assert result.status == "failed"
    assert result.code == ErrorCode.UNSUPPORTED_OR_UNKNOWN_FORMAT.value
    assert result.detected_format is None


def test_one_invalid_record_does_not_erase_valid_results():
    data = b"CCO\nBROKEN\nCCN\n"
    result = run(data, "mixed.smi")
    assert result.status == "partial_success"
    assert [m.canonical_smiles for m in result.successful_results] == ["CCO", "CCN"]
    assert [d.source_record_number for d in result.failed_record_details] == [2]
    assert result.successful_results[0].properties["formula"] == "C2H6O"


def test_ambiguous_format_requires_user_input_and_can_resume():
    # Genuine ambiguity retained after the SDF/MOL precedence correction:
    # the same bytes are both a one-column CSV with a `smiles` header and a
    # plain-SMILES text file with an optional header. Assertions are not
    # weakened; both user selections must resume to a real success.
    data = AMBIGUOUS_SINGLE_COLUMN
    result = run(data, "ambiguous.csv")
    assert result.status == "requires_user_input"
    assert result.code == ErrorCode.AMBIGUOUS_FORMAT.value
    assert set(result.candidate_formats) == {"csv", "smiles"}

    as_smiles = run(data, "ambiguous.csv", selected_format="smiles")
    assert as_smiles.status == "success"
    assert as_smiles.detected_format == "smiles"
    assert as_smiles.successful_records == 1

    as_csv = run(data, "ambiguous.csv", selected_format="csv")
    assert as_csv.status == "success"
    assert as_csv.detected_format == "csv"
    assert as_csv.selected_structure_field == "smiles"
    assert as_csv.successful_records == 1


def test_forced_format_with_no_parsable_record_returns_no_valid_molecules():
    result = run(b"nonsense structure here\n", "forced.txt", selected_format="smiles")
    assert result.status == "failed"
    assert result.code == ErrorCode.NO_VALID_MOLECULES.value
    assert result.failed_records >= 1


def test_successful_outputs_reuse_existing_conversion_capabilities(tmp_path):
    result = run(ETHANOL_MOL.encode(), "ethanol.mol", output_dir=tmp_path / "out")
    assert result.status == "success"
    assert result.output_directory is not None
    assert result.successful_results[0].properties["formula"] == "C2H6O"
    assert "png" in result.successful_results[0].outputs
    assert "mol" in result.successful_results[0].outputs
    assert result.successful_results[0].outputs["png"].startswith("converted/")


def test_uploaded_filename_is_sanitized_for_output_directory(tmp_path):
    result = run(ETHANOL_MOL.encode(), "..", output_dir=tmp_path / "out")
    assert result.status == "success"
    assert result.output_directory is not None
    assert (tmp_path / "out" / "upload.bin").exists()
    assert all(child.name != ".." for child in (tmp_path / "out").iterdir())


def test_error_messages_do_not_expose_stack_traces():
    result = run(b"CCO\nNOT_A_SMILES\n", "mixed.smi")
    for detail in result.failed_record_details:
        assert "Traceback" not in detail.message
        assert "File \"" not in detail.message
        assert detail.message


@pytest.mark.parametrize("expected", [
    ErrorCode.EMPTY_OR_UNREADABLE_FILE, ErrorCode.UNSUPPORTED_OR_UNKNOWN_FORMAT,
    ErrorCode.AMBIGUOUS_FORMAT, ErrorCode.NO_STRUCTURE_FIELD,
    ErrorCode.MULTIPLE_STRUCTURE_FIELDS, ErrorCode.MOLECULE_PARSE_FAILED,
    ErrorCode.NO_VALID_MOLECULES,
])
def test_all_stable_error_codes_are_defined(expected):
    assert expected.value == expected.name
