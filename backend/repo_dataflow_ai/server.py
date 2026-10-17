"""FlowState API: analyse a public Python GitHub repo and return its AI dataflow visualisation.

    uvicorn server:app --port 8000      (from backend/repo_dataflow_ai)

Pipeline per repo: clone -> AST index -> ONNX role classifier -> Granite writes the markdown dataflow report
-> Granite turns that report into a grounded stage/flow graph. Results are cached per commit in output/cache/.
If frontend/flowstate/dist exists it is served at /, so the whole app runs on one port.
"""

import json
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.generator import generate_dataflow
from src.indexer import checkout_and_index, parse_repo_input, remote_head
from src.roles import RoleClassifier
from src.visualizer import generate_graph, heuristic_graph

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "output" / "cache"
FRONTEND_DIST = HERE.parent.parent / "frontend" / "flowstate" / "dist"

STEPS = [
    ("clone", "Cloning repository"),
    ("index", "Indexing Python code"),
    ("roles", "Classifying dataflow roles (ONNX)"),
    ("report", "Writing dataflow report (IBM Granite)"),
    ("graph", "Building dataflow visualisation (IBM Granite)"),
]

app = FastAPI(title="FlowState API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# llama.cpp is not thread-safe, so analyses run one at a time on a single worker.
executor = ThreadPoolExecutor(max_workers=1)
jobs = {}
jobs_lock = threading.Lock()
_engine = None
_classifier = RoleClassifier()


def engine():
    global _engine
    if _engine is None:
        from src.model_engine import load_engine
        _engine = load_engine()
    return _engine


def cache_path(owner, repo, sha):
    return CACHE_DIR / f"{owner}__{repo}__{sha[:12]}.json".lower()


def run_analysis(job_id, owner, repo):
    def step(name):
        with jobs_lock:
            jobs[job_id].update(status="running", step=name)

    timings, t0 = {}, time.time()
    try:
        index = checkout_and_index(owner, repo, on_step=step)
        timings["clone_index"] = round(time.time() - t0, 1)
        if not index["files"]:
            raise RuntimeError("No Python files found in this repository.")

        step("roles")
        roles = _classifier.predict(index["symbols"])

        step("report")
        t = time.time()
        llm = engine()
        report = generate_dataflow(llm, index["structure"], max_new_tokens=900).strip()
        timings["report"] = round(time.time() - t, 1)

        step("graph")
        t = time.time()
        dataflow = generate_graph(llm, report, index, roles, f"{owner}/{repo}") if index["symbols"] else heuristic_graph(index, roles)
        timings["graph"] = round(time.time() - t, 1)

        result = {
            "owner": owner, "repo": repo, "branch": index["branch"], "sha": index["sha"],
            "truncated": index["truncated"], "engine": llm.model_name,
            "role_model": "TF-IDF + logistic regression (ONNX)" if _classifier.session else "rules",
            "report_md": report,
            "files": [{"path": f["path"], "content": f["content"], "has_main": f["has_main"]} for f in index["files"]],
            "symbols": [{k: s[k] for k in ("id", "file", "name", "kind", "line", "end_line", "signature", "doc")}
                        for s in index["symbols"]],
            "calls": index["calls"],
            "dataflow": dataflow,
            "timings": {**timings, "total": round(time.time() - t0, 1)},
        }
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path(owner, repo, index["sha"]).write_text(json.dumps(result), encoding="utf-8")
        with jobs_lock:
            jobs[job_id].update(status="done", step="done", result=result)
    except Exception as exc:
        traceback.print_exc()
        with jobs_lock:
            jobs[job_id].update(status="error", error=str(exc))


class AnalyzeRequest(BaseModel):
    repo: str
    refresh: bool = False


@app.get("/api/health")
def health():
    return {"ok": True, "engine_loaded": _engine is not None, "role_model": bool(_classifier.session)}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    target = parse_repo_input(req.repo)
    if not target:
        raise HTTPException(400, "Enter a repository as owner/repo or a GitHub URL.")
    owner, repo = target
    sha = remote_head(owner, repo)
    if not sha:
        raise HTTPException(404, "Repository not found (it must be a public GitHub repo).")
    cached = cache_path(owner, repo, sha)
    if cached.exists() and not req.refresh:
        return {"status": "done", "result": json.loads(cached.read_text(encoding="utf-8"))}

    job_id = uuid.uuid4().hex[:12]
    with jobs_lock:
        jobs[job_id] = {"id": job_id, "status": "queued", "step": "queued", "repo": f"{owner}/{repo}"}
    executor.submit(run_analysis, job_id, owner, repo)
    return {"status": "queued", "job_id": job_id, "steps": [{"id": k, "label": v} for k, v in STEPS]}


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    with jobs_lock:
        data = jobs.get(job_id)
        if not data:
            raise HTTPException(404, "Unknown job.")
        return {**data, "steps": [{"id": k, "label": v} for k, v in STEPS]}


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        file = FRONTEND_DIST / path
        if path and file.is_file() and FRONTEND_DIST in file.resolve().parents:
            return FileResponse(file)
        return FileResponse(FRONTEND_DIST / "index.html")
