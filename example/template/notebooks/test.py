import model_log
from model_log.results import local

local.get_results_df(exp_root='../', metrics=None, name_fn=lambda config: '{name}_{_id}'.format(name=config['name'], _id=config['experiment_id']))
