from __future__ import annotations

from os import PathLike
from pathlib import Path

import torch
from torch.nn import functional as F

from LLM.evaluation import (
    aggregate_window_probabilities,
    default_device,
    run_evaluation,
    tensor_window_batch,
)
from LLM.layer1_data_ingestion import count_targets, iter_window_parser_batches
from LLM.layer5_classification import VulnerabilityClassifier
from LLM.run_reporting import write_run_report


def train(
    model: VulnerabilityClassifier,
    train_data: str | PathLike[str],
    val_data: str | PathLike[str],
    epochs: int = 10,
    batch_size: int = 2,
    learning_rate: float = 3e-4,
    device: str | torch.device | None = None,
    test_data: str | PathLike[str] | None = None,
) -> list[dict[str, float]]:
    """Train on PrimeVul and save checkpoint and reports in ``LLM/runs``."""
    if epochs < 1:
        raise ValueError("epochs must be at least 1")
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be positive")

    train_path = Path(train_data)
    val_path = Path(val_data)
    test_path = Path(test_data) if test_data is not None else None
    target_device = torch.device(device) if device is not None else default_device()
    model.to(target_device)

    runs_directory = Path(__file__).resolve().parent / "runs"
    runs_directory.mkdir(parents=True, exist_ok=True)
    run_number = 1
    while True:
        run_name = f"run{run_number}"
        run_directory = runs_directory / run_name
        try:
            run_directory.mkdir()
            break
        except FileExistsError:
            run_number += 1

    negative_count, positive_count = count_targets(train_path)
    total_count = negative_count + positive_count
    class_weights = torch.tensor(
        [
            total_count / (2 * negative_count) if negative_count else 0.0,
            total_count / (2 * positive_count) if positive_count else 0.0,
        ],
        dtype=torch.float32,
        device=target_device,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    history: list[dict[str, float]] = []

    for epoch in range(epochs):
        print(f"Epoch {epoch + 1}/{epochs} - Training on {total_count} records")
        model.train()
        weighted_loss_total = 0.0
        total = 0
        for batch in iter_window_parser_batches(
            train_path,
            model.tokenizer,
            max_length=model.config.max_length,
            batch_size=batch_size,
        ):
            input_ids, attention_mask, labels, window_counts = tensor_window_batch(
                batch, target_device
            )
            optimizer.zero_grad(set_to_none=True)
            logits = model(input_ids, attention_mask)
            probabilities = aggregate_window_probabilities(logits, window_counts)
            loss = F.nll_loss(
                probabilities.clamp_min(torch.finfo(probabilities.dtype).tiny).log(),
                labels,
                weight=class_weights,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            weighted_loss_total += loss.item() * labels.numel()
            total += labels.numel()

        if total == 0:
            raise ValueError(f"No training records found in {train_path}")
        validation_metrics = run_evaluation(
            model, val_path, batch_size, target_device
        )
        metrics = {
            "epoch": float(epoch + 1),
            "train_loss": weighted_loss_total / total,
            "validation_loss": float(validation_metrics["loss"]),
            "validation_accuracy": float(validation_metrics["accuracy"]),
        }
        history.append(metrics)
        print(
            f"Epoch {epoch + 1}/{epochs}: "
            f"train_loss={metrics['train_loss']:.4f}, "
            f"validation_loss={metrics['validation_loss']:.4f}, "
            f"validation_accuracy={metrics['validation_accuracy']:.4f}"
        )

    test_metrics = (
        run_evaluation(model, test_path, batch_size, target_device)
        if test_path is not None
        else None
    )
    if test_metrics is not None:
        print(
            "Held-out test: "
            f"loss={test_metrics['loss']:.4f}, "
            f"accuracy={test_metrics['accuracy']:.4f}, "
            f"precision={test_metrics['precision']:.4f}, "
            f"recall={test_metrics['recall']:.4f}, "
            f"f1={test_metrics['f1']:.4f}"
        )

    checkpoint_file = run_directory / "model.pt"
    model.save_checkpoint(checkpoint_file)
    write_run_report(run_directory, run_name, history, test_metrics)
    print(f"Saved model checkpoint to {checkpoint_file}")
    print(f"Saved run results and graph to {run_directory}")
    return history
