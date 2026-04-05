import json
from pathlib import Path
from datetime import datetime


def ensure_parent_dir(filepath: str) -> None:
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)


def save_json(data, filepath: str) -> None:
    ensure_parent_dir(filepath)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_json_with_timestamp(data, prefix: str = "b_output_test") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"{prefix}_{ts}.json"
    save_json(data, filepath)
    return filepath