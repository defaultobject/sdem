import pymongo

from . import sacred_manager
from . import util
from . import manager

import pandas as pd
import numpy as np

import tabulate
from functools import partial

import json

import copy

import warnings

from string import Template

import pathlib

def get_default_experiment_name():
    return str(pathlib.Path().absolute()).split('/')[-2]+'_runs'

def get_names_that_match_filter(all_configs, _dict):
    matched_names = []
    for key, config in all_configs.items():
        if manager.dict_is_subset(_dict, config):
            matched_names.append(key)
    return matched_names

def get_default_all_configs(experiment_name, model_root='../models', drop_fold=True):
    if drop_fold:
        keys_to_ignore = ['order_id', 'fold', 'fold_id', 'global_id', 'experiment_id']
    else:
        keys_to_ignore = ['order_id', 'global_id', 'experiment_id']

    def prep_config(config):
        _dict = {}

        for key, item in config.items():
            if key in keys_to_ignore: continue
            _dict['config.'+key] = item
        return _dict

    def name_generator_fn(config):
        name_str = []
        for key in config.keys():
            if key in keys_to_ignore: continue
            
            name_str.append('- {name}: {item}'.format(name=key, item=config[key]))

        return ' '.join(name_str)

        model = config['model']
        name = 'Model {model} Inference: {inference} correlation_matrix_init: {correlation_matrix_init}'.format(
            model=model,
            inference=inference,
            correlation_matrix_init=config['correlation_matrix_init']
        )
        return name

    all_configs = manager.get_configs_from_model_files(model_root=model_root)

    all_configs = {
        name_generator_fn(config): prep_config(config) for config in all_configs
    }

    return all_configs

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

table_fmt = r"""
\begin{tabular}{$coaligns}
\toprule
$top
\midrule
$data
\bottomrule
\end{tabular}
"""
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
    """
        gets results grouped additional_config_columns
    """
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

class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'

def get_table_top(df):
    levels =  df.columns.levels
    num_of_levels = len(df.columns.levels)
    level_sizes = [len(l) for l in df.columns.levels]
    total_num_columns = np.prod(level_sizes)
    column_names = df.columns.names

    indices = df.index.levels
    num_indices = len(indices)
    index_sizes = [len(l) for l in indices]

    extra_columns = [' ' for i in range(num_indices-1)]

    lines = []

    for level in range(num_of_levels):
        if level + 1 < num_of_levels:
            next_level_size = level_sizes[level+1]
            
            top_table = extra_columns+[column_names[level]]
            
            for col in levels[level]:
                top_table.append(' \multicolumn{size}{c}{name} '.format_map(
                    SafeDict(
                        size='{'+str(next_level_size)+'}',
                        name='{'+str(col)+'}'
                    )
                ))
            top_table = '&'.join(top_table)
            top_table += '\\\\'

            lines.append(top_table)
        else:
            top_table = extra_columns+[column_names[level]]

            for repeat in range(total_num_columns):
                v = levels[level][repeat % level_sizes[level]]
                top_table.append(
                    ' {v} '.format(v=v)
                )
            top_table = '&'.join(top_table)
            top_table += '\\\\'

            lines.append(top_table)

    #add row names

    row_labels = list(df.index.names) + [' ' for i in range(total_num_columns-1)]
    row_labels = '&'.join(row_labels) + '\\\\'

    lines.append(row_labels)

    return r'  '.join(lines)

def get_table_middle(df):
    levels =  df.columns.levels
    num_of_levels = len(df.columns.levels)
    level_sizes = [len(l) for l in df.columns.levels]
    total_num_columns = np.prod(level_sizes)
    column_names = df.columns.names

    indices = df.index.levels
    num_indices = len(indices)
    index_sizes = [len(l) for l in indices]

    lines = []
    for index, row in df.iterrows():
        total_row = []

        need_multi_row_flags = [False for i in range(num_indices)]
        
        #essentially a bin permuator
        for _i in range(num_indices-1, -1, -1):
            if _i == num_indices -1:
                need_multi_row_flags[_i] = True
            else:
                if index[_i+1] == indices[_i+1][0]:
                    if np.all(need_multi_row_flags[_i+1:]):
                        need_multi_row_flags[_i] = True
                

        for _i in range(num_indices):
            if need_multi_row_flags[_i]:
                next_level_size = np.prod(index_sizes[_i+1:])
                total_row.append( 
                    '\multirow{size}{*}{name}'.format_map(
                        SafeDict(
                            name='{'+str(index[_i])+'}',
                            size='{'+str(next_level_size)+'}'
                        )
                    )
                )
            else:
                if _i == num_indices-1:
                    total_row.append(str(index[_i]))
                else:
                    total_row.append(' ')

        total_row .append(' ')
        total_row = ' & '.join(total_row) + ' & '.join(np.array(row)) + ' \\\\'
        lines.append(total_row)

    return r' '.join(lines)

def tabulate_multi_level_dataframe_to_latex(df):
    levels =  df.columns.levels
    num_of_levels = len(df.columns.levels)
    level_sizes = [len(l) for l in df.columns.levels]
    total_num_columns = np.prod(level_sizes)
    column_names = df.columns.names

    indices = df.index.levels
    num_indices = len(indices)
    index_sizes = [len(l) for l in indices]


    top = get_table_top(df)
    middle = get_table_middle(df)

    total_columns = total_num_columns + num_indices 

    coaligns = ''.join(["c" for c in range(total_columns)])

    table = Template(table_fmt).substitute(
        coaligns=coaligns,
        top=top,
        data=middle,
    )
    return table

    


def get_ordered_table(experiment_name, metrics, group_by, results_by, num_folds=1, name_column='experiment_id', groups_order=None, results_order=None, groups_name_fn=None, results_name_fn=None, decimal_places=2, folds=None, return_raw=False, drop=None, drop_mean_std=True):
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
    warnings.warn('This uses data from the mongo database. Make sure you have synced your local files!')

    data_frames = []

    #store dataframe without mean and std combined
    raw_data_frames = []

    for m in metrics:
        metric_name = metric_name_format(m)
        results = get_results(experiment_name, [metric_name], [name_column]+group_by+results_by)

        data = []
        #we add data names as we are constructing the columns
        data_names = None
        append_data_name_flag=False

        for row in results:
            if data_names is None:
                data_names = []
                append_data_name_flag=True

            data_row = []

            fold_column = '{m}_folds'.format(m=m)

            folds = row[fold_column]

            if (len(folds) == 0) or (len(folds) > 1):
                raise RuntimeError('There shold be exactly one fold')

            data_row.append(row['_id']['experiment_id'])
            data_row.append(row['_id']['fold_id'])
            if append_data_name_flag:
                data_names.append('experiment_id')
                data_names.append('fold_id')

            for g in group_by:
                d = row['_id'][g]

                data_row.append(d)
                if append_data_name_flag:
                    data_names.append(g)

            for g in results_by:
                d = row['_id'][g]

                data_row.append(d)
                if append_data_name_flag:
                    data_names.append(g)

            fold_id = folds[0]['fold']
            fold_score = folds[0]['score']

            data_row.append(fold_id)
            data_row.append(fold_score)
            if append_data_name_flag:
                data_names.append('fold_i')
                data_names.append(m)

            data.append(data_row)

            append_data_name_flag=False

        df = pd.DataFrame(data, columns=data_names)
        #calculate the mean and std of each group
        df = df.groupby(group_by+results_by).agg({m: ['mean', 'std']})

        raw_df = df[m].copy()

        raw_df['{m}_mean'.format(m=m)] = raw_df['mean']
        raw_df['{m}_std'.format(m=m)] = raw_df['std']
        raw_df = raw_df.drop(columns=['mean', 'std'])

        raw_df.unstack(level=results_by)
        raw_data_frames.append(raw_df)

        def combine_mean_std(row):
            m_avg = row['mean']
            m_std = row['std']
            testing_m_avg = ("{:."+str(decimal_places)+"f}").format(m_avg)
            testing_m_std = ("{:."+str(decimal_places)+"f}").format(m_std)

            val = '{avg} $\pm$ {std}'.format(avg=testing_m_avg, std=testing_m_std)
            return val

        _df = df[m].copy()
        _df['{m}_score'.format(m=m)] = _df.apply(combine_mean_std, axis=1)
        if drop_mean_std:
            _df = _df.drop(columns=['mean', 'std'])

        _df = _df.unstack(level=results_by)


        #return _df
        data_frames.append(_df)

    df =  pd.concat(data_frames, axis=1)

    if return_raw:
        raw_df = pd.concat(raw_data_frames, axis=1)
        return df, raw_df
    else:
        return df



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

