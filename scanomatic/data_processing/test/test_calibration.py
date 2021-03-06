import numpy as np
import pytest
from collections import namedtuple
from scanomatic.data_processing import calibration

data = calibration.load_data_file()


@pytest.fixture(scope='module')
def ccc():

    _ccc = calibration.get_empty_ccc('test-ccc', 'pytest')
    calibration.__CCC[_ccc[calibration.CellCountCalibration.identifier]] = _ccc
    yield _ccc
    del calibration.__CCC[_ccc[calibration.CellCountCalibration.identifier]]


def test_load_data():

    assert calibration.load_data_file() is not None


def test_load_calibration():

    assert calibration.load_calibration() is not None


def test_expand_data_lenghts():

    counts = data[calibration.CalibrationEntry.source_value_counts]
    exp_vals, _, _, _ = calibration._get_expanded_data(data)
    assert all(np.sum(c) == len(v) for c, v in zip(counts, exp_vals))


def test_expand_data_sums():

    counts = data[calibration.CalibrationEntry.source_value_counts]
    values = data[calibration.CalibrationEntry.source_values]
    data_sums = np.array(
        tuple(np.sum(np.array(c) * np.array(v))
              for c, v in zip(counts, values)))

    exp_vals, _, _, _ = calibration._get_expanded_data(data)
    expanded_sums = np.array(tuple(v.sum() for v in exp_vals), dtype=np.float)
    np.testing.assert_allclose(expanded_sums, data_sums)


def test_expand_data_targets():

    _, targets, _, _ = calibration._get_expanded_data(data)
    np.testing.assert_allclose(
        targets.astype(np.float),
        data[calibration.CalibrationEntry.target_value])


def test_expand_vector_length():

    counts = [20, 3, 5, 77, 2, 35]
    values = [20, 21, 23, 24, 26, 27]
    expanded = calibration._expand_compressed_vector(values, counts, np.float)
    assert sum(counts) == expanded.size


def test_expanded_vector_sum():
    counts = [20, 3, 5, 77, 2, 35]
    values = [20, 21, 23, 24, 26, 27]
    data_sum = np.sum(np.array(counts) * np.array(values))
    expanded = calibration._expand_compressed_vector(values, counts, np.float)
    np.testing.assert_allclose(expanded.sum(), data_sum)


def test_calibration_opt_func():

    poly = calibration.get_calibration_optimization_function(2)
    assert poly([2], 1, 1)[0] == 6
    assert poly([2], 2, 0)[0] == 4
    assert poly([2], 0, 2)[0] == 8
    poly = calibration.get_calibration_optimization_function(4)
    assert poly([1], 1, 1)[0] == 2
    assert poly([1], 2, 0)[0] == 2
    assert poly([1], 0, 2)[0] == 2
    assert poly([2], 0, 1)[0] == 16


@pytest.mark.skip("There is no data to test on yet")
def test_calculate_polynomial():
    degree = 4
    poly = calibration.calculate_polynomial(data, degree=degree)
    assert poly.size == degree + 1
    np.testing.assert_allclose(poly[1:-2], 0)
    np.testing.assert_allclose(poly[-1], 0)
    assert np.unique(poly).size > 1


@pytest.mark.skip("There is no data to test on yet")
def test_polynomial():

    poly_coeffs = calibration.calculate_polynomial(data)
    poly = calibration.get_calibration_polynomial(poly_coeffs)
    validity = calibration.validate_polynomial(data, poly)

    if validity == calibration.CalibrationValidation.BadSlope:
        raise AssertionError(calibration.CalibrationValidation.BadSlope)

    elif validity == calibration.CalibrationValidation.BadIntercept:
        raise AssertionError(calibration.CalibrationValidation.BadIntercept)

    elif validity == calibration.CalibrationValidation.BadStatistics:
        raise AssertionError(calibration.CalibrationValidation.BadStatistics)


def test_get_im_slice():
    """Test that _get_im_slice handles floats"""
    image = np.arange(0, 42).reshape((6, 7))
    model_tuple = namedtuple("Model", ['x1', 'x2', 'y1', 'y2'])
    model = model_tuple(1.5, 3.5, 2.5, 4.5)
    assert calibration._get_im_slice(image, model).sum() == 207


class TestAccessToken:

    def test_invalid_token(self, ccc):

        assert not calibration.is_valid_token(
            ccc[calibration.CellCountCalibration.identifier])

        assert not calibration.is_valid_token(
            ccc[calibration.CellCountCalibration.identifier],
            access_token='bad')

    def test_valid_token(self, ccc):

        assert calibration.is_valid_token(
            ccc[calibration.CellCountCalibration.identifier],
            access_token=ccc[
                calibration.CellCountCalibration.edit_access_token]) is True
