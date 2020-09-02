from sklearn import metrics
import numpy as np

def log_regression_scalar_metrics(ex, X, Y, prediction_fn, var_flag=True, log=True, prefix=None):
    
    if var_flag:
        pred_Y, pred_Var = prediction_fn(X)
        pred = [pred_Y, pred_Var]
    else:
        pred_Y = prediction_fn(X)
        pred = [pred_Y]

    true_Y = Y

    #fix shapes

    #remove any nans

    #log metrics
    metric_fns = {
        'mae': metrics.mean_absolute_error,
        'mse': metrics.mean_squared_error,
        'rmse': lambda true, pred: np.sqrt(metrics.mean_squared_error(true, pred)),
        'r2_score': metrics.r2_score,
    }

    metrics_results = {}
    for k in metric_fns.keys():
        metrics_results[k] = metric_fns[k](true_Y, pred_Y)

        if log:
            if prefix is None:
                name = k
            else:
                name = '{prefix}_{metric}'.format(prefix=prefix, metric=k)

            ex.log_scalar(name, metrics_results[k])

    return metrics_results, pred

