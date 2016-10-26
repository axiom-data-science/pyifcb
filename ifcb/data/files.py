"""
Access to IFCB raw data files, including directory operations.
"""

import os

from functools32 import lru_cache

from .identifiers import Pid
from .adc import AdcFile
from .hdr import parse_hdr_file
from .roi import RoiFile
from .utils import BaseDictlike
from .bins import BaseBin

class Fileset(object):
    """
    Represents a set of three raw data files
    """
    def __init__(self, basepath):
        """
        :param basepath: the base path of the files (no extension)
        """
        self.basepath = basepath
    @property
    def adc_path(self):
        """
        The path of the ``.adc`` file.
        """
        return self.basepath + '.adc'
    @property
    def hdr_path(self):
        """
        The path of the ``.hdr`` file.
        """
        return self.basepath + '.hdr'
    @property
    def roi_path(self):
        """
        The path of the ``.roi`` file.
        """
        return self.basepath + '.roi'
    @property
    @lru_cache()
    def pid(self):
        """
        A ``Pid`` representing the bin PID
        """
        return Pid(os.path.basename(self.basepath))
    @property
    def lid(self):
        """
        The bin's LID
        """
        return self.pid.bin_lid
    def exists(self):
        """
        Checks for existence of all three raw data files.

        :returns bool: whether or not all files exist
        """
        if not os.path.exists(self.adc_path):
            return False
        if not os.path.exists(self.hdr_path):
            return False
        if not os.path.exists(self.roi_path):
            return False
        return True
    # metrics
    def getsizes(self):
        """
        Get the sizes of the files.

        :returns dict: sizes of files with keys
          'hdr', 'adc', and 'roi'
        """
        hdr_size = os.path.getsize(self.hdr_path)
        adc_size = os.path.getsize(self.adc_path)
        roi_size = os.path.getsize(self.roi_path)
        return {
            'hdr': hdr_size,
            'adc': adc_size,
            'roi': roi_size
        }
    def getsize(self):
        """
        Get the total size of all three files.

        :returns int: the total size of all three files
        """
        return sum(self.getsizes().values())
    def as_bin(self):
        """
        :returns: a Bin view of this fileset.
        """
        return FilesetBin(self)
    def __repr__(self):
        return '<IFCB Fileset %s>' % self.basepath
    def __str__(self):
        return self.basepath

# bin interface to Fileset

class FilesetBin(BaseDictlike, BaseBin):
    """
    Bin interface to Fileset.

    Context manager support opens and closes the ``.roi`` file for image
    access.
    """
    def __init__(self, fileset):
        """
        :param fileset: the ``Fileset`` to represent
        """
        self.fileset = fileset
        self.adc_file = AdcFile(fileset.adc_path)
        self.roi_file = RoiFile(self.adc_file, fileset.roi_path)
    # oo interface to fileset
    @property
    @lru_cache()
    def hdr_attributes(self):
        """
        A ``dict`` representing the headers
        """
        return parse_hdr_file(self.fileset.hdr_path)
    @property
    def timestamp(self):
        """
        The bin's timestamp (as a ``datetime``)
        """
        return self.pid.timestamp
    def to_hdf(self, hdf_file, group=None, replace=True, archive=False):
        """
        Convert the fileset to HDF.

        :param hdf_file: the root HDF file pathname or
          object (``h5py.File`` or ``h5py.Group``) in which to write all raw data
        :param group: a path below the sub-group
          to use
        :param replace: whether to replace any existing data
          at that location in the HDF file
        :param archive: whether to include the full text of the .hdr
          and .roi files
        """
        from .hdf import filesetbin2hdf
        filesetbin2hdf(self, hdf_file, group=group, replace=replace, archive=archive)
    # bin interface
    @property
    def pid(self):
        """
        The bin's PID
        """
        return self.fileset.pid
    @property
    def schema(self):
        """
        The bin's schema
        """
        return self.adc_file.schema
    @property
    def images(self):
        """
        The images
        """
        return self.roi_file
    @property
    def headers(self):
        """
        The header dict
        """
        return self.hdr_attributes
    @property
    def adc(self):
        """
        The bin's ADC data as a ``pandas.DataFrame``
        """
        return self.adc_file.csv
    # dict implementation
    def iterkeys(self):
        for k in self.adc_file:
            yield k
    def __getitem__(self, ix):
        return self.adc_file[ix]
    def has_key(self, k):
        return k in self.adc_file
    def __len__(self):
        return len(self.adc_file)
    # context manager implementation
    def isopen(self):
        """
        Is the ``.roi`` file open?
        """
        return self.roi_file.isopen()
    def close(self):
        """
        Close the ``.roi`` file, if it is open.
        """
        if self.isopen():
            self.roi_file.close()
    def __exit__(self, *args):
        self.close()
    def __repr__(self):
        return '<FilesetBin %s>' % self
    def __str__(self):
        return self.fileset.__str__()

# listing and finding raw filesets and associated bin objects

def validate_path(filepath, blacklist=['skip'], whitelist=['data']):
    """
    Validate an IFCB raw data file path.

    A well-formed raw data file path relative to some root
    only contains path components that are
    not blacklisted and either
    either whitelisted or part of the file's basename (without
    extension).

    :param filepath: the pathname of the file
    :param blacklist: directory names to ignore
    :param whitelist: directory names to include, even if they
      do not match the path's basename
    :returns bool: if the pathname is valid
    """
    assert set(blacklist).isdisjoint(set(whitelist)), 'whitelist and blacklist must be disjoint'
    dirname, basename = os.path.split(filepath)
    lid, ext = os.path.splitext(basename)
    components = dirname.split(os.sep)
    for c in components:
        if c in blacklist:
            return False
        if c not in whitelist and c not in lid:
            return False
    return True

def list_filesets(dirpath, blacklist=['skip'], whitelist=['data'], sort=True, validate=True):
    """
    Iterate over entire directory tree and yield a Fileset
    object for each .adc/.hdr/.roi fileset found. Warning: for
    large directories, this is slow.

    :param blacklist: list of directory names to ignore
    :param whitelist: list of directory names to include, even if they
      do not match a file's basename
    :param sort: whether to sort output (sorts by alpha)
    :param validate: whether to validate each path
    """
    assert set(blacklist).isdisjoint(set(whitelist)), 'whitelist and blacklist must be disjoint'
    for dp, dirnames, filenames in os.walk(dirpath):
        for d in dirnames:
            if d in blacklist:
                dirnames.remove(d)
        if sort:
            dirnames.sort()
            filenames.sort()
        for f in filenames:
            basename, extension = f[:-4], f[-3:]
            if extension == 'adc' and basename+'.hdr' in filenames and basename+'.roi' in filenames:
                if validate:
                    reldir = dp[len(dirpath)+1:]
                    if not validate_path(os.path.join(reldir,basename), whitelist=whitelist, blacklist=blacklist):
                        continue
                yield dp, basename

def list_data_dirs(dirpath, blacklist=['skip'], sort=True, prune=True):
    """
    Yield the paths of any descendant directories that contain at least
    one ``.adc`` file.

    :param blacklist: list of directory names to ignore
    :param sort: whether to sort output (sorts by alpha)
    :param prune: whether, given a dir with an ``.adc`` file in it, to skip
      subdirectories
    """
    dirlist = os.listdir(dirpath)
    if sort:
        dirlist.sort()
    for name in dirlist:
        if name[-3:] == 'adc':
            yield dirpath
            if prune:
                return
    for name in dirlist:
        if name not in blacklist:
            child = os.path.join(dirpath,name)
            if os.path.isdir(child):
                # yield from recursive
                for dp in list_data_dirs(child, sort=sort, prune=prune):
                    yield dp

def find_fileset(dirpath, lid, whitelist=['data'], blacklist=['skip']):
    """
    Find a fileset anywhere below the given directory path
    given the bin's lid. This assumes that the file's path
    is valid.

    :returns Fileset: the ``Fileset``, or ``None`` if it is not found.
    """
    dirlist = os.listdir(dirpath)
    for name in dirlist:
        if name == lid + '.adc':
            basepath = os.path.join(dirpath,lid)
            return Fileset(basepath)
        elif name in whitelist or name in lid:
            # is the name whitelisted or contains part of the lid?
            fs = find_fileset(os.path.join(dirpath,name), lid, whitelist=whitelist, blacklist=blacklist)
            if fs is not None:
                return fs
    # not found
    return None

class DataDirectory(object):
    """
    Represents a directory containing IFCB raw data.

    Provides a dict-like interface allowing access to FilesetBins by LID.
    """
    def __init__(self, path='.', whitelist=['data'], blacklist=['skip']):
        """
        :param path: the path of the data directory
        :param whitelist: a list of directory names to allow
        :param blacklist: a list of directory names to disallow
        """
        self.path = path
        self.whitelist = whitelist
        self.blacklist = blacklist
    def list_filesets(self):
        """
        Yield all filesets.
        """
        for dirpath, basename in list_filesets(self.path, whitelist=self.whitelist, blacklist=self.blacklist):
            basepath = os.path.join(dirpath, basename)
            yield Fileset(basepath)
    def find_fileset(self, lid):
        """
        Locate a fileset by LID. Returns None if it is not found.

        :param lid: the LID to search for
        :type lid: str
        :returns Fileset: the fileset, or None if not found
        """
        return find_fileset(self.path, lid, whitelist=self.whitelist, blacklist=self.blacklist)
    def __iter__(self):
        # yield from list_filesets called with no keyword args
        for fs in self.list_filesets():
            yield FilesetBin(fs)
    def has_key(self, lid):
        # fast contains method that avoids iteration
        return self.find_fileset(lid) is not None
    def __getitem__(self, lid):
        fs = self.find_fileset(lid)
        if fs is None:
            raise KeyError('No fileset for %s found at or under %s' % (lid, self.path))
        return FilesetBin(fs)
    def __len__(self):
        """warning: for large datasets, this is very slow"""
        return sum(1 for _ in self)
    # subdirectories
    def list_descendants(self, **kw):
        """
        Find all 'leaf' data directories and yield ``DataDirectory``
        objects for each one. Note that this enforces blacklisting
        but not whitelisting (no fileset path validation is done).
        Accepts ``list_data_dirs`` keywords, except ``blacklist`` which
        takes on the value given in the constructor.
        """
        for dd in list_data_dirs(self.path, blacklist=self.blacklist, **kw):
            yield DataDirectory(dd)
    def __repr__(self):
        return '<DataDirectory %s>' % self.path
    def __str__(self):
        return self.path
