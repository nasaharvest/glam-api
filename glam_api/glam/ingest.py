"""
ingest.py

Utilities for ingesting datasets
"""

import os
import json
import datetime
from dateutil.relativedelta import relativedelta

import logging
from tqdm import tqdm

import numpy as np

import rasterio
from rasterio.dtypes import get_minimum_dtype
from rasterio.io import MemoryFile
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles

from django_q.tasks import async_task

from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils.text import slugify
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

from glam.models import (
    Tag,
    DataSource,
    Product,
    ProductRaster,
    BoundaryLayer,
    BoundaryFeature,
    CropMask,
    CropmaskRaster,
    AnomalyBaselineRaster,
)

from glam.utils import extract_datetime_from_filename, get_product_id_from_filename

from config.storage import RasterStorage

logging.basicConfig(
    format="%(asctime)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S", level=logging.INFO
)


def add_cropmask_rasters():
    dataset_directory = settings.MASK_DATASET_LOCAL_PATH

    # loop over the available files in the cropmask_dataset directory
    for filename in tqdm(os.listdir(dataset_directory)):
        if filename.endswith(".tif"):
            # get the file's product and cropmask
            file_parts = filename.split(".")
            file_product = file_parts[0]
            file_mask = file_parts[1]
            file_mask_type = file_parts[2]

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
                        crop_mask=cropmask, product=product, mask_type=file_mask_type
                    )
                    pass
                except CropmaskRaster.DoesNotExist as e2:
                    # if it doesn't exist, make it
                    new_dataset = CropmaskRaster(
                        crop_mask=cropmask,
                        product=product,
                        mask_type=file_mask_type,
                        date_created=datetime.date.today(),
                        local_path=os.path.join(dataset_directory, filename),
                    )
                    logging.info(f"saving {filename}")
                    new_dataset.save()
                    logging.info(f"saved {new_dataset.local_path}")

            except (Product.DoesNotExist, CropMask.DoesNotExist) as e1:
                logging.info(f"{e1}: {file_product},{file_mask}")
                pass


def add_product_rasters_by_product(product):
    try:
        valid_product = Product.objects.get(product_id=slugify(product))
        dataset_directory = os.path.join(settings.PRODUCT_DATASET_LOCAL_PATH, product)

        for filename in tqdm(os.listdir(dataset_directory)):
            if filename.endswith(".tif"):
                parts = filename.split(".")
                # ignore temporary downloads
                if len(parts) < 6:
                    if "prelim" in parts:
                        prelim = True
                        try:
                            ds_date = datetime.datetime.strptime(
                                f"{parts[-4]}.{parts[-3]}", "%Y.%j"
                            ).strftime("%Y-%m-%d")
                        except:
                            ds_date = datetime.datetime.strptime(
                                parts[-3], "%Y-%m-%d"
                            ).strftime("%Y-%m-%d")
                    else:
                        prelim = False
                        try:
                            ds_date = datetime.datetime.strptime(
                                f"{parts[-3]}.{parts[-2]}", "%Y.%j"
                            ).strftime("%Y-%m-%d")
                        except ValueError:
                            try:
                                ds_date = datetime.datetime.strptime(
                                    parts[-2], "%Y-%j"
                                ).strftime("%Y-%m-%d")
                            except:
                                ds_date = datetime.datetime.strptime(
                                    parts[-2], "%Y-%m-%d"
                                ).strftime("%Y-%m-%d")
                    logging.info(ds_date)
                    try:
                        ds = ProductRaster.objects.get(
                            product=valid_product, date=ds_date
                        )
                    except ProductRaster.DoesNotExist:
                        # if it doesn't exist, make it
                        logging.info(len(os.path.join(dataset_directory, filename)))
                        new_dataset = ProductRaster(
                            product=valid_product,
                            prelim=prelim,
                            date=ds_date,  # dont actually need this here
                            local_path=os.path.join(dataset_directory, filename),
                        )
                        logging.info(new_dataset)
                        logging.info(f"saving {filename}")
                        new_dataset.save()
                        logging.info(f"saved {new_dataset.local_path}")

    except Product.DoesNotExist as e1:
        logging.info(f"{slugify(product)} is not a valid product within the system.")


def add_product_rasters_from_storage():
    if not settings.USE_S3:
        raster_storage = FileSystemStorage()
    elif settings.USE_S3:
        raster_storage = RasterStorage()

    raster_files = raster_storage.listdir("product-rasters")[1]

    for filename in tqdm(raster_files):
        if filename.endswith(".tif"):
            if "prelim" in filename:
                prelim = True
            else:
                prelim = False
            ds_date = extract_datetime_from_filename(filename)
            product_id = get_product_id_from_filename(filename)
            dataset_directory = os.path.join(
                settings.PRODUCT_DATASET_LOCAL_PATH, product_id
            )
            if product_id and ds_date:
                logging.info(ds_date)
                logging.info(product_id)
                valid_product = Product.objects.get(product_id=slugify(product_id))
                try:
                    ds = ProductRaster.objects.get(product=valid_product, date=ds_date)
                    logging.info(f"{filename} exists")
                except ProductRaster.DoesNotExist:
                    # if it doesn't exist, make it
                    new_dataset = ProductRaster(
                        product=valid_product,
                        prelim=prelim,
                        date=ds_date,
                        local_path=filename,
                        file_object=f"product-rasters/{filename}",
                    )
                    logging.info(f"saving {filename}")
                    new_dataset.save()
                    logging.info(f"saved {new_dataset}")


# for initial ingest of anomaly baseline datasets
def add_anomaly_baselines(product_id):
    try:
        valid_product = Product.objects.get(product_id=slugify(product_id))
        baseline_directory = os.path.join(
            settings.ANOMALY_BASELINE_LOCAL_PATH, product_id
        )

        for filename in tqdm(os.listdir(baseline_directory)):
            if filename.endswith(".tif"):
                parts = filename.split(".")
                anom_len = parts[1]
                anom_type = parts[2]

                if product_id in ["chirps-precip", "copernicus-swi"]:
                    month, day = parts[3].split("-")
                    day_value = int(month + day)
                else:
                    day_value = int(parts[3])
                try:
                    AnomalyBaselineRaster.objects.get(
                        product=valid_product,
                        day_of_year=day_value,
                        baseline_type=anom_type,
                        baseline_length=anom_len,
                    )
                    logging.info(f"{filename} already ingested")
                    pass
                except AnomalyBaselineRaster.DoesNotExist as e:
                    new_baseline = AnomalyBaselineRaster(
                        product=valid_product,
                        local_path=os.path.join(baseline_directory, filename),
                    )
                    new_baseline.save()
                    logging.info(f"saved {filename}")
                    # for whatever reason, calling the upload file method
                    # within the save method for anomaly baseline datasets
                    # does not work, unlike product datasets, so we call that method
                    # to upload the datasets to s3 here after saving it
                    new_baseline.upload_file()
                    logging.info(f"uploaded {filename}")

    except Product.DoesNotExist as e1:
        logging.info(f"{slugify(product_id)} is not a valid product within the system.")


def add_geojson_layer(layer_id):
    """
    Adds a geojson file to the BoundaryLayer model.
    :param layer_id: a unique identifier for the BoundaryLayer instance.
    :return: None
    """
    try:
        BoundaryLayer.objects.get(layer_id=slugify(layer_id))
        logging.info(f"{slugify(layer_id)} already exists")
        return
    except BoundaryLayer.DoesNotExist as e:
        geojson_path = os.path.join(settings.GEOJSON_LOCAL_PATH, f"{layer_id}.geojson")
        with open(geojson_path) as f:
            geojson_data = json.load(f)
        new_layer = BoundaryLayer(
            name=geojson_data["name"],
            layer_id=slugify(layer_id),
            display_name=geojson_data["display_name"],
            desc=geojson_data["desc"],
            source=geojson_data["source"],
            date_created=geojson_data["date_created"],
            date_added=geojson_data["date_added"],
        )
        new_layer.save()
        logging.info(f"saved {layer_id}")


def add_geojson_features(layer_id):
    """
    Adds a geojson file to the BoundaryLayer and BoundaryFeature models.
    :param layer_id: a unique identifier for the BoundaryLayer instance.
    :return: None
    """
    try:
        valid_layer = BoundaryLayer.objects.get(layer_id=slugify(layer_id))
        geojson_path = os.path.join(settings.GEOJSON_LOCAL_PATH, f"{layer_id}.geojson")
        with open(geojson_path) as f:
            geojson_data = json.load(f)
        valid_layer.save()
        logging.info(f"Saved geojson for {layer_id}")
        for feature in geojson_data["features"]:
            geom = GEOSGeometry(json.dumps(feature.get("geometry")))
            # coerce Polygon into MultiPolygon
            if geom.geom_type == "Polygon":
                geom = MultiPolygon(geom)

            new_boundary_feature = BoundaryFeature(
                feature_name=feature["properties"]["name"],
                feature_id=feature["properties"]["id"],
                boundary_layer=valid_layer,
                properties=feature["properties"],
                geom=geom,
            )
            new_boundary_feature.save()
            logging.info(f"Saved feature {feature['properties']['name']}")
    except BoundaryLayer.DoesNotExist as e:
        logging.info(
            f"{slugify(layer_id)} is not a valid boundary layer within the system."
        )


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

    from glam.models import (
        Product,
        CropMask,
        ProductRaster,
        BoundaryLayer,
        BoundaryRaster,
    )

    try:
        product = Product.objects.get(product_id=product_id)
        try:
            cropmask = CropMask.objects.get(cropmask_id=cropmask_id)

            # get sample product dataset to copy metadata
            sample_product_ds = ProductRaster.objects.filter(
                product__product_id=product, prelim=False
            )[0]
            product_raster = sample_product_ds.file_object.url

            product_ds = rioxarray.open_rasterio(
                product_raster, chunks="auto", cache=False
            )

            # get cropmask raster
            cropmask_raster = cropmask.stats_raster.url

            cropmask_ds = rioxarray.open_rasterio(
                cropmask_raster, chunks="auto", cache=False
            )

            cropmask_match_ds = cropmask_ds.rio.reproject_match(
                product_ds, resampling=Resampling.cubic
            )

            # define out file
            basename = (
                product.product_id
                + "."
                + cropmask.cropmask_id
                + "."
                + cropmask.stats_mask_type
            )
            tempname = basename + "_temp.tif"
            filename = basename + ".tif"
            temp_path = os.path.join(settings.MASK_DATASET_LOCAL_PATH, tempname)
            out_path = os.path.join(settings.MASK_DATASET_LOCAL_PATH, filename)

            cropmask_match_ds[0].rio.to_raster(
                temp_path, compress="deflate", windowed=True
            )

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
                in_memory=False,
            )
            os.remove(temp_path)

            return out_path

        except Product.DoesNotExist:
            logging.info(f"No valid crop mask exists matching {cropmask_id}")
    except Product.DoesNotExist:
        logging.info(f"No valid product exists matching {product_id}")


def ingest_geoboundaries_layers(gb_directory, adm_level):
    """
    Bulk load geoBoundaries Layers
    """

    admin_level = "ADM" + str(adm_level)
    geoBoundaries = DataSource.objects.get(source_id="geoboundaries")

    for f in os.scandir(gb_directory):
        for level in os.scandir(f.path):
            if level.name == admin_level:
                metadata = ""
                citation = ""
                name = ""
                iso = ""
                created = ""
                for file in os.scandir(level.path):
                    filename, ext = os.path.splitext(file.name)
                    if ext == ".txt":
                        fileparts = filename.split("-")
                        if fileparts[-1] == "gbOpen":
                            citationFile = open(file.path)
                            citation = citationFile.read()
                        if fileparts[-1] == "metaData":
                            metadataFile = open(file.path)
                            metadata = metadataFile.read()
                            iso = fileparts[1]
                            name = "-".join(fileparts[0:3])
                    if ext == ".json":
                        metadataJSONFile = open(file.path)
                        metadataJSON = json.load(metadataJSONFile)
                        created = datetime.datetime.strptime(
                            metadataJSON["buildDate"], "%b %d, %Y"
                        ).date()
                description = metadata + "\n" + citation
                layer_id = name.lower()
                iso_tag, iso_created = Tag.objects.get_or_create(name=iso)
                level_tag, level_created = Tag.objects.get_or_create(name=level.name)
                source_vector_file = level.path + "/" + name + ".geojson"
                simplified_vector_file = (
                    level.path + "/" + name + "_simplified.topojson"
                )
                try:
                    existing_layer = BoundaryLayer.objects.get(layer_id=layer_id)
                    logging.info(f"{existing_layer.name} already saved.")
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
                    source_f = open(source_vector_file, "rb")
                    new_layer.source_data.save(name + ".geojson", File(source_f))
                    simplified_f = open(simplified_vector_file, "rb")
                    new_layer.vector_file.save(
                        name + "_simplified.topojson", File(simplified_f)
                    )
                    new_layer.save()

                    # add global masks to layer for stats
                    # other masks must be added manually
                    masks = CropMask.objects.filter(tags__name__in=["global"])
                    for mask in masks:
                        new_layer.masks.add(mask)
                    new_layer.tags.add(iso_tag)
                    new_layer.tags.add(level_tag)
                    logging.info(f"Successfully saved {new_layer.name}")


def ingest_geoboundaries_features(gb_directory, adm_level):
    """
    Bulk add geoBoundaries features for available layers
    """

    admin_level = "ADM" + str(adm_level)
    for f in os.scandir(os.path.abspath(gb_directory)):
        for level in os.scandir(f.path):
            if level.name == admin_level:
                name = ""
                iso = ""
                for file in os.scandir(level.path):
                    filename, ext = os.path.splitext(file.name)
                    if ext == ".txt":
                        fileparts = filename.split("-")
                        if fileparts[-1] == "metaData":
                            iso = fileparts[1]
                            name = "-".join(fileparts[0:3])

                layer_id = name.lower()
                vector_file = level.path + "/" + name + ".geojson"

                # First, check to see if Boundary Layer exists.
                try:
                    boundary_layer = BoundaryLayer.objects.get(layer_id=layer_id)
                except BoundaryLayer.DoesNotExist:
                    logging.info(
                        f"{layer_id} does not exist in the system as a Boundary Layer."
                    )

                # Then, check to see if any features exist
                existing_features = BoundaryFeature.objects.filter(
                    boundary_layer=boundary_layer
                )
                feature_count = existing_features.count()
                if feature_count > 0:
                    logging.info(
                        f"There are {feature_count} existing feature(s) for {boundary_layer.name}, skipping feature ingest for this layer."
                    )
                else:
                    with open(vector_file) as f:
                        try:
                            geojson = json.loads(f.read())
                            for feature in geojson.get("features", []):
                                properties = feature.get("properties", {})
                                shape_id = int(
                                    properties["shapeID"].split("-")[-1].split("B")[-1]
                                )
                                if adm_level == 0:
                                    shape_name = iso
                                # For admin levels beyond 0 there are many possibilities
                                elif adm_level >= 1:
                                    try:
                                        shape_name = properties["shapeName"]
                                    except:
                                        try:
                                            shape_name = properties["PROV_34_NA"]
                                        except:
                                            try:
                                                shape_name = properties["ADM1_NAME"]
                                            except:
                                                try:
                                                    shape_name = properties[
                                                        "admin2Name"
                                                    ]
                                                except:
                                                    try:
                                                        shape_name = properties[
                                                            "DISTRICT"
                                                        ]
                                                    except:
                                                        print(properties)
                                geom = GEOSGeometry(json.dumps(feature.get("geometry")))
                                # coerce Polygon into MultiPolygon
                                if geom.geom_type == "Polygon":
                                    geom = MultiPolygon(geom)

                                new_unit = BoundaryFeature(
                                    feature_name=shape_name,
                                    feature_id=int(shape_id),
                                    boundary_layer=boundary_layer,
                                    properties=properties,
                                    geom=geom,
                                )
                                new_unit.save()
                                logging.info(
                                    f"Successfully saved: {shape_name}-{shape_id}"
                                )
                        except Exception as e:
                            logging.info(
                                f"Unable to save features from {vector_file} : {e}"
                            )
