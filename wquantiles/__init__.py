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

Missing data
------------
Each datum owns a slab of probability whose width is proportional to its
weight, so a datum with zero weight owns nothing and is dropped before
interpolating rather than left as a node in the interpolation grid.

Entries masked out of a ``numpy.ma.MaskedArray`` are dropped the same way.

``NaN`` in the data or the weights propagates, as it does in ``np.quantile``.
Use `nanquantile` and `nanmedian` to omit it instead, as ``np.nanquantile``
does.
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

__all__ = ["quantile_1D", "quantile", "median", "nanquantile", "nanmedian"]

# Distinguishes "not passed" from a legitimate value, so that the deprecated
# `quantile=` keyword can coexist with the `q` parameter that replaced it.
_UNSET: Any = object()

_EMPTY_MSG = "no datum carries a positive weight, returning nan"


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


def _unpack(x: Any) -> tuple[np.ndarray, np.ndarray]:
    """Split an input into plain values and a boolean "ignore this" array.

    ``np.asarray`` silently discards the mask of a MaskedArray, letting
    whatever sits underneath leak into the result, so masked input is taken
    apart explicitly.
    """
    if isinstance(x, np.ma.MaskedArray):
        values = np.ma.getdata(x)
        mask = np.ma.getmaskarray(x)
    else:
        values = np.asarray(x)
        mask = np.zeros(values.shape, dtype=bool)
    if values.ndim == 0:
        # A scalar is a sample of one, as it is for np.quantile.
        values = values.reshape(1)
        mask = mask.reshape(1)
    return values, mask


def _weighted_quantile_1D(
    data: Any, weights: Any, q: float, omit_nan: bool
) -> np.floating:
    """The algorithm itself, on a single dimension."""
    data, data_mask = _unpack(data)
    weights, weights_mask = _unpack(weights)
    if data.ndim != 1:
        raise TypeError("data must be a one dimensional array")
    if weights.ndim != 1:
        raise TypeError("weights must be a one dimensional array")
    if data.shape != weights.shape:
        raise TypeError("the length of data and weights must be the same")
    if (q > 1.0) or (q < 0.0):
        raise ValueError("q must have a value between 0. and 1.")

    ignore = data_mask | weights_mask
    live = ~ignore

    # An infinite weight has no single limit: for data [1, 2, 3] with weights
    # [1, W, 1], letting W -> inf gives 1.5 at q=0.25 but 2.0 at q=0.5, so the
    # answer depends on how the limit is taken. Checked before the sign, so
    # that -inf is reported as infinite rather than as merely negative.
    if np.any(np.isinf(weights[live])):
        raise ValueError(
            "the weights must be finite; an infinite weight leaves the "
            "quantile ill-posed"
        )
    # A negative weight is not a probability mass: it pushes Pn outside [0, 1],
    # so the curve being interpolated is no longer a cumulative distribution.
    if np.any(weights[live] < 0):
        raise ValueError("the weights must not be negative")

    unknown = live & (np.isnan(weights) | np.isnan(data))
    if unknown.any():
        if not omit_nan:
            # Propagate, as np.quantile does. nanquantile omits instead.
            return np.float64(np.nan)
        ignore = ignore | unknown

    # A datum with zero weight owns no probability mass, so it must not remain
    # a node in the interpolation grid -- otherwise it can be returned as the
    # answer despite counting for nothing.
    ignore = ignore | (weights == 0)

    keep = ~ignore
    data = data[keep]
    weights = weights[keep]
    if data.size == 0:
        # Covers empty input, all-zero weights, and everything being masked.
        warnings.warn(_EMPTY_MSG, RuntimeWarning, stacklevel=3)
        return np.float64(np.nan)

    # Sort the data
    ind_sorted = np.argsort(data)
    sorted_data = data[ind_sorted]
    sorted_weights = weights[ind_sorted]
    # Compute the auxiliary arrays
    Sn = np.cumsum(sorted_weights)
    Pn = (Sn - 0.5 * sorted_weights) / Sn[-1]
    # Get the value of the weighted quantile
    return np.interp(q, Pn, sorted_data)


def _weighted_quantile(data: Any, weights: Any, q: float, omit_nan: bool) -> Any:
    """Apply the 1D algorithm along the last axis."""
    values, mask = _unpack(data)
    if values.ndim == 1:
        return _weighted_quantile_1D(data, weights, q, omit_nan)
    shape = values.shape
    flat = values.reshape((int(np.prod(shape[:-1])), shape[-1]))
    flat_mask = mask.reshape(flat.shape)
    masked = flat_mask.any()
    result = np.empty(flat.shape[0], dtype=float)
    for i in range(flat.shape[0]):
        row = np.ma.masked_array(flat[i], mask=flat_mask[i]) if masked else flat[i]
        result[i] = _weighted_quantile_1D(row, weights, q, omit_nan)
    return result.reshape(shape[:-1])


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
        Input array (one dimension). A masked array is honoured: masked
        entries are dropped.
    weights : array_like
        Array with the weights of the same size of `data`. They must be
        non-negative and finite. Entries with zero weight are dropped.
    q : float
        Quantile to compute. It must have a value between 0 and 1.
    quantile : float
        Deprecated alias for `q`.

    Returns
    -------
    quantile_1D : numpy.floating
        The output value. It is NaN if `data` or `weights` contains any NaN,
        and NaN with a `RuntimeWarning` if nothing is left to average over.

    Raises
    ------
    TypeError
        If `data` or `weights` has more than one dimension, or their lengths
        differ.
    ValueError
        If `q` lies outside [0, 1], or if any weight is negative or infinite.

    See Also
    --------
    nanquantile : the same, omitting NaN rather than propagating it.
    """
    return _weighted_quantile_1D(data, weights, _resolve_q(q, quantile), False)


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
        Input array. A masked array is honoured: masked entries are dropped.
    weights : array_like
        Array with the weights. It must have the same size of the last
        axis of `data`. Entries with zero weight are dropped.
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
        If the weights do not match the last axis of `data`.
    ValueError
        If `q` lies outside [0, 1], or if any weight is negative or infinite.

    See Also
    --------
    nanquantile : the same, omitting NaN rather than propagating it.
    """
    # TODO: Allow to specify the axis
    return _weighted_quantile(data, weights, _resolve_q(q, quantile), False)


def median(data: ArrayLike, weights: ArrayLike) -> Any:
    """
    Weighted median of an array with respect to the last axis.

    Alias for `quantile(data, weights, 0.5)`.
    """
    return quantile(data, weights, 0.5)


def nanquantile(
    data: ArrayLike,
    weights: ArrayLike,
    q: float = _UNSET,
    *,
    quantile: float = _UNSET,
) -> Any:
    """
    Weighted quantile along the last axis, ignoring NaN.

    Identical to `quantile`, except that entries whose value or whose weight
    is NaN are treated as missing and dropped, the way `np.nanquantile` treats
    them. If every entry is dropped the result is NaN and a `RuntimeWarning`
    is raised.

    See Also
    --------
    quantile : the same, propagating NaN rather than omitting it.
    """
    return _weighted_quantile(data, weights, _resolve_q(q, quantile), True)


def nanmedian(data: ArrayLike, weights: ArrayLike) -> Any:
    """
    Weighted median along the last axis, ignoring NaN.

    Alias for `nanquantile(data, weights, 0.5)`.
    """
    return nanquantile(data, weights, 0.5)
