# Copyright 2025 The Meridian Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Auxiliary functions for knots calculations."""

import bisect
from collections.abc import Collection, Sequence
import copy
import dataclasses
import math
from typing import Any
import numpy as np
# TODO: b/437393442 - migrate patsy
from patsy import highlevel
from statsmodels.regression import linear_model


__all__ = [
    'KnotInfo',
    'get_knot_info',
    'l1_distance_weights',
]


# TODO: Reimplement with a more readable method.
def _find_neighboring_knots_indices(
    times: np.ndarray,
    knot_locations: np.ndarray,
) -> Sequence[Sequence[int] | None]:
  """Return indices of neighboring knot locations.

  Returns indices in `knot_locations` that correspond to the neighboring knot
  locations for each time period. If a time point is at or before the first
  knot, the first knot is the only neighboring knot. If a time point is after
  the last knot, the last knot is the only neighboring knot.

  Args:
    times: Times `0, 1, 2,..., (n_times-1)`.
    knot_locations: The location of knots within `0, 1, 2,..., (n_times-1)`.

  Returns:
    List of length `n_times`. Each element is the indices of the neighboring
    knot locations for the respective time period. If a time point is at or
    before the first knot, the first knot is the only neighboring knot. If a
    time point is after the last knot, the last knot is the only neighboring
    knot.
  """
  neighboring_knots_indices = [None] * len(times)
  for t in times:
    # knot_locations assumed to be sorted.
    if t <= knot_locations[0]:
      neighboring_knots_indices[t] = [0]
    elif t >= knot_locations[-1]:
      neighboring_knots_indices[t] = [len(knot_locations) - 1]
    else:
      bisect_index = bisect.bisect_left(knot_locations, t)
      neighboring_knots_indices[t] = [bisect_index - 1, bisect_index]
  return neighboring_knots_indices


def l1_distance_weights(
    n_times: int, knot_locations: np.ndarray[int, np.dtype[int]]
) -> np.ndarray:
  """Computes weights at knots for every time period.

  The two neighboring knots inform the weight estimate of a particular time
  period. The amount each of the two neighboring knots inform the weight at a
  time period depends on how close (L1 distance) they are to the time period. If
  a time point coincides with a knot location, then 100% weight is given to that
  knot. If a time point lies outside the range of knots, then 100% weight is
  given to the nearest endpoint knot.

  This function computes an `(n_knots, n_times)` array of weights that are used
  to model trend and seasonality. For a given time, the array contains two
  non-zero weights. The weights are inversely proportional to the L1 distance
  from the given time to the neighboring knots. The two weights are normalized
  such that they sum to 1.

  Args:
    n_times: The number of time points.
    knot_locations: The location of knots within `0, 1, 2,..., (n_times-1)`.

  Returns:
    A weight array with dimensions `(n_knots, n_times)` with values summing up
    to 1 for each time period when summing over knots.
  """
  if knot_locations.ndim != 1:
    raise ValueError('`knot_locations` must be one-dimensional.')
  if not np.all(knot_locations == np.sort(knot_locations)):
    raise ValueError('`knot_locations` must be sorted.')
  if len(knot_locations) <= 1:
    raise ValueError('Number of knots must be greater than 1.')
  if len(knot_locations) != len(np.unique(knot_locations)):
    raise ValueError('`knot_locations` must be unique.')
  if np.any(knot_locations < 0):
    raise ValueError('knot_locations must be positive.')
  if np.any(knot_locations >= n_times):
    raise ValueError('knot_locations must be less than `n_times`.')

  times = np.arange(n_times)
  time_minus_knot = abs(knot_locations[:, np.newaxis] - times[np.newaxis, :])

  w = np.zeros(time_minus_knot.shape, dtype=np.float32)
  neighboring_knots_indices = _find_neighboring_knots_indices(
      times, knot_locations
  )
  for t in times:
    idx = neighboring_knots_indices[t]
    if len(idx) == 1:
      w[idx, t] = 1
    else:
      # Weight is in proportion to how close the two neighboring knots are.
      w[idx, t] = 1 - (time_minus_knot[idx, t] / time_minus_knot[idx, t].sum())

  return w


def _get_equally_spaced_knot_locations(n_times, n_knots):
  """Equally spaced knot locations starting at the endpoints."""
  return np.linspace(0, n_times - 1, n_knots, dtype=int)


@dataclasses.dataclass(frozen=True)
class KnotInfo:
  """Contains the number of knots, knot locations, and weights.

  Attributes:
    n_knots: The number of knots
    knot_locations: The location of knots
    weights: The weights used to multiply with the knot values to get time-
      varying coefficients.
  """

  n_knots: int
  knot_locations: np.ndarray[int, np.dtype[int]]
  weights: np.ndarray[int, np.dtype[float]]


def get_knot_info(
    n_times: int,
    knots: int | Collection[int] | None,
    is_national: bool = False,
) -> KnotInfo:
  """Returns the number of knots, knot locations, and weights.

  Args:
    n_times: The number of time periods in the data.
    knots: An optional integer or a collection of integers indicating the knots
      used to estimate time effects. When `knots` is a collection of integers,
      the knot locations are provided by that collection. Zero corresponds to a
      knot at the first time period, one corresponds to a knot at the second
      time, ..., and `(n_times - 1)` corresponds to a knot at the last time
      period. When `knots` is an integer, then there are knots with locations
      equally spaced across the time periods (including knots at zero and
      `(n_times - 1)`. When `knots` is `1`, there is a single common regression
      coefficient used for all time periods. If `knots` is `None`, then the
      numbers of knots used is equal to the number of time periods. This is
      equivalent to each time period having its own regression coefficient.
    is_national: A boolean indicator whether to adapt the knot information for a
      national model.

  Returns:
    A KnotInfo that contains the number of knots, the location of knots, and the
    weights used to multiply with the knot values to get time-varying
    coefficients.
  """

  if isinstance(knots, int):
    if knots < 1:
      raise ValueError('If knots is an integer, it must be at least 1.')
    elif knots > n_times:
      raise ValueError(
          f'The number of knots ({knots}) cannot be greater than the number of'
          f' time periods in the kpi ({n_times}).'
      )
    elif is_national and knots == n_times:
      raise ValueError(
          f'Number of knots ({knots}) must be less than number of time periods'
          f' ({n_times}) in a nationally aggregated model.'
      )
    n_knots = knots
    knot_locations = _get_equally_spaced_knot_locations(n_times, n_knots)
  elif isinstance(knots, Collection) and knots:
    if any(k < 0 for k in knots):
      raise ValueError('Knots must be all non-negative.')
    if any(k >= n_times for k in knots):
      raise ValueError(
          'Knots must all be less than the number of time periods.'
      )
    n_knots = len(knots)
    # np.unique also sorts
    knot_locations = np.unique(knots)
  elif isinstance(knots, Collection):
    raise ValueError('Knots cannot be empty.')
  else:
    # knots is None
    n_knots = 1 if is_national else n_times
    knot_locations = _get_equally_spaced_knot_locations(n_times, n_knots)

  if n_knots == 1:
    weights = np.ones((1, n_times), dtype=np.float32)
  else:
    weights = l1_distance_weights(n_times, knot_locations)

  return KnotInfo(n_knots, knot_locations, weights)


class AKS:
  """Class for automatically selecting knots in Meridian Core Library."""

  def __init__(self):
    # TODO: b/434254634 - implement
    raise NotImplementedError('Not implemented.')

  def automatic_knot_selection(self) -> tuple[list[float], linear_model.OLS]:
    # TODO: b/434254634 - implement
    raise NotImplementedError('Not implemented.')

  def _aspline(
      self,
      x: np.ndarray,
      y: np.ndarray,
      knots: np.ndarray,
      pen: np.ndarray,
      max_iter: int = 1000,
      epsilon: float = 1e-5,
      tol: float = 1e-6,
  ) -> dict[str, Any]:
    """Fits B-splines with automatic knot selection.

    Args:
      x: A flattened array of indexed time coordinates, repeated n_geos times.
        e.g. [ 0, 1, 2, 3, ... , 0, 1, 2, 3, ...].
      y: The flattened array of KPI values that have been population-scaled and
        mean-centered by geo.
      knots: Internal knots used for spline regression.
      pen: A vector of positive penalty values. The adaptive spline regression
        is performed for every value of pen.
      max_iter: Maximum number of iterations in the main loop.
      epsilon: Value of the constant in the adaptive ridge procedure (see
        Frommlet, F., Nuel, G. (2016) An Adaptive Ridge Procedure for L0
        Regularization.)
      tol: The tolerance chosen to diagnose convergence of the adaptive ridge
        procedure.

    Returns:
      A dictionary of the following items:
        sel: A list of selection coefficients for every value of pen.
        knots_sel: A list of selected knots for every value of pen.
        model: A list of fitted models for every value of pen.
        par: A list of estimated regression coefficients for every value of pen.
        sel_mat: A matrix of selected knots for every value of pen.
        aic: A list of AIC values for every value of pen.
        bic: A list of BIC values for every value of pen.
        ebic: A list of EBIC values for every value of pen.
    """
    degree = 1

    bs_cmd = (
        'bs(x,knots=['
        + ','.join(map(str, knots))
        + '],degree='
        + str(degree)
        + ',include_intercept=True)-1'
    )
    xmat = highlevel.dmatrix(bs_cmd, {'x': x})
    nrow = xmat.shape[0]
    ncol = xmat.shape[1]

    xx = xmat.T.dot(xmat)
    xy = xmat.T.dot(y)
    xx_rot = np.concat(
        [
            self._mat2rot(xx + (1e-20 * np.identity(ncol))),
            np.zeros(ncol)[:, np.newaxis],
        ],
        axis=1,
    )
    sigma0sq = linear_model.OLS(y, xmat).fit().mse_resid ** 2
    model, x_sel, knots_sel, sel_ls, par_ls, aic, bic, ebic, dim, loglik = (
        [None] * len(pen) for _ in range(10)
    )
    old_sel, w = [np.ones(ncol - degree - 1) for _ in range(2)]
    par = np.ones(ncol)
    ind_pen = 0
    for _ in range(max_iter):
      par = self._wridge_solver(
          xx_rot, xy, degree, pen[ind_pen], w, old_par=par
      )
      par_diff = np.diff(par, n=degree + 1)
      w = 1 / (par_diff**2 + epsilon**2)
      sel = w * par_diff**2
      converge = max(abs(old_sel - sel)) < tol
      if converge:
        sel_ls[ind_pen] = sel
        knots_sel[ind_pen] = knots[sel > 0.99]
        bs_cmd_iter = (
            f"bs(x,knots=[{','.join(map(str, knots_sel[ind_pen]))}],degree={degree},include_intercept=True)-1"
        )
        design_mat = highlevel.dmatrix(bs_cmd_iter, {'x': x})
        x_sel[ind_pen] = design_mat
        bs_model = linear_model.OLS(y, x_sel[ind_pen]).fit()
        model[ind_pen] = bs_model
        coefs = np.zeros(ncol, dtype=np.float32)
        idx = np.concat([sel > 0.99, np.repeat(True, degree + 1)])
        coefs[idx] = bs_model.params
        par_ls[ind_pen] = coefs

        loglik[ind_pen] = sum(bs_model.resid**2 / sigma0sq) / 2
        dim[ind_pen] = len(knots_sel[ind_pen]) + degree + 1
        aic[ind_pen] = 2 * dim[ind_pen] + 2 * loglik[ind_pen]
        bic[ind_pen] = np.log(nrow) * dim[ind_pen] + 2 * loglik[ind_pen]
        ebic[ind_pen] = bic[ind_pen] + 2 * np.log(
            np.float32(math.comb(ncol, design_mat.shape[1]))
        )
        ind_pen = ind_pen + 1
      if ind_pen > len(pen) - 1:
        break
      old_sel = sel

    sel_mat = np.round(np.stack(sel_ls, axis=-1), 1)
    return {
        'sel': sel_ls,
        'knots_sel': knots_sel,
        'model': model,
        'par': par_ls,
        'sel_mat': sel_mat,
        'aic': np.array(aic),
        'bic': np.array(bic),
        'ebic': np.array(ebic),
    }

  def _mat2rot(self, band_mat: np.ndarray) -> np.ndarray:
    """Rotates a symmetric band matrix to get the rotated matrix associated.

    Each column of the rotated matrix corresponds to a diagonal. The first
    column is the main diagonal, the second one is the upper-diagonal and so on.
    Artificial 0s are placed at the end of each column if necessary.

    Args:
      band_mat: The band square matrix to be rotated.

    Returns:
      The rotated matrix of band_mat.
    """
    p = band_mat.shape[1]
    l = 0
    for i in range(p):
      lprime = np.where(band_mat[i, :] != 0)[0]
      l = np.maximum(l, lprime[len(lprime) - 1] - i)

    rot_mat = np.zeros([p, l + 1])
    rot_mat[:, 0] = np.diag(band_mat)
    if l > 0:
      for j in range(l):
        rot_mat[:, j + 1] = np.concat([
            np.diag(band_mat[range(p - j - 1), :][:, range(j + 1, p)]),
            np.zeros(j + 1),
        ])
    return rot_mat

  def _band_weight(self, w: np.ndarray, diff: int) -> np.ndarray:
    """Creates the penalty matrix for A-Spline.

    Args:
      w: Vector of weights.
      diff: Order of the differences to be applied to the parameters. Must be a
        strictly positive integer.

    Returns:
      Weighted penalty matrix D'diag(w)D, where
      D = diff(diag(len(w) + diff), differences = diff)}. Only the non-null
      superdiagonals of the weight matrix are returned, each column
      corresponding to a diagonal.
    """
    ws = len(w)
    rows = ws + diff
    cols = diff + 1

    # Compute the entries of the difference matrix
    binom = np.zeros(cols, dtype=np.int32)
    for i in range(cols):
      binom[i] = math.comb(diff, i) * (-1) ** i

    # Compute the limit indices
    ind_mat = np.zeros([rows, 2], dtype=np.int32)
    for ind in range(rows):
      ind_mat[ind, 0] = 0 if ind - diff < 0 else ind - diff
      ind_mat[ind, 1] = ind if ind < ws - 1 else ws - 1

    # Main loop
    result = np.zeros([rows, cols])
    for j in range(cols):
      for i in range(rows - j):
        temp = 0.0
        for k in range(ind_mat[i + j, 0], ind_mat[i, 1] + 1):
          temp += binom[i - k] * binom[i + j - k] * w[k]
        result[i, j] = temp

    return result

  def _ldl(self, rot_mat: np.ndarray) -> np.ndarray:
    """Solves the Fast LDL decomposition of symmetric band matrix of length k.

    Args:
      rot_mat: Rotated row-wised matrix of dimensions n*k, with first column
        corresponding to the diagonal, the second to the first super-diagonal
        and so on.

    Returns:
      Solution of the LDL decomposition.
    """
    n = rot_mat.shape[0]
    m = rot_mat.shape[1] - 1
    rot_mat_new = copy.deepcopy(rot_mat)
    for i in range(1, n + 1):
      j0 = np.maximum(1, i - m)
      for j in range(j0, i + 1):
        for k in range(j0, j):
          rot_mat_new[j - 1, i - j] -= (
              rot_mat_new[k - 1, i - k]
              * rot_mat_new[k - 1, j - k]
              * rot_mat_new[k - 1, 0]
          )
        if i > j:
          rot_mat_new[j - 1, i - j] /= rot_mat_new[j - 1, 0]

    return rot_mat_new

  def _bandsolve_kernel(
      self, rot_mat: np.ndarray, rhs_mat: np.ndarray
  ) -> np.ndarray:
    """Solves the symmetric bandlinear system Ax = b.

    This is the kernel function that solves the system, where A is the rotated
    form of the band matrix and b is the right hand side.

    Args:
      rot_mat: Band square matrix in the rotated form. It's the visual rotation
        by 90 degrees of the matrix, where subdiagonal are discarded.
      rhs_mat: right hand side of the equation. Can be either a vector or a
        matrix. If not supplied, the function return the inverse of rot_mat.

    Returns:
      Solution of the linear problem.
    """
    rot_mat_ldl = self._ldl(rot_mat)
    x = copy.deepcopy(rhs_mat)
    n = rot_mat.shape[0]
    k = rot_mat_ldl.shape[1] - 1
    l = rhs_mat.shape[1]

    for l in range(l):
      # solve b=inv(L)b
      for i in range(2, n + 1):
        jmax = np.minimum(i - 1, k)
        for j in range(1, jmax + 1):
          x[i - 1, l] -= rot_mat_ldl[i - j - 1, j] * x[i - j - 1, l]

      # solve b=b/D
      for i in range(n):
        x[i, l] /= rot_mat_ldl[i, 0]

      # solve b=inv(t(L))b=inv(L*D*t(L))b
      for i in range(n - 1, 0, -1):
        jmax = np.minimum(n - i, k)
        for j in range(1, jmax + 1):
          x[i - 1, l] -= rot_mat_ldl[i - 1, j] * x[i + j - 1, l]

    return x

  def _bandsolve(self, rot_mat: np.ndarray, rhs_mat: np.ndarray) -> np.ndarray:
    """Solves the symmetric bandlinear system Ax = b.

    Here A is the rotated form of the band matrix and b is the right hand side.

    Args:
      rot_mat: Band square matrix in the rotated form. It's the visual rotation
        by 90 degrees of the matrix, where subdiagonal are discarded.
      rhs_mat: right hand side of the equation. Can be either a vector or a
        matrix. If not supplied, the function return the inverse of rot_mat.

    Returns:
      Solution of the linear problem.
    """

    nrow = rot_mat.shape[0]
    ncol = rot_mat.shape[1]
    if (nrow == ncol) & (rot_mat[nrow - 1, ncol - 1] != 0):
      raise ValueError('rot_mat should be a rotated matrix!')
    if rot_mat[nrow - 1, 1] != 0:
      raise ValueError('rot_mat should be a rotated matrix!')

    if rhs_mat.ndim == 1:
      if len(rhs_mat) != nrow:
        raise ValueError('Dimension problem!')
      else:
        return self._bandsolve_kernel(rot_mat, rhs_mat[:, np.newaxis])
    elif rhs_mat.ndim == 2:
      if rhs_mat.shape[0] != nrow:
        raise ValueError('Dimension problem!')
      else:
        return self._bandsolve_kernel(rot_mat, rhs_mat[:, np.newaxis])
    else:
      raise ValueError('rhs_mat must either be a vector or a matrix')

  def _wridge_solver(
      self,
      xx_rot: np.ndarray,
      xy: np.ndarray,
      degree: int,
      pen: float,
      w: np.ndarray,
      old_par: np.ndarray,
      max_iter: int = 1000,
      tol: float = 1e-8,
  ) -> np.ndarray | None:
    """Fits B-Splines with weighted penalization over differences of parameters.

    Args:
      xx_rot: The matrix X'X where X is the design matrix. This argument is
        given in the form of a band matrix, i.e., successive columns represent
        superdiagonals.
      xy: The vector of currently estimated points X'y, where y is the
        y-coordinate of the data.
      degree: The degree of the B-splines.
      pen: Positive penalty constant.
      w: Vector of weights. The case w = np.ones(xx_rot.shape[0] - degree - 1)
        corresponds to fitting P-splines with difference order degree + 1. See
        Eilers, P., Marx, B. (1996) Flexible smoothing with B-splines and
        penalties.
      old_par: The previous parameter vector.
      max_iter: Maximum number of Newton-Raphson iterations to be computed.
      tol: The tolerance chosen to diagnose convergence of the adaptive ridge
        procedure.

    Returns:
      The estimated parameter of the spline regression.
    """

    def _hessian_solver(par, xx_rot, xy, pen, w, diff):
      """Inverts the hessian and multiplies it by the score.

      Args:
        par: The parameter vector.
        xx_rot: The matrix X'X where X is the design matrix. This argument is
          given in the form of a rotated band matrix, i.e., successive columns
          represent superdiagonals.
        xy: The vector of currently estimated points X'y, where y is the
          y-coordinate of the data.
        pen: Positive penalty constant.
        w: Vector of weights.
        diff: The order of the differences of the parameter. Equals degree + 1
          in adaptive spline regression.

      Returns:
        The solution of the linear system: (X'X + pen*D'WD)^{-1} X'y - par
      """
      if xx_rot.shape[1] != diff + 1:
        raise ValueError('Error: xx_rot must have diff + 1 columns')
      return (
          self._bandsolve(xx_rot + pen * self._band_weight(w, diff), xy)[:, 0]
          - par
      )

    par = None
    for _ in range(max_iter):
      par = old_par + _hessian_solver(
          par=old_par, xx_rot=xx_rot, xy=xy, pen=pen, w=w, diff=degree + 1
      )
      ind = old_par != 0
      rel_error = max(abs(par - old_par)[ind] / abs(old_par)[ind])
      if rel_error < tol:
        break
      old_par = par

    return par
