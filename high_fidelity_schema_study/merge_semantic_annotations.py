from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .semantic_layer import merge_annotation_result


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
ANNOTATION_MANIFEST_PATH = DATA_ROOT / "semantic_annotations" / "manifest.json"
MERGED_ROOT = DATA_ROOT / "semantic_merged"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    manifest = load_json(ANNOTATION_MANIFEST_PATH)
    ensure_dir(MERGED_ROOT)
    merged_entries = []

    for item in manifest["results"]:
        if item.get("status") != "ok" or item.get("validation_error_count", 0) > 0:
            continue
        result_payload = load_json(DATA_ROOT / item["result_file"])
        task_payload = load_json(DATA_ROOT / result_payload["task_file"])
        merged = merge_annotation_result(
            deterministic_schema=task_payload["task"]["deterministic_schema"],
            result=result_payload["result"],
            model_info=result_payload.get("model_info"),
        )

        scope = item["scope"]
        out_name = Path(result_payload["task_file"]).name.replace(".task.json", ".merged.json")
        out_dir = MERGED_ROOT / scope
        ensure_dir(out_dir)
        out_path = out_dir / out_name
        out_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        merged_entries.append(
            {
                "scope": scope,
                "task_file": result_payload["task_file"],
                "merged_file": str(out_path.relative_to(DATA_ROOT)).replace("\\", "/"),
                "conflict_count": len(merged.get("metadata", {}).get("semantic_annotation", {}).get("conflicts", [])),
            }
        )

    (MERGED_ROOT / "manifest.json").write_text(json.dumps({"entries": merged_entries}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
