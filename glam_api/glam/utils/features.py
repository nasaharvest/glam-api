import os
import logging
# import other required modules
import rasterio
import numpy as np
from multiprocessing import Pool
from rasterio.windows import Window

from django.conf import settings

# set up logging
logging.basicConfig(level="INFO")
log = logging.getLogger(__name__)


def getWindows(width, height, blocksize) -> list:
    hnum, vnum = width, height
    windows = []
    for hstart in range(0, hnum, blocksize):
        for vstart in range(0, vnum, blocksize):
            hwin = blocksize
            vwin = blocksize
            if ((hstart + blocksize) > hnum):
                hwin = (hnum % blocksize)
            if ((vstart + blocksize) > vnum):
                vwin = (vnum % blocksize)
            targetwindow = Window(hstart, vstart, hwin, vwin)
            windows += [targetwindow]
    return windows


def _unique_admin_worker(args: tuple) -> list:
    targetwindow, admin_path = args
    admin_handle = rasterio.open(admin_path, 'r')
    admin_noDataVal = admin_handle.meta['nodata']
    admin_data = admin_handle.read(1, window=targetwindow)
    admin_handle.close()
    # loop over all admin codes present in admin_data
    # exclude nodata value
    uniqueadmins = np.unique(admin_data[admin_data != admin_noDataVal])
    return uniqueadmins.tolist()


def _update_unique_admins(old_array, new_array) -> list:
    out_array = old_array
    out_array += new_array
    return np.unique(out_array)


def get_unique_features(
        admin_path, n_cores=settings.N_PROCESSES,
        block_scale_factor=settings.BLOCK_SCALE_FACTOR) -> list:

    n_cores = int(n_cores)
    block_scale_factor = int(block_scale_factor)

    # get metadata
    with rasterio.open(admin_path, 'r') as meta_handle:
        meta_profile = meta_handle.profile
        # block size
        if meta_profile['tiled']:
            blocksize = meta_profile['blockxsize'] * block_scale_factor
        else:
            log.warning(f"Input file {admin_path} is not tiled!")
            blocksize = settings.DEFAULT_BLOCK_SIZE * block_scale_factor
        # raster dimensions
        hnum = meta_handle.width
        vnum = meta_handle.height

    # get windows
    windows = getWindows(hnum, vnum, blocksize)

    # generate parallel args
    parallel_args = [
        (w, admin_path) for w in windows
    ]

    # do parallel
    final_output = []
    with Pool(processes=n_cores) as p:
        for window_output in p.map(_unique_admin_worker, parallel_args):
            _update_unique_admins(final_output, window_output)

    p.close()
    p.join()

    return np.unique(final_output).tolist()
