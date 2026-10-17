from pathlib import Path

from LLM.layer5_classification import VulnerabilityClassifier
from LLM.training import train


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    train(
        VulnerabilityClassifier(),
        project_root / "assets/primevul/primevul_train.jsonl",
        project_root / "assets/primevul/primevul_valid.jsonl",
        test_data=project_root / "assets/primevul/primevul_test.jsonl",
        epochs=10,
    )


if __name__ == "__main__":
    main()
