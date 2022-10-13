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
from ..models import (Product, ProductDataset, AdminLayer, AdminDataset,
                      CropMask, MaskDataset, AnomalyBaselineDataset)

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=logging.INFO)


def update_admin_datasets():
    dataset_directory = settings.ADMIN_DATASET_LOCAL_PATH

    # loop over the available files in the admin_dataset directory
    for filename in tqdm(os.listdir(dataset_directory)):
        if filename.endswith(".tif"):
            # get the file's product and admin layer
            file_product, file_admin, _ = filename.split('.')
            # slugify names
            file_product = slugify(file_product)
            file_admin = slugify(file_admin)

            # see if related product and admin layer are in the system
            try:
                product = Product.objects.get(product_id=file_product)
                adminlayer = AdminLayer.objects.get(adminlayer_id=file_admin)

                # see if adminlayer dataset already in the system for this combination
                try:
                    AdminDataset.objects.get(
                        admin_layer=adminlayer,
                        product=product)
                    pass
                except AdminDataset.DoesNotExist as e2:
                    # if it doesn't exist, make it
                    new_dataset = AdminDataset(
                        admin_layer=adminlayer,
                        product=product,
                        date_created=datetime.date.today(),
                        local_path=os.path.join(dataset_directory, filename))
                    logging.info(f'saving {filename}')
                    new_dataset.save()
                    logging.info(f'saved {new_dataset.local_path}')

            except (Product.DoesNotExist, AdminLayer.DoesNotExist) as e1:
                logging.info(f'{e1}: {file_product},{file_admin}')
                pass


def update_mask_datasets():
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
                    MaskDataset.objects.get(
                        crop_mask=cropmask,
                        product=product)
                    pass
                except MaskDataset.DoesNotExist as e2:
                    # if it doesn't exist, make it
                    new_dataset = MaskDataset(
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


def update_product_datasets(product):
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

                try:
                    ProductDataset.objects.get(
                        product=valid_product,
                        date=ds_date)
                    pass
                except ProductDataset.DoesNotExist as e2:
                    # if it doesn't exist, make it
                    new_dataset = ProductDataset(
                        product=valid_product,
                        date=ds_date,  # dont actually need this here
                        local_path=os.path.join(dataset_directory, filename))
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
                            AnomalyBaselineDataset.objects.get(
                                product=valid_product,
                                day_of_year=day_value,
                                baseline_type=anom_type,
                                baseline_length=anom_len
                            )
                            logging.info(f'{filename} already ingested')
                            pass
                        except AnomalyBaselineDataset.DoesNotExist as e:
                            new_baseline = AnomalyBaselineDataset(
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
    anomaly_baselines = AnomalyBaselineDataset.objects.all()
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
        product_ds = ProductDataset.objects.get(
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

        baselines = AnomalyBaselineDataset.objects.filter(
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

    except ProductDataset.DoesNotExist:
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

#     datasets = ProductDataset.objects.filter(product=product).order_by('-date')

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
#             anom_baselines = AnomalyBaselineDataset.objects.filter(
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

#     ds = ProductDataset.objects.get(product=product, date=date)

#     if ds.product.product_id == 'chirps':
#         base_file = os.path.basename(ds.local_path)
#         parts = base_file.split(".")
#         year, month, day = parts[1].split('-')
#         day_value = int(month+day)
#         doy = day_value
#     else:
#         doy = ds.date.timetuple().tm_yday
#     anom_baselines = AnomalyBaselineDataset.objects.filter(
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
#     all_nrt = ProductDataset.objects.filter(product=mod13q4n)
#     keep_ten = ProductDataset.objects.filter(
#         product=mod13q4n).order_by('-date')[:15]

#     all_nrt.exclude(pk__in=keep_ten).delete()


# add geojson

# def add_geojson():
#     import sys, csv
#     from server.models import AdminLayer, AdminUnit

#     maxInt = sys.maxsize

#     gaul0 = AdminLayer.objects.get(adminlayer_id='gaul0')

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
#                 admin = AdminUnit.objects.get(admin_layer=gaul0, admin_unit_id=int(row[2]))
#                 admin.geojson = row[0]
#                 print(admin.geojson)
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


# from server.models import Product, ProductDataset, AdminLayer, AdminDataset, AdminUnit, Variable

# products = Product.objects.all()

# adm0_layers = AdminLayer.objects.filter(tags__name="ADM0")

# for product in tqdm.tqdm(products, desc="product") :
#     for layer in tqdm.tqdm(adm0_layers, desc="layer"):
#         try:
#             admin_ds = AdminDataset.objects.get(admin_layer=layer, product=product)
#         except:
#             # dataset does not exist
#             # get sample dataset to copy metadata
#             sample_dataset = ProductDataset.objects.filter(product__product_id=product)[0]
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
#             # get admin id as integer
#             new_vector['shapeID'] = new_vector['shapeID'].astype(str).str.split('-').str[2].str.replace(r'[^0-9]+', '').astype(int)

#             shapes = ((geom,value) for geom, value in zip(new_vector.geometry, new_vector['shapeID']))
#             filename = product.product_id + '.' + layer.adminlayer_id+'.tif'
#             out_path = os.path.join(settings.ADMIN_DATASET_LOCAL_PATH, filename)

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
