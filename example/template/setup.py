"""
    This file creates the required folder structure and setups the experiment data
"""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.model_selection import KFold

import json 

from model_log.util import read_yaml
ex_config = read_yaml('experiment_config.yaml')


np.random.seed(5)

#ensure correct data structure
Path("data/").mkdir(exist_ok=True)
Path("results/").mkdir(exist_ok=True)

f = lambda x: np.sin(x*10)

FOLDS = ex_config['NUM_FOLDS']
N = 100

X_all = np.linspace(0, 1, N)[:, None]
Y_all = f(X_all) + 0.1*np.random.randn(N)[:, None]

XS_vis = np.linspace(-1, 2, 500)[:, None]
YS_vis = f(XS_vis)

kf = KFold(n_splits=FOLDS)

#CREATE TRAINING/TEST DATA
fold = 0
for train_index, test_index in kf.split(X_all):
    X, Y = X_all[train_index], Y_all[train_index]
    XS, YS = X_all[test_index], Y_all[test_index]
    
    training_data = {
        'X': X, 
        'Y': Y, 
    }

    testing_data = {
        'X': XS, 
        'Y': YS, 
    }

    with open('data/train_data_{fold}.pickle'.format(fold=fold), 'wb') as file:
        pickle.dump(training_data, file)

    with open('data/test_data_{fold}.pickle'.format(fold=fold), "wb") as file:
        pickle.dump(testing_data, file)

    fold += 1

prediction_data = {
    'vis': {
        'X': XS_vis,
        'Y': YS_vis
    },

}

with open('data/pred_data.pickle', "wb") as file:
    pickle.dump(prediction_data, file)
