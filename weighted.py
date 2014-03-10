"""
Library to compute weighted quantiles, including the weighted median, of
numpy arrays.
"""
from __future__ import print_function
import numpy as np


def quantile_1D(data, weights, quantile):
    """
    Compute the weighted quantile of a 1D numpy array.
    """
    # Sort the data
    ind_sorted = np.argsort(data)
    sorted_data = data[ind_sorted]
    sorted_weights = weights[ind_sorted]
    # Compute the auxiliary arrays
    Sn = np.cumsum(sorted_weights)
    Pn = (Sn-0.5*sorted_weights)/np.sum(sorted_weights)
    # Get the value of the weighted median
    return np.interp(quantile, Pn, sorted_data)


def quantile(data, weights, quantile):
    """
    Weighted quantile of a 3D data array with respect to the last axis.
    TODO: Extend to other shapes.
    """
    nx, ny, n = data.shape
    imr = data.reshape((nx*ny, n))
    result = np.apply_along_axis(quantile_1D, -1, imr, weights, quantile)
    return result.reshape((nx,ny))


def median(data, weights):
    """
    Weighted median of a 3D data array with respect to the last axis.
    """
    return quantile(data, weights, 0.5)

