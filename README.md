# Sacred Experiment Manager (sem)



##  Description 

Sacred Experiment manager combines [sacred](https://github.com/IDSIA/sacred) and [dvc](https://dvc.org) to run experiments locally, on clusters and across different users. `sem` can work with and without a mongo database.

# Installation 

## Setup Mongo

To install `mongodb` on a mac see here https://docs.mongodb.com/manual/tutorial/install-mongodb-on-os-x/. 

```
mongo
```

```
use sacred
db.createUser(
  {
    user: "default",
    pwd: "default",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
  }
)
```

## Install

```
pip install requirements.py
pip install -e .
```

### SEML

SEML requires a config file:

```
mkdir ~/.config/seml/
```

and for the responses use:

```json
username: default
password: default
port: 27017
database: sacred
host: localhost
```



## Required Experiment Layout

### Folder Structure

To use Experiment Manager every experiment must have the following  structure

```
<experiment_name>/
<experiment_name>/experiment_config.yaml
<experiment_name>/models/m_<model_name>.py
```

where each model file is prefixed by `m_`.

### experiment_config.yaml

This yaml file is used to define cluster/remote host settings as well as any global experiment settings (e.g number of folds, number of epochs etc) that will be used by the python files. A minimal example is:

```yaml
#==============================EXPERIMENT MANAGER SETTINGS==============================
experiment:
  use_config_id: True
  overwrite_id: True


#==============================CLUSTER SETTINGS==============================
local:
  type: 'local'

```



### Model files `m_<model_name>.py` 

Each model files follows  `sacred` model files closely. A minimal example is:

```python
import sys

from experiment_manager import Experiment
from experiment_manager.util import read_yaml

import pickle
import numpy as np

ex = Experiment(__file__)
ec = read_yaml('../experiment_config.yaml')

@ex.configs
def get_config():
    return [
        {'name': 'test', 'fold':0},
        {'name': 'test', 'fold':1},
        {'name': 'test', 'fold':2},
        {'name': 'test', 'fold':3}
    ]

@ex.automain
def run(config):
    N = 100
    X = np.random.randn(N)
    Y = np.random.randn(N)
    prediction_fn = lambda X: np.random.randn(X.shape[0])
    
    train_metrics, train_pred = ex.log_metrics(X, Y, prediction_fn, var_flag=False, log=True, prefix='training')
    test_metrics, test_pred = ex.log_metrics(X, Y, prediction_fn, var_flag=False, log=True, prefix='testing')

    config_id = config['experiment_id']
    results = {'epochs': list(range(0, 100))}
    pickle.dump(results, open( "../results/{name}.pickle".format(name=config_id), "wb" ) )
    ex.add_artifact("../results/{name}.pickle".format(name=config_id))

```



Each model must include a main function (a function decorated by `@ex.automain`) and a function that returns an array of experiment config dicts (decorated by `@ex.configs`). Experiment manager will automatically add the following fields to each dict:

```
	experiment_id: hash of each config dict
	config_id: hash of each config dict with 'fold' field removed (so that fold_id) is consistent across folds. 
	order_id: order of each config dict in the list
	global_id: a global UUID
```

## Running an experiment manually

To run an experiment you can  run each experiment manually by passing order_id into the python file, e.g:

```bash
python m_<model_name>.py 0
```

which will run the main function with the configuration with order_id = 0. 



## Running experiments with Experiment Manager

An alternative is to add this script at

```
<experiment_name>/run.py
```

where `run.py` is 

```python
from pathlib import Path
from experiment_manager import main

#Ensure folder structure exists
Path("models/").mkdir(exist_ok=True)
Path("models/runs").mkdir(exist_ok=True)

main.run()
```

this file has an argument parser who's options can be explored using

```bash
python run.py -h
```

The most basic usage is to run all model configurations 

```python
python run.py
python run.py --sync
```

where the first command will run all configs and store experiment output in local storage. The second command will sync all local storage with the mongo db.

## Visualising Experiments

All experiments are sacred experiments and so can be visualised with [omniboard](https://github.com/vivekratnavel/omniboard). To start omniboard:

```bash
python run.py --omniboard
```



## Run using singularity

Edit the `experiment_config.yaml` file to include the following:



```yaml
<cluster>:
  sif: '../../projects/dsp/dsp_latest.sif'
```



## DVC Setup

### Google API Setup

Follow https://dvc.org/doc/user-guide/setup-google-drive-remote#using-a-custom-google-cloud-project 

- Create project here  https://console.developers.google.com/

- Open  `OAuth consent screen`
- Create OAuth client Credentials

- Enable `Google Drive API`

- Will need to authenticate on first use

### In repo

```
dvc init
dvc remote add gremote gdrive://<folder_url_id>
dvc remote modify gremote gdrive_client_id <client ID>
dvc remote modify gremote gdrive_client_secret <client secret>
dvc remote default gremote
```

