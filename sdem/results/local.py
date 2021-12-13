""" Helper function for extracting results and metrics from an sdem experiment. """
import os
import pickle
from ..computation import manager, sacred_manager, startup
from .. import utils, template
import pandas as pd
import json
from loguru import logger
import typing
import numpy as np
from pathlib import Path

from typing import List, Tuple

def _flatten_checkpoint_dict(d):
    df = pd.json_normalize(d, sep="_")
    return df.to_dict(orient="records")[0]

def _get_last_checkpoints(d):
    _d = {}
    for key, item in d.items():
        _d[key] = d[key]["values"][-1]

    return _flatten_checkpoint_dict(_d)

def get_results_that_match_dict(_dict: dict, exp_root: Path, squeeze: bool = False) -> Tuple[dict, dict]:
    """

    """
    # Ensure root is a path 
    exp_root = Path(exp_root)

    # load experiment configs
    experiment_config = startup.load_config(exp_root=exp_root)

    # Load all configs

    model_path = manager.get_models_folder_path(experiment_config, exp_root=exp_root)

    config_arr = manager.get_configs_from_model_files(
        experiment_config,
        model_root= model_path
    )

    # For configs that match filter load the corresponding results pickle file
    matched_configs = []
    matched_results = []

    result_pattern = manager.get_results_output_pattern(experiment_config)
    results_path = manager.get_results_path(experiment_config, exp_root=exp_root)

    for config in config_arr:
        if utils.dict_is_subset(_dict, config):

            results_file = manager.substitute_config_in_str(
                result_pattern,
                config
            )

            res_file = results_path / results_file

            if res_file.exists():

                # Read pickle and save config
                matched_configs.append(config)
                results = pickle.load(open(res_file, "rb"))
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

def get_run_configs(exp_root):
    runs_root = str(Path(exp_root) / 'models' / 'runs')
    experiment_folders = sacred_manager.get_sacred_experiment_folders(runs_root)
    config_list = []
    for run in experiment_folders:
        # load config and metrics
        with open(f"{runs_root}/{run}/config.json") as f:
            config = json.load(f)
        config_list.append(config)

    return config_list

def get_results_df(exp_root: Path):
    """
    General Structure:
        - Goes through every sacred run folder
        - extracts config and metrics
        - construct resuts file name from config
        - load results
        - Aggregates and return

    Notes:
        If there are multiple checkpoints then the last one is used
    """

    # load experiment configs
    experiment_config = startup.load_config(exp_root=exp_root)

    # Get sacred runs path
    runs_root = manager.get_sacred_runs_path(experiment_config, exp_root=exp_root)

    # Get all folders that are correspond to sacred runs
    experiment_folders = sacred_manager.get_sacred_experiment_folders(runs_root)

    # each config may have a different set of columns.metrics etc 
    # So we group together all configs that have the same columns and metrics
    # Each item of these lists correspond to another group
    columns = []
    results_df = []

    for run in experiment_folders:
        # load config and metrics
        with open(runs_root / run / 'config.json') as f:
            config = json.load(f)

        with open(runs_root / run / "metrics.json") as f:
            metrics = json.load(f)

        if bool(metrics) == False:
            # metrics is empty
            logger.info(f"Skiping {run} because metrics is empty")
            continue

        # When there are multiply checkpoints we use the last one
        metrics = _get_last_checkpoints(metrics)

        # Get config and metrics columns so we can find which group to add to 
        config_columns = list(config.keys())
        metric_columns = list(metrics.keys())
        column_names = config_columns + metric_columns

        # Find group index
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
    """ Merge mean and std column into a form like mean \pm std with mean and std rounded to a given decimal places. """
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
    results_by = None,
    decimal_places=2,
    select_filter: typing.Optional[typing.List[dict]] = None,
    drop_filter: typing.Optional[typing.List[dict]] = None,
    combine=False,
    flatten=False,
    metric_fn=None,
    scale: typing.Optional[dict]=None,
    verbose=False
):
    """
    Constructs a table of results from an sdem experiment. This supports finding mean and standard deviations over a given group (i.e folds).

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

    exp_root = Path(exp_root)

    if results_by:
        if group_by:
            group_by = group_by + results_by
        else:
            group_by = results_by

    # Load results for all experiments
    # Each element of the list corresponds to separate table 
    all_results_df = get_results_df(exp_root)

    
    # Create one table for each group of configs found in all_results_df
    ordered_dfs =[]
    for results_df in all_results_df:
        if verbose:
            print(results_df.keys())

        # create actions to apply over a grouped table
        agg_dict = {}
        for m in metrics:
            agg_dict[m] = ['mean', 'std']

        if group_by is not None:
            #ensure that none of the group by columns are unhashable
            for g in group_by:
                if results_df[g].apply(pd.api.types.is_hashable).all() == False:
                    #g is not hashable
                    results_df[g] = results_df[g].apply(str)

            if scale is not None:
                for m in metrics:
                    if m in scale.keys():
                        results_df[m] = results_df[m]*scale[m]

            # Apply agg_dict over the found groups
            _ordered_df = results_df.groupby(group_by).agg(agg_dict)

        else:
            # There are no folds/groups to average over
            _ordered_df = results_df

        ordered_dfs.append(_ordered_df)

    if combine:
        ordered_df = pd.concat(ordered_dfs, axis=0)

        if flatten:
            # Ordered df is a multi-layered pandas Dataframe
            #  We reduces it to a single layer and combine mean and std columns into a single

            ordered_df = flatten_and_rename_columns(ordered_df)
            ordered_df.reset_index(level=ordered_df.index.names, inplace=True)

            # Remove rows by drop_filter
            if drop_filter:
                ordered_df = filter_results(ordered_df, drop_filter)

            # Only keep rows that match select_filter
            if select_filter:
                ordered_df = select_results(ordered_df, select_filter)

            #
            for m in metrics:
                # For each metric combine the mean and std into a form like `mean \pm std`
                ordered_df[f'{m}_score'] = ordered_df.apply(
                    lambda row: combine_mean_std(row, m, decimal_places), 
                    axis=1
                )
                # Remove mean and std only columns
                ordered_df = ordered_df.drop([f'{m}_mean', f'{m}_std'], axis=1)
            
        return ordered_df
    else:
        return ordered_dfs
