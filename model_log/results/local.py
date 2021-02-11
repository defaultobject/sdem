import os
import pickle
from ..computation import manager
from .. import utils
import pandas as pd

def _flatten_dict(d):
    df =  pd.json_normalize(d, sep='_')
    return df.to_dict(orient='records')[0]


def get_results_df(exp_root, metrics, name_fn, metric_fn=None):
    """
        Only works for pickle data
        Collects every results
    """


    if metric_fn is None:
        metric_fn = lambda res_dict: res_dict['metrics']

    exp_root = utils.ensure_backslash(exp_root)

    configs = manager.get_configs_from_model_files(model_root = exp_root+'/models')

    config_columns = None
    metric_columns = None
    columns = None

    results_df = []

    for config in configs:
        config_results_name = name_fn(config)

        results_path = f'{exp_root}results/{config_results_name}.pickle'

        if os.path.exists(results_path):
            results = pickle.load(open(results_path, "rb" ))
            metrics = metric_fn(results)
            metrics = _flatten_dict(metrics)

            if config_columns is None:
                config_columns = list(config.keys())
                metric_columns = list(metrics.keys())
                columns = config_columns + metric_columns

            row = list(config.values()) + list(metrics.values())

            if len(row) == len(columns):
                results_df.append(row)


    return pd.DataFrame(results_df, columns=columns)


def get_ordered_table(experiment_name, metrics, group_by, results_by, num_folds=1, name_column='experiment_id', groups_order=None, results_order=None, groups_name_fn=None, results_name_fn=None, decimal_places=2, folds=None, return_raw=False, drop=None, drop_mean_std=True, metric_scale=None):
    """
        Args:
            input_df: dataframe to turn into a structured table
            group_by: list of columns/keys that define the distinct groups to average results over (rows of table)
            results_by: list of columns to get the average of. (columns of table)
            groups_order: how to order the rows of the table
            results_order: how to order the columns of the table
            groups_name_fn: function to label the rows of the table
            results_name_fn: function to label the columns of the table
            drop: array of dictionaries to drop results by
            
    """
    pass


