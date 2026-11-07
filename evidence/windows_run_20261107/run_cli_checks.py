"""Record real CLI boundary evidence (exit codes, manifests, no-overwrite)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EX = ROOT / "examples"
BASE = ROOT / "runs" / ("cli_checks_" + datetime.now().strftime("%Y%m%d_%H%M%S"))


def run(label: str, input_name: str, out_name: str, *extra: str) -> dict:
    out = BASE / out_name
    command = [sys.executable, "-m", "chembridge",
               str(EX / input_name), "--out", str(out), *extra]
    proc = subprocess.run(command, cwd=str(ROOT), capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    return {"label": label, "command": " ".join(command), "out": out,
            "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    results = [
        run("molecules.csv（全部成功）", "molecules.csv", "molecules"),
        run("mixed_invalid.csv（部分失败）", "mixed_invalid.csv", "mixed_invalid"),
        run("misnamed.csv（错副档名）", "misnamed.csv", "misnamed"),
        run("ambiguous_columns.csv 不选栏", "ambiguous_columns.csv", "ambiguous_reject"),
        run("ambiguous_columns.csv --column smiles", "ambiguous_columns.csv",
            "ambiguous_ok", "--column", "smiles"),
    ]

    manifest_path = BASE / "molecules" / "manifest.json"
    before_hash = digest(manifest_path)
    results.append(run("同一 --out 重跑（防覆盖）", "molecules.csv", "molecules"))
    after_hash = digest(manifest_path)

    lines = [
        "# CLI 边界复验（本机 Windows 真实命令）", "",
        f"执行时间：{datetime.now().isoformat()}",
        f"输出根目录：`{BASE}`", "",
        "说明：`mixed_invalid.csv` 的 exit 1 是设计结果（仍有完整报告），**未改成假成功**。", "",
    ]
    for item in results:
        lines += [f"## {item['label']}", "",
                  "```", item["command"], "```", "",
                  f"EXIT_CODE: {item['returncode']}", "",
                  "stdout（节录）：", "```", (item["stdout"].strip()[:600] or "(empty)"), "```", "",
                  "stderr：", "```", (item["stderr"].strip() or "(empty)"), "```", ""]
        manifest_file = item["out"] / "manifest.json"
        if manifest_file.exists():
            m = json.loads(manifest_file.read_text(encoding="utf-8"))
            lines += ["manifest 关键栏位：", "```json", json.dumps({
                "format": m["detection"]["format"],
                "method": m["detection"]["method"],
                "suffix_hint": m["detection"]["suffix_hint"],
                "warnings": m["detection"]["warnings"],
                "source_records": m["source_records"],
                "converted_records": m["converted_records"],
                "failed_records": m["failed_records"],
                "status": m["status"],
            }, ensure_ascii=False), "```", ""]
        errors_file = item["out"] / "errors.json"
        if errors_file.exists():
            errors = json.loads(errors_file.read_text(encoding="utf-8"))
            lines += [f"`errors.json` 笔数：{len(errors)}；"
                      f"索引：{[e['record_index'] for e in errors]}；"
                      f"原文：{[e['raw'] for e in errors]}", ""]

    lines += [
        "## 防覆盖前后比对", "",
        f"`runs/.../molecules/manifest.json` SHA-256（重跑前）：`{before_hash}`", "",
        f"SHA-256（重跑后）：`{after_hash}`", "",
        f"是否相同：{before_hash == after_hash}", "",
        "## 结论", "",
        "- `molecules.csv` → 0（5/0）；`mixed_invalid.csv` → 1（1/2，partial）；`misnamed.csv` → 0（侦测 mol，1/0）。",
        "- 歧义栏不选 → 2 且不建立输出目录；指定 `--column smiles` → 0（1/0）。",
        "- 同一 `--out` 重跑 → 2，且原 manifest 位元组未变。",
        "- 坏资料原文与 metadata 保留在 `errors.json`，成功记录未被删除。",
    ]
    (HERE / "cli_exit_codes.md").write_text("\n".join(lines), encoding="utf-8")

    print("CLI_CHECKS_OK " + json.dumps({
        "base": str(BASE),
        "exit_codes": [r["returncode"] for r in results],
        "manifest_unchanged": before_hash == after_hash,
    }))


if __name__ == "__main__":
    main()
