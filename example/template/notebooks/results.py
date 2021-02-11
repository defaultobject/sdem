import model_log
from model_log.results import local

results_df = local.get_results_df(exp_root='../', metrics=None, name_fn=lambda config: '{name}_{_id}'.format(name=config['name'], _id=config['experiment_id']))

print(results_df.group_by('fold_group_id').mean())

