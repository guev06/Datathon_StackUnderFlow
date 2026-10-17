from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from LLM.evaluation import default_device
from LLM.layer5_classification import VulnerabilityClassifier


def summarize_predictions(
    name: str,
    true_counts: list[int],
    predicted_counts: list[int],
    confusion: list[list[int]],
) -> dict[str, Any]:
    total = sum(true_counts)
    correct = confusion[0][0] + confusion[1][1]
    true_positive = confusion[1][1]
    false_positive = confusion[0][1]
    false_negative = confusion[1][0]
    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    precision = (
        true_positive / precision_denominator if precision_denominator else 0.0
    )
    recall = true_positive / recall_denominator if recall_denominator else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "path": name,
        "examples": total,
        "actual_counts": {
            "not_vulnerable": true_counts[0],
            "vulnerable": true_counts[1],
        },
        "predicted_counts": {
            "not_vulnerable": predicted_counts[0],
            "vulnerable": predicted_counts[1],
        },
        "confusion_matrix": {
            "rows_actual_0_1_columns_predicted_0_1": confusion,
        },
        "accuracy": correct / total,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def latest_run(runs_directory: Path) -> Path:
    runs = [
        path
        for path in runs_directory.iterdir()
        if path.is_dir() and re.fullmatch(r"run\d+", path.name)
    ] if runs_directory.exists() else []
    if not runs:
        raise FileNotFoundError(
            f"No run folders found in {runs_directory}. Train a model first."
        )
    return max(runs, key=lambda path: int(path.name.removeprefix("run")))


def test_model(
    checkpoint: Path,
    test_data: Path,
    limit: int,
) -> None:
    device = default_device()
    model = VulnerabilityClassifier.load_checkpoint(checkpoint, map_location=device)
    model.to(device)

    total = 0
    correct = 0
    true_counts = [0, 0]
    predicted_counts = [0, 0]
    confusion = [[0, 0], [0, 0]]
    with test_data.open(encoding="utf-8") as records:
        for line_number, line in enumerate(records, start=1):
            if limit and total >= limit:
                break
            try:
                record: Any = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {test_data}"
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(f"Expected a JSON object on line {line_number}")
            source = record.get("func")
            target = record.get("target")
            if (
                not isinstance(source, str)
                or type(target) is not int
                or target not in (0, 1)
            ):
                raise ValueError(
                    f"Line {line_number} must have string 'func' and target 0 or 1"
                )

            prediction = model.predict(source)
            predicted_target = int(prediction["vulnerable"])
            is_correct = predicted_target == target
            total += 1
            true_counts[target] += 1
            predicted_counts[predicted_target] += 1
            confusion[target][predicted_target] += 1
            correct += int(is_correct)

            print(
                json.dumps(
                    {
                        "example": total,
                        "expected": (
                            "vulnerable" if target == 1 else "not_vulnerable"
                        ),
                        "prediction": prediction,
                        "correct": is_correct,
                    },
                    indent=2,
                )
            )

    if total == 0:
        raise ValueError(f"No test records found in {test_data}")
    print(
        json.dumps(
            {
                "metrics": summarize_predictions(
                    "mean class probabilities across all byte windows",
                    true_counts,
                    predicted_counts,
                    confusion,
                ),
                "correct": correct,
            },
            indent=2,
        )
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run a saved vulnerability model on PrimeVul test examples."
    )
    parser.add_argument(
        "--run",
        help="Run folder name, such as run3. Defaults to the latest run.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=project_root / "assets/primevul/primevul_test_paired.jsonl",
        help="JSONL test file (defaults to the smaller paired PrimeVul test split).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of examples to test; use 0 to test the full file.",
    )
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be 0 or a positive integer")

    runs_directory = project_root / "LLM/runs"
    run_directory = (
        runs_directory / args.run if args.run else latest_run(runs_directory)
    )
    if args.run and not re.fullmatch(r"run\d+", args.run):
        parser.error("--run must have the form runN, for example run3")
    checkpoint = run_directory / "model.pt"
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Model checkpoint not found: {checkpoint}")

    print(f"Loading model: {checkpoint}")
    print(f"Testing with: {args.data}")
    test_model(checkpoint, args.data, args.limit)


if __name__ == "__main__":
    main()
