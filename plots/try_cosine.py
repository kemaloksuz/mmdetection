import numpy as np
import torch
import matplotlib.patches as patches
from matplotlib import pyplot as plt


def export_legend(legend, filename):
    fig = legend.figure
    fig.canvas.draw()
    bbox=legend.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(filename, dpi="figure", bbox_inches=bbox)

if __name__ == '__main__':
    
    # cls_scores
    upper_limit = 2
    lower_limit = -1
    split = 0.001
    cls_scores = np.arange(lower_limit, upper_limit, split)
    gammas = [2, 2.5]
    lw_vals = [10, 15]
    # losses 
    ax = plt.subplot(121)
    plt.plot(figsize=(20,20))
    for gamma in gammas:
        loss_cos = np.power(1-cls_scores, gamma)*(np.cos((1.57)*cls_scores+1.57)+1)
        if lw_vals != None:
            linewidth = 2
            for lw in lw_vals:
                loss_cos = loss_cos * lw
                label = "Cos loss w/gamma={}, lw={}".format(gamma, lw)
                ax.plot(cls_scores, loss_cos, label = label, linewidth=linewidth)
                linewidth += 0.7

    loss_CE = -1*np.log(cls_scores) 
    ax.plot(cls_scores, loss_CE, label="CE", linewidth=5.0)
    ax.axhline(0, color='black')
    ax.axvline(0, color='black')
    ax.set_ylim(-1.75, 20)
    ax.set_xlim(-0.25, 1.5)
    ax.grid()
    legend = ax.legend()
    export_legend(legend, "losses_legend.png")
    ax.get_legend().remove()
    plt.xlabel(r'$GT probability$')
    plt.ylabel(r'$Loss$')
    plt.title("Losses")
    plt.tight_layout()

    # Derivatives
    ax = plt.subplot(122)
    for gamma in gammas:
        der_cos = ((-1*gamma*np.power(1-cls_scores, gamma-1))*(np.cos(1.57*cls_scores+1.57)+1)) \
                  + (np.power(1-cls_scores, gamma)*(-1.57*np.sin(1.57*cls_scores+1.57)))
        if lw_vals != None:
            linewidth=2
            for lw in lw_vals:
                der_cos = der_cos * lw
                label = "Cos loss w/gamma={}, lw={}".format(gamma, lw)
                ax.plot(cls_scores, der_cos, label=label, linewidth=linewidth)
                linewidth += 0.7
    derivative_CE = -1 / cls_scores
    ax.plot(cls_scores, derivative_CE, label="CE", linewidth=5.0)
    plt.title("Derivatives")
    plt.tight_layout()
    # Derivatives
    ax.axhline(0, color='black')
    ax.axvline(0, color='black')
    
    ax.set_ylim(-30, 2)
    ax.set_xlim(-0.25, 1.5)
    
    legend = ax.legend()
    export_legend(legend, "derivatives_legend.png")
    ax.get_legend().remove()
    ax.grid()
    plt.xlabel(r'$GT probability$')
    plt.ylabel(r'$\Delta Loss$')
    plt.tight_layout()

    # show
    plt.show()
    

