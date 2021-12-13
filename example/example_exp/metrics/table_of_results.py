import sdem
from sdem.results.local import get_ordered_table, get_results_that_match_dict
import tabulate
from pathlib import Path

results_df = get_ordered_table(
    '../',
    metrics=['train_rmse', 'test_rmse'],
    group_by=[
        'name', 
    ],
    results_by=[''],
    combine=True,
    flatten=True,
)

print(tabulate.tabulate(results_df, headers=results_df.columns))

results_df = get_ordered_table(
    '../',
    metrics=['train_rmse', 'test_rmse'],
    group_by=[
        'name', 
    ],
    results_by=['fold'],
    combine=True,
    flatten=True,
)

print(tabulate.tabulate(results_df, headers=results_df.columns))

