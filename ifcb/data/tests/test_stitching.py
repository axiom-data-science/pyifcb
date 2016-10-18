import unittest

import numpy as np

from ..files import DataDirectory, FilesetBin
from ..stitching import Stitcher
from .fileset_info import TEST_FILES, TEST_DATA_DIR

class TestStitcher(unittest.TestCase):
    def test_stitched_size(self):
        dd = DataDirectory(TEST_DATA_DIR)
        for lid, tf in TEST_FILES.items():
            if 'stitched_roi_number' in tf: # does this have stitching data?
                b = FilesetBin(dd[lid])
                s = Stitcher(b)
                target = tf['stitched_roi_number']
                coords = tf['stitched_roi_coords']
                assert target in s
                assert s[target].shape == tf['stitched_roi_shape']
                assert np.all(s[target][coords] == tf['stitched_roi_slice'])
            