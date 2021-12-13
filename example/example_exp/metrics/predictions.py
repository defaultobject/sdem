import sdem
from sdem.results.local import get_results_that_match_dict

import matplotlib.pyplot as plt

res_list, config_list = get_results_that_match_dict(
    {
        'fold': 0,
    },
    '../'
)

print(f'Number of experiments found {len(res_list)}')
