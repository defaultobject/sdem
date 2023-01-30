""" Helper functions to predicting and computing metrics using sdem """

import numpy as np
import pandas as pd
from ..computation.metrics import log_regression_scalar_metrics, log_binary_scalar_metrics
from rich.console import Console

console = Console()

def collect_results_for_dataset(ex, model, data, dataset_name, prediction_fn, returns_ci, data_type):
    XS = data['X']

    YS = None

    if 'Y' in data.keys():
        YS = data['Y']

    metrics = {}

    if returns_ci:
        median, ci_lower, ci_upper = prediction_fn(XS)
        median = np.array(median)
        ci_lower = np.array(ci_lower)
        ci_upper = np.array(ci_upper)

        predictions = {
            'median': median,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper
        }

        pred_mu = median
    else:
        pred_mu, pred_var = prediction_fn(XS)
        pred_mu = np.array(pred_mu)
        pred_var = np.array(pred_var)

        predictions = {
            'mu': pred_mu,
            'var': pred_var
        }

    # Log metrics for each output
    if YS is not None:
        # Use min of predicition and Y so that we just compute metrics on which outputs are provided
        P = min(pred_mu.shape[0], YS.shape[1])

        for p in range(P):
            metric_name = f'{dataset_name}_{p}'

            if data_type == 'regression':
                metrics_p = log_regression_scalar_metrics(
                        ex, YS[:, p], pred_mu[p], log=True, prefix=metric_name
                )
            elif data_type == 'binary':
                metrics_p = log_binary_scalar_metrics(
                        ex, YS[:, p], pred_mu[p], log=True, prefix=metric_name
                )
            else:
                raise RuntimeError()

            metrics[metric_name] = metrics_p

    return predictions, metrics

def collect_results(ex, model, pred_fn, pred_data:dict, returns_ci: bool = False, training_time=None, data_type='regression'):
    results = {}

    results = {}
    results['metrics'] = {}
    results['predictions'] = {}

    for dataset_name in pred_data.keys():
        console.rule(f'Predicting on {dataset_name}')

        dataset_predictions, dataset_metrics = collect_results_for_dataset(
            ex,
            model,
            pred_data[dataset_name],
            dataset_name,
            pred_fn,
            returns_ci,
            data_type
        )

        # Log results
        results['predictions'][dataset_name] = dataset_predictions
        # combine dicts
        results['metrics'] = {**results['metrics'], **dataset_metrics}

    if training_time is not None:
        ex.log_scalar('training_time', training_time)
        results['metrics']['training_time'] = training_time

    return results



