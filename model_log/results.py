import pymongo

from . import sacred_manager
from . import util

import pandas as pd
import numpy as np

import tabulate
from functools import partial

import json

import copy

import warnings

#"latex_booktabs_raw"
latex_booktabs_raw_format = tabulate.TableFormat(lineabove=partial(tabulate._latex_line_begin_tabular, booktabs=True),
          linebelowheader=tabulate.Line("\\midrule", "", "", ""),
          linebetweenrows=None,
          linebelow=tabulate.Line("\\bottomrule\n\\end{tabular}", "", "", ""),
          headerrow=partial(tabulate._latex_row, escrules={}),
          datarow=partial(tabulate._latex_row, escrules={}),
          padding=1, with_header_hide=None)


metric_name_format = lambda m: '$metrics.{m}.values'.format(m=m)
training_metric_name = lambda m: '$metrics.training_{m}.values'.format(m=m)
testing_metric_name = lambda m: '$metrics.testing_{m}.values'.format(m=m)

def get_unwinds(metrics):
    """
        In sacred each of the metrics are stored in an array. We need to go through and flatten them / unwind them.
    """
    unwind_pipeline = []
    for m in metrics:
        unwind_pipeline.append({ '$unwind': m })

    return unwind_pipeline

def get_group(metrics, additional_config_columns):
    """
        Group looks like:
            { 
                '$group': { 
                    '_id': {
                        'fold_id': '$config.fold_id',
                        'filename': '$config.filename',
                        'name': '$name'
                    },
                    '_avg': {
                        '$avg': metric_name,
                    },
                    '_std_samp': {
                        '$stdDevSamp': metric_name,
                    },
                    '_std_pop': {
                        '$stdDevPop' : metric_name,
                    },
                    '_count': {
                        '$sum': 1,
                    },
                    '_total': {
                        '$avg': metric_name,
                    },
                   'folds': {
                        '$push': {
                            'fold': '$config.fold',
                            'score': metric_name
                        }
                   },

                }
            }
        this function constructs this dict for a generic number of metrics and a generic number of additional columns
    """
    group_field = {}


    id_field = {
        'fold_id': '$config.fold_id',
        'filename': '$config.filename',
    }

    for n in additional_config_columns:
        id_field[n] = '$config.{n}'.format(n=n)


    group_field['_id'] = id_field


    for m in metrics:
        training_name = m
        training_name_no_dollar = m.split('.')[1] #metric name is of the form config.m.values, we only want to extract m

        group_field['{n}_avg'.format(n=training_name_no_dollar)] = {
                '$avg': '{m}'.format(m=training_name)
        }

        group_field['{n}_std_pop'.format(n=training_name_no_dollar)] = {
                '$stdDevPop': '{m}'.format(m=training_name)
        }

        group_field['{n}_std_samp'.format(n=training_name_no_dollar)] = {
                '$stdDevSamp': '{m}'.format(m=training_name)
        }

        group_field['{n}_count'.format(n=training_name_no_dollar)] = {
                '$sum': 1
        }

        group_field['{n}_folds'.format(n=training_name_no_dollar)] = {
            '$push': {
                'fold': '$config.fold',
                'score': training_name
            }
        }


    return [{'$group': group_field}]



def get_results(experiment_name, metrics,additional_config_columns ):
    collection = sacred_manager.get_collection(experiment_name)
    pipeline = [
        {
            '$project': {
                '_id': 1,
                'config': 1,
                'metrics': 1
            }
        }
    ]
    pipeline = pipeline + get_unwinds(metrics)

    pipeline = pipeline + get_group(metrics, additional_config_columns)
    results = list(collection.aggregate(pipeline))
    return results



def dict_print(_dict):
    print(json.dumps(
        _dict,
        sort_keys=True,
        indent=4,
        separators=(',', ': ')
    ))

def sort_folds(folds):
    sort_array = [s['fold'] for s in folds] 
    sort_args = np.argsort(sort_array)
    return [folds[s] for s in sort_args]

def max_folds(results, folds_column):
    #not all experiments will have data for all folds, so get the max number of folds
    num_folds = [len(d[folds_column]) for d in results]
    return max(num_folds)

def tabulate_table(df, latex=False, showindex=False):
    columns = df.columns
    if latex:
        coaligns = ["center" for c in df.columns]
        print(tabulate.tabulate(df, headers=columns, tablefmt=latex_booktabs_raw_format, showindex=showindex, colalign=coaligns))
    else:
        print(tabulate.tabulate(df, headers=columns, showindex=showindex))

def get_table_per_metric_with_folds(experiment_name, metrics, name_column, additional_columns=None, additional_columns_headers = None, models=None, decimal_places=2, print_latex=False, print_table=True):
    warnings.warn('This uses data from the mongo database. Make sure you have synced your local files!')
    dataframes = []

    if additional_columns is None:
        additional_columns = []
        additional_columns_headers = []

    for m in metrics:
        metric_name = metric_name_format(m)
        results = get_results(experiment_name, [metric_name], [name_column]+additional_columns)

        data = []
        name_columns = [ 'Name' ] 
        fold_col = '{m}_folds'.format(m=m)
        fold_columns = list(range(max_folds(results, fold_col))) 
        aggregated_columns = [ 
            '{m} AVG'.format(m=m), 
            '{m} STD'.format(m=m)
        ]

        for col in results:

            name = col['_id'][name_column]

            additional_data = []
            for n in additional_columns:
                additional_data.append(col['_id'][n])

            testing_m_avg = col['{m}_avg'.format(m=m)]
            testing_m_std = col['{m}_std_pop'.format(m=m)]

            folds = col[fold_col]
            folds = sort_folds(folds)

            fold_scores = []
            #folds are now in order of folds so we can just loop thorugh
            for i in fold_columns:
                #get fold
                fold_idx = None
                for _i, f in enumerate(folds):
                    if f['fold'] == i:
                        fold_idx = _i


                if fold_idx is None:
                    fold_scores.append('N/A')
                else:
                    score = folds[fold_idx]['score']
                    score = ("{:."+str(decimal_places)+"f}").format(score)

                    fold_scores.append(score)

            testing_m_avg = ("{:."+str(decimal_places)+"f}").format(testing_m_avg)
            testing_m_std = ("{:."+str(decimal_places)+"f}").format(testing_m_std)

            data.append([name]+additional_data+ fold_scores+[ testing_m_avg, testing_m_std])

        columns = name_columns+additional_columns_headers+fold_columns+aggregated_columns

        df = pd.DataFrame(data, columns=columns)

        if models:
            df = df.set_index('Name').loc[models].reset_index()
        
        dataframes.append(df)

        if print_table:
            tabulate_table(df, latex=print_latex)
   
    return dataframes

def get_table_with_metrics(experiment_name, metrics, name_column, models=None,combine_mean_and_std=True, decimal_places=2, print_latex=False):
    """
        If models then only return results from models in preserved order

    """
    warnings.warn('This uses data from the mongo database. Make sure you have synced your local files!')
    data_columns = ['Name']


    for m in metrics:
        if combine_mean_and_std:
            data_columns.append(m)
        else:
            data_columns.append('AVG {m}'.format(m=m))
            data_columns.append('STD {m}'.format(m=m))

    data = {}

    for m in metrics:
        metric_value_name_in_db = metric_name_format(m)
        results = get_results(experiment_name, [metric_value_name_in_db], [name_column])

        #go through returns rows. Should only be one returned.
        for col in results:
            name = col['_id'][name_column]
            data_row = []

            col_avg = '{m}_avg'.format(m=m)
            col_std = '{m}_std_pop'.format(m=m)

            m_avg = col[col_avg]
            m_std = col[col_std]

            if m_avg is None:
                print('Metric {m} with column {name} not found'.format(m=m, name=col_avg))
                continue

            if m_std is None:
                print('Metric {m} with column {name} not found'.format(m=m, name=col_std))
                continue

            testing_m_avg = ("{:."+str(decimal_places)+"f}").format(m_avg)
            testing_m_std = ("{:."+str(decimal_places)+"f}").format(m_std)

            if combine_mean_and_std:
                val = '{avg} $\pm$ {std}'.format(avg=testing_m_avg, std=testing_m_std)

                data_row.append(val)
            else:
                data_row.append(testing_m_avg)
                data_row.append(testing_m_std)

            if name not in data.keys():
                data[name] = data_row
            else:
                data[name] = data[name] + data_row 

    df = pd.DataFrame.from_dict(data, orient='index')
    if models:
        df = df.loc[models]
    df.reset_index(level=0, inplace=True)
    df.columns = data_columns

    tabulate_table(df, latex=print_latex)

    return df


def get_results_for_best_group(experiment_name: str, group_configs: dict, metric_id, metrics, fold_id, use_max=True):
    group_configs = copy.deepcopy(group_configs)
    group_fold_ids = sacred_manager.get_fold_ids_that_match_config(
        experiment_name,
        group_configs
    )
    
    dataframes = get_table_per_metric_with_folds(experiment_name, metrics, 'fold_id', print_table=False);
    _df = dataframes[metric_id]
    
    metric_name = metrics[metric_id]

    experiment_to_plot = {}
    for k in group_fold_ids.keys():
        _filtered_df = _df[_df['Name'].isin(group_fold_ids[k])]
        if _filtered_df.empty:
            print('Nothing matched group: ', group_fold_ids[k])
            print('Continuing!')
            continue

        col_name = '{metric_name} AVG'.format(metric_name=metric_name)
        _filtered_df[col_name] = pd.to_numeric(_filtered_df[col_name])
        if use_max:
            experiment_to_plot[k] = _filtered_df.loc[_filtered_df[col_name].idxmax()]['Name']
        else:
            experiment_to_plot[k] = _filtered_df.loc[_filtered_df[col_name].idxmin()]['Name']
    
    #now we have the fold_ids we need to find the experiment ids
    config = group_configs.copy()
    #we only want to include configs that we can match
    _config = {}
    for k in group_fold_ids.keys():
        if k not in experiment_to_plot.keys():
            print('Could not find experiment: ', k, ' -- continuing!')
            continue

        _config[k] =  config[k]
        _config[k]['config.fold'] = fold_id
        _config[k]['config.fold_id'] = experiment_to_plot[k]
        
    experiments = sacred_manager.match_config_filters_to_experiment_ids(experiment_name,_config)
    return experiments

def get_configs_of_experiment_ids(experiment_name: str, experiment_ids):
    _configs = []
    for _id in experiment_ids:
        _filter = {'config.experiment_id': _id}
        row = sacred_manager.get_sacred_columns_of_experiement_filter(experiment_name, _filter)
        print(_filter)
        print(len(row))
        if len(row) == 0:
            print('experiment id {_id} not found. ignoring!'.format(_id=_id))
            continue

        if len(row) > 1:
            print('experiment id {_id} should be unique. ignoring!'.format(_id=_id))
            continue

        row = row[0]['config']
        _configs.append(row)
    return _configs

