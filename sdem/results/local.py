import os
import pickle
from ..computation import manager, sacred_manager
from .. import utils, template
import pandas as pd
import json
from loguru import logger
import typing
import numpy as np


def _flatten_dict(d):
    df = pd.json_normalize(d, sep="_")
    return df.to_dict(orient="records")[0]


def _get_last_checkpoints(d):
    _d = {}
    for key, item in d.items():
        _d[key] = d[key]["values"][-1]

    return _flatten_dict(_d)


def get_results_that_match_dict(_dict, exp_root, name_fn=None, squeeze=False):
    tmpl = template.get_template()

    if name_fn is None:
        name_fn = tmpl["result_name_fn"]

    model_folder = tmpl["model_dir"]
    exp_root = utils.ensure_backslash(exp_root)

    config_arr = manager.get_configs_from_model_files(
        model_root=exp_root + f"{model_folder}"
    )

    matched_configs = []
    matched_results = []

    for config in config_arr:
        if utils.dict_is_subset(_dict, config):
            config_results_name = name_fn(config)

            results_path = f"{exp_root}results/{config_results_name}.pickle"

            if os.path.exists(results_path):
                matched_configs.append(config)

                results = pickle.load(open(results_path, "rb"))
                matched_results.append(results)

    if len(matched_results) == 0:
        logger.info(f"No results found for {_dict}")
    if squeeze:
        if len(matched_results) == 1:
            matched_results = matched_results[0]
            matched_configs = matched_configs[0]
        else:
            if len(matched_results) > 1:
                logger.info("Cannot squeeze, too many results!")

    return matched_results, matched_configs


def index_of_match(elem, arr):
    for i, a in enumerate(arr):
        if elem == a:
            return i
    return None


def _get_results_df(exp_root, metrics, name_fn=None, metric_fn=None):
    """
    Only works for pickle data
    Collects every results
    """

    tmpl = template.get_template()

    if metric_fn is None:
        metric_fn = tmpl["results_metric_fn"]

    if name_fn is None:
        name_fn = tmpl["result_name_fn"]

    exp_root = utils.ensure_backslash(exp_root)

    configs = manager.get_configs_from_model_files(model_root=exp_root + "/models")

    # each config may have a different set of columns.metrics etc
    columns = []
    results_df = []

    for config in configs:
        config_results_name = name_fn(config)

        results_path = f"{exp_root}results/{config_results_name}.pickle"
        run_path = f"{exp_root}models/runs/{run_id}/"

        if os.path.exists(results_path):
            results = pickle.load(open(results_path, "rb"))
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

    return [
        pd.DataFrame(results_df[i], columns=columns[i]) for i in range(len(columns))
    ]


def get_results_df(exp_root, name_fn=None, metric_fn=None):
    """
    Only works for pickle data
    General Structure:
        - Goes through every sacred run folder
        - extracts config and metrics
        - construct resuts file name from config
        - load results
        - Aggregates and return
    """

    tmpl = template.get_template()

    if metric_fn is None:
        metric_fn = tmpl["results_metric_fn"]

    if name_fn is None:
        name_fn = tmpl["result_name_fn"]

    exp_root = utils.ensure_backslash(exp_root)

    runs_root = exp_root + "/models/runs"
    experiment_folders = sacred_manager.get_experiment_folders(runs_root)

    # each config may have a different set of columns.metrics etc
    columns = []
    results_df = []

    for run in experiment_folders:
        # load config and metrics
        with open(f"{runs_root}/{run}/config.json") as f:
            config = json.load(f)

        with open(f"{runs_root}/{run}/metrics.json") as f:
            metrics = json.load(f)

        if bool(metrics) == False:
            # metrics is empty
            logger.info(f"Skiping {run}")
            continue

        metrics = _get_last_checkpoints(metrics)

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

    return [
        pd.DataFrame(results_df[i], columns=columns[i]) for i in range(len(columns))
    ]


def flatten_and_rename_columns(df):
    flattened_columns = df.columns.to_flat_index()
    renamed_columns = []
    for t in flattened_columns:
        renamed_columns.append('_'.join(t))
    df.columns = renamed_columns
    return df

def filter_dataframe_by_dict(df, d):
    dict_df = pd.DataFrame.from_dict(d)

    df = pd.merge(df, dict_df, how='outer', on=list(dict_df.columns), indicator=True)
    df = df.query('_merge != "both"')

    return df.drop('_merge', axis=1)

def filter_results(ordered_df, drop_by):
    #get all combinations of drop_by dictionaries
    _filters = []
    for d in drop_by:
        _filters.append(utils.get_all_permutations(d))

    _df = ordered_df
    for d in _filters:
        _df = filter_dataframe_by_dict(_df, d)

    return _df

def select_dataframe_by_dict(df, d):
    dict_df = pd.DataFrame.from_dict(d)

    df = pd.merge(df, dict_df, how='inner', on=list(dict_df.columns))

    return df

def select_results(ordered_df, selected_by):
    """Filter ordered_df by selected rows that match selected_by."""
    #get all combinations of selected_by dictionaries
    _filters = []
    for d in selected_by:
        _filters.append(utils.get_all_permutations(d))

    #a list of filters acts and as OR
    df_arr = []
    for d in _filters:
        _df = select_dataframe_by_dict(ordered_df, d)
        df_arr.append(_df)

    return pd.concat(df_arr, axis=0)

def combine_mean_std(row, metric, decimal_places):
    m_avg = row[f'{metric}_mean']
    m_std = row[f'{metric}_std']
    testing_m_avg = ("{:."+str(decimal_places)+"f}").format(m_avg)
    testing_m_std = ("{:."+str(decimal_places)+"f}").format(m_std)

    val = '{avg} $\pm$ {std}'.format(avg=testing_m_avg, std=testing_m_std)
    return val


def get_ordered_table(
    exp_root,
    metrics: typing.List[str],
    group_by: typing.Optional[typing.List[str]] = None,
    decimal_places=2,
    select_filter: typing.Optional[typing.List[dict]] = None,
    drop_filter: typing.Optional[typing.List[dict]] = None,
    combine=False,
    flatten=False,
    name_fn=None,
    metric_fn=None
):
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

    all_results_df = get_results_df(exp_root, name_fn=name_fn, metric_fn=metric_fn)
    
    ordered_dfs =[]
    for results_df in all_results_df:
        #create agg_dict
        agg_dict = {}
        for m in metrics:
            agg_dict[m] = ['mean', 'std']

        if group_by is not None:
            #ensure that none of the group by columns are unhashable
            for g in group_by:
                if results_df[g].apply(pd.api.types.is_hashable).all() == False:
                    #g is not hashable
                    results_df[g] = results_df[g].apply(str)

            _ordered_df = results_df.groupby(group_by).agg(agg_dict)

        else:
            _ordered_df = results_df

        ordered_dfs.append(_ordered_df)

    if combine:
        ordered_df = pd.concat(ordered_dfs, axis=0)

        if flatten:
            ordered_df = flatten_and_rename_columns(ordered_df)
            ordered_df.reset_index(level=ordered_df.index.names, inplace=True)

            if drop_filter:
                ordered_df = filter_results(ordered_df, drop_filter)

            if select_filter:
                ordered_df = select_results(ordered_df, select_filter)

            for m in metrics:
                ordered_df[f'{m}_score'] = ordered_df.apply(lambda row: combine_mean_std(row, m, decimal_places), axis=1)
                ordered_df = ordered_df.drop([f'{m}_mean', f'{m}_std'], axis=1)
            
        return ordered_df
    else:
        for ordered_df in ordered_dfs:
            print(ordered_df)

    return None
