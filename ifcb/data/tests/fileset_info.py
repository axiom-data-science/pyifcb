import os
import sys

import numpy as np

from ifcb.data import files

TEST_DATA_DIR=os.path.join('ifcb','data','tests','data')

WHITELIST = ['data','white']

TEST_FILES = {
    'D20130526T095207_IFCB013': {
        'n_rois': 19,
        'roi_numbers': [7, 11, 13, 21, 32, 33, 47, 49, 54, 61, 66, 68, 73, 78, 80, 92, 99, 102, 114],
        'roi_number': 99,
        'roi_shape': (34, 64),
        'roi_slice': np.array([[172, 168, 172, 166, 171],
                               [168, 170, 172, 171, 170],
                               [167, 174, 171, 175, 168],
                               [173, 171, 173, 170, 171],
                               [176, 169, 176, 173, 172]], dtype=np.uint8),
        'sizes': {
            'roi': 98472,
            'hdr': 2970,
            'adc': 19513
        }
    },
    'IFCB5_2012_028_081515': {
        'n_rois': 6,
        'roi_numbers': [1, 2, 3, 4, 5, 6],
        'roi_number': 1,
        'roi_shape': (45, 96),
        'roi_slice': np.array([[208, 207, 206, 206, 207],
                               [206, 206, 206, 207, 206],
                               [206, 207, 205, 206, 208],
                               [208, 208, 208, 208, 209],
                               [206, 206, 205, 207, 207]], dtype=np.uint8),
        'sizes': {
            'roi': 71083,
            'hdr': 307,
            'adc': 1011
        }
    }
}

def data_dir():
    for p in sys.path:
        fp = os.path.join(p, TEST_DATA_DIR)
        if os.path.exists(fp):
            return fp
    raise KeyError('cannot find %s on sys.path' % TEST_DATA_DIR)

def list_test_filesets():
    for fs in files.DataDirectory(data_dir(), whitelist=WHITELIST):
        yield fs