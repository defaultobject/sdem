import os
import pickle
from ..computation import manager
from .. import utils, template
import pandas as pd

def _flatten_dict(d):
    df =  pd.json_normalize(d, sep='_')
    return df.to_dict(orient='records')[0]

def get_results_that_match_dict(_dict, exp_root, name_fn = None):
    tmpl = template.get_template()

    if name_fn is None:
        name_fn = tmpl['result_name_fn']

    model_folder = tmpl['model_dir']
    exp_root = utils.ensure_backslash(exp_root)

    config_arr = manager.get_configs_from_model_files(model_root = exp_root+f'{model_folder}')

    matched_configs = []
    matched_results = []

    for config in config_arr:
        if utils.dict_is_subset(_dict, config):
            config_results_name = name_fn(config)

            results_path = f'{exp_root}results/{config_results_name}.pickle'

            if os.path.exists(results_path):
                matched_configs.append(config)

                results = pickle.load(open(results_path, "rb" ))
                matched_results.append(results)

    return matched_results, matched_configs


def index_of_match(elem, arr):
    for i, a in enumerate(arr):
        if elem == a:
            return i
    return None

def get_results_df(exp_root, metrics, name_fn=None, metric_fn=None):
    """
        Only works for pickle data
        Collects every results
    """


    tmpl = template.get_template()

    if metric_fn is None:
        metric_fn = tmpl['results_metric_fn']

    if name_fn is None:
        name_fn = tmpl['result_name_fn']

    exp_root = utils.ensure_backslash(exp_root)

    configs = manager.get_configs_from_model_files(model_root = exp_root+'/models')

    #each config may have a different set of columns.metrics etc
    columns = []
    results_df = []


    for config in configs:
        config_results_name = name_fn(config)

        results_path = f'{exp_root}results/{config_results_name}.pickle'

        if os.path.exists(results_path):
            results = pickle.load(open(results_path, "rb" ))
            metrics = metric_fn(results)
            metrics = _flatten_dict(metrics)

            config_columns = list(config.keys())
            metric_columns = list(metrics.keys())
            column_names = config_columns + metric_columns

            config_index = index_of_match(column_names, columns)

            if config_index is None:
                columns.append(column_names)

            row = list(config.values()) + list(metrics.values())

            if config_index is None:
                results_df.append([row])
            else:
                results_df[config_index].append(row)


    return [pd.DataFrame(results_df[i], columns=columns[i]) for i in range(len(columns))]


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


