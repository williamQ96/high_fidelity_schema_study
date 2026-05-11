from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT / "data"
ANNOTATION_ROOT = DATA_ROOT / "semantic_annotations"
MANIFEST_PATH = ANNOTATION_ROOT / "manifest.json"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def main() -> None:
    existing = {}
    if MANIFEST_PATH.exists():
        text = MANIFEST_PATH.read_text(encoding="utf-8")
        try:
            existing = json.loads(text)
        except json.JSONDecodeError:
            from high_fidelity_schema_study.semantic_annotate import load_json as tolerant_load_json

            existing = tolerant_load_json(MANIFEST_PATH)

    results: List[Dict[str, Any]] = []
    for scope_dir in [ANNOTATION_ROOT / "internal", ANNOTATION_ROOT / "external"]:
        if not scope_dir.exists():
            continue
        scope = scope_dir.name
        for result_file in sorted(scope_dir.glob("*.result.json")):
            payload = load_json(result_file)
            results.append(
                {
                    "task_file": payload["task_file"],
                    "scope": scope,
                    "result_file": str(result_file.relative_to(DATA_ROOT)).replace("\\", "/"),
                    "validation_error_count": len(payload.get("validation_errors", [])),
                    "status": "ok",
                }
            )

    manifest = {
        "api_base": existing.get("api_base", "http://127.0.0.1:1234/v1"),
        "model": existing.get("model", ""),
        "results": results,
    }
    atomic_write_json(MANIFEST_PATH, manifest)


if __name__ == "__main__":
    main()
