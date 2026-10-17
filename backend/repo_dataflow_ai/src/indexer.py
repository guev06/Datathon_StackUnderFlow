"""Clone a GitHub repository and index its Python code: symbols with exact line spans, calls and imports."""

import ast
import os
import re
import subprocess
import tempfile
from pathlib import Path

from .parser import SKIP_DIRS

MAX_FILES = 300
MAX_FILE_BYTES = 300_000
TEST_PATH = re.compile(r"(^|/)(tests?|testing)/|(^|/)(test_[^/]*|[^/]*_test|conftest)\.py$")
LOW_PRIORITY = re.compile(r"(^|/)(tests?|testing|docs?|examples?|benchmarks?|scripts)/|(^|/)(test_[^/]*|[^/]*_test|conftest|setup)\.py$")


def parse_repo_input(text):
    """Accept owner/repo, github.com/owner/repo or a full URL; return (owner, repo) or None."""
    cleaned = re.sub(r"^https?://", "", text.strip())
    cleaned = re.sub(r"^(www\.)?github\.com/", "", cleaned)
    cleaned = re.sub(r"\.git$", "", cleaned).strip("/")
    parts = cleaned.split("/")
    if len(parts) < 2 or not all(re.fullmatch(r"[\w.-]+", p) for p in parts[:2]):
        return None
    return parts[0], parts[1]


def clone_repo(owner, repo, dest):
    """Shallow-clone a public GitHub repo into `dest`; return (branch, commit sha)."""
    url = f"https://github.com/{owner}/{repo}.git"
    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:limit=1m", "--quiet", url, str(dest)],
        capture_output=True, text=True, timeout=180, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode != 0:
        raise RuntimeError("Repository not found or not public." if "not found" in result.stderr.lower()
                           else f"git clone failed: {result.stderr.strip()[:300]}")
    branch = subprocess.run(["git", "-C", str(dest), "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    sha = subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    return branch, sha


def remote_head(owner, repo):
    """Commit sha of the default branch without cloning (used as the cache key), or None."""
    result = subprocess.run(["git", "ls-remote", f"https://github.com/{owner}/{repo}.git", "HEAD"],
                            capture_output=True, text=True, timeout=30, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    return result.stdout.split()[0] if result.returncode == 0 and result.stdout else None


def list_python_files(root):
    """Repo-relative paths of Python source files, core code first, tests/docs last."""
    root = Path(root)
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in filenames:
            path = Path(dirpath) / name
            if name.endswith(".py") and path.stat().st_size < MAX_FILE_BYTES:
                paths.append(path.relative_to(root).as_posix())
    return sorted(paths, key=lambda p: (bool(LOW_PRIORITY.search(p)), p.count("/"), p))


def _docline(node):
    doc = (ast.get_docstring(node) or "").strip()
    return doc.splitlines()[0][:160] if doc else ""


def _called_names(node):
    """Bare names of everything called inside `node` (foo(), obj.foo(), mod.sub.foo() all give 'foo')."""
    names = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                names.append(f.id)
            elif isinstance(f, ast.Attribute):
                names.append(f.attr)
    return list(dict.fromkeys(names))


def _dotted_calls(node):
    """Calls rendered as written (e.g. 'requests.get', 'json.dump'), used by the role classifier."""
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            try:
                out.append(ast.unparse(n.func))
            except Exception:
                pass
    return list(dict.fromkeys(out))[:60]


def _symbol(path, node, parent=None):
    is_class = isinstance(node, ast.ClassDef)
    name = f"{parent}.{node.name}" if parent else node.name
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    sym = {
        "id": f"{path}::{name}",
        "file": path,
        "name": name,
        "kind": "class" if is_class else ("method" if parent else "function"),
        "line": start,
        "end_line": node.end_lineno or node.lineno,
        "doc": _docline(node),
        "decorators": [ast.unparse(d) for d in getattr(node, "decorator_list", [])],
    }
    if is_class:
        sym["signature"] = f"class {node.name}" + (f"({', '.join(ast.unparse(b) for b in node.bases)})" if node.bases else "")
        sym["calls"] = []
        sym["dotted_calls"] = []
        sym["args"] = []
    else:
        sym["signature"] = f"def {node.name}({ast.unparse(node.args)})"
        sym["calls"] = _called_names(node)
        sym["dotted_calls"] = _dotted_calls(node)
        sym["args"] = [a.arg for a in node.args.args + node.args.kwonlyargs]
    return sym


def index_file(path, source):
    """Symbols of one file (top-level functions, classes and their methods) plus a module entry-point flag."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [], [], False
    symbols = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(_symbol(path, node))
        elif isinstance(node, ast.ClassDef):
            symbols.append(_symbol(path, node))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(_symbol(path, sub, parent=node.name))
    imports = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    has_main = bool(re.search(r"^if\s+__name__\s*==\s*['\"]__main__['\"]", source, re.M))
    script = script_statements(tree)
    if script:
        symbols.append(_module_symbol(path, script))
    return symbols, list(dict.fromkeys(imports)), has_main


def script_statements(tree):
    """Top-level statements that do work (calls, loops, `if __name__ == "__main__"`), not definitions or constants."""
    out = []
    for i, node in enumerate(tree.body):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue
        if i == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # module docstring
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and not any(isinstance(n, ast.Call) for n in ast.walk(node)):
            continue  # plain constants
        out.append(node)
    # A couple of stray calls (e.g. logging setup) are not a script.
    return out if len(out) >= 3 or any(isinstance(n, (ast.If, ast.For, ast.While, ast.With)) for n in out) else []


def _module_symbol(path, nodes):
    wrapper = ast.Module(body=nodes, type_ignores=[])
    return {
        "id": f"{path}::<script>",
        "file": path,
        "name": "<script>",
        "kind": "module",
        "line": nodes[0].lineno,
        "end_line": nodes[-1].end_lineno or nodes[-1].lineno,
        "doc": f"Top-level code that runs when {path.split('/')[-1]} is executed",
        "decorators": [],
        "signature": f"# top-level code of {path}",
        "calls": _called_names(wrapper),
        "dotted_calls": _dotted_calls(wrapper),
        "args": [],
    }


def build_call_edges(symbols):
    """Edges caller -> callee between repo symbols, matched on bare names (prefers same-file targets)."""
    by_name = {}
    for s in symbols:
        if s["kind"] != "class":
            by_name.setdefault(s["name"].split(".")[-1], []).append(s)
        else:
            by_name.setdefault(s["name"], []).append(s)
    edges, seen = [], set()
    for s in symbols:
        for called in s["calls"]:
            targets = by_name.get(called, [])
            if len(targets) > 1:
                same = [t for t in targets if t["file"] == s["file"]]
                targets = same or targets[:1]
            for t in targets[:1]:
                key = (s["id"], t["id"])
                if t["id"] != s["id"] and key not in seen:
                    seen.add(key)
                    edges.append({"source": s["id"], "target": t["id"]})
    return edges


def index_repo(root):
    """Index every Python file under `root`. Returns files (with content), symbols and call edges."""
    root = Path(root)
    paths = list_python_files(root)
    truncated = len(paths) > MAX_FILES
    files, symbols = [], []
    for rel in paths[:MAX_FILES]:
        content = (root / rel).read_text(encoding="utf-8", errors="replace")
        syms, imports, has_main = index_file(rel, content)
        files.append({"path": rel, "content": content, "imports": imports, "has_main": has_main})
        symbols.extend(syms)
    return {"files": files, "symbols": symbols, "calls": build_call_edges(symbols), "truncated": truncated}


def checkout_and_index(owner, repo, on_step=lambda step: None):
    """Clone into a temporary folder, index it plus build the parser summary for the report, and clean up."""
    from .parser import parse_codebase

    with tempfile.TemporaryDirectory(prefix="flowstate-") as tmp:
        dest = Path(tmp) / repo
        on_step("clone")
        branch, sha = clone_repo(owner, repo, dest)
        on_step("index")
        index = index_repo(dest)
        structure = parse_codebase(dest)
    # Core code first so the summary the model sees isn't spent on tests when it gets truncated.
    # Tests are left out too: they describe how the code is checked, not how data flows through it.
    order = {f["path"]: i for i, f in enumerate(index["files"])}
    core = [p for p in structure if p in order and not TEST_PATH.search(p)] or [p for p in structure if p in order]
    structure = {p: structure[p] for p in sorted(core, key=order.get)}
    return {"owner": owner, "repo": repo, "branch": branch, "sha": sha, "structure": structure, **index}
