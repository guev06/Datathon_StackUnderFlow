from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def write_results_graph(
    history: list[dict[str, float]],
    test_metrics: dict[str, float | int] | None,
    model_name: str,
    path: Path,
) -> None:
    width = 900
    height = 520
    left = 80
    right = 40
    plot_width = width - left - right
    loss_top = 75
    loss_height = 150
    score_top = 315
    score_height = 125
    escaped_name = html.escape(model_name)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#263238}'
        '.axis{stroke:#78909c;stroke-width:1}.grid{stroke:#e0e6e9}'
        '.train{stroke:#1565c0}.validation{stroke:#ef6c00}'
        '.accuracy{stroke:#2e7d32}.precision{stroke:#6a1b9a}'
        '.recall{stroke:#00838f}.f1{stroke:#c62828}'
        '.line{fill:none;stroke-width:2.5}</style>',
        f'<text x="{left}" y="30" font-size="20" font-weight="bold">'
        f'Training report: {escaped_name}</text>',
        f'<text x="{left}" y="56" font-size="14">Loss by epoch</text>',
        f'<text x="{left}" y="290" font-size="14">'
        "Validation and held-out test scores</text>",
    ]

    def draw_axes(top: int, plot_height: int, y_labels: list[str]) -> None:
        for index, label in enumerate(y_labels):
            y = top + index * plot_height / max(1, len(y_labels) - 1)
            elements.append(
                f'<line class="grid" x1="{left}" y1="{y:.1f}" '
                f'x2="{left + plot_width}" y2="{y:.1f}"/>'
            )
            elements.append(
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" '
                f'font-size="11">{label}</text>'
            )
        elements.append(
            f'<line class="axis" x1="{left}" y1="{top}" '
            f'x2="{left}" y2="{top + plot_height}"/>'
        )
        elements.append(
            f'<line class="axis" x1="{left}" y1="{top + plot_height}" '
            f'x2="{left + plot_width}" y2="{top + plot_height}"/>'
        )

    def line_points(
        values: list[float], top: int, plot_height: int, upper: float
    ) -> str:
        if not values:
            return ""
        points: list[str] = []
        for index, value in enumerate(values):
            x = (
                left
                if len(values) == 1
                else left + index * plot_width / (len(values) - 1)
            )
            y = top + plot_height - min(max(value / upper, 0.0), 1.0) * plot_height
            points.append(f"{x:.1f},{y:.1f}")
        return " ".join(points)

    def add_legend(
        items: list[tuple[str, str]], y: int, start_x: int = left
    ) -> None:
        x = start_x
        for label, class_name in items:
            elements.append(
                f'<line class="{class_name}" x1="{x}" y1="{y}" '
                f'x2="{x + 22}" y2="{y}" stroke-width="3"/>'
            )
            elements.append(
                f'<text x="{x + 28}" y="{y + 4}" font-size="12">'
                f"{html.escape(label)}</text>"
            )
            x += 140

    loss_values = [
        value
        for row in history
        for value in (row["train_loss"], row["validation_loss"])
    ]
    max_loss = max(loss_values, default=1.0)
    loss_limit = max(max_loss * 1.1, 0.1)
    draw_axes(
        loss_top,
        loss_height,
        [f"{loss_limit:.2f}", f"{loss_limit / 2:.2f}", "0"],
    )
    for index, row in enumerate(history):
        x = (
            left
            if len(history) == 1
            else left + index * plot_width / (len(history) - 1)
        )
        elements.append(
            f'<text x="{x:.1f}" y="{loss_top + loss_height + 18}" '
            f'text-anchor="middle" font-size="11">{int(row["epoch"])}</text>'
        )
    for field, class_name in (
        ("train_loss", "train"),
        ("validation_loss", "validation"),
    ):
        points = line_points(
            [row[field] for row in history], loss_top, loss_height, loss_limit
        )
        if points:
            elements.append(
                f'<polyline class="line {class_name}" points="{points}"/>'
            )
    add_legend(
        [("Train loss", "train"), ("Validation loss", "validation")],
        loss_top + loss_height + 43,
    )

    draw_axes(score_top, score_height, ["1.0", "0.5", "0.0"])
    points = line_points(
        [row["validation_accuracy"] for row in history],
        score_top,
        score_height,
        1.0,
    )
    if points:
        elements.append(
            f'<polyline class="line accuracy" points="{points}"/>'
        )

    if test_metrics is not None:
        test_values = [
            float(test_metrics["accuracy"]),
            float(test_metrics["precision"]),
            float(test_metrics["recall"]),
            float(test_metrics["f1"]),
        ]
        bar_width = min(38, plot_width / (len(test_values) * 2))
        gap = bar_width * 0.45
        group_width = len(test_values) * (bar_width + gap) - gap
        base_x = left + plot_width - group_width
        colors = ["#2e7d32", "#6a1b9a", "#00838f", "#c62828"]
        labels = ["Test acc.", "Test prec.", "Test recall", "Test F1"]
        for index, (value, color, label) in enumerate(
            zip(test_values, colors, labels)
        ):
            x = base_x + index * (bar_width + gap)
            bar_height = value * score_height
            y = score_top + score_height - bar_height
            elements.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
                f'height="{bar_height:.1f}" fill="{color}" opacity="0.8"/>'
            )
            elements.append(
                f'<text x="{x + bar_width / 2:.1f}" '
                f'y="{score_top + score_height + 17}" '
                f'text-anchor="middle" font-size="9">{label}</text>'
            )

    add_legend(
        [("Validation accuracy", "accuracy")],
        score_top + score_height + 43,
    )
    if test_metrics is None:
        elements.append(
            f'<text x="{left}" y="{height - 20}" font-size="12">'
            "No held-out test split was provided.</text>"
        )
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def write_run_report(
    run_directory: Path,
    model_name: str,
    history: list[dict[str, float]],
    test_metrics: dict[str, float | int] | None,
) -> None:
    run_directory.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "model_name": model_name,
        "training_history": history,
        "test_metrics": test_metrics,
    }
    (run_directory / "metrics.json").write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = [
        f"Model: {model_name}",
        f"Epochs: {len(history)}",
    ]
    if history:
        last_epoch = history[-1]
        summary.extend(
            [
                f"Final training loss: {last_epoch['train_loss']:.4f}",
                f"Final validation loss: {last_epoch['validation_loss']:.4f}",
                f"Final validation accuracy: "
                f"{last_epoch['validation_accuracy']:.4f}",
            ]
        )
    if test_metrics is not None:
        summary.extend(
            [
                f"Held-out test examples: {test_metrics['examples']}",
                f"Test loss: {test_metrics['loss']:.4f}",
                f"Test accuracy: {test_metrics['accuracy']:.4f}",
                f"Test precision: {test_metrics['precision']:.4f}",
                f"Test recall: {test_metrics['recall']:.4f}",
                f"Test F1: {test_metrics['f1']:.4f}",
                "Confusion matrix counts: "
                f"TP={test_metrics['true_positive']}, "
                f"FP={test_metrics['false_positive']}, "
                f"FN={test_metrics['false_negative']}, "
                f"TN={test_metrics['true_negative']}",
            ]
        )
    else:
        summary.append("Held-out test split: not provided")
    (run_directory / "results.txt").write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8",
    )
    write_results_graph(
        history,
        test_metrics,
        model_name,
        run_directory / "results.svg",
    )
