import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import gridspec

def get_mean_std_figure_from_ordered_table(table_df_groups, color_scheme, row_labels, group_labels, dataset_labels, fig=None, axes=None, matplotlib_settings=None, plot_y_label=True, grouped=False):
    """
        Args:
            table_df_groups: List[DataFrames] - each element of the list has its own axis

    """
    if matplotlib_settings is None:
        matplotlib_settings = {}

    #Start with MSE

    num_datasets = len(table_df_groups)
    num_groups = len(table_df_groups[0])

    #gs = gridspec.GridSpec(num_groups, 1) 
    #gs.update(wspace=0.0, hspace=0.0)

    if fig is None:
        fig, axes = plt.subplots(num_groups, sharex=True, gridspec_kw = {'wspace':1.0, 'hspace':0})

    step = 1.0
    
    count = sum([len(df) for df in table_df_groups])
    pos = count

    if 'linewidth' not in matplotlib_settings.keys():
        matplotlib_settings['linewidth'] = 5

    if 'markersize' not in matplotlib_settings.keys():
        matplotlib_settings['markersize'] = 5

    if 'myfont_label' not in matplotlib_settings.keys():
        matplotlib_settings['myfont_label'] = 'none'

    if 'myfont_ticks' not in matplotlib_settings.keys():
        matplotlib_settings['myfont_ticks'] = 'none'

    for j, group_dfs in enumerate(table_df_groups):
        for i, table_df in enumerate(group_dfs):
            #ax = plt.subplot(gs[i])
            ax = axes[i][j]

            #all postiions that table_df will use
            table_df_all_pos = [pos - step*i for i in range(len(table_df))]

            #collect labels of models
            labels = []

            if i == 0:
                ax.set_title(dataset_labels[j], fontdict={'fontsize': 6})

            row_i = 0
            for index, row in table_df.iterrows():
                m = '{col}'
                mean = np.squeeze(np.array(row[m.format(col='mean')]))
                std = np.squeeze(np.array(row[m.format(col='std')]))

                color_key = row['key']
                color = color_scheme[color_key]

                line_color = color['linecolor']

                print(len(table_df_groups))
                if grouped:
                    labels.append(
                        r'$\textsc{'+row_labels[row_i]+'}'+
                        '_{'+'{group}'.format(group=group_labels[i])+'}'+
                        r'$'
                    )

                else:
                    labels.append(
                        r'$\textsc{'+row_labels[row_i]+'}'+
                        '_{'+'{group}'.format(group=group_labels[row_i])+'}'+
                        r'$'
                    )

                row_i += 1

                if color_key == 'gp':
                    ax.axvline(
                        mean, 
                        0.0, 
                        1.0,
                        color = 'darkgray',
                        linewidth = matplotlib_settings['linewidth'],
                        linestyle = '--',
                        zorder=0
                    )

                ax.plot(
                    mean, 
                    pos,
                    'o',
                    markersize =  matplotlib_settings['markersize'], 
                    color = line_color
                )

                ax.errorbar(
                    mean,
                    pos,
                    xerr=std,
                    #linewidth = 144/5,
                    color = line_color,
                    linewidth = matplotlib_settings['linewidth']
                )

                pos -= step

            ax.xaxis.set_major_locator(plt.MaxNLocator(5))


            if j == 0:
                if plot_y_label:
                    ax.set_yticks( ticks  = table_df_all_pos)
                    ax.set_yticklabels(
                        labels,
                        fontdict = {'fontsize': 6}
                    )
                else:
                    ax.set_yticklabels([])
            else:
                ax.set_yticklabels([])

            ax.set_ylim(min(table_df_all_pos)-0.5*step, max(table_df_all_pos)+0.5*step)






        #ax.set_ylabel(group_labels[i], fontproperties=matplotlib_settings['myfont_label'])

    #fig.tight_layout()
    #plt.subplots_adjust(hspace=.0) 
    return ax
