import sys
sys.path.append('.')
sys.path.append('..')
#for docker/cluster
sys.path.append('../libs')

#for local running
sys.path.append('../../../libs')

from deepkernels import deep_RBF
from gpflow.training import AdamOptimizer, ScipyOptimizer

import gpflow

import model_log
from model_log import Experiment
from model_log.util import read_yaml, get_all_permutations

import warnings
warnings.simplefilter('always', UserWarning)

import yaml
import pickle

from pathlib import Path

import numpy as np

#used because it is more accurate
from timeit import default_timer as timer


ex = Experiment(__file__)
ex_config = read_yaml('../experiment_config.yaml')

@ex.configs
def get_config():
    #num_folds and split_type keys needed to load dataloader
    configs =  {
        'name': ['template'],
        'fold': list(range(ex_config['NUM_FOLDS']))
    }

    return get_all_permutations(configs)

@ex.automain
def main(config):
    print(config)
    np.random.seed(0)

    #ensure checkpoint folder exists
    Path("checkpoints/").mkdir(exist_ok=True)

    name = '{name}_{_id}'.format(name=config['name'], _id=config['experiment_id'])

    #===========================Load Data===========================
    data = pickle.load(open('../data/train_data_{fold}.pickle'.format(fold=config['fold']), "rb" ))

    X = data['X']
    Y = data['Y']

    #===========================Fit GP===========================

    #kernel = gpflow.kernels.RBF(input_dim=1)
    kernel = deep_RBF(input_dim=1,active_dims = [0],variance = 1.0)
    m = gpflow.models.GPR(X, Y, kern=kernel)

    #===========================Train===========================
    #used because it is more accurate
    elbos = []

    def logger(x):
        refresh=100
        sess = m.enquire_session()
        obj = m.objective.eval(session=sess)
        elbos.append(obj)
        if x % refresh == 0:
            print(obj)

    start = timer()
    #add trainer here
    elbos = []
    opt = AdamOptimizer()
    opt.minimize(m,  maxiter=10)
    end = timer()
    training_time = end - start

    #===========================Predict===========================
    data_test = pickle.load(open('../data/test_data_{fold}.pickle'.format(fold=config['fold']), "rb" ))
    data_pred = pickle.load(open('../data/pred_data.pickle', "rb" ))
    XS, YS = data_test['X'], data_test['Y']

    results = {}
    results['train'] = {}
    results['test'] = {}
    results['metrics'] = {}

    def prediction_fn(X):
        return m.predict_y(X)

    #predict at training locations
    train_metrics, pred_train  = ex.log_metrics(X, Y, prediction_fn, var_flag=True, log=True, prefix='pred_training')
    mu_train, var_train = pred_train

    results['train']['mean'] = mu_train
    results['train']['var'] = var_train
    results['metrics']['train'] = train_metrics

    #predict at testing locations
    test_metrics, pred_test  = ex.log_metrics(XS, YS, prediction_fn, var_flag=True, log=True, prefix='pred_testing')
    mu_test, var_test = pred_test

    results['test']['mean'] = mu_test
    results['test']['var'] = var_test
    results['metrics']['test'] = test_metrics

    #log training time
    results['metrics']['training_time'] = training_time
    ex.log_scalar('training_time', training_time)


    results['pred'] = {}
    #predict at prediction locations (useful for creating vis)
    for key in data_pred.keys():
        results['pred'][key] = {}
        pred_mu, pred_var = prediction_fn(data_pred[key]['X'])
        results['pred'][key]['mean'] = pred_mu
        results['pred'][key]['var'] = pred_var

    pickle.dump(results, open( "../results/{name}.pickle".format(name=name), "wb" ) )
    ex.add_artifact("../results/{name}.pickle".format(name=name))





