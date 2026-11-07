"""Reusable service boundary: convert_file(input_path, output_dir, ...)."""
from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import platform
import shutil
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import selfies as sf
from rdkit import Chem, rdBase
from rdkit.Chem import Crippen, Descriptors, Draw, Lipinski, QED, rdDepictor, rdMolDescriptors
from rdkit.Chem.Draw import rdMolDraw2D

from .io import InputError, detect, load_text, parse_records

OUTPUTS = {"csv", "json", "smi", "sdf", "mol", "png", "svg", "inchi", "selfies"}
DEFAULT_OUTPUTS = ("csv", "json", "smi", "sdf", "mol", "png", "svg", "inchi", "selfies")


def properties(mol):
    return {
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "molecular_weight_Da": Descriptors.MolWt(mol),
        "exact_mass_Da": Descriptors.ExactMolWt(mol),
        "rdkit_logp": Crippen.MolLogP(mol),
        "tpsa_A2": rdMolDescriptors.CalcTPSA(mol),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
        "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
        "rings": rdMolDescriptors.CalcNumRings(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "formal_charge": Chem.GetFormalCharge(mol),
        "fragments": len(Chem.GetMolFrags(mol)),
        "qed": QED.qed(mol),
    }


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str, allow_nan=False), encoding="utf-8")


def convert_file(input_path, output_dir, *, input_format="auto", column=None,
                 column_format="auto", outputs=DEFAULT_OUTPUTS, image_limit=100, allow_pdb=False):
    """Convert a small-molecule file. A fresh output directory is required.

    Individual invalid records are reported without discarding valid records.
    Structural errors (ambiguity, unsupported schema, size) raise InputError.
    No model/API/network calls are performed.
    """
    started = time.perf_counter()
    input_path, output_dir = Path(input_path), Path(output_dir)
    if isinstance(outputs, str):
        outputs = tuple(x.strip() for x in outputs.split(",") if x.strip())
    outputs = tuple(dict.fromkeys(outputs))
    unknown = set(outputs) - OUTPUTS
    if unknown or not outputs:
        raise InputError(f"Select at least one supported output; unknown formats: {sorted(unknown)}")
    if not isinstance(image_limit, int) or not 0 <= image_limit <= 5000:
        raise InputError("image_limit must be an integer from 0 to 5000.")
    text = load_text(input_path)
    detection = detect(text, input_path.name, input_format)
    records = parse_records(text, detection, column, column_format, allow_pdb)
    if output_dir.exists():
        raise InputError("Output directory already exists; choose a new directory to avoid overwriting results.")
    output_dir.mkdir(parents=True)
    shutil.copyfile(input_path, output_dir / "original_input.bin")
    input_hash = hashlib.sha256((output_dir / "original_input.bin").read_bytes()).hexdigest()
    success, errors, export_errors = [], [], []
    drawn = 0
    sdf = Chem.SDWriter(str(output_dir / "molecules.sdf")) if "sdf" in outputs else None
    try:
        for position, record in enumerate(records, 1):
            if record.error:
                errors.append({"record_index": record.index, "name": record.name,
                               "error": record.error, "raw": record.raw, "metadata": record.metadata})
                continue
            mol = record.mol
            rid = f"m{position:05d}"
            try:
                smiles = Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)
                props = properties(mol)
            except Exception as exc:
                errors.append({"record_index": record.index, "name": record.name,
                               "error": "Property calculation failed: " + str(exc),
                               "raw": record.raw, "metadata": record.metadata})
                continue
            warnings = []
            if props["fragments"] > 1:
                warnings.append("Multiple fragments retained; descriptors refer to the complete supplied structure.")
            # All per-molecule paths use internal numeric IDs; names never become paths.
            item = {"id": rid, "record_index": record.index, "name": record.name,
                    "smiles": smiles, "properties": props, "metadata": record.metadata,
                    "warnings": warnings, "outputs": {}, "representations": {}}
            export_mol = Chem.Mol(mol)
            export_mol.SetProp("_Name", str(record.name).replace("\n", " ").replace("\r", " "))
            for key, value in props.items():
                export_mol.SetProp("CB_" + key, str(value))
            export_mol.SetProp("CB_record_id", rid)
            if not export_mol.GetNumConformers() and {"mol", "sdf"} & set(outputs):
                rdDepictor.Compute2DCoords(export_mol)
                warnings.append("2D coordinates generated for MOL/SDF; no 3D geometry was inferred.")
            for fmt in outputs:
                try:
                    if fmt == "sdf":
                        sdf.write(export_mol)
                        item["outputs"][fmt] = "molecules.sdf"
                    elif fmt == "mol":
                        folder = output_dir / "mol"
                        folder.mkdir(exist_ok=True)
                        Chem.MolToMolFile(export_mol, str(folder / f"{rid}.mol"))
                        item["outputs"][fmt] = f"mol/{rid}.mol"
                    elif fmt == "inchi":
                        with rdBase.BlockLogs():
                            value = Chem.MolToInchi(mol)
                        if not value:
                            raise ValueError("InChI generation returned an empty result.")
                        item["representations"]["inchi"] = value
                    elif fmt == "selfies":
                        item["representations"]["selfies"] = sf.encoder(smiles)
                    elif fmt in {"png", "svg"} and drawn < image_limit:
                        folder = output_dir / "images"
                        folder.mkdir(exist_ok=True)
                        depiction = Chem.Mol(mol)
                        rdDepictor.Compute2DCoords(depiction)
                        path = folder / f"{rid}.{fmt}"
                        if fmt == "png":
                            Draw.MolToImage(depiction, size=(600, 450)).save(path)
                        else:
                            drawer = rdMolDraw2D.MolDraw2DSVG(600, 450)
                            rdMolDraw2D.PrepareAndDrawMolecule(drawer, depiction)
                            drawer.FinishDrawing()
                            path.write_text(drawer.GetDrawingText(), encoding="utf-8")
                        item["outputs"][fmt] = f"images/{rid}.{fmt}"
                except Exception as exc:
                    export_errors.append({"id": rid, "record_index": record.index,
                                          "output": fmt, "error": str(exc)})
            if {"png", "svg"} & set(outputs):
                if drawn >= image_limit:
                    warnings.append("Image limit reached; no depiction generated for this record.")
                drawn += 1
            success.append(item)
    finally:
        if sdf is not None:
            sdf.close()
    # JSON keeps source metadata; table/line formats intentionally store a subset.
    if "json" in outputs:
        _write_json(output_dir / "molecules.json", {"schema": "chembridge.molecules.v1", "molecules": success})
    if "csv" in outputs:
        fields = ["id", "record_index", "name", "canonical_smiles"]
        fields += list(success[0]["properties"]) if success else list(properties(Chem.MolFromSmiles("CCO")))
        with (output_dir / "properties.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for item in success:
                writer.writerow({"id": item["id"], "record_index": item["record_index"], "name": item["name"],
                                 "canonical_smiles": item["smiles"], **item["properties"]})
    for fmt, key, filename in [("smi", "smiles", "molecules.smi"),
                                ("inchi", "inchi", "molecules.inchi"),
                                ("selfies", "selfies", "molecules.selfies")]:
        if fmt in outputs:
            lines = []
            for item in success:
                value = item.get(key) if key == "smiles" else item["representations"].get(key)
                if value:
                    lines.append(f"{value}\t{item['id']}\n")
            (output_dir / filename).write_text("".join(lines), encoding="utf-8")
    _write_json(output_dir / "errors.json", errors)
    _write_json(output_dir / "export_errors.json", export_errors)
    status = "complete" if success and not errors and not export_errors else "partial" if success else "failed"
    manifest = {
        "schema": "chembridge.run.v1", "tool_version": "0.1.0", "status": status,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_name": input_path.name, "input_sha256": input_hash,
        "detection": asdict(detection), "source_records": len(records),
        "converted_records": len(success), "failed_records": len(errors),
        "export_errors": len(export_errors), "elapsed_seconds": round(time.perf_counter() - started, 4),
        "requested_outputs": list(outputs), "image_limit": image_limit,
        "environment": {"python": platform.python_version(), "rdkit": rdBase.rdkitVersion,
                        "selfies_distribution": importlib.metadata.version("selfies"), "selfies_module": sf.__version__},
        "policy": {"neutralize": False, "strip_salts": False, "tautomer_standardize": False,
                   "deduplicate": False, "preserve_input_coordinates_if_present": True,
                   "draw_on_copy": True, "ml_prediction": False},
        "limitations": ["Canonical SMILES is RDKit-version-dependent and does not unify tautomers/protonation states.",
                        "MOL/SMILES/InChI/SELFIES may lose source metadata; original bytes and JSON metadata are retained.",
                        "Standard InChI can normalize chemical detail; no universal lossless conversion is claimed.",
                        "Descriptors are RDKit calculations/estimates, not experimental measurements or learned bioactivity predictions."]
    }
    _write_json(output_dir / "manifest.json", manifest)
    return manifest
