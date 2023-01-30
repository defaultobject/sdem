# SacreD Experiment Manager (sdem)

## Description

Sacred Experiment manager combines [sacred](https://github.com/IDSIA/sacred) and [dvc](https://dvc.org) to run experiments locally, on HPC clusters and across different users. 

Currently `sdem` works with `sacred` local files, but there are plans to support `mongo` experiments.

## Installation

Requires python==3.9

### Through pip

```bash
pip install sdem
```

### From github

```bash
git clone git@github.com:defaultobject/sdem.git
cd sdem
pip install -e .
```

## Example

The full example is shown in the `example` folder.

#### Run

There are two ways to run a file, the first is through the `sdem` cli. In The experiment folder run:

```bash
sdem --verbose run
```

which will sequentially run all models found in the `models` folder.

Alternatively we can directly run the models file:

```bash
python m_model.py -1
```

#### View table of results

`sdem` provides some convenient functions to see the results of the experiments ran. To automatically create a table of results go into the `metrics` folder and run

```bash
python table_of_results.py
```

which runs

```python
results_df = get_ordered_table(
    '../',
    metrics=['train_rmse', 'test_rmse'],
    group_by=[
        'name', 
    ],
    results_by=[''],
    combine=True,
    flatten=True,
)
```

This will go through every sacred run, and group the metrics by `name` and compute the mean and std across all experiments in this group (ie across folds). This results in 

```
    name          train_rmse_score    test_rmse_score
--  ------------  ------------------  -----------------
 0  linear_model  0.10 $\pm$ 0.01     0.10 $\pm$ 0.03
```

To view the results of each fold we can simply add this to the `results_by` argument

```python
results_df = get_ordered_table(
    '../',
    metrics=['train_rmse', 'test_rmse'],
    group_by=[
        'name', 
    ],
    results_by=['fold'],
    combine=True,
    flatten=True,
)
```

which results in

```
    name            fold  train_rmse_score    test_rmse_score
--  ------------  ------  ------------------  -----------------
 0  linear_model       0  0.11 $\pm$ nan      0.09 $\pm$ nan
 1  linear_model       1  0.11 $\pm$ nan      0.06 $\pm$ nan
 2  linear_model       2  0.09 $\pm$ nan      0.14 $\pm$ nan
 3  linear_model       3  0.11 $\pm$ nan      0.09 $\pm$ nan
 4  linear_model       4  0.10 $\pm$ nan      0.11 $\pm$ nan
```

#### Get results for a given experiment

As shown in `predictions.py` we can load (unpacked) pickles and configs for the run experiments:

```python
res_list, config_list = get_results_that_match_dict(
    {
        'fold': 0,
    },
    '../'
)

print(f'Number of experiments found {len(res_list)}')
```

This will return the (unpacked) pickles and configs of all experiments that match the passed dictionary, in this case it will return the one with fold equal to zero.

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
