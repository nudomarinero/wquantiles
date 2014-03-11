"""
Library to compute weighted quantiles, including the weighted median, of
numpy arrays.
"""
from __future__ import print_function
import numpy as np

__version__ = "0.2"


def quantile_1D(data, weights, quantile):
    """
    Compute the weighted quantile of a 1D numpy array.

    Parameters
    ----------
    data : ndarray
        Input array (one dimension).
    weights : ndarray
        Array with the weights of the same size of `data`.
    quantile : float
        Quantile to compute. It must have a value between 0 and 1.

    Returns
    -------
    quantile_1D : float
        The output value.
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

    Parameters
    ----------
    data : ndarray
        Input array.
    weights : ndarray
        Array with the weights of the same size of `data`.
    quantile : float
        Quantile to compute. It must have a value between 0 and 1.

    Returns
    -------
    quantile : float
        The output value.
    """
    # TODO: Extend to other shapes
    nx, ny, n = data.shape
    imr = data.reshape((nx*ny, n))
    result = np.apply_along_axis(quantile_1D, -1, imr, weights, quantile)
    return result.reshape((nx,ny))


def median(data, weights):
    """
    Weighted median of a 3D data array with respect to the last axis.

    Alias for `quantile(data, weights, 0.5)`.
    """
    return quantile(data, weights, 0.5)

