import json
import logging
import multiprocessing
import itertools

from tqdm import tqdm
from datetime import datetime, timedelta

import rasterio

from rasterstats import zonal_stats

from django_q.tasks import async_task

from django.conf import settings
from django.db import IntegrityError

from ..models import (Product, ProductRaster, CropMask, CropmaskRaster,
                      BoundaryLayer, BoundaryFeature, BoundaryRaster, ZonalStats)


# set up logging
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=settings.LOG_LEVELS[settings.LOG_LEVEL])
# logging.basicConfig(level="DEBUG")
log = logging.getLogger(__name__)


def chunks(features, cores, product_raster_path, cropmask_raster_path, mask_type):
    """Yield successive n-sized chunks from a slice-able iterable."""
    return [(features[i:i+cores], product_raster_path, cropmask_raster_path, mask_type) for i in range(0, len(features), cores)]


def zonal_stats_partial(feats, product_raster_path, cropmask_raster_path, mask_type):
    """Wrapper for zonal stats, takes a list of features"""
    return zonal_stats(
        feats,
        product_raster_path,
        mask_raster=cropmask_raster_path,
        mask_type=mask_type,
        stats=['count', 'min', 'max', 'mean', 'std', 'nodata']
    )


def bulk_zonal_stats(product_raster, cropmask_raster, boundary_layer):

    # Create multiprocessing Pool using number of cores specified in settings.
    n_cores = settings.N_CORES
    p = multiprocessing.Pool(n_cores)
    # Get queryset of boundary features.
    boundary_features = BoundaryFeature.objects.filter(
        boundary_layer=boundary_layer)

    # Open raster and get CRS to transform vector geometry.
    raster_dataset = rasterio.open(product_raster.local_path)
    crs_wkt = raster_dataset.crs.wkt

    geoms = [json.loads(feature.geom.transform(crs_wkt, clone=True).geojson)
             for feature in boundary_features]

    # Divide features for processing across N number of cores.
    params = chunks(
        features=geoms,
        cores=n_cores,
        product_raster_path=product_raster.local_path,
        cropmask_raster_path=cropmask_raster.local_path if cropmask_raster else None,
        mask_type=cropmask_raster.mask_type if cropmask_raster else "binary")

    # Use Pool.startmap method to map over chunks of features and execute zonal stats calculation.
    stats_lists = p.starmap(zonal_stats_partial, tqdm(params))
    # Combine results into a single list.
    stats = list(itertools.chain(*stats_lists))
    # Zip results into list of tuples with corresponding boundary feautre.
    results = list(zip(boundary_features, stats))

    # Create list of ZonalStats records for bulk_create.
    insert_list = []
    for feat, stats in results:
        insert_list.append(
            ZonalStats(
                product_raster=product_raster,
                cropmask_raster=cropmask_raster,
                boundary_layer=boundary_layer,
                feature_id=feat.feature_id,
                pixel_count=stats['count'],
                percent_arable=(stats['count']/stats['feature_count'])*100,
                min=stats['min'],
                max=stats['max'],
                mean=stats['mean'],
                std=stats['std'],
                date=product_raster.date
            )
        )
    try:
        zonal_stats_added = ZonalStats.objects.bulk_create(insert_list)
        log.info(f'Successfully saved {len(zonal_stats_added)} records.')

        return zonal_stats_added

    except IntegrityError:
        log.error(
            f'A zonal statistics record for this combination of [{product_raster}, {cropmask_raster}, {boundary_layer}, {product_raster.date}] already exists in the database. No records saved.')

        return None


def queue_bulk_stats(
        products: list = None, cropmasks: list = None,
        boundarylayers: list = None, years: list = None):

    # Create product queryset.
    # If no product is specified, select all.
    # Otherwise, create en empty queryset and add each product specified.
    if products == None:
        product_queryset = Product.objects.all()
    else:
        product_queryset = Product.objects.none()
        for product in products:
            queryset = Product.objects.filter(product_id=product)
            product_queryset = product_queryset | queryset

    # Create a similar queryset for crop masks.
    if cropmasks == None:
        cropmask_queryset = CropMask.objects.all()
    else:
        cropmask_queryset = CropMask.objects.none()
        for cropmask in cropmasks:
            queryset = CropMask.objects.filter(cropmask_id=cropmask)
            cropmask_queryset = cropmask_queryset | queryset

    # Create a similar queryset for boundary layers
    if boundarylayers == None:
        boundarylayer_queryset = BoundaryLayer.objects.all()
    else:
        boundarylayer_queryset = BoundaryLayer.objects.none()
        for boundarylayer in boundarylayers:
            queryset = BoundaryLayer.objects.filter(layer_id=boundarylayer)
            boundarylayer_queryset = boundarylayer_queryset | queryset

    # Loop over combinations of Product * CropMask * BoundaryLayer.
    for product in product_queryset:
        for boundary_layer in boundarylayer_queryset:
            try:
                # Retreive queryset of features belonging to each BoundaryLayer.
                boundary_features = BoundaryFeature.objects.filter(
                    boundary_layer=boundary_layer)
                # Make sure feature queryset count is greater than 0.
                assert boundary_features.count() > 0

                # Only loop over crop masks that are set in the BoundaryLayer model.
                for cropmask in boundary_layer.masks.all():
                    if cropmask in cropmask_queryset:
                        # Get ProductRaster queryset
                        product_rasters = ProductRaster.objects.filter(
                            product=product
                        )
                        for product_raster in tqdm(
                            product_rasters,
                            desc=f'{product.product_id}-{cropmask.cropmask_id}-'
                                f'{boundary_layer.layer_id}'):
                            # If years are provided, only include datasets within specified years.
                            if years:
                                if product_raster.date.year in years:

                                    # Try to retreive related mask dataset,
                                    # if they do not exist then pass.
                                    try:
                                        if cropmask.cropmask_id == 'no-mask':
                                            cropmask_raster = None
                                        else:
                                            cropmask_raster = CropmaskRaster.objects.get(
                                                product=product, crop_mask=cropmask)

                                        # Add bulk_zonal_stats function to task queue.
                                        async_task(
                                            bulk_zonal_stats, product_raster, cropmask_raster, boundary_layer, group=product.product_id)
                                        log.info(f'Queueing Zonal Stats for '
                                                 f'{product.product_id}:'
                                                 f'{product_raster.date}-'
                                                 f'{cropmask.cropmask_id}-'
                                                 f'{boundary_layer.layer_id}')
                                    except CropmaskRaster.DoesNotExist:
                                        log.debug(
                                            f'No matching CropmaskRaster found for combination of \
                                            {product.product_id} & {cropmask.cropmask_id}')

                            # If no years are specified, queue all dates.
                            else:
                                try:
                                    if cropmask.cropmask_id == 'no-mask':
                                        cropmask_raster = None
                                    else:
                                        cropmask_raster = CropmaskRaster.objects.get(
                                            product=product, crop_mask=cropmask)

                                    async_task(
                                        bulk_zonal_stats, product_raster, cropmask_raster, boundary_layer, group=product.product_id)
                                    log.debug(f'Queueing Zonal Stats for '
                                              f'{product.product_id}:'
                                              f'{product_raster.date}-'
                                              f'{cropmask.cropmask_id}-'
                                              f'{boundary_layer.layer_id}')
                                except CropmaskRaster.DoesNotExist:
                                    log.debug(
                                        f'No matching CropmaskRaster found for combination of \
                                        {product.product_id} & {cropmask.cropmask_id}')
            except AssertionError as error:
                log.debug(
                    f'No available features found for {boundary_layer.layer_id}')


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


# to-do: function to export stats using command line

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
