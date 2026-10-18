"""Turns the markdown dataflow report into an interactive dataflow graph grounded in the real code.

Granite reads the report plus a catalogue of the repository's functions and returns stages and flows as JSON.
The JSON schema is compiled into a llama.cpp grammar whose symbol references are an enum of catalogue ids,
so every stage can only point at code that exists. Line spans come from the AST index, never from the model.
"""

import json
import re
from collections import Counter

from .indexer import TEST_PATH
from .roles import ROLES

MAX_CATALOGUE = 110
MAX_STAGES = 9

SYSTEM_PROMPT = """You are a software architect who turns a written description of a repository's dataflow into a \
dataflow diagram. You will get the description and a catalogue of the repository's real functions and classes, each \
with an id like S7, its file, its predicted dataflow role and its docstring.

Produce the diagram as JSON:
- "stages": 3 to 9 steps in the order data moves through the program. Each stage has a short title (2-5 words), a \
one-sentence summary of what happens to the data there, a kind (entry, input, transform, storage or output) and \
"refs": the ids of the 1-6 catalogue entries whose code implements that step.
- "flows": arrows between stages. "label" names the data handed over (e.g. "parsed config", "rows", "HTML report").

Rules:
- The description is a numbered walkthrough: normally make one stage per numbered step, reusing its title.
- A stage is a concrete operation on data, named with a verb ("Parse CLI arguments", "Read .env file", "Resolve \
variables"). Never copy the description's section headings ("Entry Point", "Data Flow", "Final Output").
- Each catalogue id belongs to at most one stage. Leave out tests.
- Only cite ids from the catalogue. Prefer the functions the description names. Follow the real call order.
"""

USER_TEMPLATE = """Repository: {repo}

## Dataflow description
{report}

## Code catalogue (id | symbol | kind | role | summary)
{catalogue}

Return the dataflow diagram JSON."""


def _rank_symbols(index, roles, report):
    """Score symbols by how likely they belong in the diagram: named in the report, roles, call-graph degree."""
    mentioned = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", report))
    degree = Counter()
    for e in index["calls"]:
        degree[e["source"]] += 1
        degree[e["target"]] += 1
    scored = []
    symbols = [s for s in index["symbols"] if not TEST_PATH.search(s["file"])] or index["symbols"]
    for s in symbols:
        short = s["name"].split(".")[-1]
        role = roles.get(s["id"], ("transform", 0))[0]
        score = min(degree[s["id"]], 8) * 0.5
        score += 6 if short in mentioned else 0
        score += 2 if role in ("entry", "input", "output", "storage") else 0
        score -= 4 if short.startswith("_") else 0
        score -= 4 if re.search(r"(^|/)(docs?|examples?|benchmarks?)/", s["file"]) else 0
        score -= 1 if s["kind"] == "method" else 0
        score += 3 if s["kind"] == "module" else 0
        scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:MAX_CATALOGUE]]


def _schema(ids):
    stage_ids = [f"s{i}" for i in range(1, MAX_STAGES + 1)]
    return {
        "type": "object",
        "properties": {
            "stages": {
                "type": "array", "minItems": 3, "maxItems": MAX_STAGES,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "enum": stage_ids},
                        "title": {"type": "string", "maxLength": 48},
                        "summary": {"type": "string", "maxLength": 240},
                        "kind": {"type": "string", "enum": ROLES},
                        "refs": {"type": "array", "minItems": 1, "maxItems": 6, "items": {"type": "string", "enum": ids}},
                    },
                    "required": ["id", "title", "summary", "kind", "refs"],
                },
            },
            "flows": {
                "type": "array", "maxItems": 16,
                "items": {
                    "type": "object",
                    "properties": {
                        "from": {"type": "string", "enum": stage_ids},
                        "to": {"type": "string", "enum": stage_ids},
                        "label": {"type": "string", "maxLength": 40},
                    },
                    "required": ["from", "to", "label"],
                },
            },
        },
        "required": ["stages", "flows"],
    }


def _call_flows(stages, index):
    """Count code-level calls between stages so the UI can show which arrows are backed by real calls."""
    owner = {}
    for st in stages:
        for ref in st["refs"]:
            owner.setdefault(ref, st["id"])
    counts = Counter()
    for e in index["calls"]:
        a, b = owner.get(e["source"]), owner.get(e["target"])
        if a and b and a != b:
            counts[(a, b)] += 1
    return counts


def _finalise(stages, flows, index, roles, source):
    stage_ids = {s["id"] for s in stages}
    clean, seen = [], set()
    for f in flows:
        key = (f["from"], f["to"])
        if f["from"] in stage_ids and f["to"] in stage_ids and f["from"] != f["to"] and key not in seen:
            seen.add(key)
            clean.append({"source": f["from"], "target": f["to"], "label": f.get("label", "").strip(), "kind": "flow"})
    # Stages come in execution order, so any stage the model left without an incoming arrow follows the previous one.
    has_in = {f["target"] for f in clean}
    for a, b in zip(stages, stages[1:]):
        if b["id"] not in has_in:
            clean.append({"source": a["id"], "target": b["id"], "label": "", "kind": "flow"})
    calls = _call_flows(stages, index)
    for f in clean:
        f["calls"] = calls.get((f["source"], f["target"]), 0)
    for (a, b), n in calls.items():
        if (a, b) not in seen and not any(f["source"] == a and f["target"] == b for f in clean) and n >= 1:
            clean.append({"source": a, "target": b, "label": f"{n} call{'s' if n > 1 else ''}", "kind": "call", "calls": n})

    by_id = {s["id"]: s for s in index["symbols"]}
    for st in stages:
        st["refs"] = [r for r in dict.fromkeys(st["refs"]) if r in by_id]
        st["files"] = sorted({by_id[r]["file"] for r in st["refs"]})
    return {"stages": stages, "flows": clean, "source": source,
            "roles": {sid: {"role": r, "confidence": round(c, 2)} for sid, (r, c) in roles.items()}}


def heuristic_graph(index, roles, report=""):
    """Deterministic fallback: one stage per dataflow role, filled with the highest-ranked symbols of that role."""
    ranked = _rank_symbols(index, roles, report)
    titles = {"entry": "Entry points", "input": "Load input", "transform": "Process data",
              "storage": "Persist state", "output": "Produce output"}
    summaries = {"entry": "Execution starts here and arguments or requests are received.",
                 "input": "Data is read from files, the network or the environment.",
                 "transform": "The data is parsed, validated and transformed.",
                 "storage": "Results are written to a database, cache or other store.",
                 "output": "Final results are written, printed or returned to the caller."}
    stages = []
    for role in ROLES:
        refs = [s["id"] for s in ranked if roles.get(s["id"], ("transform",))[0] == role][:6]
        if refs:
            stages.append({"id": f"s{len(stages) + 1}", "title": titles[role], "summary": summaries[role], "kind": role, "refs": refs})
    flows = [{"from": a["id"], "to": b["id"], "label": ""} for a, b in zip(stages, stages[1:])]
    return _finalise(stages, flows, index, roles, "heuristic")


def _attach_mentions(stages, ranked):
    """Small models sometimes describe a function in a stage but cite a different id; add the ones a stage names."""
    by_short = {}
    for sym in ranked:
        short = sym["name"].split(".")[-1]
        if len(short) >= 4 and sym["kind"] != "module":
            by_short.setdefault(short, sym["id"])
    claimed = {r for st in stages for r in st["refs"]}
    for st in stages:
        for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", f"{st['title']} {st['summary']}"):
            sid = by_short.get(word)
            if sid and sid not in claimed and len(st["refs"]) < 6:
                st["refs"].insert(0, sid)
                claimed.add(sid)


def generate_graph(engine, report, index, roles, repo_name):
    """Ask the model to convert the markdown report into a grounded stage/flow graph; fall back to heuristics."""
    ranked = _rank_symbols(index, roles, report)
    if len(ranked) < 3:
        return heuristic_graph(index, roles, report)
    alias = {f"S{i + 1}": s["id"] for i, s in enumerate(ranked)}
    lines = []
    for short, sid in alias.items():
        s = next(x for x in ranked if x["id"] == sid)
        role = roles.get(sid, ("transform", 0))[0]
        label = "top-level script code" if s["kind"] == "module" else s["name"]
        lines.append(f"{short} | {s['file']}::{label} | {s['kind']} | {role} | {s['doc'][:90]}")
    prompt = USER_TEMPLATE.format(repo=repo_name, report=report.strip()[:6000], catalogue="\n".join(lines))
    try:
        raw = engine.generate(prompt, system=SYSTEM_PROMPT, max_new_tokens=1400, temperature=0.1, schema=_schema(list(alias)))
        data = json.loads(raw)
    except Exception:
        return heuristic_graph(index, roles, report)

    # Each symbol keeps only its first stage; stages are renumbered s1..sN in order and flows remapped.
    stages, renamed, claimed = [], {}, set()
    for st in data.get("stages", []):
        refs = [alias[r] for r in dict.fromkeys(st.get("refs", [])) if r in alias and alias[r] not in claimed]
        if not refs or st.get("id") in renamed or re.search(r"\btest", st["title"], re.I):
            continue
        claimed.update(refs)
        renamed[st["id"]] = f"s{len(stages) + 1}"
        stages.append({"id": renamed[st["id"]], "title": st["title"].strip() or "Step", "summary": st["summary"].strip(),
                       "kind": st["kind"], "refs": refs})
    if len(stages) < 2:
        return heuristic_graph(index, roles, report)
    _attach_mentions(stages, ranked)
    flows = [{**f, "from": renamed[f["from"]], "to": renamed[f["to"]]}
             for f in data.get("flows", []) if f.get("from") in renamed and f.get("to") in renamed]
    return _finalise(stages, flows, index, roles, "model")
