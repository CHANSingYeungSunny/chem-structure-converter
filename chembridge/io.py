"""Content-aware detection and per-record parsing; never guess between columns."""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import selfies as sf
from rdkit import Chem, rdBase

MAX_BYTES = 20 * 1024 * 1024
MAX_RECORDS = 5000
FORMATS = {"mol", "sdf", "csv", "tsv", "smiles", "inchi", "selfies", "json", "mol2", "pdb"}
ALIASES = {"smi": "smiles", "smiles": "smiles", "sd": "sdf", "sf": "selfies"}
STRUCTURE_HEADERS = {
    "smiles": "smiles", "canonicalsmiles": "smiles", "isomericsmiles": "smiles",
    "inchi": "inchi", "selfies": "selfies", "molblock": "mol",
}


class InputError(ValueError):
    pass


@dataclass
class Detection:
    format: str
    reason: str
    method: str
    suffix_hint: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class Record:
    index: int
    name: str
    raw: str
    representation: str
    metadata: dict = field(default_factory=dict)
    mol: object = None
    error: str = ""


def normalize_header(value):
    return re.sub(r"[\s_\-]", "", value.lower())


def decode_bytes(data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise InputError("Input exceeds the 20 MiB compressed/uncompressed limit.")
    if data.startswith(b"\x1f\x8b"):
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                data = gz.read(MAX_BYTES + 1)
        except (OSError, EOFError) as exc:
            raise InputError(f"Invalid gzip stream: {exc}") from exc
        if len(data) > MAX_BYTES:
            raise InputError("Decompressed input exceeds 20 MiB.")
    try:
        if data.startswith((b"\xff\xfe", b"\xfe\xff")):
            return data.decode("utf-16")
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError("Expected UTF-8 or BOM-marked UTF-16 text; binary images/PDF/CDX are unsupported.") from exc


def load_text(path: Path) -> str:
    with path.open("rb") as stream:
        return decode_bytes(stream.read(MAX_BYTES + 1))


def _hint(filename):
    p = Path(filename.lower())
    if p.suffix == ".gz":
        p = Path(p.stem)
    suffix = p.suffix.lstrip(".")
    return ALIASES.get(suffix, suffix)


def _parse_value(value, fmt):
    # Suppress toolkit stderr locally; structured errors are returned to the caller.
    with rdBase.BlockLogs():
        if fmt == "smiles":
            params = Chem.SmilesParserParams()
            params.parseName = False
            mol = Chem.MolFromSmiles(value.strip(), params)
        elif fmt == "inchi":
            mol = Chem.MolFromInchi(value.strip())
        elif fmt == "selfies":
            mol = Chem.MolFromSmiles(sf.decoder(value.strip()))
        elif fmt == "mol":
            mol = Chem.MolFromMolBlock(value, sanitize=True, removeHs=True, strictParsing=True)
        elif fmt == "mol2":
            mol = Chem.MolFromMol2Block(value, sanitize=True, removeHs=True)
        elif fmt == "pdb":
            mol = Chem.MolFromPDBBlock(value, sanitize=True, removeHs=True, proximityBonding=False)
        else:
            raise InputError(f"Unsupported molecular representation: {fmt}")
    if mol is None or mol.GetNumAtoms() == 0:
        raise InputError(f"Cannot parse/validate {fmt} structure.")
    if mol.GetNumAtoms() > 1000:
        raise InputError("Molecule exceeds 1000 atoms; use a specialized large-molecule workflow.")
    if any(a.GetAtomicNum() == 0 for a in mol.GetAtoms()):
        raise InputError("Wildcard/query/repeat-unit atoms are outside this small-molecule MVP.")
    return mol


def _valid(value, fmt):
    try:
        _parse_value(value, fmt)
        return True
    except Exception:
        return False


def _lines(text):
    return [(i, line.strip()) for i, line in enumerate(text.splitlines(), 1)
            if line.strip() and not line.lstrip().startswith("#")]


def _cell_format(value):
    if value.strip().startswith("InChI="):
        return "inchi"
    # Only the dedicated SELFIES route uses this syntax hint; validate afterwards.
    if re.fullmatch(r"(?:\[[^\[\]]+\])+", value.strip()) and _valid(value, "selfies"):
        if _valid(value, "smiles"):
            return "ambiguous-text"
        return "selfies"
    return "smiles"


def detect(text: str, filename="input", forced="auto") -> Detection:
    hint = _hint(filename)
    if not text.strip():
        raise InputError("The input is empty.")
    if forced != "auto":
        if forced not in FORMATS:
            raise InputError(f"Unknown input format: {forced}")
        return Detection(forced, "User explicitly selected this parser.", "explicit", hint)
    stripped = text.lstrip()
    fmt, reason = None, None
    # Distinctive signatures outrank a potentially misleading filename extension.
    if re.search(r"^@<TRIPOS>MOLECULE\s*$", text, re.M):
        fmt, reason = "mol2", "TRIPOS molecule signature."
    elif re.search(r"^(?:ATOM  |HETATM)", text, re.M):
        fmt, reason = "pdb", "PDB ATOM/HETATM record signature."
    elif re.search(r"^\$\$\$\$\s*$", text, re.M):
        fmt, reason = "sdf", "SDF record separator ($$$$)."
    elif re.search(r"V(?:2000|3000)\s*$", text, re.M) and "M  END" in text:
        fmt, reason = "mol", "MDL version marker and M  END."
    elif stripped.startswith(("{", "[")):
        # SELFIES starts with '[' too; recognized JSON containers or .json win.
        try:
            value = json.loads(text)
            if isinstance(value, (dict, list)):
                fmt, reason = "json", "JSON container; molecular schema checked during parsing."
        except json.JSONDecodeError:
            if stripped.startswith("{") or hint == "json":
                raise InputError("Malformed JSON; refusing to reinterpret it as SMILES.")
    if fmt is None:
        first = _lines(text)[0][1] if _lines(text) else ""
        for delimiter, table_fmt in [("\t", "tsv"), (",", "csv"), (";", "csv")]:
            # InChI strings can contain semicolons; their prefix is stronger evidence.
            if delimiter in first and not first.startswith("InChI="):
                fields = next(csv.reader([first], delimiter=delimiter))
                known = any(normalize_header(x) in STRUCTURE_HEADERS for x in fields)
                if known or hint in {"csv", "tsv"} or len(fields) > 1:
                    fmt, reason = table_fmt, "Delimited table; structure column must be resolved."
                    break
    if fmt is None:
        lines = _lines(text)
        if not lines:
            raise InputError("No data records found.")
        first = lines[0][1].split()[0]
        if first.startswith("InChI="):
            fmt, reason = "inchi", "InChI= prefix."
        elif hint == "selfies":
            fmt, reason = "selfies", "SELFIES filename hint; every record will be validated."
        elif hint == "smiles":
            fmt, reason = "smiles", "SMILES filename hint; every record will be validated."
        elif hint in FORMATS:
            fmt, reason = hint, "Filename hint without a decisive content signature; validation required."
        else:
            candidates = [f for f in ["smiles", "selfies"] if _valid(first, f)]
            if len(candidates) != 1:
                raise InputError("Unknown or ambiguous text format. Use --input-format explicitly.")
            fmt, reason = candidates[0], "First non-comment record parses with one supported text parser (heuristic)."
    warnings = []
    if hint in FORMATS and hint != fmt:
        warnings.append(f"Filename suggests {hint}, but content suggests {fmt}; content takes priority.")
    method = "heuristic" if "heuristic" in reason or "hint" in reason else "signature"
    return Detection(fmt, reason, method, hint, warnings)


def _table_records(text, fmt, column=None, column_format="auto"):
    delimiter = "\t" if fmt == "tsv" else ","
    if fmt == "csv":
        # Determine only the delimiter; never use Sniffer.has_header to discard a row.
        try:
            delimiter = csv.Sniffer().sniff(text[:16384], delimiters=",;\t").delimiter
        except csv.Error:
            pass
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter, strict=True))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        raise InputError("Empty table.")
    header = [x.strip() for x in rows[0]]
    if len(set(header)) != len(header):
        raise InputError("Duplicate column names; rename them before import.")
    named = [(h, STRUCTURE_HEADERS[normalize_header(h)]) for h in header
             if normalize_header(h) in STRUCTURE_HEADERS]
    if column is not None:
        if column not in header:
            raise InputError(f"Column {column!r} not found. CSV/TSV requires a header row.")
        chosen = column
        rep = STRUCTURE_HEADERS.get(normalize_header(chosen), "auto")
    elif len(named) == 1:
        chosen, rep = named[0]
    elif len(named) > 1:
        raise InputError("Multiple structure columns: " + ", ".join(h for h, _ in named)
                         + ". Select --column (and optionally --column-format).")
    else:
        # Unnamed molecular headers: a unique column whose sampled cells are >=80% parsable.
        sample = rows[1:21]
        candidates = []
        for j, h in enumerate(header):
            cells = [r[j].strip() for r in sample if len(r) > j and r[j].strip()]
            if cells and sum(_valid(v, _cell_format(v)) for v in cells) / len(cells) >= .8:
                candidates.append(h)
        if len(candidates) != 1:
            raise InputError("Cannot identify a unique structure column. CSV/TSV needs headers; use --column.")
        chosen, rep = candidates[0], "auto"
    if column_format != "auto":
        rep = column_format
    j = header.index(chosen)
    records = []
    for row_number, row in enumerate(rows[1:], 2):
        metadata = dict(zip(header, row))
        name = next((metadata[h] for h in header if normalize_header(h) in {"id", "name", "compoundid"}), str(row_number))
        raw = row[j] if len(row) > j else ""
        record = Record(row_number, name, raw, rep if rep != "auto" else _cell_format(raw), metadata)
        if len(row) != len(header):
            record.error = "Column count does not match the header; record was not converted."
        records.append(record)
    return records


def parse_records(text: str, detection: Detection, column=None, column_format="auto", allow_pdb=False):
    fmt = detection.format
    if fmt in {"csv", "tsv"}:
        records = _table_records(text, fmt, column, column_format)
    elif fmt == "json":
        value = json.loads(text)
        if isinstance(value, dict) and "molecules" in value:
            value = value["molecules"]
        elif isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            raise InputError("JSON must be an object, a list of objects, or {molecules: [...]}.")
        records = []
        for i, item in enumerate(value, 1):
            if not isinstance(item, dict):
                records.append(Record(i, str(i), repr(item), "", error="Expected a JSON molecule object."))
                continue
            candidates = [(k, f) for k, f in [("smiles", "smiles"), ("inchi", "inchi"),
                          ("selfies", "selfies"), ("molblock", "mol")] if k in item]
            if len(candidates) != 1:
                records.append(Record(i, str(item.get("name", i)), json.dumps(item), "", item,
                                      error="JSON record requires exactly one of smiles/inchi/selfies/molblock."))
                continue
            key, rep = candidates[0]
            records.append(Record(i, str(item.get("name", item.get("id", i))), item[key], rep, item))
    elif fmt == "sdf":
        records = []
        blocks = re.split(r"^\$\$\$\$[^\S\n]*$", text, flags=re.M)
        for i, block in enumerate(blocks, 1):
            if not block.strip():
                if i < len(blocks):
                    records.append(Record(i, str(i), block, "mol", error="Empty SDF record."))
                continue
            # Consume ONLY the newline after the separator; the MOL title may be blank.
            if i > 1:
                block = re.sub(r"^\r?\n", "", block, count=1)
            with rdBase.BlockLogs():
                supplier = Chem.ForwardSDMolSupplier(io.BytesIO((block + "\n$$$$\n").encode("utf-8")),
                                                     sanitize=True, removeHs=True, strictParsing=True)
                mol = next(supplier, None)
            name = block.splitlines()[0] if block.splitlines() else str(i)
            record = Record(i, name, block, "mol", mol=mol)
            if mol is None:
                record.error = "Cannot parse/validate this SDF record."
            else:
                record.metadata = mol.GetPropsAsDict(includePrivate=False, includeComputed=False)
            records.append(record)
    elif fmt == "mol2":
        blocks = re.split(r"(?=^@<TRIPOS>MOLECULE\s*$)", text, flags=re.M)
        records = [Record(i, str(i), b, fmt) for i, b in enumerate([b for b in blocks if b.strip()], 1)]
        detection.warnings.append("MOL2 reader supports RDKit-compatible atom typing only; charges/force-field metadata are not preserved as a force-field file.")
    elif fmt in {"mol", "pdb"}:
        if fmt == "pdb":
            if not allow_pdb:
                raise InputError("PDB lacks reliable bond orders. Experimental import requires --allow-pdb; supply MOL/SDF/SMILES for authoritative chemistry.")
            if len(re.findall(r"^MODEL\s", text, re.M)) > 1:
                raise InputError("Multi-model PDB is unsupported; select a single small-molecule model.")
            if not re.search(r"^CONECT", text, re.M):
                raise InputError("PDB import requires explicit CONECT records; proximity bonding is disabled.")
            detection.warnings.append("Experimental PDB: CONECT topology only, bond order/protonation may be incomplete; review every computed property. Protein workflows are out of scope.")
        records = [Record(1, Path("input").stem, text, fmt)]
    else:
        records = []
        for position, (i, line) in enumerate(_lines(text)):
            parts = line.split(maxsplit=1)
            if position == 0 and len(parts) == 1 and parts[0].lower() in {"smiles", "inchi", "selfies"}:
                continue  # documented optional single-token header
            records.append(Record(i, parts[1] if len(parts) > 1 else str(i), parts[0], fmt))
    if not records:
        raise InputError("No molecule records found.")
    if len(records) > MAX_RECORDS:
        raise InputError(f"More than {MAX_RECORDS} records; split the input into smaller files.")
    for record in records:
        if record.error:
            continue
        try:
            if record.mol is None:
                if not isinstance(record.raw, str) or not record.raw.strip():
                    raise InputError("Missing or non-text molecular structure.")
                record.mol = _parse_value(record.raw, record.representation)
            # Revalidate SDF objects through the common policy, without losing coordinates.
            if record.mol.GetNumAtoms() > 1000 or record.mol.GetNumAtoms() == 0:
                raise InputError("Only nonempty molecules of at most 1000 atoms are supported.")
            if any(a.GetAtomicNum() == 0 for a in record.mol.GetAtoms()):
                raise InputError("Wildcard/query/repeat-unit atoms are unsupported.")
            if record.mol.HasProp("_Name") and record.mol.GetProp("_Name"):
                record.name = record.mol.GetProp("_Name")
        except Exception as exc:
            record.error = str(exc)
            record.mol = None
    return records
