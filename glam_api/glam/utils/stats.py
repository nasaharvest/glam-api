import os
import logging
from tqdm import tqdm
from datetime import datetime, timedelta
# import other required modules
import rasterio
import numpy as np
from multiprocessing import Pool
from rasterio.windows import Window

from django.conf import settings
from django_q.tasks import async_task

from ..models import (Product, ProductRaster, CropMask, CropmaskRaster,
                      BoundaryLayer, BoundaryRaster, ZonalStats)

"""
Some functions derived from 'glam_data_processing'
https://github.com/fdfoneill/glam_data_processing
"""

# set up logging
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
# logging.basicConfig(level="DEBUG")
log = logging.getLogger(__name__)

# repeatedly used functions and objects


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


def getValidRange(dtype: str) -> tuple:
    try:
        if (dtype == "byte") or ("int" in dtype):
            try:
                return (np.iinfo(dtype).min, np.iinfo(dtype).max)
            except:
                raise ValueError
        # elif ("float" in dtype):
        # 	try:
        # 		# return (np.finfo(dtype).min, np.finfo(dtype).max)
        # 		return (0, np.finfo(dtype).max)
        # 	except:
        # 		raise ValueError
        else:
            raise ValueError
    except ValueError:
        raise ValueError(
            f"Data type '{dtype}' not recognized by getValidRange()")
    # validRange = {
    # 	"byte":(-128,127),
    # 	"uint8":(0,255),
    # 	"int8":(-128,127),
    # 	"uint16":(0,65535),
    # 	"int16":(-32768,32767),
    # 	"uint32":(0,4294967295),
    # 	"int32":(-2147483648,2147483647)
    # }
    # try:
    # 	return validRange[dtype]
    # except KeyError:
    # 	log.exception(f"Data type '{dtype}' not recognized\
    #  by glam_data_processing.stats.getValidRange()")

##############################################################################


# ZONAL STATS and helper functions

def _mp_worker_ZS(args: tuple) -> dict:
    """A function for use with the multiprocessing
    package, passed to each worker.

    Returns a dictionary of the form:
        {zone_id:{'value':VALUE,'arable_pixels':VALUE,'percent_arable':VALUE},}

    Parameters
    ----------
    args:tuple
        Tuple containing the following (in order):
            targetwindow
            product_path
            mask_path
            boundary_path
    """
    targetwindow, product_path, mask_path, boundary_path, mask_type = args

    if "nomask" in mask_path:
        mask_path = None

    # get product raster info
    product_handle = rasterio.open(product_path, 'r')
    product_noDataVal = product_handle.meta['nodata']
    product_data = product_handle.read(1, window=targetwindow)
    product_handle.close()

    # get mask raster info
    if mask_path is not None:
        mask_handle = rasterio.open(mask_path, 'r')
        mask_noDataVal = mask_handle.meta['nodata']
        mask_data = mask_handle.read(1, window=targetwindow)
        mask_handle.close()
    else:
        mask_data = np.full(product_data.shape, 1)

    # get admin raster info
    admin_handle = rasterio.open(boundary_path, 'r')
    admin_noDataVal = admin_handle.meta['nodata']
    admin_data = admin_handle.read(1, window=targetwindow)
    admin_handle.close()

    # create empty output dictionary
    out_dict = {}

    # loop over all admin codes present in admin_data
    # exclude nodata value
    #!!! 12/1/2021 mask_data > 0 NOT mask_data == 1
    uniqueadmins = np.unique(admin_data[admin_data != admin_noDataVal])
    for admin_code in uniqueadmins:
        if mask_path is not None:
            arable_pixels = int(
                (admin_data[(admin_data == admin_code) & (mask_data != mask_noDataVal) & (mask_data > 0)]).size)
        else:
            arable_pixels = int(
                (admin_data[(admin_data == admin_code) & (mask_data > 0)]).size)

        if arable_pixels == 0:
            continue

        if mask_type == 'percent':
            pd = product_data[
                (mask_data != mask_noDataVal) & (mask_data > 0) &
                (product_data != product_noDataVal) & (admin_data == admin_code)
            ]

            md = mask_data[
                (mask_data != mask_noDataVal) & (mask_data > 0) &
                (product_data != product_noDataVal) & (admin_data == admin_code)
            ]

            masked = np.array(pd * md, dtype='int64')
            percent_arable = (float(masked.size) / float(arable_pixels)) * 100
            value = ((masked.sum()/md.sum()) if (masked.size > 0) else 0)

        else:
            masked = np.array(
                product_data[
                    (product_data != product_noDataVal) & (mask_data == 1) &
                    (admin_data == admin_code)], dtype='int64')
            percent_arable = (float(masked.size) / float(arable_pixels)) * 100
            value = (masked.mean() if (masked.size > 0) else 0)

        out_dict[admin_code] = {
            "value": value,
            "arable_pixels": arable_pixels,
            "percent_arable": percent_arable
        }

    return out_dict


def _update_ZS(stored_dict, this_dict) -> dict:
    """Updates stats dictionary with values from a new window result

    Parameters
    ----------
    stored_dict:dict
        Dictionary to be updated with new data
    this_dict:dict
        New data with which to update stored_dict
    """
    out_dict = stored_dict
    for k in this_dict.keys():
        this_info = this_dict[k]
        try:
            stored_info = stored_dict[k]
        except KeyError:
            # if stored_dict has no info for zone k (new zone in this window),
            #  set it equal to the info from this_dict
            out_dict[k] = this_info
            continue
        # calculate number of visible arable pixels for both dicts
        # by multiplying arable_pixels with percent_arable
        arable_visible_stored = (
            stored_info["arable_pixels"] * stored_info["percent_arable"] / 100.0)
        arable_visible_this = (
            this_info["arable_pixels"] * this_info["percent_arable"] / 100.0)
        try:
            # weight of stored_dict value is the ratio of its visible
            # arable pixels to the total number of visible arable pixels
            stored_weight = arable_visible_stored / (
                arable_visible_stored + arable_visible_this)
        except ZeroDivisionError:
            # if no visible pixels at all, weight everything at 0
            stored_weight = 0
        try:
            # weight of this_dict value is the ratio of its visible
            # arable pixels to the total number of visible arable pixels
            this_weight = arable_visible_this / (
                arable_visible_this + arable_visible_stored)
        except ZeroDivisionError:
            # if the total visible arable pixels are 0,
            # everything gets weight 0
            this_weight = 0
        # weighted mean value
        value = (stored_info['value'] * stored_weight) + \
            (this_info['value'] * this_weight)
        # sum of arable pixels
        arable_pixels = stored_info['arable_pixels'] + \
            this_info['arable_pixels']
        # directly recalculate total percent arable from sum of
        # arable_visible divided by arable_pixels
        percent_arable = ((arable_visible_stored + arable_visible_this) /
                          arable_pixels) * 100
        # percent_arable = (stored_info['percent_arable'] * stored_weight) + \
        # 				  (this_info['percent_arable'] * this_weight)
        out_dict[k] = {
            'value': value,
            'arable_pixels': arable_pixels,
            'percent_arable': percent_arable
        }
    return out_dict


def zonalStats(
        product_path: str, mask_path: str, boundary_path: str, mask_type: str = 'binary',
        n_cores: int = 1, block_scale_factor: int = 8, default_block_size: int = 256,
        time: bool = False) -> dict:
    """A function for calculating zonal statistics on a raster image

    Returns a dictionary of the form:
    {zone_id:{'value':VALUE,'arable_pixels':VALUE,'percent_arable':VALUE},...}

    Parameters
    ----------
    product_path:str
        Path to product dataset on disk
    mask_path:str
        Path to crop mask dataset on disk
    boundary_path:str
        Path to admin dataset on disk
    n_cores:int
        Number of cores to use for parallel processing. Default is 1
    block_scale_factor:int
        Relative size of processing windows compared to 
        product_path native blocksize. 
        Default is 8, calculated to be optimal for all n_cores (1-50) on 
        GEOG cluster node 18
    default_block_size:int
        If product_path is not tiled, this argument is used as the block size.
        Inthat case, windows will be of size 
        (default_block size * block_scale_factor) on each side.
    time:bool
        Whether to log the time taken to return. Default false
    """
    # start timer
    start_time = datetime.now()
    # coerce numeric arguments to correct type
    n_cores = int(n_cores)
    block_scale_factor = int(block_scale_factor)
    # get metadata
    with rasterio.open(product_path, 'r') as meta_handle:
        meta_profile = meta_handle.profile
        # block size
        if meta_profile['tiled']:
            blocksize = meta_profile['blockxsize'] * block_scale_factor
        else:
            log.warning(f"Input file {product_path} is not tiled!")
            blocksize = default_block_size * block_scale_factor
        # raster dimensions
        hnum = meta_handle.width
        vnum = meta_handle.height

    # get windows
    windows = getWindows(hnum, vnum, blocksize)

    # generate parallel args
    parallel_args = [
        (w, product_path, mask_path, boundary_path, mask_type) for w in windows
    ]

    # note progress
    checkpoint_1_time = datetime.now()
    log.debug(f"Finished preparing in {checkpoint_1_time-start_time}.\
              \nStarting parallel processing on {n_cores} core(s).")

    # do parallel
    final_output = {}
    p = Pool(processes=n_cores)
    for window_output in p.map(_mp_worker_ZS, parallel_args):
        _update_ZS(final_output, window_output)
    p.close()
    p.join()

    # note final time
    log.debug(f"Finished parallel processing in \
              {datetime.now()-checkpoint_1_time}.")
    if time:
        log.info(f"Finished processing {product_path} x {mask_path} x \
                 {boundary_path} in {datetime.now()-start_time}.")
    else:
        log.debug(f"Finished processing {product_path} x {mask_path} x \
                  {boundary_path} in {datetime.now()-start_time}.")

    return final_output


##############################################################################

# PERCENTILES

def _mp_worker_PCT(args: tuple) -> np.array:
    """
    A multiprocessing worker function to extract the histogram 
    of a raster window

    ***

    Parameters
    ----------
    args:tuple
        Tuple of the following parameters:
            targetwindow
            raster_path
            histogram_min
            histogram_max
            binwidth

    Returns
    -------
    first item of histogram of a windowed read of raster_path 
    using targetwindow, with bins of number and size determined by 
    histogram_min/max and binwidth passed
    """

    # extract arguments
    targetwindow, raster_path, histogram_min, histogram_max, binwidth = args

    # calculate number of bins
    n_bins = int((histogram_max / binwidth) - (histogram_min / binwidth))

    # get data from raster
    raster_handle = rasterio.open(raster_path, 'r')
    raster_noDataVal = raster_handle.meta['nodata']
    raster_data = raster_handle.read(1, window=targetwindow)
    raster_handle.close()

    # mask
    raster_data = raster_data[raster_data != raster_noDataVal]

    # calculate and return histogram
    return np.histogram(
        raster_data, bins=n_bins, range=(histogram_min, histogram_max))[0]


# def percentiles(
#         raster_path: str, percentiles: list = [10, 90], binwidth: int = 10,
#         n_cores: int = 1, block_scale_factor: int = 8,
#         default_block_size: int = 256, time: bool = False) -> list:
#     """
#     Function that approximates percentiles of a raster,
#     leveraging multiple cores

#     ***

#     Parameters
#     ----------
#     raster_path:str
#         Path to raster file on disk
#     percentiles:list
#         List of desired percentiles as integers. Default is [10, 90].
#         Determines which percentile values will be returned
#     binwidth:int
#         Width of histogram bins used to calculate percentiles;
#         larger bins improves speed at the cost of precision
#     n_cores:int
#         How many processers to use. Default 1
#     block_scale_factor:int
#         Amount by which to scale native blocksize of raster file
#         for the purposes of windowed reads. Default 8
#     default_block_size:int
#         If product_path is not tiled, this argument is used as the block size.
#         In that case, windows will be of size
#         (default_block size * block_scale_factor) on each side.
#     time:bool
#         Whether to log the time taken to return. Default false

#     Returns
#     -------
#     List of percentile values, corresponding to the integers passed as the
#     'percentiles' parameter
#     """

#     startTime = datetime.now()

#     # validate inputs
#     binwidth = int(binwidth)
#     n_cores = int(n_cores)
#     block_scale_factor = int(block_scale_factor)
#     default_block_size = int(default_block_size)
#     for p in percentiles:
#         try:
#             assert (type(p) == int) or (type(p) == float)
#         except AssertionError:
#             raise ValueError("All values in list of 'percentiles' \
#                              must be integers or floats")
#         if (p < 0) or (p > 100):
#             raise ValueError("All values in list of 'percentiles' \
#                              must be between 0 and 100")

#     # get metadata from raster
#     with rasterio.open(raster_path, 'r') as meta_handle:
#         meta_profile = meta_handle.profile
#         # block size
#         if meta_profile['tiled']:
#             blocksize = meta_profile['blockxsize'] * int(block_scale_factor)
#         else:
#             log.warning(f"Input file {product_path} is not tiled!")
#             blocksize = default_block_size * int(block_scale_factor)
#         # raster dimensions
#         hnum = meta_handle.width
#         vnum = meta_handle.height
#         # data type
#         dtype = meta_profile['dtype']

#     # get windows and valid range
#     windows = getWindows(hnum, vnum, blocksize)
#     histogram_min, histogram_max = getValidRange(dtype)
#     # log.info(f"Histogram range: {histogram_min}, {histogram_max}")
#     # log.info(f"Binwidth: {binwidth}")
#     # compile parallel arguments into tuples (functions passed to Pool.map()
#     # must take exactly one argument)
#     parallel_args = [
#         (w, raster_path, histogram_min,
#          histogram_max, binwidth) for w in windows
#     ]
#     # do multiprocessing
#     n_bins = int((histogram_max / binwidth) - (histogram_min / binwidth))
#     # tuple of (counts, bin_boundaries).
#     # Note that len(bin_boundaries) == ( len(counts) + 1 )
#     out_counts, out_bins = np.histogram(
#         np.array([0]), bins=n_bins, range=(histogram_min, histogram_max))
#     p = Pool(processes=int(n_cores))
#     for window_counts in p.map(_mp_worker_PCT, parallel_args):
#         out_counts = out_counts + window_counts
#     p.close()
#     p.join()

#     # calculate desired percentiles
#     out_values = []
#     percentile_index = 0
#     bin_index = 0
#     total_sum = sum(out_counts)
#     progressive_sum = 0
#     # break loop when we either run out of bins (shouldn't happen!)
#     # or calculate all desired percentiles
#     while (percentile_index < len(percentiles)):
#         progressive_sum += out_counts[bin_index]  # update progressive_sum
#         # get the current percentile we're at
#         current_percentile = (progressive_sum / total_sum) * 100
#         # check current percentile vs. the next threshold
#         # in the list of "percentiles" passed
#         if current_percentile >= percentiles[percentile_index]:
#             # if triggered,
#             # append the average of current bin to the output list
#             out_values.append(
#                 (out_bins[bin_index] + out_bins[bin_index + 1]) / 2)
#             percentile_index += 1  # increment percentile index
#         bin_index += 1  # increment bin index
#         if (bin_index >= len(out_counts)):
#             raise ValueError("Ran out of bins before reaching \
#                              all desired percentiles! Check algorithm.")

#     return out_values


"""
end glam_data_processing functions
"""


def bulk_zonal_stats(product_ds, cropmask_ds, boundary_ds):
    # get optimal processing parameters
    if product_ds.product.meta['optimal_bsf']:
        bsf = product_ds.product.meta['optimal_bsf']
    else:
        bsf = settings.BLOCK_SCALE_FACTOR

    if product_ds.product.meta['optimal_cores']:
        if product_ds.product.meta['optimal_cores'] > settings.N_PROCESSES:
            n_cores = settings.N_PROCESSES
        else:
            n_cores = product_ds.product.meta['optimal_cores']
    else:
        n_cores = settings.N_PROCESSES

    # calculate zonal stats
    results = zonalStats(
        product_path=product_ds.local_path,
        mask_path=cropmask_ds.local_path if cropmask_ds else "nomask",
        boundary_path=boundary_ds.local_path,
        n_cores=n_cores,
        mask_type=cropmask_ds.mask_type if cropmask_ds else "binary",
        block_scale_factor=bsf
    )
    # create list of ZonalStats records for bulk_create
    insert_list = []
    for feature in results:
        insert_list.append(
            ZonalStats(
                product_raster=product_ds,
                cropmask_raster=cropmask_ds,
                boundary_raster=boundary_ds,
                feature_id=feature,
                arable_pixels=results[feature]['arable_pixels'],
                percent_arable=results[feature]['percent_arable'],
                mean_value=results[feature]['value'],
                date=product_ds.date
            )
        )
    # bulk insert
    ZonalStats.objects.bulk_create(insert_list)


def queue_bulk_stats(
        products: list = None, cropmasks: list = None,
        boundarylayers: list = None, years: list = None):
    # create querysets
    if products == None:
        product_queryset = Product.objects.all()
    else:
        product_queryset = Product.objects.none()
        for product in products:
            queryset = Product.objects.filter(product_id=product)
            product_queryset = product_queryset | queryset

    if cropmasks == None:
        cropmask_queryset = CropMask.objects.all()
    else:
        cropmask_queryset = CropMask.objects.none()
        for cropmask in cropmasks:
            queryset = CropMask.objects.filter(cropmask_id=cropmask)
            cropmask_queryset = cropmask_queryset | queryset

    if boundarylayers == None:
        boundarylayer_queryset = BoundaryLayer.objects.all()
    else:
        boundarylayer_queryset = BoundaryLayer.objects.none()
        for boundarylayer in boundarylayers:
            queryset = BoundaryLayer.objects.filter(layer_id=boundarylayer)
            boundarylayer_queryset = boundarylayer_queryset | queryset

    # loop over combinations of ProductRaster x CropmaskRaster x BoundaryRaster
    for product in product_queryset:
        for layer in boundarylayer_queryset:
            # loop over masks belonging to boundary layer
            for cropmask in layer.masks.all():
                if cropmask in cropmask_queryset:
                    # get product datasets
                    product_rasters = ProductRaster.objects.filter(
                        product=product
                    )
                    for product_ds in tqdm(
                        product_rasters,
                        desc=f'{product.product_id}-{cropmask.cropmask_id}-'
                             f'{layer.layer_id}'):
                        # if years are provided, only include datasets within specified years
                        if years:
                            if product_ds.date.year in years:
                                # try to retreive related boundary and mask datasets
                                # if they do not exist, pass
                                try:
                                    boundary_ds = BoundaryRaster.objects.get(
                                        product=product, boundary_layer=layer)
                                    if cropmask.cropmask_id == 'no-mask':
                                        mask_ds = None
                                    else:
                                        mask_ds = CropmaskRaster.objects.get(
                                            product=product, crop_mask=cropmask)

                                    # add to queue
                                    async_task(
                                        bulk_zonal_stats, product_ds, mask_ds, boundary_ds, group=product.product_id)
                                    log.debug(f'Queueing Zonal Stats for '
                                              f'{product.product_id}:'
                                              f'{product_ds.date}-'
                                              f'{cropmask.cropmask_id}-'
                                              f'{layer.layer_id}')
                                except:
                                    log.debug(f'Combination unavailable for '
                                              f'{product.product_id}-'
                                              f'{cropmask.cropmask_id}-'
                                              f'{layer.layer_id}')
                        # if years not specified, queue all dates
                        else:
                            try:
                                boundary_ds = BoundaryRaster.objects.get(
                                    product=product, boundary_layer=layer)
                                if cropmask.cropmask_id == 'no-mask':
                                    mask_ds = None
                                else:
                                    mask_ds = CropmaskRaster.objects.get(
                                        product=product, crop_mask=cropmask)

                                # add to queue
                                async_task(
                                    bulk_zonal_stats, product_ds, mask_ds, boundary_ds, group=product.product_id)
                                log.debug(f'Queueing Zonal Stats for '
                                          f'{product.product_id}:'
                                          f'{product_ds.date}-'
                                          f'{cropmask.cropmask_id}-'
                                          f'{layer.layer_id}')
                            except:
                                log.debug(f'Combination unavailable for '
                                          f'{product.product_id}-'
                                          f'{cropmask.cropmask_id}-'
                                          f'{layer.layer_id}')


def queue_zonal_stats(product_id: str, date: str):
    product = Product.objects.get(product_id=product_id)
    cropmasks = CropMask.objects.all()
    boundarylayers = BoundaryLayer.objects.all()

    for layer in boundarylayers:
        # loop over masks belonging to boundary layer
        for cropmask in layer.masks.all():
            if cropmask in cropmasks:
                # get product datasets
                product_raster = ProductRaster.objects.get(
                    product=product, date=date)
                try:
                    boundary_ds = BoundaryRaster.objects.get(
                        product=product, boundary_layer=layer)
                    if cropmask.cropmask_id == 'no-mask':
                        mask_ds = None
                    else:
                        mask_ds = CropmaskRaster.objects.get(
                            product=product, crop_mask=cropmask)

                    # add to queue
                    async_task(
                        bulk_zonal_stats, product_raster, mask_ds, boundary_ds, group=product.product_id)
                    log.debug(f'Queueing Zonal Stats for '
                              f'{product.product_id}:'
                              f'{product_raster.date}-'
                              f'{cropmask.cropmask_id}-'
                              f'{layer.layer_id}')
                except:
                    log.debug(f'Combination unavailable for '
                              f'{product.product_id}-'
                              f'{cropmask.cropmask_id}-'
                              f'{layer.layer_id}')


# def remove_duplicate_stats():

def fill_zonal_stats():
    start = datetime.now()

    products = Product.objects.all()
    boundarylayers = BoundaryLayer.objects.all()
    cropmasks = CropMask.objects.all()

    for product in products:
        for layer in boundarylayers:
            for cropmask in layer.masks.all():
                if cropmask in cropmasks:
                    product_rasters = ProductRaster.objects.filter(
                        product=product
                    )
                    for product_ds in tqdm(
                        product_rasters,
                        desc=f'{product.product_id}-{cropmask.cropmask_id}-'
                             f'{layer.layer_id}'):
                        try:
                            boundary_ds = BoundaryRaster.objects.get(
                                product=product, boundary_layer=layer)
                            if cropmask.cropmask_id == 'no-mask':
                                mask_ds = None
                            else:
                                mask_ds = CropmaskRaster.objects.get(
                                    product=product, crop_mask=cropmask)

                            zs_query = ZonalStats.objects.filter(
                                product_raster=product_ds,
                                cropmask_raster=mask_ds,
                                boundary_raster=boundary_ds,
                                date=product_ds.date
                            )
                            if zs_query.count() < 1:
                                print(f'Queueing Zonal Stats for '
                                      f'{product.product_id}:'
                                      f'{product_ds.date}-'
                                      f'{cropmask.cropmask_id}-'
                                      f'{layer.layer_id}')
                                # add to queue
                                # async_task(
                                #     bulk_zonal_stats, product_ds, mask_ds, admin_ds, group=product.product_id)
                                # log.debug(f'Queueing Zonal Stats for '
                                #         f'{product.product_id}:'
                                #         f'{product_ds.date}-'
                                #         f'{cropmask.cropmask_id}-'
                                #         f'{layer.layer_id}')
                        except:
                            log.debug(f'Combination unavailable for '
                                      f'{product.product_id}-'
                                      f'{cropmask.cropmask_id}-'
                                      f'{layer.layer_id}')

    finish = datetime.now()
    duration = finish - start
    print('total time: ' + duration)


# export stats

# def export_stats():

#     from glam.models import ZonalStats
#     import pandas as pd

#     filename = 'mod09a1_gaul1.csv'

#     q = ZonalStats.objects.filter(
#         boundary_raster__boundary_layer__layer_id='gaul1',
#         product_raster__product__product_id='mod09a1',
#         date__gte='2020-01-01'
#     )

#     l = list(
#         q.values(
#             "product_raster__product__product_id",
#             "cropmask_raster__crop_mask__cropmask_id",
#             "boundary_raster__boundary_layer__layer_id",
#             "feature_id",
#             "arable_pixels",
#             "mean_value",
#             "date"
#         )
#     )

#     lookup_fields = [
#         "product_raster__product__product_id",
#         "cropmask_raster__crop_mask__cropmask_id",
#         "boundary_raster__boundary_layer__layer_id",
#         "feature_id", "arable_pixels", "mean_value", "date"
#     ]

#     df = pd.DataFrame.from_records(l, columns=lookup_fields)

#     df.rename(columns={
#         'product_raster__product__product_id': 'product_id',
#         'cropmask_raster__crop_mask__cropmask_id': 'cropmask_id',
#         'boundary_raster__boundary_layer__layer_id': 'layer_id'
#         }, inplace=True)

#     df.to_csv(filename, index=False)
