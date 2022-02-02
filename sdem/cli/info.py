from ..computation import manager

import typer

import rich
from rich.table import Table

model_app = typer.Typer()
results_app = typer.Typer()


@model_app.command()
def list(ctx: typer.Context):
    state = ctx.obj

    # Collect paths to all experiment files
    model_files = manager.get_model_files(state, model_root=None)

    # Convert to rich table
    table = Table(show_header=True)
    table.add_column(f'Found {len(model_files)} model files')

    for m in model_files:
        table.add_row(str(m))

    state.console.print()
    state.console.print(table)
