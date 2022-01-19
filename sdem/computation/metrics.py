from sklearn import metrics
import numpy as np

def log_regression_scalar_metrics(
    ex, true_Y, pred_Y, log=True, prefix=None
):

    # fix shapes
    N = true_Y.shape[0]

    true_Y = np.array(true_Y)
    pred_Y = np.array(pred_Y)

    true_Y = true_Y.reshape([N])
    pred_Y = pred_Y.reshape([N])

    # remove any nans
    non_nan_idx = np.logical_not(np.isnan(true_Y))

    true_Y = true_Y[non_nan_idx]
    pred_Y = pred_Y[non_nan_idx]

    # metrics to compute
    metric_fns = {
        "mae": metrics.mean_absolute_error,
        "mse": metrics.mean_squared_error,
        "rmse": lambda true, pred: np.sqrt(metrics.mean_squared_error(true, pred)),
        "r2_score": metrics.r2_score,
    }

    # Go through each metric, compute and log using sacred
    metrics_results = {}
    for k in metric_fns.keys():

        if np.any(np.isnan(pred_Y)):
            print('NaNs in prediction')
            metrics_results[k] = None
            continue

        metrics_results[k] = metric_fns[k](true_Y, pred_Y)

        if log:
            if prefix is None:
                name = k
            else:
                name = "{prefix}_{metric}".format(prefix=prefix, metric=k)

            ex.log_scalar(name, metrics_results[k])

    return metrics_results

def log_compute_regression_scalar_metrics(
    ex, X, Y, prediction_fn, var_flag=True, log=True, prefix=None
):

    if var_flag:
        pred_Y, pred_Var = prediction_fn(X)
        pred = [pred_Y, pred_Var]
    else:
        pred_Y = prediction_fn(X)
        pred = [pred_Y]

    true_Y = Y

    return log_regression_scalar_metrics(
        ex, true_Y, pred_Y, log=log, prefix=prefix
    ), pred   


