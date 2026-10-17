"""Train the dataflow-role classifier and export it to ONNX.

Follows the IBM LinuxONE (jupyter-lab-ml) workflow: train with scikit-learn on any machine, export to the
portable ONNX format, and run inference with onnxruntime (which also runs on IBM Z / LinuxONE, s390x).

Training data is weakly supervised: functions from a large Python corpus (the standard library and installed
packages by default) are labelled by the rules in src/roles.py. Half the samples have their call tokens removed,
so the model also learns to recognise roles from names, arguments and docstrings alone, which is what lets it
generalise past the rules.

    python -m training.train_role_classifier                      # stdlib + site-packages
    python -m training.train_role_classifier --corpus ~/code      # add your own folders
"""

import random
import sys
import sysconfig
from collections import Counter
from pathlib import Path

import click
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.indexer import index_file, list_python_files  # noqa: E402
from src.roles import ONNX_PATH, ROLES, features, rule_role  # noqa: E402


def collect(corpora, limit, seed):
    rng = random.Random(seed)
    samples = []
    for corpus in corpora:
        corpus = Path(corpus)
        if not corpus.is_dir():
            continue
        for rel in list_python_files(corpus):
            try:
                source = (corpus / rel).read_text(encoding="utf-8", errors="replace")
                symbols, _, _ = index_file(rel, source)
            except (OSError, ValueError, RecursionError):
                continue
            for s in symbols:
                if s["kind"] in ("function", "method") and not s["name"].split(".")[-1].startswith("__"):
                    samples.append((s, rule_role(s) or "transform"))
        click.echo(f"  {corpus}: {len(samples)} functions so far", err=True)
    # Keep the classes balanced: 'transform' dominates any real codebase.
    by_role = {r: [x for x in samples if x[1] == r] for r in ROLES}
    cap = max(2000, min(limit // len(ROLES), max(len(v) for k, v in by_role.items() if k != "transform")))
    balanced = []
    for role, items in by_role.items():
        rng.shuffle(items)
        balanced += items[:cap]
    rng.shuffle(balanced)
    return balanced


@click.command()
@click.option("--corpus", "extra", multiple=True, type=click.Path(file_okay=False), help="Extra folders of Python code.")
@click.option("--limit", default=60_000, show_default=True, help="Maximum training samples.")
@click.option("--seed", default=0, show_default=True)
def main(extra, limit, seed):
    paths = sysconfig.get_paths()
    corpora = [paths["stdlib"], paths["purelib"], *extra]
    click.echo("Collecting functions ...", err=True)
    samples = collect(corpora, limit, seed)
    rng = random.Random(seed)
    texts = [features(s, with_calls=rng.random() < 0.5) for s, _ in samples]
    labels = [label for _, label in samples]
    click.echo(f"Training on {len(texts)} samples: {dict(Counter(labels))}", err=True)

    x_train, x_test, y_train, y_test = train_test_split(texts, labels, test_size=0.15, random_state=seed, stratify=labels)
    model = Pipeline([
        ("tfidf", TfidfVectorizer(token_pattern=r"\S+", lowercase=False, min_df=2, max_features=30_000, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")),
    ])
    model.fit(x_train, y_train)
    click.echo(classification_report(y_test, model.predict(x_test), digits=3))

    from skl2onnx import to_onnx
    from skl2onnx.common.data_types import StringTensorType

    onx = to_onnx(
        model,
        initial_types=[("text", StringTensorType([None, 1]))],
        options={TfidfVectorizer: {"tokenexp": None, "separators": [" "]}, LogisticRegression: {"zipmap": False}},
        target_opset={"": 17, "ai.onnx.ml": 3},
    )
    ONNX_PATH.parent.mkdir(parents=True, exist_ok=True)
    ONNX_PATH.write_bytes(onx.SerializeToString())

    # Check the ONNX export agrees with scikit-learn before shipping it.
    import onnxruntime as ort
    sess = ort.InferenceSession(str(ONNX_PATH), providers=["CPUExecutionProvider"])
    sample = x_test[:500]
    onnx_labels = sess.run(None, {"text": np.array([[t] for t in sample])})[0]
    agreement = np.mean([a == b for a, b in zip(onnx_labels, model.predict(sample))])
    click.echo(f"Saved {ONNX_PATH} ({ONNX_PATH.stat().st_size / 1024:.0f} KB); ONNX/sklearn agreement {agreement:.1%}", err=True)


if __name__ == "__main__":
    main()
