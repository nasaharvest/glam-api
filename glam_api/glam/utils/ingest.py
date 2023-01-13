"""
ingest.py

Utilities for ingesting datasets
"""
import os
import datetime
import logging
from tqdm import tqdm

# from glam_data_processing.baselines import updateBaselines

from django_q.tasks import async_task

from django.conf import settings
from django.utils.text import slugify
from ..models import (Product, ProductRaster, BoundaryLayer, BoundaryRaster,
                      CropMask, CropmaskRaster, AnomalyBaselineRaster)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=logging.INFO)


def add_boundary_rasters():
    dataset_directory = settings.BOUNDARY_RASTER_LOCAL_PATH

    # loop over the available files in the boundary raster directory
    for filename in tqdm(os.listdir(dataset_directory)):
        if filename.endswith(".tif"):
            # get the file's product and boundary layer id
            file_product, layer_id, _ = filename.split('.')
            # slugify names
            file_product = slugify(file_product)
            layer_id = slugify(layer_id)

            # see if related product and boundary layer are in the system
            try:
                product = Product.objects.get(product_id=file_product)
                boundary_layer = BoundaryLayer.objects.get(
                    layer_id=layer_id)

                # see if boundary layer dataset already in the system for this combination
                try:
                    BoundaryRaster.objects.get(
                        boundary_layer=boundary_layer,
                        product=product)
                    pass
                except BoundaryRaster.DoesNotExist as e2:
                    # if it doesn't exist, make it
                    new_dataset = BoundaryRaster(
                        boundary_layer=boundary_layer,
                        product=product,
                        date_created=datetime.date.today(),
                        local_path=os.path.join(dataset_directory, filename))
                    logging.info(f'saving {filename}')
                    new_dataset.save()
                    logging.info(f'saved {new_dataset.local_path}')

            except (Product.DoesNotExist, BoundaryLayer.DoesNotExist) as e1:
                logging.info(f'{e1}: {file_product},{layer_id}')
                pass


def add_cropmask_rasters():
    dataset_directory = settings.MASK_DATASET_LOCAL_PATH

    # loop over the available files in the cropmask_dataset directory
    for filename in tqdm(os.listdir(dataset_directory)):
        if filename.endswith(".tif"):
            # get the file's product and cropmask
            file_product, file_mask, _ = filename.split('.')
            # slugify names
            file_product = slugify(file_product)
            file_mask = slugify(file_mask)

            # see if related product and cropmask are in the system
            try:
                product = Product.objects.get(product_id=file_product)
                cropmask = CropMask.objects.get(cropmask_id=file_mask)

                # see if cropmask dataset already in the system for this combination
                try:
                    CropmaskRaster.objects.get(
                        crop_mask=cropmask,
                        product=product)
                    pass
                except CropmaskRaster.DoesNotExist as e2:
                    # if it doesn't exist, make it
                    new_dataset = CropmaskRaster(
                        crop_mask=cropmask,
                        product=product,
                        date_created=datetime.date.today(),
                        local_path=os.path.join(dataset_directory, filename))
                    logging.info(f'saving {filename}')
                    new_dataset.save()
                    logging.info(f'saved {new_dataset.local_path}')

            except (Product.DoesNotExist, CropMask.DoesNotExist) as e1:
                logging.info(f'{e1}: {file_product},{file_mask}')
                pass


def add_legacy_product_rasters(product):
    """
    Add files that used previous naming convention
    (product ID's have been changed)
    """
    try:
        if product == 'chirps':
            product = 'chirps-precip'
        elif product == 'swi':
            product = 'copernicus-swi'
        elif product == 'merra-2-max':
            product = 'merra-2-max-temp'
        elif product == 'merra-2-mean':
            product = 'merra-2-mean-temp'
        elif product == 'merra-2-min':
            product = 'merra-2-min-temp'
        elif product == 'mod09a1':
            product = 'mod09a1-ndwi'
        elif product == 'mod09q1':
            product = 'mod09q1-ndvi'
        elif product == 'mod13q1':
            product = 'mod13q1-ndvi'
        elif product == 'myd09q1':
            product = 'myd09q1-ndvi'
        elif product == 'myd13q1':
            product = 'myd13q1-ndvi'
        elif product == 'mod13q4n':
            product = 'mod13q4n-ndvi'
        elif product == 'vnp09h1':
            product = 'vnp09h1-ndvi'

        valid_product = Product.objects.get(product_id=slugify(product))
        dataset_directory = os.path.join(
            settings.PRODUCT_DATASET_LOCAL_PATH, product)

        for filename in tqdm(os.listdir(dataset_directory)):
            if filename.endswith(".tif"):
                parts = filename.split(".")
                try:
                    ds_date = datetime.datetime.strptime(
                        f"{parts[1]}.{parts[2]}", "%Y.%j").strftime("%Y-%m-%d")
                except:
                    ds_date = datetime.datetime.strptime(
                        parts[1], "%Y-%m-%d").strftime("%Y-%m-%d")

                try:
                    ds = ProductRaster.objects.get(
                        product=valid_product,
                        date=ds_date)
                except ProductRaster.DoesNotExist:
                    # if it doesn't exist, make it
                    prelim = False
                    if 'prelim' in filename:
                        prelim = True
                        valid_product = filename.split('-')[0]
                    new_dataset = ProductRaster(
                        product=valid_product,
                        prelim=prelim,
                        date=ds_date,  # dont actually need this here
                        local_path=os.path.join(dataset_directory, filename))
                    logging.info(f'saving {filename}')
                    new_dataset.save()
                    logging.info(f'saved {new_dataset.local_path}')

    except Product.DoesNotExist as e1:
        logging.info(
            f'{slugify(product)} is not a valid product within the system.')


def add_product_rasters(product):
    try:
        valid_product = Product.objects.get(product_id=slugify(product))
        dataset_directory = os.path.join(
            settings.PRODUCT_DATASET_LOCAL_PATH, product)

        for filename in tqdm(os.listdir(dataset_directory)):
            if filename.endswith(".tif"):
                parts = filename.split(".")
                try:
                    ds_date = datetime.datetime.strptime(
                        f"{parts[1]}.{parts[2]}", "%Y.%j").strftime("%Y-%m-%d")
                except:
                    ds_date = datetime.datetime.strptime(
                        parts[1], "%Y-%m-%d").strftime("%Y-%m-%d")
                logging.info(ds_date)
                try:
                    ds = ProductRaster.objects.get(
                        product=valid_product,
                        date=ds_date)
                except ProductRaster.DoesNotExist:
                    # if it doesn't exist, make it
                    logging.info(
                        len(os.path.join(dataset_directory, filename)))
                    prelim = False
                    if 'prelim' in filename:
                        logging.info('hi')
                        prelim = True
                    new_dataset = ProductRaster(
                        product=valid_product,
                        prelim=prelim,
                        date=ds_date,  # dont actually need this here
                        local_path=os.path.join(dataset_directory, filename))
                    logging.info(new_dataset)
                    logging.info(f'saving {filename}')
                    new_dataset.save()
                    logging.info(f'saved {new_dataset.local_path}')

    except Product.DoesNotExist as e1:
        logging.info(
            f'{slugify(product)} is not a valid product within the system.')


# for initial ingest of anomaly baseline datasets
def add_anomaly_baselines(product):
    try:
        valid_product = Product.objects.get(product_id=slugify(product))
        product_directory = os.path.join(
            settings.ANOMALY_BASELINE_LOCAL_PATH, product)

        for sub_dir in tqdm(os.listdir(product_directory), desc=f'{product}'):
            anom_type, anom_len = sub_dir.split('_')
            anomaly_dir = os.path.join(product_directory, sub_dir)
            for filename in tqdm(os.listdir(anomaly_dir), desc=f'{sub_dir}'):
                if filename.endswith(".tif"):
                    file_parts = filename.split('.')
                    if file_parts[-2] != 'TEMP':
                        if product == 'chirps':
                            month, day = file_parts[1].split('-')
                            day_value = int(month+day)
                        else:
                            day_value = file_parts[1]
                        try:
                            AnomalyBaselineRaster.objects.get(
                                product=valid_product,
                                day_of_year=day_value,
                                baseline_type=anom_type,
                                baseline_length=anom_len
                            )
                            logging.info(f'{filename} already ingested')
                            pass
                        except AnomalyBaselineRaster.DoesNotExist as e:
                            new_baseline = AnomalyBaselineRaster(
                                product=valid_product,
                                local_path=os.path.join(anomaly_dir, filename)
                            )
                            new_baseline.save()
                            logging.info(f'saved {filename}')
                            # for whatever reason, calling the upload file method
                            # within the save method for anomaly baseline datasets
                            # does not work, unlike product datasets, so we call that method
                            # to upload the datasets to s3 here after saving it
                            new_baseline.upload_file()
                            logging.info(f'uploaded {filename}')

    except Product.DoesNotExist as e1:
        logging.info(
            f'{slugify(product)} is not a valid product within the system.')


def upload_new_anomaly_baselines():
    anomaly_baselines = AnomalyBaselineRaster.objects.all()
    # simply reupload file at local_path, if file is newer than saved date
    for dataset in tqdm(anomaly_baselines):
        file_date = datetime.date.fromtimestamp(
            os.stat(dataset.local_path).st_mtime)
        if file_date > dataset.date_updated:
            logging.info(f'uploading new version of {dataset.slug}')
            dataset.upload_file()
            dataset.date_updated = file_date
            dataset.save()
            logging.info(f'{dataset.slug} upload complete')


def upload_baselines_by_date(product_name, date):
    try:
        product_ds = ProductRaster.objects.get(
            product__name=product_name, date=date)
        # get day of year from file name

        if product_ds.product.product_id == 'chirps':
            base_file = os.path.basename(product_ds.local_path)
            parts = base_file.split(".")
            year, month, day = parts[1].split('-')
            day_value = int(month+day)
            doy = day_value
        else:
            doy = product_ds.date.timetuple().tm_yday

        baselines = AnomalyBaselineRaster.objects.filter(
            product__name=product_name, day_of_year=doy
        )

        for dataset in baselines:
            file_date = datetime.date.fromtimestamp(
                os.stat(dataset.local_path).st_mtime)
            if file_date > dataset.date_updated:
                logging.info(f'uploading new version of {dataset.slug}')
                dataset.upload_file()
                dataset.date_updated = file_date
                dataset.save()
                logging.info(f'{dataset.slug} upload complete')

    except ProductRaster.DoesNotExist:
        logging.info(f'Could not retreive valid dataset')


# def update_anomaly_baselines_by_product(product_id):
#     product = Product.objects.get(product_id=product_id)

#     # get optimal processing parameters
#     if product.meta['optimal_bsf']:
#         bsf = product.meta['optimal_bsf']
#     else:
#         bsf = settings.BLOCK_SCALE_FACTOR

#     if product.meta['optimal_cores']:
#         if product.meta['optimal_cores'] > settings.N_PROCESSES:
#             n_cores = settings.N_PROCESSES
#         else:
#             n_cores = product.meta['optimal_cores']
#     else:
#         n_cores = settings.N_PROCESSES

#     datasets = ProductRaster.objects.filter(product=product).order_by('-date')

#     # only consider data from past 366 days
#     last = datasets[0].date
#     start = last - datetime.timedelta(days=366)

#     for ds in datasets:
#         if ds.date < start:
#             pass
#         else:
#             added = ds.date_added
#             if ds.product.product_id == 'chirps':
#                 base_file = os.path.basename(ds.local_path)
#                 parts = base_file.split(".")
#                 year, month, day = parts[1].split('-')
#                 day_value = int(month+day)
#                 doy = day_value
#             else:
#                 doy = ds.date.timetuple().tm_yday
#             anom_baselines = AnomalyBaselineRaster.objects.filter(
#                 product=product, day_of_year=doy)

#             try:
#                 anom_updated = anom_baselines[0].date_updated
#             except:
#                 anom_updated = datetime.datetime.strptime(
#                     "2000-01-01", "%Y-%m-%d").date()

#             if added > anom_updated:
#                 logging.info(f'updating baselines {ds}')
#                 update = updateBaselines(
#                     product.name, ds.date, n_cores, bsf, time=True)
#                 logging.info(f'{update}')
#                 for bl in anom_baselines:
#                     logging.info(f'uploading fresh baseline {bl}')
#                     bl.upload_file()
#                     bl.date_updated = datetime.date.today()
#                     bl.save
#             else:
#                 logging.info(f'passing {ds}')


# def update_anomaly_baselines_by_product_and_date(product_id, date):
#     product = Product.objects.get(product_id=product_id)

#     # get optimal processing parameters
#     if product.meta['optimal_bsf']:
#         bsf = product.meta['optimal_bsf']
#     else:
#         bsf = settings.BLOCK_SCALE_FACTOR

#     if product.meta['optimal_cores']:
#         if product.meta['optimal_cores'] > settings.N_PROCESSES:
#             n_cores = settings.N_PROCESSES
#         else:
#             n_cores = product.meta['optimal_cores']
#     else:
#         n_cores = settings.N_PROCESSES

#     ds = ProductRaster.objects.get(product=product, date=date)

#     if ds.product.product_id == 'chirps':
#         base_file = os.path.basename(ds.local_path)
#         parts = base_file.split(".")
#         year, month, day = parts[1].split('-')
#         day_value = int(month+day)
#         doy = day_value
#     else:
#         doy = ds.date.timetuple().tm_yday
#     anom_baselines = AnomalyBaselineRaster.objects.filter(
#         product=product, day_of_year=doy)

#     logging.info(f'updating baselines {ds}')
#     update = updateBaselines(product.name, ds.date, n_cores, bsf, time=True)
#     logging.info(f'{update}')
#     for bl in anom_baselines:
#         logging.info(f'uploading fresh baseline {bl}')
#         bl.upload_file()
#         bl.date_updated = datetime.date.today()
#         bl.save


# def trim_nrt_ndvi():
#     mod13q4n = Product.objects.get(product_id='mod13q4n')
#     all_nrt = ProductRaster.objects.filter(product=mod13q4n)
#     keep_ten = ProductRaster.objects.filter(
#         product=mod13q4n).order_by('-date')[:15]

#     all_nrt.exclude(pk__in=keep_ten).delete()


# add geojson

# def add_geojson():
#     import sys, csv
#     from glam.models import BoundaryLayer, BoundaryFeature

#     maxInt = sys.maxsize

#     gaul0 = BoundaryLayer.objects.get(layer_id='gaul0')

#     while True:
#         try:
#             csv.field_size_limit(maxInt)
#             break
#         except OverflowError:
#             maxInt = int(maxInt/10)

#     with open('test.csv') as f:
#         reader = csv.reader(f)
#         next(reader)
#         for row in reader:
#             try:
#                 feature = BoundaryFeature.objects.get(boundary_layer=gaul0, feature_id=int(row[2]))
#                 feature.geojson = row[0]
#                 print(feature.geojson)
#             except:
#                 print('bad!',row[2],row[3])

# geoboundaries rasters
# import os
# import time
# import tqdm
# from django.conf import settings

# import rasterio
# from rasterio.io import MemoryFile
# from rasterio import features
# from rio_cogeo.cogeo import cog_translate
# from rio_cogeo.profiles import cog_profiles

# from pyproj import CRS

# import numpy as np
# import geopandas as gpd


# from glam.models import Product, ProductRaster, BoundaryLayer, BoundaryRaster, BoundaryFeature, Variable

# products = Product.objects.all()

# adm0_layers = BoundaryLayer.objects.filter(tags__name="ADM0")

# for product in tqdm.tqdm(products, desc="product") :
#     for layer in tqdm.tqdm(adm0_layers, desc="layer"):
#         try:
#             boundary_ds = BoundaryRaster.objects.get(boundary_layer=layer, product=product)
#         except:
#             # dataset does not exist
#             # get sample dataset to copy metadata
#             sample_dataset = ProductRaster.objects.filter(product__product_id=product)[0]
#             with rasterio.open(sample_dataset.file_object.url) as raster:
#                 meta = raster.meta.copy()
#                 raster_wkt = raster.profile['crs'].to_wkt()

#             raster_crs = CRS.from_wkt(raster_wkt)

#             vector = gpd.read_file(layer.vector_file.url)
#             vector_wkt = vector.crs.to_wkt()
#             vector_crs = CRS.from_wkt(vector_wkt)

#             new_vector = vector.copy()

#             # reproject vector to product CRS
#             new_vector['geometry'] = new_vector['geometry'].to_crs(raster_crs)
#             # get feature id as integer
#             new_vector['shapeID'] = new_vector['shapeID'].astype(str).str.split('-').str[2].str.replace(r'[^0-9]+', '').astype(int)

#             shapes = ((geom,value) for geom, value in zip(new_vector.geometry, new_vector['shapeID']))
#             filename = product.product_id + '.' + layer.layer_id+'.tif'
#             out_path = os.path.join(settings.BOUNDARY_RASTER_LOCAL_PATH, filename)

#             out = rasterio.open(out_path, 'w+', **meta)
#             burned = features.rasterize(shapes=shapes, fill=0, out_shape=out.shape, transform=out.transform, dtype=meta['dtype'])

#             cog_options = cog_profiles.get("deflate")

#             out_meta = meta
#             out_meta.update(cog_options)

#             with MemoryFile() as memfile:
#                 with memfile.open(**meta) as mem:
#                     mem.write_band(1, burned)
#                     cog_translate(
#                         mem,
#                         out_path,
#                         out_meta,
#                         in_memory=False
#                     )

def create_matching_mask_raster(product_id, cropmask_id):
    """
    function to create a resampled cropmask raster dataset that mathches size and resolution of product raster for zonal statistics calculation
    """
    import os
    import time
    import tqdm
    import shutil
    from django.conf import settings

    import rasterio
    from rasterio.enums import Resampling

    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles

    import rioxarray

    from ..models import Product, CropMask, ProductRaster, BoundaryLayer, BoundaryRaster

    try:
        product = Product.objects.get(product_id=product_id)
        try:
            cropmask = CropMask.objects.get(cropmask_id=cropmask_id)

            # get sample product dataset to copy metadata
            sample_product_ds = ProductRaster.objects.filter(
                product__product_id=product, prelim=False)[0]
            product_raster = sample_product_ds.file_object.url

            product_ds = rioxarray.open_rasterio(
                product_raster, chunks="auto", cache=False)

            # get cropmask raster
            cropmask_raster = cropmask.stats_raster.url

            cropmask_ds = rioxarray.open_rasterio(
                cropmask_raster, chunks="auto", cache=False)

            cropmask_match_ds = cropmask_ds.rio.reproject_match(
                product_ds, resampling=Resampling.cubic)

            # define out file
            tempname = product.product_id + '.' + cropmask.cropmask_id+'_temp.tif'
            filename = product.product_id + '.' + cropmask.cropmask_id+'.tif'
            temp_path = os.path.join(
                settings.MASK_DATASET_LOCAL_PATH, tempname)
            out_path = os.path.join(
                settings.MASK_DATASET_LOCAL_PATH, filename)

            cropmask_match_ds[0].rio.to_raster(
                temp_path, compress="deflate", windowed=True)

            temp = rasterio.open(temp_path)

            # prepare cog definition
            cog_options = cog_profiles.get("deflate")
            out_meta = temp.meta.copy()
            out_meta.update(cog_options)

            cog_translate(
                temp,
                out_path,
                out_meta,
                allow_intermediate_compression=True,
                quiet=False,
                in_memory=False
            )

            os.remove(temp_path)

        except Product.DoesNotExist:
            logging.info(f'No valid crop mask exists matching {cropmask_id}')
    except Product.DoesNotExist:
        logging.info(f'No valid product exists matching {product_id}')


def create_boundary_raster(product_id, layer_id, feature_id_field_name, feature_func=None):
    import os
    from django.conf import settings
    import rasterio
    from rasterio.io import MemoryFile
    from rasterio import features
    from rio_cogeo.cogeo import cog_translate
    from rio_cogeo.profiles import cog_profiles
    from pyproj import CRS
    import geopandas as gpd
    from ..models import Product, ProductRaster, BoundaryLayer, BoundaryRaster

    try:
        product = Product.objects.get(product_id=product_id)
        boundary_layer = BoundaryLayer.objects.get(layer_id=layer_id)
        boundary_raster = BoundaryRaster.objects.get(
            product=product, boundary_layer=boundary_layer)
        logging.info(
            f'Combination exists for {boundary_layer.layer_id} & {product.product_id}')
    except BoundaryRaster.DoesNotExist:
        logging.info(
            f'Combination does not exist for {boundary_layer.layer_id} & {product.product_id}')
        logging.info(
            f'Creating raster file for {boundary_layer.layer_id} at {product.product_id} resolution')
        # get sample dataset to copy metadata
        sample_dataset = ProductRaster.objects.filter(
            product__product_id=product)[0]
        raster = rasterio.open(sample_dataset.file_object.url)

        # copy metadata of sample dataset
        meta = raster.meta.copy()

        # get CRS
        raster_wkt = raster.profile['crs'].to_wkt()
        raster_crs = CRS.from_wkt(raster_wkt)

        # retrieve vector file
        vector = gpd.read_file(boundary_layer.source_data.url)

        # first assign vector CRS
        vector.crs = "EPSG:4326"
        vector_wkt = vector.crs.to_wkt()
        vector_crs = CRS.from_wkt(vector_wkt)

        # reproject new vector to product CRS
        new_vector = vector.copy()
        new_vector['geometry'] = new_vector['geometry'].to_crs(raster_crs)

        # get feature id as integer
        if feature_func:
            new_vector[feature_id_field_name] = feature_func(
                vector, feature_id_field_name)

        # get list of values (feature ids)
        zone_vals = []
        for i in range(len(new_vector)):
            zone_vals.append(new_vector[feature_id_field_name])

        # set data type based on value list
        dtype = rasterio.dtypes.get_minimum_dtype(zone_vals)

        if dtype == None:
            dtype = "int16"

        # update meta object
        meta.update({"dtype": dtype})
        meta.update({"nodata": 0})

        # get shapes
        shapes = ((geom, value) for geom, value in zip(
            new_vector.geometry, new_vector[feature_id_field_name]))

        # define out file
        filename = product.product_id + '.' + boundary_layer.layer_id+'.tif'
        out_path = os.path.join(settings.BOUNDARY_RASTER_LOCAL_PATH, filename)

        # prepare cog definition
        cog_options = cog_profiles.get("deflate")
        out_meta = meta
        out_meta.update(cog_options)

        # rasterize in memory and create output with cog_translate
        with MemoryFile() as memfile:
            with memfile.open(**meta) as mem:
                burned = features.rasterize(
                    shapes=shapes, fill=0, out_shape=mem.shape, transform=mem.transform, dtype=dtype)
                mem.write_band(1, burned)
                cog_translate(
                    mem,
                    out_path,
                    out_meta,
                    in_memory=False
                )

        logging.info(f'Successfully created file: {out_path}')

    except Product.DoesNotExist:
        logging.info(
            f'{product_id} is not a valid product id in the system. Please try again')


def geoboundaries_feature_func(vector, field_name):
    """
    function to parse geoboundaries shapeID for raster creation
    """
    return vector[field_name].astype(str).str.split(
        '-').str[-1].str.split('B').str[-1].astype('int64')


def ingest_geoboundaries_layers(gb_directory, adm_level):
    """
    Bulk load geoBoundaries Layers
    """
    import os
    import json
    import datetime
    from django.core.files import File
    from ..models import Tag, DataSource, BoundaryLayer, CropMask

    admin_level = "ADM" + str(adm_level)
    geoBoundaries = DataSource.objects.get(source_id='geoboundaries')

    for f in os.scandir(gb_directory):
        for level in os.scandir(f.path):
            if level.name == admin_level:
                metadata = ''
                citation = ''
                name = ''
                iso = ''
                created = ''
                for file in os.scandir(level.path):
                    filename, ext = os.path.splitext(file.name)
                    if ext == '.txt':
                        fileparts = filename.split('-')
                        if fileparts[-1] == 'gbOpen':
                            citationFile = open(file.path)
                            citation = citationFile.read()
                        if fileparts[-1] == 'metaData':
                            metadataFile = open(file.path)
                            metadata = metadataFile.read()
                            iso = fileparts[1]
                            name = '-'.join(fileparts[0:3])
                    if ext == '.json':
                        metadataJSONFile = open(file.path)
                        metadataJSON = json.load(metadataJSONFile)
                        created = datetime.datetime.strptime(
                            metadataJSON["buildUpdateDate"], "%b %d, %Y").date()
                description = (metadata + "\n" + citation)
                layer_id = name.lower()
                iso_tag, iso_created = Tag.objects.get_or_create(name=iso)
                level_tag, level_created = Tag.objects.get_or_create(
                    name=level.name)
                source_vector_file = level.path+'/'+name+'.geojson'
                simplified_vector_file = level.path+'/'+name+'_simplified.topojson'
                try:
                    existing_layer = BoundaryLayer.objects.get(
                        layer_id=layer_id
                    )
                    logging.info(f'{existing_layer.name} already saved.')
                except BoundaryLayer.DoesNotExist:

                    new_layer = BoundaryLayer(
                        name=name,
                        layer_id=layer_id,
                        display_name=name,
                        desc=description,
                        source=geoBoundaries,
                        date_created=created,
                        date_added=datetime.date.today(),
                    )
                    source_f = open(source_vector_file, 'rb')
                    new_layer.source_data.save(name+'.geojson', File(source_f))
                    simplified_f = open(simplified_vector_file, 'rb')
                    new_layer.vector_file.save(
                        name+'_simplified.topojson', File(simplified_f))
                    new_layer.save()

                    # add global masks to layer for stats
                    # other masks must be added manually
                    masks = CropMask.objects.filter(tags__name__in=['global'])
                    for mask in masks:
                        new_layer.masks.add(mask)
                    new_layer.tags.add(iso_tag)
                    new_layer.tags.add(level_tag)
                    logging.info(f'Successfully saved {new_layer.name}')


def ingest_geoboundaries_features(gb_directory, adm_level):
    """
    Bulk add geoBoundaries features for available layers
    """
    import os
    import json
    from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
    from ..models import BoundaryLayer, BoundaryFeature

    admin_level = "ADM" + str(adm_level)
    for f in os.scandir(os.path.abspath(gb_directory)):
        for level in os.scandir(f.path):
            if level.name == admin_level:
                name = ''
                iso = ''
                for file in os.scandir(level.path):
                    filename, ext = os.path.splitext(file.name)
                    if ext == '.txt':
                        fileparts = filename.split('-')
                        if fileparts[-1] == 'metaData':
                            iso = fileparts[1]
                            name = '-'.join(fileparts[0:3])

                layer_id = name.lower()
                vector_file = level.path+'/'+name+'.geojson'

                # First, check to see if Boundary Layer exists.
                try:
                    boundary_layer = BoundaryLayer.objects.get(
                        layer_id=layer_id)
                except BoundaryLayer.DoesNotExist:
                    logging.info(
                        f'{layer_id} does not exist in the system as a Boundary Layer.')

                # Then, check to see if any features exist
                existing_features = BoundaryFeature.objects.filter(
                    boundary_layer=boundary_layer)
                feature_count = existing_features.count()
                if feature_count > 0:
                    logging.info(
                        f'There are {feature_count} existing feature(s) for {boundary_layer.name}, skipping feature ingest for this layer.')
                else:
                    with open(vector_file) as f:
                        try:
                            geojson = json.loads(f.read())
                            for feature in geojson.get('features', []):
                                properties = feature.get('properties', {})
                                shape_id = int(properties['shapeID'].split(
                                    '-')[-1].split('B')[-1])
                                if adm_level == 0:
                                    shape_name = iso
                                # For admin levels beyond 0 there are many possibilities
                                elif adm_level >= 1:
                                    try:
                                        shape_name = properties['shapeName']
                                    except:
                                        try:
                                            shape_name = properties['PROV_34_NA']
                                        except:
                                            try:
                                                shape_name = properties['ADM1_NAME']
                                            except:
                                                try:
                                                    shape_name = properties['admin2Name']
                                                except:
                                                    try:
                                                        shape_name = properties['DISTRICT']
                                                    except:
                                                        print(properties)
                                geom = GEOSGeometry(
                                    json.dumps(feature.get('geometry')))
                                # coerce Polygon into MultiPolygon
                                if geom.geom_type == "Polygon":
                                    geom = MultiPolygon(geom)

                                new_unit = BoundaryFeature(
                                    feature_name=shape_name,
                                    feature_id=int(shape_id),
                                    boundary_layer=boundary_layer,
                                    properties=properties,
                                    geom=geom
                                )
                                new_unit.save()
                                logging.info(
                                    f'Successfully saved: {shape_name}-{shape_id}')
                        except Exception as e:
                            logging.info(
                                f'Unable to save features from {vector_file} : {e}')
