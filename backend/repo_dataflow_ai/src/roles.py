"""Dataflow role of each function (entry / input / transform / storage / output).

A TF-IDF + logistic regression model trained by training/train_role_classifier.py and exported to ONNX,
following the IBM LinuxONE pattern of training anywhere and running ONNX inference on IBM Z.
"""

import re
from pathlib import Path

import numpy as np

ROLES = ["entry", "input", "transform", "storage", "output"]
ONNX_PATH = Path(__file__).resolve().parent.parent / "artifacts" / "role_classifier.onnx"

# Weak-supervision rules: used to label the training corpus, and as a high-precision override at inference.
_RULES = {
    "entry": re.compile(r"(^|\.)(ArgumentParser|parse_args|command|group|route|get|post|put|delete|websocket|"
                        r"run_app|uvicorn\.run|app\.run|Typer|main)$"),
    "input": re.compile(r"(^|\.)(read|read_text|read_bytes|readline|readlines|read_csv|read_json|read_excel|"
                        r"read_parquet|load|loads|safe_load|urlopen|recv|input|getenv|glob|listdir|scandir|"
                        r"walk|fetch|download|requests\.get|httpx\.get|get_json|from_file|open_dataset|imread)$"),
    "storage": re.compile(r"(^|\.)(execute|executemany|commit|cursor|connect|insert|insert_one|insert_many|"
                          r"update_one|bulk_write|add_all|flush|to_sql|set|hset|lpush|setex|save_model|"
                          r"create_all|session\.add|db\.add|put_item|upload_file|cache)$"),
    "output": re.compile(r"(^|\.)(write|write_text|write_bytes|writelines|dump|dumps|to_csv|to_json|to_excel|"
                         r"to_parquet|savefig|show|print|echo|secho|send|sendall|post|put|jsonify|render|"
                         r"render_template|emit|publish|imwrite|save)$"),
}
_ENTRY_DECORATOR = re.compile(r"(command|group|route|\.get|\.post|\.put|\.delete|\.websocket|callback|task)\b")
_ENTRY_NAME = re.compile(r"^(main|cli|run|app|entry|entrypoint|start|serve)$")


def split_ident(text):
    """'loadUserCSV_file' -> ['load', 'user', 'csv', 'file']"""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    return [t.lower() for t in re.split(r"[^A-Za-z0-9]+", text) if t and not t.isdigit()]


def features(sym, with_calls=True):
    """Whitespace-separated tokens describing a function: name, args, docstring, decorators and (optionally) calls."""
    toks = ["n_" + t for t in split_ident(sym["name"].split(".")[-1])]
    toks += ["a_" + t for a in sym.get("args", []) for t in split_ident(a) if t not in ("self", "cls")]
    toks += ["d_" + t for t in split_ident(sym.get("doc", ""))[:24]]
    toks += ["k_" + t for d in sym.get("decorators", []) for t in split_ident(d)]
    if with_calls:
        for c in sym.get("dotted_calls", [])[:40]:
            parts = c.split(".")
            toks.append("c_" + parts[-1].lower())
            if len(parts) > 1:
                toks.append("m_" + parts[0].lower())
    toks.append("kind_" + sym.get("kind", "function"))
    return " ".join(toks) or "empty"


def rule_role(sym):
    """Heuristic label from calls, decorators and name; None when nothing matches (treated as 'transform')."""
    name = sym["name"].split(".")[-1]
    if _ENTRY_NAME.match(name) or any(_ENTRY_DECORATOR.search(d) for d in sym.get("decorators", [])):
        return "entry"
    calls = sym.get("dotted_calls", [])
    scores = {role: sum(1 for c in calls if rx.search(c)) for role, rx in _RULES.items() if role != "entry"}
    if any(c.endswith(("ArgumentParser", "parse_args")) for c in calls):
        return "entry"
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


class RoleClassifier:
    """Runs the exported ONNX model with onnxruntime; falls back to the rules if the model is missing."""

    def __init__(self, path=ONNX_PATH):
        self.session = None
        if Path(path).exists():
            import onnxruntime as ort
            self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            self.input_name = self.session.get_inputs()[0].name

    def predict(self, symbols):
        """Return {symbol id: (role, confidence)} for every function/method in `symbols`."""
        funcs = [s for s in symbols if s["kind"] != "class"]
        out = {}
        if self.session and funcs:
            texts = np.array([[features(s)] for s in funcs])
            labels, probs = self.session.run(None, {self.input_name: texts})
            for s, label, p in zip(funcs, labels, probs):
                out[s["id"]] = (str(label), float(np.max(p)))
        for s in funcs:
            rule = rule_role(s)
            if rule and (s["id"] not in out or out[s["id"]][1] < 0.6):
                out[s["id"]] = (rule, 0.9)
            out.setdefault(s["id"], ("transform", 0.5))
        # A class takes the most common role of its methods.
        for s in symbols:
            if s["kind"] == "class":
                roles = [out[m["id"]][0] for m in symbols if m["kind"] == "method" and m["name"].startswith(s["name"] + ".")]
                out[s["id"]] = (max(set(roles), key=roles.count), 0.5) if roles else ("transform", 0.5)
        return out
