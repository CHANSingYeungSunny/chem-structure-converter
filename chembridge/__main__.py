import argparse
import json
import sys

from .io import FORMATS, InputError
from .pipeline import DEFAULT_OUTPUTS, convert_file


def main():
    parser = argparse.ArgumentParser(description="Local chemical structure detection, validation, depiction and conversion.")
    parser.add_argument("input", help="Input molecular file (UTF-8, UTF-16 BOM, optional gzip).")
    parser.add_argument("--out", required=True, help="New output directory (must not exist).")
    parser.add_argument("--input-format", choices=["auto", *sorted(FORMATS)], default="auto")
    parser.add_argument("--column", help="Exact CSV/TSV structure column name.")
    parser.add_argument("--column-format", choices=["auto", "smiles", "inchi", "selfies", "mol"], default="auto")
    parser.add_argument("--outputs", default=",".join(DEFAULT_OUTPUTS), help="Comma-separated: csv,json,smi,sdf,mol,png,svg,inchi,selfies")
    parser.add_argument("--image-limit", type=int, default=100)
    parser.add_argument("--allow-pdb", action="store_true", help="Experimental PDB; requires explicit CONECT and chemistry review.")
    args = parser.parse_args()
    try:
        manifest = convert_file(args.input, args.out, input_format=args.input_format, column=args.column,
                                column_format=args.column_format, outputs=args.outputs,
                                image_limit=args.image_limit, allow_pdb=args.allow_pdb)
    except (InputError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
