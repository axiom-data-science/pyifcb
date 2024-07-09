"""
Support for reading images from IFCB ``.roi`` files.
"""

import os
from functools import cached_property

import numpy as np

from .adc import AdcFile
from .utils import BaseDictlike

def read_image(inroi, byte_offset, width, height):
    """
    Read an image from raw 8-bit binary data.

    :param inroi: an open file in binary read mode
    :param byte_offset: the position in the file to seek to
    :param width: the width of the image in pixels
    :param height: the height of the image in pixels

    :returns array-like: an 8-bit 2d image
    """
    length = width * height
    inroi.seek(byte_offset)
    pixel_values = inroi.read(length)
    return np.frombuffer(pixel_values, dtype=np.uint8).reshape((width,height))

class RoiFile(BaseDictlike):
    """
    Wraps and provides access to an IFCB ``.roi`` file.
    Provides context manager support for keeping the
    file open while images are read from it. Also
    provides dict-like support including len, iteration,
    and access to images by target number.

    Requires an associated ``.adc`` file or ``AdcFile`` object.
    """
    def __init__(self, adc, roi_path):
        """
        :param adc: the path of the ``.adc`` file, or an ``AdcFile`` object
        :param roi_path: the path to the ``.roi`` file
        """
        # duck type adc argument
        self.adc = None
        try:
            adc.pid # should work for AdcFile objects
            self.adc = adc
        except AttributeError:
            self.adc = AdcFile(adc)
        self.path = roi_path
        self._inroi = None # start with the file closed
    @cached_property
    def csv(self):
        """adc data with non-ROI targets removed"""
        # remove 0x0 rois from adc data
        csv = self.adc.csv
        s = self.adc.schema
        return csv[csv[s.ROI_WIDTH] != 0]
    @property
    def lid(self):
        """
        The bin's LID
        """
        return self.adc.lid
    def getsize(self):
        """
        :returns int: the size of the file in bytes
        """
        return os.path.getsize(self.path)
    def isopen(self):
        """
        Flag indicating if the file is open
        """
        return self._inroi is not None
    def _open(self):
        if self.isopen():
            raise ValueError('RoiFile already open')
        self._inroi = open(self.path, 'rb')
    def close(self):
        """
        Close the file.

        It is OK to call this even if the file is closed.
        """
        # allow re-closing
        if self.isopen():
            self._inroi.close()
        self._inroi = None
    def __enter__(self):
        self._open()
        return self
    def __exit__(self, *args):
        self.close()
    def shape(self, roi_number):
        roi_number = int(roi_number)
        s = self.adc.schema
        width = self.csv[s.ROI_WIDTH][roi_number]
        height = self.csv[s.ROI_HEIGHT][roi_number]
        return (height, width)
    def get_image(self, roi_number):
        """
        Read an image from the file. Note that the dict-like
        interface can be used to access images by target number.

        :param roi_number: the (1-based) target number for this ROI
        :returns numpy.array: an 8-bit 2d image
        """
        roi_number = int(roi_number)
        s = self.adc.schema
        keys = [s.START_BYTE, s.ROI_WIDTH, s.ROI_HEIGHT]
        try:
            bo, width, height = [self.csv[k][roi_number] for k in keys]
        except KeyError:
            raise KeyError('adc data does not contain a roi #%d' % roi_number)
        if width * height == 0:
            raise KeyError('roi #%d is 0x0' % roi_number)
        if not self.isopen():
            self._open()
            try:
                im = read_image(self._inroi, bo, height, width)
            except:
                raise
            finally:
                self.close()
        else:
            im = read_image(self._inroi, bo, height, width)
        return im
    def __len__(self):
        return len(self.csv)
    @property
    def index(self):
        """
        An array-like object containing the target number
          of each ROI in the file, in order
        """
        return self.csv.index
    def keys(self):
        return self.index
    def has_key(self, k):
        return k in self.keys()
    def __getitem__(self, roi_number):
        return self.get_image(roi_number)
    def to_dict(self):
        """
        Convert item pairs to a dict.

        Warning: holds all image data in memory, so for a typical
        IFCB data file will consume large amounts of memory.

        An alternative is to use RoiFile's dict-like interface, as
        long as you can keep the .roi file open.

        :returns dict: a dict with target numbers as keys and
          images as values.
        """
        return dict(self.items())
    def to_hdf(self, hdf_file, group=None, replace=True):
        """
        Convert the image data to HDF5.

        :param hdf_file: the root HDF
          object (h5py.File or h5py.Group) in which to write
          the image data and index
        :param group: a path below the sub-group
          to use
        :param replace: whether to replace any existing data
          at that location in the HDF file
        """
        from .hdf import roi2hdf
        roi2hdf(self, hdf_file, group, replace=replace)
    def __repr__(self):
        return '<ROI file %s>' % self.path
    def __str__(self):
        return self.path
