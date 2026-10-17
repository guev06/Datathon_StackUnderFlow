from pathlib import Path

from LLM.layer5_classification import VulnerabilityClassifier
from LLM.training import train

data = Path("assets/primevul")

train(
    VulnerabilityClassifier(),
    data / "primevul_train_paired.jsonl",
    data / "primevul_valid_paired.jsonl",
    test_data=data / "primevul_test_paired.jsonl",
    epochs=20,
    batch_size=8,
)