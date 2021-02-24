def get_results_df(resulsts_root, metrics, name_fn):
    """
    Collects every results
    """
    pass


def get_ordered_table(
    experiment_name,
    metrics,
    group_by,
    results_by,
    num_folds=1,
    name_column="experiment_id",
    groups_order=None,
    results_order=None,
    groups_name_fn=None,
    results_name_fn=None,
    decimal_places=2,
    folds=None,
    return_raw=False,
    drop=None,
    drop_mean_std=True,
    metric_scale=None,
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
    pass
