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

from absl.testing import absltest
from absl.testing import parameterized
from meridian import constants
from meridian.model import model
from meridian.model import model_test_data
from meridian.model.eda import eda_engine
import tensorflow as tf
import xarray as xr


class EDAEngineTest(
    parameterized.TestCase,
    model_test_data.WithInputDataSamples,
    tf.test.TestCase,
):

  def setUp(self):
    super().setUp()
    model_test_data.WithInputDataSamples.setup(self)

  # --- Test cases for controls_scaled_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_with_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_CONTROLS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_CONTROLS,
          ),
      ),
  )
  def test_controls_scaled_da_present(self, input_data_fixture, expected_shape):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    controls_scaled_da = engine.controls_scaled_da
    self.assertIsInstance(controls_scaled_da, xr.DataArray)
    self.assertEqual(controls_scaled_da.shape, expected_shape)
    self.assertCountEqual(
        controls_scaled_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.CONTROL_VARIABLE],
    )
    self.assertAllClose(controls_scaled_da.values, meridian.controls_scaled)

  # --- Test cases for media_raw_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_with_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_MEDIA_CHANNELS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_MEDIA_CHANNELS,
          ),
      ),
  )
  def test_media_raw_da_present(self, input_data_fixture, expected_shape):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    media_da = engine.media_raw_da
    self.assertIsInstance(media_da, xr.DataArray)
    self.assertEqual(media_da.shape, expected_shape)
    self.assertCountEqual(
        media_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.MEDIA_CHANNEL],
    )
    start = meridian.n_media_times - meridian.n_times
    true_media_da = meridian.input_data.media
    self.assertIsInstance(true_media_da, xr.DataArray)
    self.assertAllClose(media_da.values, true_media_da.values[:, start:, :])

  # --- Test cases for media_scaled_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_with_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_MEDIA_CHANNELS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_MEDIA_CHANNELS,
          ),
      ),
  )
  def test_media_scaled_da_present(self, input_data_fixture, expected_shape):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    media_da = engine.media_scaled_da
    self.assertIsInstance(media_da, xr.DataArray)
    self.assertEqual(media_da.shape, expected_shape)
    self.assertCountEqual(
        media_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.MEDIA_CHANNEL],
    )
    start = meridian.n_media_times - meridian.n_times
    self.assertAllClose(
        media_da.values, meridian.media_tensors.media_scaled[:, start:, :]
    )

  # --- Test cases for media_spend_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_with_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_MEDIA_CHANNELS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_MEDIA_CHANNELS,
          ),
      ),
  )
  def test_media_spend_da_present(self, input_data_fixture, expected_shape):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    media_da = engine.media_spend_da
    self.assertIsInstance(media_da, xr.DataArray)
    self.assertEqual(media_da.shape, expected_shape)
    self.assertCountEqual(
        media_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.MEDIA_CHANNEL],
    )
    self.assertAllClose(media_da.values, meridian.media_tensors.media_spend)

  # --- Test cases for organic_media_raw_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_non_media_and_organic",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_ORGANIC_MEDIA_CHANNELS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_non_media_and_organic",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_ORGANIC_MEDIA_CHANNELS,
          ),
      ),
  )
  def test_organic_media_raw_da_present(
      self, input_data_fixture, expected_shape
  ):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    organic_media_da = engine.organic_media_raw_da
    self.assertIsInstance(organic_media_da, xr.DataArray)
    self.assertEqual(organic_media_da.shape, expected_shape)
    self.assertCountEqual(
        organic_media_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.ORGANIC_MEDIA_CHANNEL],
    )
    start = meridian.n_media_times - meridian.n_times
    true_organic_media_da = meridian.input_data.organic_media
    self.assertIsInstance(true_organic_media_da, xr.DataArray)
    self.assertAllClose(
        organic_media_da.values, true_organic_media_da.values[:, start:, :]
    )

  # --- Test cases for organic_media_scaled_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_non_media_and_organic",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_ORGANIC_MEDIA_CHANNELS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_non_media_and_organic",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_ORGANIC_MEDIA_CHANNELS,
          ),
      ),
  )
  def test_organic_media_scaled_da_present(
      self, input_data_fixture, expected_shape
  ):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    organic_media_da = engine.organic_media_scaled_da
    self.assertIsInstance(organic_media_da, xr.DataArray)
    self.assertEqual(organic_media_da.shape, expected_shape)
    self.assertCountEqual(
        organic_media_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.ORGANIC_MEDIA_CHANNEL],
    )
    start = meridian.n_media_times - meridian.n_times
    self.assertAllClose(
        organic_media_da.values,
        meridian.organic_media_tensors.organic_media_scaled[:, start:, :],
    )

  # --- Test cases for non_media_scaled_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_non_media_and_organic",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_NON_MEDIA_CHANNELS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_non_media_and_organic",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_NON_MEDIA_CHANNELS,
          ),
      ),
  )
  def test_non_media_scaled_da_present(
      self, input_data_fixture, expected_shape
  ):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    non_media_da = engine.non_media_scaled_da
    self.assertIsInstance(non_media_da, xr.DataArray)
    self.assertEqual(non_media_da.shape, expected_shape)
    self.assertCountEqual(
        non_media_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.NON_MEDIA_CHANNEL],
    )
    self.assertAllClose(
        non_media_da.values, meridian.non_media_treatments_normalized
    )

  # --- Test cases for rf_spend_da ---
  @parameterized.named_parameters(
      dict(
          testcase_name="geo",
          input_data_fixture="input_data_with_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_RF_CHANNELS,
          ),
      ),
      dict(
          testcase_name="national",
          input_data_fixture="national_input_data_media_and_rf",
          expected_shape=(
              model_test_data.WithInputDataSamples._N_GEOS_NATIONAL,
              model_test_data.WithInputDataSamples._N_TIMES,
              model_test_data.WithInputDataSamples._N_RF_CHANNELS,
          ),
      ),
  )
  def test_rf_spend_da_present(self, input_data_fixture, expected_shape):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    rf_spend_da = engine.rf_spend_da
    self.assertIsInstance(rf_spend_da, xr.DataArray)
    self.assertEqual(rf_spend_da.shape, expected_shape)
    self.assertCountEqual(
        rf_spend_da.coords.keys(),
        [constants.GEO, constants.TIME, constants.RF_CHANNEL],
    )
    self.assertAllClose(rf_spend_da.values, meridian.rf_tensors.rf_spend)

  @parameterized.named_parameters(
      dict(
          testcase_name="controls_scaled_da",
          input_data_fixture="input_data_with_media_and_rf_no_controls",
          property_name="controls_scaled_da",
      ),
      dict(
          testcase_name="media_raw_da",
          input_data_fixture="input_data_with_rf_only",
          property_name="media_raw_da",
      ),
      dict(
          testcase_name="media_scaled_da",
          input_data_fixture="input_data_with_rf_only",
          property_name="media_scaled_da",
      ),
      dict(
          testcase_name="media_spend_da",
          input_data_fixture="input_data_with_rf_only",
          property_name="media_spend_da",
      ),
      dict(
          testcase_name="organic_media_raw_da",
          input_data_fixture="input_data_with_media_and_rf",
          property_name="organic_media_raw_da",
      ),
      dict(
          testcase_name="organic_media_scaled_da",
          input_data_fixture="input_data_with_media_and_rf",
          property_name="organic_media_scaled_da",
      ),
      dict(
          testcase_name="non_media_scaled_da",
          input_data_fixture="input_data_with_media_and_rf",
          property_name="non_media_scaled_da",
      ),
      dict(
          testcase_name="rf_spend_da",
          input_data_fixture="input_data_with_media_only",
          property_name="rf_spend_da",
      ),
  )
  def test_property_absent(self, input_data_fixture, property_name):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)
    self.assertIsNone(getattr(engine, property_name))

  @parameterized.named_parameters(
      dict(
          testcase_name="n_media_times_gt_n_times",
          input_data_fixture="input_data_non_media_and_organic",
      ),
      dict(
          testcase_name="n_media_times_eq_n_times",
          input_data_fixture="input_data_non_media_and_organic_same_time_dims",
      ),
  )
  def test_properties_are_truncated(self, input_data_fixture):
    meridian = model.Meridian(getattr(self, input_data_fixture))
    engine = eda_engine.EDAEngine(meridian)

    properties_to_test = [
        engine.media_raw_da,
        engine.media_scaled_da,
        engine.organic_media_raw_da,
        engine.organic_media_scaled_da,
    ]

    for prop in properties_to_test:
      self.assertIsInstance(prop, xr.DataArray)
      self.assertEqual(
          prop.sizes[constants.TIME],
          model_test_data.WithInputDataSamples._N_TIMES,
      )
      self.assertNotIn(constants.MEDIA_TIME, prop.coords)
      self.assertIn(constants.TIME, prop.coords)


if __name__ == "__main__":
  absltest.main()
