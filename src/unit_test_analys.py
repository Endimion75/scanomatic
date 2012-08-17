#!/usr/bin/env python

import unittest
import analysis_grid_cell_dissection as gc
import numpy as np


class Test_Grid_Cell_Item(unittest.TestCase):

    Item = gc.Cell_Item

    def test_load_no_parent(self):

        I = np.random.random((100, 100))
        i = self.Item(None, None, I)

        self.assertEqual((I == i.grid_array).sum(), I.shape[0] * I.shape[1])

    def test_identity(self):

        Id = ["test", 1, [1, 3]]

        i = self.Item(None, Id, np.zeros((100, 100)))

        self.assertEqual(Id, i._identifier)

    def test_filter_shape(self):

        I = np.random.random(np.random.randint(50, 150, 2))

        i = self.Item(None, None, I)

        self.assertTupleEqual(I.shape, i.filter_array.shape)

    def test_logging_behaviour(self):

        i = self.Item(None, None, np.zeros((100, 100)))

        i.logger.info("Test")
        i.logger.debug("Test")
        i.logger.warning("Test")
        i.logger.error("Test")
        i.logger.critical("Test")

    def test_get_round_kernel(self):

        refs = []
        tests = []

        i = self.Item(None, None, np.zeros((100, 100)))

        for x in xrange(10):

            r = np.random.randint(5, 15)

            c = i.get_round_kernel(radius=r)

            self.assertAlmostEqual(abs(1 - np.pi * r ** 2 / c.sum()), 0.000,
                                                                    places=1)

    def test_do_analysis(self):

        i = self.Item(None, None, np.zeros((100, 100)))

        ret = i.do_analysis()

        self.assertEqual(ret, None)

        self.assertDictEqual(i.features, dict())

    def test_set_data_source(self):

        I1 = np.random.random((100, 100))

        i = self.Item(None, None, I1)

        I2 = np.random.random((105, 104))

        i.set_data_source(I2)

        self.assertIs(i.grid_array, I2)
        self.assertIsNot(i.grid_array, I1)

        self.assertEqual((I2 == i.grid_array).sum(),
                            I2.shape[0] * I2.shape[1])

        self.assertTupleEqual(I2.shape, i.filter_array.shape)



class Test_Grid_Cell_Cell(Test_Grid_Cell_Item):

    Item = gc.Cell

    def setUp(self):

        self.i_shape = (105, 104)
        self.I = np.random.random(self.i_shape)

    def test_filter(self):

        c = self.Item(None, None, self.I)

        self.assertEqual(c.filter_array.sum(), self.I.shape[0]*self.I.shape[1])

    def test_do_analysis(self):

        i = self.Item(None, None, self.I)

        ret = i.do_analysis()

        self.assertEqual(ret, None)

        k = sorted(i.features.keys())

        self.assertListEqual(k, sorted(('area', 'pixelsum', 'mean',
                        'median', 'IQR', 'IQR_mean')))

        self.assertEquals(i.features['area'], self.I.shape[0] * self.I.shape[1])
        self.assertAlmostEqual(i.features['mean'], self.I.mean(), places=3)

        self.assertAlmostEqual(i.features['median'], np.median(self.I),
                                                            places=3)

        self.assertEquals(i.features['pixelsum'], self.I.sum())

    def test_type(self):

        i = self.Item(None, None, self.I)

        self.assertEqual(i.CELLITEM_TYPE, 3)

class Test_Grid_Cell_Blob(Test_Grid_Cell_Item):

    Item = gc.Blob

    def setUp(self):

        self.i_shape = (105, 104)
        self.I = np.random.random(self.i_shape)

    def test_do_analysis(self):

        i = self.Item(None, None, self.I)

        ret = i.do_analysis()

        self.assertEqual(ret, None)

        k = sorted(i.features.keys())

        self.assertListEqual(k, sorted(('area', 'pixelsum', 'mean',
                        'median', 'IQR', 'IQR_mean', 'perimeter',
                        'centroid')))

        #self.assertEquals(i.features['area'], I.shape[0] * I.shape[1])
        #self.assertAlmostEqual(i.features['mean'], I.mean(), places=3)
        #self.assertAlmostEqual(i.features['median'], np.median(I), places=3)
        #self.assertEquals(i.features['pixelsum'], I.sum())

    def test_set_blob_from_shape_circle(self):

        I = np.random.random((105,104))

        i = self.Item(None, None, I)

        r = np.random.randint(10, 20)

        i.set_blob_from_shape(circle=((50, 50), r))

        self.assertTupleEqual(i.filter_array.shape, I.shape)

        i.do_analysis()

        self.assertAlmostEqual(abs(1 - np.pi * r ** 2 / i.features['area']), 0.000,
                                                                places=1)

    def test_set_blob_from_shape_rect(self):

        i = self.Item(None, None, self.I)

        rect = [[21, 24], [56, 71]]
        r_area = (rect[1][0] - rect[0][0], rect[1][1] - rect[0][1])
 
        i.set_blob_from_shape(rect=rect)

        self.assertTupleEqual(i.filter_array.shape, self.I.shape)

        i.do_analysis()

        self.assertEqual(i.features['area'], r_area[0] * r_area[1])

    def test_full_empty_filters(self):

        i = self.Item(None, None, self.I)

        i.filter_array = np.zeros(self.i_shape)

        i.do_analysis()

        self.assertEqual(i.features['area'], 0)
        self.assertEqual(i.features['pixelsum'], 0)

        i.filter_array = np.ones(self.i_shape)

        i.do_analysis()

        self.assertEqual(i.features['area'], self.i_shape[0] * self.i_shape[1])
        self.assertEqual(i.features['pixelsum'], self.I.sum())

    def test_type(self):

        i = self.Item(None, None, self.I)

        self.assertEqual(i.CELLITEM_TYPE, 1)

    def test_thresholds(self):

        locA = 2
        locB = 30
        locC = 200

        I1 = np.random.normal(locA, size=self.i_shape)
        I2 = np.random.normal(locB, size=self.i_shape)

        I = np.random.randint(0, 2, self.i_shape)

        I[np.where(I == 1)] = I1[np.where(I == 1)]
        I[np.where(I == 0)] = I2[np.where(I == 0)]

        i = self.Item(None, None, I)


        for t in xrange(-5, 10):

            i.set_threshold(threshold=t)

            self.assertEqual(i.threshold, t)

        t2 = np.random.randint(5, 15)
        i.set_threshold(threshold=t2, relative=True)

        self.assertEqual(t2 + t, i.threshold)

        i.set_threshold(threshold=0)
        i.set_threshold()

        self.assertLess(i.threshold, locB)
        self.assertGreater(i.threshold, locA)

        I3 = np.random.normal(locC, size=self.i_shape)

        II = I.copy()

        II[np.where(II < i.threshold)] = I3[np.where(II < i.threshold)]

        i.set_threshold(im=II)

        self.assertLess(i.threshold, locC)
        self.assertGreater(i.threshold, locB)

    def test_cirularity_of_filter(self):

        i = self.Item(None, None, self.I)

        i.filter_array[:,:] = 0
        c_center = (50, 50)
        c_r = 20
        circle = gc.points_in_circle((c_center, c_r))

        for pos in circle:

            i.filter_array[pos] = 1

        c_o_m, radius = i.get_ideal_circle(i.filter_array)
        c_o_m_fraction = sum([abs(1 - x[0] / x[1]) for x in \
            zip(c_o_m, c_center)])

        self.assertAlmostEqual(c_o_m_fraction, 0.000, places=1)
        self.assertAlmostEqual(radius/float(c_r), 1.00, places=1)
        self.assertAlmostEqual(i.get_circularity(), 1.00, places=1) 

        rect = [[21, 24], [56, 71]]
        r_area = (rect[1][0] - rect[0][0], rect[1][1] - rect[0][1])

        i.set_blob_from_shape(rect=rect)

        self.assertGreater(i.get_circularity(), 2.0)

        i.filter_array *= 0

        self.assertEqual(i.get_circularity(), 1000)

    def test_detect_threshold(self):

        i = self.Item(None, None, self.I.copy())

        i.set_blob_from_shape(circle=((50, 50), 20))

        i_filter = i.filter_array.copy()

        self.assertIsNot(i_filter, i.filter_array)

        I2 = np.random.normal(40, size=self.i_shape)

        i.grid_array[np.where(i.filter_array)] = I2[np.where(i.filter_array)]

        i.threshold_detect(threshold=10)        

        self.assertEqual(np.abs(i_filter - i.filter_array).sum(), 0)

        self.assertEqual(i.grid_array[np.where(i.filter_array)].sum(),
                    i.grid_array[np.where(i_filter)].sum())

        i.threshold_detect(threshold=10, color_logic="inv")

        self.assertEqual(np.abs((i_filter == 0) - i.filter_array).sum(), 0)

        self.assertEqual(i.grid_array[np.where(i.filter_array)].sum(),
                    i.grid_array[np.where(i_filter == 0)].sum())

        i.threshold_detect()

        self.assertEqual(np.abs(i_filter - i.filter_array).sum(), 0)

        self.assertEqual(i.grid_array[np.where(i.filter_array)].sum(),
                    i.grid_array[np.where(i_filter)].sum())

    def test_manual_detect(self):

        i = self.Item(None, None, self.I.copy())

        i.set_blob_from_shape(circle=((50, 50), 20))

        i_filter = i.filter_array.copy()

        self.assertIsNot(i_filter, i.filter_array)

        I2 = np.random.normal(40, size=self.i_shape)

        i.grid_array[np.where(i.filter_array)] = I2[np.where(i.filter_array)]

        i.manual_detect((45, 50), 25)

        self.assertGreater(np.abs(i.filter_array - i_filter).sum(), 0)
 
        i_filter = i.filter_array.copt()

        i.set_blob_from_shape(circle=((45, 50), 25))

        self.assertEqual(np.abs(i.filter_array - i_filter).sum(), 0)

if __name__ == "__main__":

    unittest.main()
