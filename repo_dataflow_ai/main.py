"""CLI entry point."""

from pathlib import Path

import click

from src.generator import generate_dataflow, write_output
from src.parser import parse_codebase


@click.command()
@click.option(
    "--repo-path",
    required=True,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Folder of the repository to analyse.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    help="File to save the dataflow report to. Prints to the terminal if omitted.",
)
def main(repo_path, output):
    """Generate a step-by-step dataflow report for the Python repository at --repo-path."""
    click.echo(f"Parsing {repo_path} ...", err=True)
    summary = parse_codebase(repo_path)
    if not summary:
        raise click.ClickException(f"No .py files found in {repo_path}")
    click.echo(f"Found {len(summary)} Python files.", err=True)

    # Imported here so --help and argument errors respond instantly instead of waiting for torch to load.
    from src.model_engine import ModelEngine

    click.echo("Loading model (the first run downloads the weights) ...", err=True)
    engine = ModelEngine()

    click.echo("Generating dataflow report ...", err=True)
    report = generate_dataflow(engine, summary)

    if output:
        path = write_output(report, output)
        click.echo(f"Report saved to {path}", err=True)
    else:
        click.echo(report)


if __name__ == "__main__":
    main()
