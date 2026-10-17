"""Extract a structural summary (imports, functions, classes, assignments) of a Python codebase."""

import ast
import json
import os
from pathlib import Path

import click

SKIP_DIRS = {"__pycache__", "venv", "env", "node_modules", "build", "dist", "site-packages"}
MAX_VALUE_LEN = 80


def _truncate(text, limit=MAX_VALUE_LEN):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _signature(node):
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    sig = f"{prefix} {node.name}({ast.unparse(node.args)})"
    if node.returns:
        sig += f" -> {ast.unparse(node.returns)}"
    return sig


def _assignment(node):
    if isinstance(node, ast.Assign):
        targets = " = ".join(ast.unparse(t) for t in node.targets)
        return f"{targets} = {_truncate(ast.unparse(node.value))}"
    line = f"{ast.unparse(node.target)}: {ast.unparse(node.annotation)}"
    if node.value is not None:
        line += f" = {_truncate(ast.unparse(node.value))}"
    return line


def parse_file(path):
    """Return the imports, functions, classes and module-level assignments of one file."""
    source = Path(path).read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return {"error": f"SyntaxError: {exc.msg} (line {exc.lineno})"}

    # Imports can appear anywhere (inside functions, try blocks, TYPE_CHECKING), so walk the whole tree.
    imports = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    info = {
        "imports": list(dict.fromkeys(imports)),
        "functions": [],
        "classes": [],
        "assignments": [],
    }

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            info["functions"].append(_signature(node))
        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases)
            info["classes"].append({
                "name": f"class {node.name}({bases})" if bases else f"class {node.name}",
                "methods": [
                    _signature(n) for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ],
            })
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            info["assignments"].append(_assignment(node))
    # Scripts do their work at module level; list what that code calls so the model can follow it.
    script_calls = [
        ast.unparse(n.func) for stmt in tree.body
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))
        for n in ast.walk(stmt) if isinstance(n, ast.Call)
    ]
    info["script_calls"] = list(dict.fromkeys(script_calls))[:40]
    return info


def parse_codebase(root):
    """Walk `root` recursively and map each .py file's relative path to its parsed structure."""
    root = Path(root).resolve()
    structure = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune in place so os.walk never descends into virtualenvs, caches or hidden folders.
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for name in sorted(filenames):
            if name.endswith(".py"):
                path = Path(dirpath) / name
                structure[path.relative_to(root).as_posix()] = parse_file(path)
    return structure


def format_structure(structure):
    """Render the parsed structure as one combined, readable string."""
    lines = []
    for path, info in structure.items():
        lines.append(f"# File: {path}")
        if "error" in info:
            lines.append(f"# !! {info['error']}")
        else:
            lines.extend(info["imports"])
            lines.extend(info["assignments"])
            lines.extend(info["functions"])
            for cls in info["classes"]:
                lines.append(cls["name"])
                lines.extend(f"    {method}" for method in cls["methods"])
            if info.get("script_calls"):
                lines.append(f"# top-level code calls: {', '.join(info['script_calls'])}")
        lines.append("")
    return "\n".join(lines)


@click.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output the raw dictionary as JSON.")
def main(folder, as_json):
    """Print the structure of every .py file under FOLDER."""
    structure = parse_codebase(folder)
    click.echo(json.dumps(structure, indent=2) if as_json else format_structure(structure))


if __name__ == "__main__":
    main()
