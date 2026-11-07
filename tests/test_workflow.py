import csv
import gzip
import json
import subprocess
import sys
from pathlib import Path

import pytest
from rdkit import Chem
from rdkit.Chem import AllChem

from chembridge.io import InputError, decode_bytes, detect
from chembridge.pipeline import convert_file


def run(tmp_path, text, name="input.smi", **kwargs):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    out = tmp_path / "result"
    manifest = convert_file(path, out, **kwargs)
    data = json.loads((out / "molecules.json").read_text()) if (out / "molecules.json").exists() else None
    return manifest, data, out


def test_ethanol_known_properties_and_all_outputs(tmp_path):
    manifest, data, out = run(tmp_path, "CCO ethanol\n")
    assert manifest["status"] == "complete"
    p = data["molecules"][0]["properties"]
    assert p["formula"] == "C2H6O"
    assert p["molecular_weight_Da"] == pytest.approx(46.069, abs=.001)
    assert p["hbd"] == p["hba"] == 1
    assert p["heavy_atoms"] == 3 and p["rings"] == 0
    assert (out / "images/m00001.png").read_bytes().startswith(b"\x89PNG")
    assert "<svg" in (out / "images/m00001.svg").read_text()
    assert len(list(Chem.SDMolSupplier(str(out / "molecules.sdf")))) == 1


@pytest.mark.parametrize("name,text,fmt", [
    ("input.smi", "CCO eth\n", "smiles"),
    ("input.smiles", "CCO\n", "smiles"),
    ("input.inchi", "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3 eth\n", "inchi"),
    ("input.selfies", "[C][C][O] eth\n", "selfies"),
    ("input.csv", "name,SMILES\neth,CCO\n", "csv"),
    ("input.tsv", "name\tsmiles\neth\tCCO\n", "tsv"),
    ("input.csv", "name;smiles\neth;CCO\n", "csv"),
    ("input.json", '[{"name":"eth","smiles":"CCO"}]', "json"),
    ("input.json", '{"molecules":[{"inchi":"InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"}]}', "json"),
    ("input.data", "CCO\n", "smiles"),
])
def test_core_input_variants(tmp_path, name, text, fmt):
    manifest, data, _ = run(tmp_path, text, name, outputs="json")
    assert manifest["detection"]["format"] == fmt
    assert data["molecules"][0]["smiles"] == "CCO"


@pytest.mark.parametrize("v3000", [False, True])
def test_mol_signature_outranks_wrong_extension(tmp_path, v3000):
    block = Chem.MolToMolBlock(Chem.MolFromSmiles("CCO"), forceV3000=v3000)
    manifest, data, _ = run(tmp_path, block, "misnamed.csv", outputs="json")
    assert manifest["detection"]["format"] == "mol"
    assert manifest["detection"]["warnings"]
    assert data["molecules"][0]["smiles"] == "CCO"


def test_csv_mixed_invalid_and_blank_are_counted(tmp_path):
    manifest, data, out = run(tmp_path, 'id,smiles,source\na,CCO,lab\nb,invalid,lab\nc,,lab\nd,C,lab\n', outputs="json,csv")
    assert manifest["source_records"] == 4
    assert manifest["converted_records"] == manifest["failed_records"] == 2
    assert manifest["status"] == "partial"
    errors = json.loads((out / "errors.json").read_text())
    assert [e["record_index"] for e in errors] == [3, 4]
    assert data["molecules"][0]["metadata"]["source"] == "lab"


def test_ambiguous_csv_requires_selection(tmp_path):
    text = "name,smiles,inchi\na,CCO,InChI=1S/CH4/h1H4\n"
    with pytest.raises(InputError, match="Multiple structure columns"):
        run(tmp_path, text, outputs="json")
    assert not (tmp_path / "result").exists()
    manifest, data, _ = run(tmp_path, text, outputs="json", column="inchi")
    assert manifest["status"] == "complete" and data["molecules"][0]["smiles"] == "C"


def test_nonstandard_unique_column(tmp_path):
    _, data, _ = run(tmp_path, "label,structure\nethanol,CCO\nbenzene,c1ccccc1\n", "data.csv", outputs="json")
    assert len(data["molecules"]) == 2


def test_unknown_column_two_plausible_columns_refuses(tmp_path):
    with pytest.raises(InputError, match="unique structure column"):
        run(tmp_path, "left,right\nCCO,CCC\nCCC,CCN\n", "data.csv", outputs="json")


def test_table_wrong_width_not_silently_truncated(tmp_path):
    manifest, _, _ = run(tmp_path, "smiles,name\nCCO,eth,extra\n", "data.csv", outputs="json")
    assert manifest["status"] == "failed"


def test_json_bad_records_preserved(tmp_path):
    text = '[{"smiles":"CCO"}, {"smiles":"C","inchi":"bad"}, 5, {"smiles":null}]'
    manifest, _, out = run(tmp_path, text, "data.json", outputs="json")
    assert manifest["converted_records"] == 1 and manifest["failed_records"] == 3
    assert len(json.loads((out / "errors.json").read_text())) == 3


def test_broken_json_not_guessed(tmp_path):
    with pytest.raises(InputError, match="Malformed JSON"):
        run(tmp_path, '{"smiles":"CCO"', "data.json", outputs="json")


def test_stereo_charge_isotope_salt_roundtrip(tmp_path):
    values = ["N[C@@H](C)C(=O)O", "N[C@H](C)C(=O)O", "[13CH3]CO", "[NH4+].[Cl-]"]
    manifest, data, out = run(tmp_path, "\n".join(values), outputs="json,sdf,smi,mol,selfies")
    assert manifest["converted_records"] == 4
    expected = [Chem.MolToSmiles(Chem.MolFromSmiles(s), isomericSmiles=True) for s in values]
    assert [m["smiles"] for m in data["molecules"]] == expected
    assert expected[0] != expected[1]
    recovered = [Chem.MolToSmiles(m, isomericSmiles=True) for m in Chem.SDMolSupplier(str(out / "molecules.sdf"))]
    assert recovered == expected
    assert data["molecules"][-1]["properties"]["fragments"] == 2


def test_sdf_metadata_bad_record_and_blank_title(tmp_path):
    mol = Chem.MolFromSmiles("CCO")
    valid = Chem.MolToMolBlock(mol) + "\n>  <SOURCE>\nmy lab\n\n$$$$\n"
    text = valid + "bad\n$$$$\n" + valid
    manifest, data, _ = run(tmp_path, text, "data.sdf", outputs="json")
    assert manifest["source_records"] == 3 and manifest["failed_records"] == 1
    assert data["molecules"][0]["metadata"]["SOURCE"] == "my lab"


def test_coordinates_not_overwritten_by_drawing(tmp_path):
    mol = Chem.AddHs(Chem.MolFromSmiles("CCO"))
    assert AllChem.EmbedMolecule(mol, randomSeed=7) == 0
    block = Chem.MolToMolBlock(mol)
    original = Chem.MolFromMolBlock(block)
    _, _, out = run(tmp_path, block, "three_d.mol", outputs="json,sdf,png")
    recovered = next(iter(Chem.SDMolSupplier(str(out / "molecules.sdf"))))
    assert recovered.GetConformer().Is3D()
    assert recovered.GetConformer().GetPositions() == pytest.approx(original.GetConformer().GetPositions(), abs=1e-4)


def test_gzip_magic_and_utf16(tmp_path):
    path = tmp_path / "data.smi.gz"
    path.write_bytes(gzip.compress("CCO ethanol".encode()))
    manifest = convert_file(path, tmp_path / "gz", outputs="json")
    assert manifest["converted_records"] == 1
    assert decode_bytes("CCO".encode("utf-16")) == "CCO"


def test_invalid_gzip_and_nontext_rejected():
    with pytest.raises(InputError):
        decode_bytes(b"\x1f\x8bgarbage")
    with pytest.raises(InputError):
        decode_bytes(b"\xff\xff\xff")


def test_output_never_overwritten(tmp_path):
    _, _, out = run(tmp_path, "CCO", outputs="json")
    before = (out / "manifest.json").read_bytes()
    with pytest.raises(InputError, match="already exists"):
        convert_file(tmp_path / "input.smi", out)
    assert (out / "manifest.json").read_bytes() == before


def test_image_limit_and_duplicate_retention(tmp_path):
    manifest, data, out = run(tmp_path, "CCO a\nCCO b", outputs="png,json", image_limit=1)
    assert manifest["converted_records"] == 2
    assert len(list((out / "images").glob("*.png"))) == 1
    assert any("limit" in x for x in data["molecules"][1]["warnings"])


def test_ambiguous_plaintext_selfies_requires_explicit_format():
    with pytest.raises(InputError, match="ambiguous"):
        detect("[C][C][O]", "data.txt")


def test_pdb_requires_optin_and_connectivity(tmp_path):
    pdb = Chem.MolToPDBBlock(Chem.MolFromSmiles("CCO"))
    with pytest.raises(InputError, match="allow-pdb"):
        run(tmp_path, pdb, "input.pdb", outputs="json")
    manifest, _, _ = run(tmp_path, pdb, "input.pdb", outputs="json", allow_pdb=True)
    assert manifest["converted_records"] == 1
    assert any("Experimental PDB" in s for s in manifest["detection"]["warnings"])


def test_pdb_without_conect_rejected(tmp_path):
    pdb = "HETATM    1  C1  UNL     1       0.000   0.000   0.000  1.00  0.00           C  \nEND\n"
    with pytest.raises(InputError, match="CONECT"):
        run(tmp_path, pdb, "input.pdb", outputs="json", allow_pdb=True)


MOL2 = """@<TRIPOS>MOLECULE
water
3 2 0 0 0
SMALL
NO_CHARGES

@<TRIPOS>ATOM
1 O1 0.000 0.000 0.000 O.3 1 WAT 0.000
2 H1 0.758 0.000 0.504 H 1 WAT 0.000
3 H2 -0.758 0.000 0.504 H 1 WAT 0.000
@<TRIPOS>BOND
1 1 2 1
2 1 3 1
"""


def test_limited_mol2(tmp_path):
    manifest, data, _ = run(tmp_path, MOL2, "input.mol2", outputs="json")
    assert manifest["converted_records"] == 1
    assert data["molecules"][0]["properties"]["formula"] == "H2O"


def test_wildcards_rejected(tmp_path):
    manifest, _, _ = run(tmp_path, "*CC*", outputs="json")
    assert manifest["failed_records"] == 1


def test_json_export_reimports(tmp_path):
    _, _, out = run(tmp_path, "CCO a\nCCN b")
    manifest = convert_file(out / "molecules.json", tmp_path / "roundtrip", outputs="smi")
    assert manifest["converted_records"] == 2


def test_cli_nonzero_partial_and_structural_error(tmp_path):
    path = tmp_path / "mixed.smi"
    path.write_text("CCO\ninvalid")
    command = [sys.executable, "-m", "chembridge", str(path), "--out", str(tmp_path / "cli"), "--outputs", "json"]
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 1
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2 and "already exists" in result.stderr


def test_empty_input(tmp_path):
    with pytest.raises(InputError, match="empty"):
        run(tmp_path, "", outputs="json")


def test_bracketed_unlabelled_column_does_not_guess(tmp_path):
    manifest, _, _ = run(tmp_path, "structure\n[C][C][O]\n", "data.csv", outputs="json", column="structure")
    assert manifest["failed_records"] == 1


def test_optional_header_only_at_beginning(tmp_path):
    manifest, _, _ = run(tmp_path, "smiles\nCCO\nsmiles\n", outputs="json")
    assert manifest["source_records"] == 2 and manifest["failed_records"] == 1
