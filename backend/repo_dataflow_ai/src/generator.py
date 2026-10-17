"""Constructs code prompts and writes the dataflow output."""

from pathlib import Path

from .parser import format_structure

SYSTEM_PROMPT = """You are a senior software architect. You will be given a structural summary of a \
Python repository: for each file, its imports, module-level assignments, function signatures and classes.

Describe how data flows through the repository as a clear, numbered, step-by-step explanation:
1. Identify the entry point(s) where execution starts and where input data comes from.
2. Trace how data moves between files and functions, naming the specific modules and functions involved.
3. Note where data is transformed, stored, or handed to external libraries or services.
4. Finish with where the final output ends up.

Base your answer only on the summary. If something cannot be determined from it, say so instead of guessing."""

USER_TEMPLATE = """Here is the repository structure summary:

{summary}

Describe the repository's dataflow step by step."""

# Keeps the prompt well inside a small model's context window (roughly 6k tokens).
MAX_SUMMARY_CHARS = 24_000


def build_prompt(summary):
    """Turn a parsed summary (dict from parse_codebase, or its formatted string) into the user prompt."""
    if isinstance(summary, dict):
        summary = format_structure(summary)
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[:MAX_SUMMARY_CHARS] + "\n# ... (summary truncated)"
    return USER_TEMPLATE.format(summary=summary)


def generate_dataflow(engine, summary, max_new_tokens=1024):
    """Ask the model for a step-by-step dataflow description of the summarised repository."""
    return engine.generate(build_prompt(summary), system=SYSTEM_PROMPT, max_new_tokens=max_new_tokens)


def write_output(text, output_path):
    """Write the generated description to `output_path`, creating parent folders as needed."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path
