import sys
# required for when running on a cluster
sys.path.append('../')
from typing import List

import sklearn
from sklearn.linear_model import LinearRegression
import numpy as np
from pathlib import Path
import pickle

import sdem
from sdem import Experiment
from sdem.utils import read_yaml, get_all_permutations, print_dict

# Setup sacred experiment
ex = Experiment(__file__)

@ex.configs
def get_config() -> List[dict]:
    configs =  {
        'name': ['linear_model'],
        'fold': list(range(5))
    }
    return get_all_permutations(configs)

def get_raw_data():
    np.random.seed(0)

    N = 50

    x = np.linspace(0, 1, N)
    y = x + 0.1*np.random.randn(N)

    return x[:, None], y

def get_fold(fold):
    X, y = get_raw_data()

    kf_gen = sklearn.model_selection.KFold(n_splits=5, shuffle=False).split(X)

    # kf is a generator, convert to list so we can index
    kf = [k for k in kf_gen]

    train_index, test_index = kf[fold]

    X_train, X_test = X[train_index], X[test_index]
    y_train, y_test = y[train_index], y[test_index]

    return  X_train, X_test, y_train, y_test


@ex.automain
def main(config):
    print_dict(config)

    # Output format name. This must match the pattern defined in the experiment config.
    name = '{name}_{_id}'.format(name=config['name'], _id=config['experiment_id'])

    # Make sure folder for results exists
    results_root = Path('../results/')
    results_root.mkdir(exist_ok=True)

    # Get training data for current fold
    X_train, X_test, y_train, y_test = get_fold(config['fold'])

    # Make model
    m = LinearRegression().fit(X_train, y_train)

    # Log metrics
    def pred_fn(X):
        return m.predict(X)

    train_metrics, pred_train = ex.log_metrics(
        X_train, y_train, pred_fn, var_flag=False, prefix='train'
    )
    test_metrics, pred_test = ex.log_metrics(
        X_test, y_test, pred_fn, var_flag=False, prefix='test'
    )
    
    results = {
        'metrics': {
            'train': train_metrics,
            'test': test_metrics
        },
        'predictions': {
            'train': pred_train,
            'test': pred_test 
        }
    }

    # save results
    print_dict(results['metrics'])

    pickle.dump(results, open(results_root/ f'{name}.pickle', "wb" ) )
    ex.add_artifact(results_root/ f'{name}.pickle')
