## @package random_distributions_demo
## Demonstrates to generation of numbers from an arbitrary distribution.
##

import numpy
from orangecontrib.aps.util.random_distributions import *
from orangecontrib.aps.util.enhanced_grid import Grid2D
from random import random

from matplotlib import pyplot as plt

def index_of(array, value):
    array = numpy.asarray(array)
    idx = (numpy.abs(array - value)).argmin()
    return idx

# Demonstrates to generation of points from a 2D distribution.
# An image is produced that shows an estimate of the distribution
# for a samnple of points generate from the specified distribution.
def demo_distribution_2d():
    data = numpy.loadtxt("/Users/lrebuffi/TEST.dat", skiprows=1)

    x_values = numpy.unique(data[:, 0])
    y_values = numpy.unique(data[:, 1])

    min_x = numpy.min(x_values)
    max_x = numpy.max(x_values)
    delta_x =  numpy.max(x_values) -  numpy.min(x_values)

    min_y = numpy.min(y_values)
    max_y = numpy.max(y_values)
    delta_y =  numpy.max(y_values) -  numpy.min(y_values)

    dim_x = len(x_values)
    dim_y = len(y_values)

    z_values = numpy.zeros((dim_x, dim_y))

    for i in range(dim_x):
        for j in range(dim_y):
            index = i*dim_x + j

            z_values[i, j] = data[index, 2]

    fig, ax = plt.subplots(ncols=2)
    ax[0].imshow(z_values, interpolation='bilinear', origin='lower', extent=[0, 100, 0, 100],
              vmax=numpy.max(z_values), vmin=numpy.min(z_values))

    grid = Grid2D((dim_x, dim_y))
    grid[..., ...] = z_values.tolist()

    probabilities = distribution_from_grid(grid, dim_x, dim_y)

    d = Distribution2D(probabilities, (min_x, min_y), (max_x, max_y))

    samples = []

    for k in range(1000000):
        samples.append(d(random(), random()))

    z_values_rand = numpy.zeros((dim_x, dim_y))

    for sample in samples:
        x_value = sample[0]
        y_value = sample[1]

        i = index_of(x_values, min_x + x_value*delta_x)
        j = index_of(y_values, min_y + y_value*delta_y)
        
        z_values_rand[i, j] += 1

    ax[1].imshow(z_values_rand, interpolation='bilinear', origin='lower', extent=[0, 100, 0, 100],
              vmax=numpy.max(z_values_rand), vmin=numpy.min(z_values_rand))
    plt.show()



#Run any of these to see how they work.
#demo_distribution_1d()
demo_distribution_2d()
