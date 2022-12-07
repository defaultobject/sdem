from sklearn import metrics
import numpy as np

def fix_shapes_and_nans(true_Y, pred_Y):

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

    return true_Y, pred_Y

def log_binary_scalar_metrics(
    ex, true_Y, pred_Y, log=True, prefix=None, cutoff = 0.5
):
    true_Y, pred_Y = fix_shapes_and_nans(true_Y, pred_Y)

    pred_Y_rounded = np.copy(pred_Y)
    pred_Y_rounded[pred_Y_rounded >= cutoff] = 1
    pred_Y_rounded[pred_Y_rounded < cutoff] = 0

    metrics_results = {}

    try:
        fpr, tpr, thresholds = metrics.roc_curve(true_Y, pred_Y, pos_label=1)

        # for ROC curves
        metrics_results['roc_fpr'] = fpr.tolist()
        metrics_results['roc_tpr'] = tpr.tolist()

        metrics_results['auc'] = metrics.auc(fpr, tpr)
    except Exception as e:
        # for ROC curves
        metrics_results['roc_fpr'] = np.NaN
        metrics_results['roc_tpr'] = np.NaN
        metrics_results['auc'] = np.NaN

    try:
        tn, fp, fn, tp = metrics.confusion_matrix(true_Y, pred_Y_rounded).ravel()

        metrics_results['sensitivity'] = metrics.recall_score(true_Y, pred_Y_rounded)
        metrics_results['precision'] = metrics.precision_score(true_Y, pred_Y_rounded)
        metrics_results['specificity'] = tn / (tn + fp)
        metrics_results['tn'] = tn 
        metrics_results['fp'] = fp 
        metrics_results['fn'] = fn 
        metrics_results['tp'] = tp 
    except Exception as e:
        metrics_results['sensitivity'] = np.NaN
        metrics_results['precision'] = np.NaN
        metrics_results['specificity'] = np.NaN
        metrics_results['tn'] = np.NaN 
        metrics_results['fp'] = np.NaN 
        metrics_results['fn'] = np.NaN 
        metrics_results['tp'] = np.NaN 


    # log 
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='auc'), metrics_results['auc'])
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='sensitivity'), metrics_results['sensitivity'])
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='precision'), metrics_results['precision'])
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='specificity'), metrics_results['specificity'])
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='tn'), metrics_results['tn'])
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='fp'), metrics_results['fp'])
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='fn'), metrics_results['fn'])
    ex.log_scalar("{prefix}_{metric}".format(prefix=prefix, metric='tp'), metrics_results['tp'])

    return metrics_results

def log_regression_scalar_metrics(
    ex, true_Y, pred_Y, log=True, prefix=None
):

    true_Y, pred_Y = fix_shapes_and_nans(true_Y, pred_Y)

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

        if true_Y.size == 0:
            print('No True Data')
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


