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

"""Meridian EDA Engine."""

import functools
from meridian import constants
from meridian.model import model
import numpy as np
import tensorflow as tf
import xarray as xr


class EDAEngine:
  """Meridian EDA Engine."""

  def __init__(self, meridian: model.Meridian):
    self._meridian = meridian

  @functools.cached_property
  def controls_scaled_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.controls is None:
      return None
    controls_scaled_da = _data_array_like(
        da=self._meridian.input_data.controls,
        values=self._meridian.controls_scaled,
    )
    return controls_scaled_da

  @functools.cached_property
  def media_raw_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.media is None:
      return None
    return self._truncate_media_time(self._meridian.input_data.media)

  @functools.cached_property
  def media_scaled_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.media is None:
      return None
    media_scaled_da = _data_array_like(
        da=self._meridian.input_data.media,
        values=self._meridian.media_tensors.media_scaled,
    )
    return self._truncate_media_time(media_scaled_da)

  @functools.cached_property
  def media_spend_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.media_spend is None:
      return None
    media_spend_da = _data_array_like(
        da=self._meridian.input_data.media_spend,
        values=self._meridian.media_tensors.media_spend,
    )
    # No need to truncate the media time for media spend.
    return media_spend_da

  @functools.cached_property
  def organic_media_raw_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.organic_media is None:
      return None
    return self._truncate_media_time(self._meridian.input_data.organic_media)

  @functools.cached_property
  def organic_media_scaled_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.organic_media is None:
      return None
    organic_media_scaled_da = _data_array_like(
        da=self._meridian.input_data.organic_media,
        values=self._meridian.organic_media_tensors.organic_media_scaled,
    )
    return self._truncate_media_time(organic_media_scaled_da)

  @functools.cached_property
  def non_media_scaled_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.non_media_treatments is None:
      return None
    non_media_scaled_da = _data_array_like(
        da=self._meridian.input_data.non_media_treatments,
        values=self._meridian.non_media_treatments_normalized,
    )
    return non_media_scaled_da

  @functools.cached_property
  def rf_spend_da(self) -> xr.DataArray | None:
    if self._meridian.input_data.rf_spend is None:
      return None
    rf_spend_da = _data_array_like(
        da=self._meridian.input_data.rf_spend,
        values=self._meridian.rf_tensors.rf_spend,
    )
    return rf_spend_da

  def _truncate_media_time(self, da: xr.DataArray) -> xr.DataArray:
    """Truncates the first `start` elements of the media time of a variable."""
    # This should not happen. If it does, it means this function is mis-used.
    if constants.MEDIA_TIME not in da.coords:
      raise ValueError(
          f"Variable does not have a media time coordinate: {da.name}"
      )

    start = self._meridian.n_media_times - self._meridian.n_times
    da = da.copy().isel({constants.MEDIA_TIME: slice(start, None)})
    da = da.rename({constants.MEDIA_TIME: constants.TIME})
    return da


def _data_array_like(
    *, da: xr.DataArray, values: np.ndarray | tf.Tensor
) -> xr.DataArray:
  """Returns a DataArray from `values` with the same structure as `da`.

  Args:
    da: The DataArray whose structure (dimensions, coordinates, name, and attrs)
      will be used for the new DataArray.
    values: The numpy array or tensorflow tensor to use as the values for the
      new DataArray.

  Returns:
    A new DataArray with the provided `values` and the same structure as `da`.
  """
  return xr.DataArray(
      values,
      coords=da.coords,
      dims=da.dims,
      name=da.name,
      attrs=da.attrs,
  )
