"""Deals image as used by first pass analysis"""

__author__ = "Martin Zackrisson"
__copyright__ = "Swedish copyright laws apply"
__credits__ = ["Martin Zackrisson", "Andreas Skyman"]
__license__ = "GPL v3.0"
__version__ = "0.9991"
__maintainer__ = "Martin Zackrisson"
__email__ = "martin.zackrisson@gu.se"
__status__ = "Development"


#
# DEPENDENCIES
#

import time
import itertools
import numpy as np
from matplotlib.pyplot import imread

#
# SCANNOMATIC LIBRARIES
#

from scanomatic.io.grid_history import GriddingHistory
from scanomatic.io.logger import Logger
from scanomatic.io.fixtures import FixtureSettings
from scanomatic.models.factories.fixture_factories import FixturePlateFactory

import imageBasics
import imageFixture
import imageGrayscale


def _get_coords_sorted(coords):

    return zip(*map(sorted, zip(*coords)))


def get_image_scale(im):

    small_error = 0.01
    invalid_scale = -1.0

    if im is not None:

        scale_d1, scale_d2 = [im.shape[i] / float(FixtureImage.EXPECTED_IM_SIZE[i]) for i in range(2)]

        if abs(scale_d1 - scale_d2) < small_error:

            return (scale_d1 + scale_d2) / 2.0

        return invalid_scale


def _get_rotated_vector(x, y, rotation):

    return x * np.cos(rotation), y * np.sin(rotation)


class FixtureImage(object):

    MARKER_DETECTION_SCALE = 0.25
    EXPECTED_IM_SIZE = (6000, 4800)

    def __init__(self, fixture=None):

        """

        :type fixture: scanomatic.io.fixtures.FixtureSettings
        """
        self._logger = Logger("Fixture Image")

        self._reference_fixture_settings = fixture
        self._current_fixture_settings = None
        """:type : scanomatic.io.fixtures.Fixture_Settings"""
        if fixture:
            self._history = GriddingHistory(fixture)
        else:
            self._history = None

        self.im = None
        self.im_original_scale = None
        self.im_path = None
        self._name = "default"

    def __getitem__(self, key):

        if key in ['current']:
            if self._current_fixture_settings is None:
                self._current_fixture_settings = FixtureSettings(self.name)
            return self._current_fixture_settings

        elif key in ['fixture', 'reference']:
            if self._reference_fixture_settings is None:
                self._reference_fixture_settings = FixtureSettings(self.name)
                self._name = self.name

            return self._reference_fixture_settings

        else:

            raise KeyError(key)

    @property
    def name(self):

        if self._reference_fixture_settings:
            return self._reference_fixture_settings.model.name
        else:
            return self._name

    @name.setter
    def name(self, value):

        if self._reference_fixture_settings:
            self._reference_fixture_settings.model.name = value
        else:
            self._name = value


    def set_image(self, image=None, image_path=None):

        self.im_path = image_path

        if image is not None:

            self.im = image

        elif image_path is not None:

            self.im = imread(image_path)
            if self.im is None:
                self._logger.error("Could not load image")

            else:
                self._logger.info("Loaded image {0} with shape {1}".format(image_path, self.im.shape))
        else:

            self._logger.warning("No information supplied about how to load image, thus none loaded")

            self.im = None

        self.im_original_scale = get_image_scale(self.im)

    def analyse_current(self):

        logger = self._logger

        t = time.time()
        logger.debug("Threading invokes marker analysis")

        self.run_marker_analysis()

        logger.debug(
            "Threading marker detection complete," +
            "invokes setting area positions (acc-time {0} s)".format(
                time.time() - t))

        self.set_current_areas()

        logger.debug(
            "Threading areas set(acc-time: {0} s)".format(time.time() - t))

        self.analyse_grayscale()

        logger.debug(
            "Grayscale ({0}) analysed (acc-time: {1} s)".format(
                self['grayscale_type'],
                time.time() - t))

        logger.debug(
            "Threading done (took: {0} s)".format(time.time() - t))

    def _get_markings(self, source='reference'):

        markers = self[source].get_marker_positions()

        if markers:

            return np.array(markers[0]), np.array(markers[1])

        return None, None

    def run_marker_analysis(self, markings=None):

        _logger = self._logger

        t = time.time()
        if markings is None:
            markings = len(self["fixture"].model.orientation_marks_x)

        _logger.info("Running marker detection ({0} markers on {1})".format(markings, self.im_path))

        analysis_img = self._get_image_in_correct_scale()

        im_analysis = imageFixture.FixtureImage(
            image=analysis_img,
            pattern_image_path=self["reference"].get_marker_path(),
            scale=self['reference'].model.scale)

        x_positions, y_positions = im_analysis.find_pattern(markings=markings)

        self["current"].model.orientation_marks_x = x_positions
        self["current"].model.orientation_marks_y = y_positions

        if x_positions is None or y_positions is None:

            _logger.error("No markers found")

        _logger.debug("Marker Detection complete (acc {0} s)".format(time.time() - t))

    def _get_image_in_correct_scale(self):

        scale = self['reference'].model.scale
        if scale is None or scale == self.im_original_scale:
            analysis_img = self.im
        else:
            analysis_img = imageBasics.Quick_Scale_To_im(
                im=self.im,
                scale=self.MARKER_DETECTION_SCALE / self.im_original_scale)

        return analysis_img

    def _set_current_mark_order(self):

        x_centered, y_centered = self._get_centered_mark_positions("current")
        x_centered_ref, y_centered_ref = self._get_centered_mark_positions("reference")

        if all(o is not None and o.size > 0 for o in (x_centered, y_centered, x_centered_ref, y_centered_ref)):

            length = np.sqrt(x_centered ** 2 + y_centered ** 2)
            length_ref = np.sqrt(x_centered_ref ** 2 + y_centered_ref ** 2)

            sort_order, sort_error = self._get_sort_order(length, length_ref)

            self._logger.debug(
                "Found sort order that matches the reference {0} (error {1})".format(sort_order, sort_error))

            self.__set_current_mark_order(sort_order)

        else:

            self._logger.critical("Missmatch in number of markings!")

    def __set_current_mark_order(self, sort_order):

        current_model = self["current"].model
        current_model.orientation_marks_x = current_model.orientation_marks_x[sort_order]
        current_model.orientation_marks_y = current_model.orientation_marks_y[sort_order]

    def _get_centered_mark_positions(self, source="current"):

        x_positions = self[source].model.orientation_marks_x
        y_positions = self[source].model.orientation_marks_y

        if x_positions is None or y_positions is None:
            return None, None

        x_positions = np.array(x_positions)
        y_positions = np.array(y_positions)

        marking_center = np.array((x_positions.mean(), y_positions.mean()))

        x_centered = x_positions - marking_center[0]
        y_centered = y_positions - marking_center[1]

        return x_centered, y_centered

    @staticmethod
    def _get_sort_order(length, reference_length):

        s = range(len(length))

        length_deltas = []
        sort_orders = []
        for sort_order in itertools.permutations(s):

            length_deltas.append((length[list(sort_order)] - reference_length) ** 2)
            sort_orders.append(sort_order)

        length_deltas = np.array(length_deltas).sum(1)
        return list(sort_orders[length_deltas.argmin()]), np.sqrt(length_deltas.min())

    def _get_rotation(self):

        x_centered, y_centered = self._get_centered_mark_positions("current")
        x_centered_ref, y_centered_ref = self._get_centered_mark_positions("reference")
        length = np.sqrt(x_centered ** 2 + y_centered ** 2)
        length_ref = np.sqrt(x_centered_ref ** 2 + y_centered_ref ** 2)

        rotations = np.arccos(x_centered / length)
        rotations = rotations * (y_centered > 0) + -1 * rotations * (y_centered < 0)

        rotations_ref = np.arccos(x_centered_ref / length_ref)
        rotations_ref = rotations_ref * (y_centered_ref > 0) + -1 * rotations_ref * (y_centered_ref < 0)

        """:type : float"""
        return (rotations - rotations_ref).mean()

    def _get_offset(self):

        current_model = self['current'].model
        ref_model = self['reference'].model

        x_delta = current_model.orientation_marks_x - ref_model.orientation_marks_x
        y_delta = current_model.orientation_marks_y - ref_model.orientation_marks_y
        return x_delta.mean(), y_delta.mean()

    def get_plate_im_section(self, plate_model, scale=1.0):

        """

        :type plate_model: scanomatic.models.fixture_models.FixturePlateModel
        """
        im = self.im

        if im is not None and plate_model is not None:

            try:

                return im[max(plate_model.y1 * scale, 0): min(plate_model.y2 * scale, im.shape[0]),
                          max(plate_model.x2 * scale, 0): min(plate_model.x2 * scale, im.shape[1])]

            except (IndexError, TypeError):

                return None

    def get_grayscale_im_section(self, grayscale_model, scale=1.0):
        """

        :type grayscale_model: scanomatic.models.fixture_models.GrayScaleAreaModel
        """
        im = self.im

        if im is not None and grayscale_model is not None:

            try:

                return im[max(grayscale_model.y1 * scale, 0): min(grayscale_model.y2 * scale, im.shape[0]),
                          max(grayscale_model.x1 * scale, 0): min(grayscale_model.x2 * scale, im.shape[1])]

            except (IndexError, TypeError):

                return None

    def analyse_grayscale(self):

        current_model = self["current"].model
        im = self.get_grayscale_im_section(current_model.grayscale, scale=1.0)


        if im is None or 0 in im.shape:
            err = "No valid grayscale area. "
            if self.im is None:
                self._logger.error(err + "No image loaded")
            elif current_model.grayscale is None:
                self._logger.error(err + "Grayscale area model not set")
            elif im is None:
                self._logger.error(err + "Image (shape {0}) could not be sliced according to {1}".format(
                    self.im.shape, dict(**current_model.grayscale)))
            elif 0 in im.shape:
                self._logger.error(err + "Grayscale area has bad shape ({0})".format(im.shape))

            return False

        current_model.grayscale.values = imageGrayscale.get_grayscale(self, current_model.grayscale)[1]

    def _set_area_relative(self, area, rotation=None, offset=(0, 0)):

        """

        :type area: scanomatic.models.fixture_models.FixturePlateModel |  scanomatic.models.fixture_models.GrayScaleAreaModel
        """

        if rotation:
            self._logger.warning("Not supporting rotations yet (got {0})".format(rotation))
            # area.x1, area.y1 = _get_rotated_vector(area.x1, area.y1, rotation)
            # area.x2, area.y2 = _get_rotated_vector(area.x2, area.y2, rotation)

        for dim, keys in {1: ('x1', 'x2'), 0: ('y1', 'y2')}.items():
            for key in keys:
                area[key] += offset[dim]
                if area[key] > self.EXPECTED_IM_SIZE[dim]:
                    self._logger.warning("{0} value ({1}) outside image, setting to img border".format(key, area[key]))
                    area[key] = self.EXPECTED_IM_SIZE[dim]
                elif area[key] < 0:
                    self._logger.warning("{0} value ({1}) outside image, setting to img border".format(key, area[key]))
                    area[key] = 0

    def set_current_areas(self):

        self._set_current_mark_order()
        offset = self._get_offset()
        rotation = self._get_rotation()
        current_model = self["current"].model
        ref_model = self["fixture"].model

        self._logger.info(
            "Positions on current '{0}' will be moved {1} and rotated {2} due to diff to reference {3}".format(
                current_model.name, offset, rotation, ref_model.name))

        while current_model.plates:
            current_model.plates.pop()

        for plate in ref_model.plates:
            cur_plate = FixturePlateFactory.copy(plate)
            current_model.plates.append(cur_plate)
            self._set_area_relative(cur_plate, rotation, offset)

        self._set_area_relative(current_model.grayscale, rotation, offset)