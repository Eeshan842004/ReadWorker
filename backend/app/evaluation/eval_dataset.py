import json
from pathlib import Path

EVAL_DATA_PATH = Path(__file__).resolve().parents[2] / "eval_data" / "golden_qa.json"


def load_golden_qa(path: Path | None = None) -> list[dict]:
    """Load golden QA pairs.

    Each item: {"question": str, "ground_truth": str, "contexts": list[str]}.
    """
    target = path or EVAL_DATA_PATH
    if not target.exists():
        return []
    with target.open(encoding="utf-8") as f:
        return json.load(f)


def is_placeholder(item: dict) -> bool:
    """True if the golden item still holds template placeholder text."""
    gt = (item.get("ground_truth") or "").upper()
    return gt.startswith("REPLACE") or gt in {"...", ""}


def usable_golden_qa(path: Path | None = None) -> list[dict]:
    return [item for item in load_golden_qa(path) if not is_placeholder(item)]
