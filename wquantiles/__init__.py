"""
Library to compute weighted quantiles, including the weighted median, of
numpy arrays.

The estimator implemented here is the *interpolated weighted percentile*: the
data are sorted, a weighted cumulative distribution
``Pn = (Sn - 0.5 * w) / Sn[-1]`` is built, and the result is linearly
interpolated from it. With unit weights this is exactly numpy's
``method="hazen"`` (Hyndman-Fan type 5).

Note that this is *not* the discrete weighted median, and *not* what
``np.quantile(..., weights=...)`` computes -- numpy only supports weights with
``method="inverted_cdf"``, which returns an actual data value rather than an
interpolated one. The two disagree on most inputs.
"""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import ArrayLike

try:
    from importlib.metadata import PackageNotFoundError, version as _version

    __version__ = _version("wquantiles")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "unknown"

__all__ = ["quantile_1D", "quantile", "median"]

# Distinguishes "not passed" from a legitimate value, so that the deprecated
# `quantile=` keyword can coexist with the `q` parameter that replaced it.
_UNSET: Any = object()


def _resolve_q(q: Any, quantile: Any) -> Any:
    """Accept the quantile under its current name or its deprecated one."""
    if quantile is not _UNSET:
        if q is not _UNSET:
            raise TypeError(
                "the quantile was passed twice, as `q` and as `quantile`; "
                "pass it only as `q`"
            )
        warnings.warn(
            "The `quantile` keyword argument is deprecated, use `q` instead. "
            "It will be removed in a future release.",
            DeprecationWarning,
            stacklevel=3,
        )
        return quantile
    if q is _UNSET:
        raise TypeError("missing a required argument: 'q'")
    return q


def _check_weights(weights: np.ndarray) -> None:
    """Reject weights that would make the result meaningless."""
    # Non-finite first: NaN would slip past the comparison below, since any
    # comparison with NaN is False.
    if not np.all(np.isfinite(weights)):
        raise ValueError("the weights must all be finite")
    if np.any(weights < 0.0):
        raise ValueError("the weights must not be negative")


def quantile_1D(
    data: ArrayLike,
    weights: ArrayLike,
    q: float = _UNSET,
    *,
    quantile: float = _UNSET,
) -> np.floating:
    """
    Compute the weighted quantile of a 1D numpy array.

    Parameters
    ----------
    data : array_like
        Input array (one dimension).
    weights : array_like
        Array with the weights of the same size of `data`. They must be
        finite, non-negative, and must not all be zero.
    q : float
        Quantile to compute. It must have a value between 0 and 1.
    quantile : float
        Deprecated alias for `q`.

    Returns
    -------
    quantile_1D : numpy.floating
        The output value. It is NaN if `data` contains any NaN.

    Raises
    ------
    TypeError
        If `data` or `weights` is not one dimensional, or their lengths
        differ.
    ValueError
        If `q` lies outside [0, 1], if `data` is empty, or if the weights are
        non-finite, negative, or sum to zero.
    """
    q = _resolve_q(q, quantile)
    # Check the data
    data = np.asarray(data)
    weights = np.asarray(weights)
    if data.ndim != 1:
        raise TypeError("data must be a one dimensional array")
    if weights.ndim != 1:
        raise TypeError("weights must be a one dimensional array")
    if data.shape != weights.shape:
        raise TypeError("the length of data and weights must be the same")
    if data.size == 0:
        raise ValueError("data must not be empty")
    if (q > 1.0) or (q < 0.0):
        raise ValueError("q must have a value between 0. and 1.")
    _check_weights(weights)
    # Sort the data
    ind_sorted = np.argsort(data)
    sorted_data = data[ind_sorted]
    sorted_weights = weights[ind_sorted]
    # Compute the auxiliary arrays
    Sn = np.cumsum(sorted_weights)
    if Sn[-1] == 0:
        raise ValueError("the sum of the weights must not be zero")
    Pn = (Sn - 0.5 * sorted_weights) / Sn[-1]
    # A NaN anywhere in the data poisons the result, as it does in np.quantile.
    # Checked after the weights so that invalid weights still raise.
    if np.isnan(sorted_data).any():
        return np.float64(np.nan)
    # Get the value of the weighted quantile
    return np.interp(q, Pn, sorted_data)


def quantile(
    data: ArrayLike,
    weights: ArrayLike,
    q: float = _UNSET,
    *,
    quantile: float = _UNSET,
) -> Any:
    """
    Weighted quantile of an array with respect to the last axis.

    Parameters
    ----------
    data : array_like
        Input array.
    weights : array_like
        Array with the weights. It must have the same size of the last
        axis of `data`.
    q : float
        Quantile to compute. It must have a value between 0 and 1.
    quantile : float
        Deprecated alias for `q`.

    Returns
    -------
    quantile : numpy.floating or ndarray
        The output value for one dimensional `data`, otherwise an array with
        the shape of `data` minus its last axis.

    Raises
    ------
    TypeError
        If `data` has no dimensions, or the weights do not match the last
        axis of `data`.
    ValueError
        If `q` lies outside [0, 1], if `data` is empty, or if the weights are
        non-finite, negative, or sum to zero.
    """
    # TODO: Allow to specify the axis
    q = _resolve_q(q, quantile)
    data = np.asarray(data)
    weights = np.asarray(weights)
    nd = data.ndim
    if nd == 0:
        raise TypeError("data must have at least one dimension")
    elif nd == 1:
        return quantile_1D(data, weights, q)
    else:
        n = data.shape
        imr = data.reshape((np.prod(n[:-1]), n[-1]))
        result = np.apply_along_axis(quantile_1D, -1, imr, weights, q)
        return result.reshape(n[:-1])


def median(data: ArrayLike, weights: ArrayLike) -> Any:
    """
    Weighted median of an array with respect to the last axis.

    Alias for `quantile(data, weights, 0.5)`.
    """
    return quantile(data, weights, 0.5)
