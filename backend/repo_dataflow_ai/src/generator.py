"""Constructs code prompts and writes the dataflow output."""

from pathlib import Path

from .parser import format_structure

SYSTEM_PROMPT = """You are a senior software architect. You will be given a structural summary of a \
Python repository: for each file, its imports, module-level assignments, function signatures and classes.

Describe how data flows through the repository as a numbered walkthrough of 4 to 8 steps, in the order the \
data moves: from the entry point(s) and where input comes from, through where it is transformed, stored or handed \
to external libraries or services, to where the final output ends up.

Write each step as one list item in this form:
1. **<Short verb-first title of this step>**: what happens to the data, naming the specific \
`file.py` and `function()` or `Class` involved.

For a library with no single entry point, follow the main public API call a user would make.
After the list, add one short paragraph summarising the overall flow.

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
