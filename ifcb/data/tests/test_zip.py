import unittest

from ..zip import bin2zip, ZipBin
from ..files import FilesetBin

from ...tests.utils import withfile

from .fileset_info import list_test_filesets
from .bins import assert_bin_equals

class TestZipBin(unittest.TestCase):
    @withfile
    def test_roundtrip(self, path):
        for fs in list_test_filesets():
            with FilesetBin(fs) as out_bin:
                bin2zip(out_bin, path)
                with ZipBin(path) as in_bin:
                    assert_bin_equals(in_bin, out_bin)