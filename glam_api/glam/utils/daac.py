import os
import re
import sys
import csv
import glob
import h5py
import requests
import subprocess
from requests_futures.sessions import FuturesSession
from concurrent.futures import as_completed
import logging
from io import StringIO
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm
import rasterio
from rasterio.dtypes import get_minimum_dtype
from rasterio.io import MemoryFile
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
import numpy as np
from cmr import CollectionQuery, GranuleQuery, ToolQuery, ServiceQuery, VariableQuery

from django.conf import settings

from ..utils import exceptions
from config.local_settings.credentials import CREDENTIALS

from ..utils.spectral import calc_ndvi, calc_ndwi

logging.basicConfig(
    format="%(asctime)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    level=settings.LOG_LEVELS[settings.LOG_LEVEL],
)
log = logging.getLogger(__name__)

LP_DAAC_URL = "https://e4ftl01.cr.usgs.gov/"
LAADS_DAAC_URL = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/"
LANCE_NRT_URL = "https://nrt3.modaps.eosdis.nasa.gov/archive/allData/"

NASA_PRODUCTS = [
    "MOD09Q1",
    "MYD09Q1",
    "MOD13Q1",
    "MYD13Q1",
    "MOD09A1",
    "MYD09A1",
    "MYD09GA",
    "MOD09Q1N",
    "MOD13Q4N",
    "MOD09CMG",
    "VNP09H1",
    "VNP09A1",
    "VNP09GA",
    "VNP09CMG",
    "MCD12Q1",
]

# WKT of default Sinusoidal Projection
SINUS_WKT = 'PROJCS["unnamed",GEOGCS["Unknown datum based upon the custom spheroid",DATUM["Not_specified_based_on_custom_spheroid",SPHEROID["Custom spheroid",6371007.181,0]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]]],PROJECTION["Sinusoidal"],PARAMETER["longitude_of_center",0],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'


def get_collection(product):
    # determine whether Near-Real-Time product
    prefix = product[:3]

    # assign correct collection number
    if prefix == "VNP":
        collection = "001"
    else:
        collection = "061"
    return collection


def get_lp_directory(product):
    prefix = product[:3]

    if prefix == "VNP":
        directory = "VIIRS"
    elif prefix == "MOD":
        directory = "MOLT"
    elif prefix == "MYD":
        directory = "MOLA"
    elif prefix == "MCD":
        directory = "MOTA"

    return directory


def get_dtype_from_sds_name(sds_name):
    # given name of sds return string representation of dtype
    if "sur_refl_b" in sds_name:
        return "int16"
    elif sds_name in ["sur_refl_qc_500m"]:
        return "uint32"
    elif sds_name in [
        "sur_refl_szen",
        "sur_refl_vzen",
        "sur_refl_raz",
        "RelativeAzimuth",
        "SolarZenith",
        "SensorZenith",
        "SurfReflect_I1",
        "SurfReflect_I2",
        "SurfReflect_I3",
        "SurfReflect_I1_1",
        "SurfReflect_I2_1",
    ]:
        return "int16"
    elif sds_name in [
        "sur_refl_state_500m",
        "sur_refl_day_of_year",
        "sur_refl_state_250m",
        "sur_refl_qc_250m",
        "SurfReflect_Day_Of_Year",
        "SurfReflect_State_500m",
        "SurfReflect_QC_500m",
    ]:
        return "uint16"
    elif sds_name in ["LC_Type1"]:
        return "uint8"


def get_h5_geo_info(file):
    # Get info from the StructMetadata Object
    metadata = file["HDFEOS INFORMATION"]["StructMetadata.0"][()].split()
    # Info returned is of type Byte, must convert to string before using it
    metadata_byte2str = [s.decode("utf-8") for s in metadata]
    # Get upper left points
    ulc = [i for i in metadata_byte2str if "UpperLeftPointMtrs" in i]
    ulc_lon = float(
        ulc[0].replace("=", ",").replace("(", "").replace(")", "").split(",")[1]
    )
    ulc_lat = float(
        ulc[0].replace("=", ",").replace("(", "").replace(")", "").split(",")[2]
    )
    return (ulc_lon, 0.0, ulc_lat, 0.0)


def is_nrt(product):
    if product[-1] == "N":
        nrt = True
    else:
        nrt = False
    return nrt


def get_sds(dataset, name):
    for sds in dataset.subdatasets:
        sds_parts = sds.split(":")
        if sds_parts[0] == "HDF4_EOS":
            if sds_parts[-1] == name:
                band = rasterio.open(sds)
                return (band.read(), band.nodata)
        elif sds_parts[0] == "HDF5":
            if sds_parts[-1].split("/")[-1] == name:
                band = rasterio.open(sds)
                return (band.read(), band.nodata)


def get_sds_path(dataset, name):
    for sds in dataset.subdatasets:
        sds_parts = sds.split(":")
        if sds_parts[0] == "HDF4_EOS":
            if sds_parts[-1] == name:
                return sds
        elif sds_parts[0] == "HDF5":
            if sds_parts[-1].split("/")[-1] == name:
                return sds


def apply_mask(in_array, source_dataset, nodata):
    """
    This function removes non-clear pixels from an input array,
    including clouds, cloud shadow, and water.

    For M*D CMG files, removes pixels ranked below "8" in
    MOD13Q1 compositing method, as well as water.

    Returns a cleaned array.

    ...

    Parameters
    ----------

    in_array: numpy.array
        The array to be cleaned. This must have the same dimensions
        as source_dataset, and preferably have been extracted from the
        stack.
    source_dataset: str
        Path to a hierarchical data file containing QA layers with
        which to perform the masking. Currently valid formats include
        MOD09Q1 hdf and VNP09H1 files.
    """

    # get file extension and product suffix
    file_path = source_dataset.name
    file_name = os.path.basename(file_path)
    suffix = file_name.split(".")[0][3:]
    ext = file_name.split(".")[-1]

    # product-conditional behavior

    # MODIS pre-generated VI masking
    if suffix in ["13Q1", "13Q4", "13Q4N"]:
        if suffix[-1] == "1":
            pr_arr, pr_nodata = get_sds(
                source_dataset, "250m 16 days pixel reliability"
            )
            qa_arr, qa_nodata = get_sds(source_dataset, "250m 16 days VI Quality")
        else:
            pr_arr, pr_nodata = get_sds(source_dataset, "250m 8 days pixel reliability")
            qa_arr, qa_nodata = get_sds(source_dataset, "250m 8 days VI Quality")

        # in_array[(pr_arr != 0) & (pr_arr != 1)] = nodata

        # mask clouds
        in_array[(qa_arr & 0b11) > 1] = nodata  # bits 0-1 > 01 = Cloudy

        # mask Aerosol
        in_array[(qa_arr & 0b11000000) == 0] = nodata  # climatology
        in_array[(qa_arr & 0b11000000) == 192] = nodata  # high

        # mask water
        in_array[
            ((qa_arr & 0b11100000000000) != 2048)
            & ((qa_arr & 0b11100000000000) != 4096)
            & ((qa_arr & 0b11100000000000) != 8192)
        ] = nodata
        # 001 = land, 010 = coastline, 100 = ephemeral water

        # mask snow/ice
        in_array[(qa_arr & 0b100000000000000) != 0] = nodata  # bit 14

        # mask cloud shadow
        in_array[(qa_arr & 0b1000000000000000) != 0] = nodata  # bit 15

        # mask cloud adjacent pixels
        in_array[(qa_arr & 0b100000000) != 0] = nodata  # bit 8

    # MODIS and VIIRS surface reflectance masking
    # CMG
    elif suffix == "09CM":
        if ext == "hdf":  # MOD09CMG
            qa_arr, qa_nodata = get_sds(source_dataset, "Coarse Resolution QA")
            state_arr, state_nodata = get_sds(
                source_dataset, "Coarse Resolution State QA"
            )
            vang_arr, vang_nodata = get_sds(
                source_dataset, "Coarse Resolution View Zenith Angle"
            )
            vang_arr[vang_arr <= 0] = 9999
            sang_arr, sang_nodata = get_sds(
                source_dataset, "Coarse Resolution Solar Zenith Angle"
            )
            rank_arr = np.full(qa_arr.shape, 10)  # empty rank array

            # perform the ranking!
            logging.debug("--rank 9: SNOW")
            SNOW = (state_arr & 0b1000000000000) | (
                state_arr & 0b1000000000000000
            )  # state bit 12 OR 15
            rank_arr[SNOW > 0] = 9  # snow
            del SNOW
            logging.debug("--rank 8: HIGHAEROSOL")
            HIGHAEROSOL = state_arr & 0b11000000  # state bits 6 AND 7
            rank_arr[HIGHAEROSOL == 192] = 8
            del HIGHAEROSOL
            logging.debug("--rank 7: CLIMAEROSOL")
            CLIMAEROSOL = state_arr & 0b11000000  # state bits 6 & 7
            # CLIMAEROSOL=(cloudMask & 0b100000000000000) # cloudMask bit 14
            rank_arr[CLIMAEROSOL == 0] = 7  # default aerosol level
            del CLIMAEROSOL
            logging.debug("--rank 6: UNCORRECTED")
            UNCORRECTED = qa_arr & 0b11  # qa bits 0 AND 1
            rank_arr[UNCORRECTED == 3] = 6  # flagged uncorrected
            del UNCORRECTED
            logging.debug("--rank 5: SHADOW")
            SHADOW = state_arr & 0b100  # state bit 2
            rank_arr[SHADOW == 4] = 5  # cloud shadow
            del SHADOW
            logging.debug("--rank 4: CLOUDY")
            # set adj to 11 and internal to 12 to verify in qa output
            # state bit 0 OR bit 1 OR bit 10 OR bit 13
            CLOUDY = state_arr & 0b11
            # rank_arr[CLOUDY!=0]=4 # cloud pixel
            del CLOUDY
            CLOUDADJ = state_arr & 0b10000000000000
            # rank_arr[CLOUDADJ>0]=4 # adjacent to cloud
            del CLOUDADJ
            CLOUDINT = state_arr & 0b10000000000
            rank_arr[CLOUDINT > 0] = 4
            del CLOUDINT
            logging.debug("--rank 3: HIGHVIEW")
            rank_arr[sang_arr > (85 / 0.01)] = 3  # HIGHVIEW
            logging.debug("--rank 2: LOWSUN")
            rank_arr[vang_arr > (60 / 0.01)] = 2  # LOWSUN
            # BAD pixels
            # qa bits (2-5 OR 6-9 == 1110)
            logging.debug("--rank 1: BAD pixels")
            BAD = (qa_arr & 0b111100) | (qa_arr & 0b1110000000)
            rank_arr[BAD == 112] = 1
            rank_arr[BAD == 896] = 1
            rank_arr[BAD == 952] = 1
            del BAD

            logging.debug("-building water mask")
            water = state_arr & 0b111000  # check bits
            water[water == 56] = 1  # deep ocean
            water[water == 48] = 1  # continental/moderate ocean
            water[water == 24] = 1  # shallow inland water
            water[water == 40] = 1  # deep inland water
            water[water == 0] = 1  # shallow ocean
            rank_arr[water == 1] = 0
            vang_arr[water == 32] = 9999  # ephemeral water???
            water[state_arr == 0] = 0
            water[water != 1] = 0  # set non-water to zero
            in_array[rank_arr <= 7] = nodata
        elif ext == "h5":  # VNP09CMG
            qf2, qf2_nodata = get_sds(source_dataset, "SurfReflect_QF2")
            qf4, qf4_nodata = get_sds(source_dataset, "SurfReflect_QF4")
            state_arr, state_nodata = get_sds(source_dataset, "State_QA")
            vang_arr, vang_nodata = get_sds(source_dataset, "SensorZenith")
            vang_arr[vang_arr <= 0] = 9999
            sang_arr, sang_nodata = get_sds(source_dataset, "SolarZenith")
            rank_arr = np.full(state_arr.shape, 10)  # empty rank array

            # perform the ranking!
            logging.debug("--rank 9: SNOW")
            SNOW = state_arr & 0b1000000000000000  # state bit 15
            rank_arr[SNOW > 0] = 9  # snow
            del SNOW
            logging.debug("--rank 8: HIGHAEROSOL")
            HIGHAEROSOL = qf2 & 0b10000  # qf2 bit 4
            rank_arr[HIGHAEROSOL != 0] = 8
            del HIGHAEROSOL
            logging.debug("--rank 7: AEROSOL")
            CLIMAEROSOL = state_arr & 0b1000000  # state bit 6
            # CLIMAEROSOL=(cloudMask & 0b100000000000000) # cloudMask bit 14
            # rank_arr[CLIMAEROSOL==0]=7 # "No"
            del CLIMAEROSOL
            # logging.debug("--rank 6: UNCORRECTED")
            # UNCORRECTED = (qa_arr & 0b11) # qa bits 0 AND 1
            # rank_arr[UNCORRECTED==3]=6 # flagged uncorrected
            # del UNCORRECTED
            logging.debug("--rank 5: SHADOW")
            SHADOW = state_arr & 0b100  # state bit 2
            rank_arr[SHADOW != 0] = 5  # cloud shadow
            del SHADOW
            logging.debug("--rank 4: CLOUDY")
            # set adj to 11 and internal to 12 to verify in qa output
            # CLOUDY = ((state_arr & 0b11)) # state bit 0 OR bit 1 OR bit 10 OR bit 13
            # rank_arr[CLOUDY!=0]=4 # cloud pixel
            # del CLOUDY
            # CLOUDADJ = (state_arr & 0b10000000000) # nonexistent for viirs
            # #rank_arr[CLOUDADJ>0]=4 # adjacent to cloud
            # del CLOUDADJ
            CLOUDINT = state_arr & 0b10000000000  # state bit 10
            rank_arr[CLOUDINT > 0] = 4
            del CLOUDINT
            logging.debug("--rank 3: HIGHVIEW")
            rank_arr[sang_arr > (85 / 0.01)] = 3  # HIGHVIEW
            logging.debug("--rank 2: LOWSUN")
            rank_arr[vang_arr > (60 / 0.01)] = 2  # LOWSUN
            # BAD pixels
            # qa bits (2-5 OR 6-9 == 1110)
            logging.debug("--rank 1: BAD pixels")
            BAD = qf4 & 0b110
            rank_arr[BAD != 0] = 1
            del BAD

            logging.debug("-building water mask")
            water = state_arr & 0b111000  # check bits 3-5
            water[water == 40] = 0  # "coastal" = 101
            water[water > 8] = 1  # sea water = 011; inland water = 010
            # water[water==16]=1 # inland water = 010
            # water[state_arr==0]=0
            water[water != 1] = 0  # set non-water to zero
            water[water != 0] = 1
            rank_arr[water == 1] = 0
            in_array[rank_arr <= 7] = nodata
        else:
            raise exceptions.FileTypeError("File must be of format .hdf or .h5")
    # standard
    else:
        # viirs
        if ext == "h5":
            qa_arr, qa_nodata = get_sds(source_dataset, "SurfReflect_QC_500m")
            state_arr, state_nodata = get_sds(source_dataset, "SurfReflect_State_500m")
        # MOD09A1
        elif suffix == "09A1":
            qa_arr, qa_nodata = get_sds(source_dataset, "sur_refl_qc_500m")
            state_arr, state_nodata = get_sds(source_dataset, "sur_refl_state_500m")
        elif suffix == "09GA":
            qa_arr, qa_nodata = get_sds(source_dataset, "QC_500m_1")
            state_arr, state_nodata = get_sds(source_dataset, "state_1km_1")
        # all other MODIS products
        elif ext == "hdf":
            qa_arr, qa_nodata = get_sds(source_dataset, "sur_refl_qc_250m")
            state_arr, state_nodata = get_sds(source_dataset, "sur_refl_state_250m")
        else:
            raise exceptions.FileTypeError("File must be of format .hdf or .h5")

        # mask clouds
        in_array[(state_arr & 0b11) != 0] = nodata
        in_array[(state_arr & 0b10000000000) != 0] = -3000  # internal cloud mask

        # mask cloud shadow
        in_array[(state_arr & 0b100) != 0] = nodata

        # mask cloud adjacent pixels
        in_array[(state_arr & 0b10000000000000) != 0] = nodata

        # mask aerosols
        in_array[(state_arr & 0b11000000) == 0] = nodata  # climatology
        # high; known to be an unreliable flag in MODIS collection 6
        in_array[(state_arr & 0b11000000) == 192] = nodata

        # mask snow/ice
        in_array[(state_arr & 0b1000000000000) != 0] = nodata

        # mask water
        # checks against three 'allowed' land/water classes and excludes pixels that don't match
        in_array[
            ((state_arr & 0b111000) != 8)
            & ((state_arr & 0b111000) != 16)
            & ((state_arr & 0b111000) != 32)
        ] = nodata

        # mask bad solar zenith
        # in_array[(qa_arr & 0b11100000) != 0] = nodata

    # return output
    return in_array


def get_ndvi_array(dataset):
    file_path = dataset.name
    file_name = os.path.basename(file_path)
    suffix = file_name.split(".")[0][3:]
    ext = file_name.split(".")[-1]

    if suffix in ["09Q4", "13Q4", "13Q4N"]:
        band_name = "250m 8 days NDVI"
        ndvi_array, ndvi_nodata = get_sds(dataset, band_name)
        return (ndvi_array, ndvi_nodata)
    elif suffix == "13Q1":
        band_name = "250m 16 days NDVI"
        ndvi_array, ndvi_nodata = get_sds(dataset, band_name)
        return (ndvi_array, ndvi_nodata)
    elif suffix == "09CM":
        if ext == "hdf":
            red_name = "Coarse Resolution Surface Reflectance Band 1"
            nir_name = "Coarse Resolution Surface Reflectance Band 2"
        elif ext == "h5":
            red_name = "SurfReflect_I1"
            nir_name = "SurfReflect_I2"

        red_band, red_nodata = get_sds(dataset, red_name)
        nir_band, nir_nodata = get_sds(dataset, nir_name)

        ndvi_array = calc_ndvi(red_band, nir_band)
        return (ndvi_array, red_nodata)
    elif suffix == "09GA":
        if ext == "hdf":
            red_name = "sur_refl_b01_1"
            nir_name = "sur_refl_b02_1"
        elif ext == "h5":
            red_name = "SurfReflect_I1_1"
            nir_name = "SurfReflect_I2_1"
        else:
            raise exceptions.FileTypeError("File must be of type .hdf or .h5")

        # Discovered negative surface reflectance values in MOD09 & MYD09
        # that threw off NDVI calculations
        # clip values to (0,10000)

        # get numpy array from red band dataset
        red_band, red_nodata = get_sds(dataset, red_name)
        # dont clip nodata values
        red_band[red_band != red_nodata] = np.clip(
            red_band[red_band != red_nodata], 0, 10000
        )

        # get numpy array from nir band dataset
        nir_band, nir_nodata = get_sds(dataset, nir_name)
        nir_band[nir_band != nir_nodata] = np.clip(
            nir_band[nir_band != nir_nodata], 0, 10000
        )

        ndvi_array = calc_ndvi(red_band, nir_band)

        return (ndvi_array, red_nodata)

    else:
        if ext == "hdf":
            red_name = "sur_refl_b01"
            nir_name = "sur_refl_b02"
        elif ext == "h5":
            red_name = "SurfReflect_I1"
            nir_name = "SurfReflect_I2"
        else:
            raise exceptions.FileTypeError("File must be of type .hdf or .h5")

        # Discovered negative surface reflectance values in MOD09 & MYD09
        # that threw off NDVI calculations
        # clip values to (0,10000)

        # get numpy array from red band dataset
        red_band, red_nodata = get_sds(dataset, red_name)
        # dont clip nodata values
        red_band[red_band != red_nodata] = np.clip(
            red_band[red_band != red_nodata], 0, 10000
        )

        # get numpy array from nir band dataset
        nir_band, nir_nodata = get_sds(dataset, nir_name)
        nir_band[nir_band != nir_nodata] = np.clip(
            nir_band[nir_band != nir_nodata], 0, 10000
        )

        ndvi_array = calc_ndvi(red_band, nir_band)

        return (ndvi_array, red_nodata)


def get_ndwi_array(dataset):
    file_path = dataset.name
    file_name = os.path.basename(file_path)
    suffix = file_name.split(".")[0][3:]
    ext = file_name.split(".")[-1]

    if suffix == "09A1":
        nir_name = "sur_refl_b02"
        swir_name = "sur_refl_b06"

        # Discovered negative surface reflectance values in MOD09 & MYD09
        # that threw off NDVI calculations
        # clip values to (0,10000)

        nir_band, nir_nodata = get_sds(dataset, nir_name)
        nir_band[nir_band != nir_nodata] = np.clip(
            nir_band[nir_band != nir_nodata], 0, 10000
        )

        swir_band, swir_nodata = get_sds(dataset, swir_name)
        swir_band[swir_band != swir_nodata] = np.clip(
            swir_band[swir_band != swir_nodata], 0, 10000
        )

        ndwi_array = calc_ndwi(nir_band, swir_band)
    else:
        raise exceptions.UnsupportedError(
            "Only MOD09A1 imagery is supported for NDWI generation"
        )

    return (ndwi_array, nir_nodata)


def pull_from_lp(product, date_obj, out_dir, **kwargs):
    # download tiles and return list of file paths

    collection = get_collection(product)
    nrt = is_nrt(product)

    lp_date = date_obj.strftime("%Y.%m.%d")
    out_list = []

    if nrt:
        reqs = []
        doy = date_obj.strftime("%j")
        csv_url = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/{collection[1:]}/{product}/{date_obj.year}/{doy}?fields=all&format=csv"
        r = requests.get(csv_url)
        file_csv = StringIO(r.text)
        reader = csv.DictReader(file_csv)

        for row in reader:
            url = row["downloadsLink"]
            ext = url.split(".")[-1]
            if ext == "hdf":
                request = {
                    "path": os.path.join(out_dir, os.path.basename(url)),
                    "command": [
                        "wget",
                        "-q",
                        "-e",
                        "robots=off",
                        "-m",
                        "-np",
                        "-R",
                        ".html,.tmp",
                        "-nH",
                        "-nd",
                        url,
                        "--header",
                        f"Authorization: Bearer {CREDENTIALS['NRT_TOKEN']}",
                        "-P",
                        out_dir,
                    ],
                }
                reqs.append(request)

        total_files = len(reqs)
        if total_files < 1:
            raise exceptions.UnavailableError(f"Download failed. No files available.")

        for request in tqdm(reqs, desc="Downloading NRT .hdf files."):
            r = subprocess.run(request["command"])
            if r.returncode == 0:
                out_list.append(request["path"])

    else:
        # Scrape LP DAAC Data Pool
        # https: // e4ftl01.cr.usgs.gov/MOLT/MOD13Q1.061/2022.08.29/
        directory = get_lp_directory(product)
        dir_url = f"{LP_DAAC_URL}{directory}/{product}.{collection}/{lp_date}/"
        dir_request = requests.get(dir_url)
        soup = BeautifulSoup(dir_request.content, "html.parser")
        if directory == "VIIRS":
            suffix = "h5"
        else:
            suffix = "hdf"
        expr = re.compile(f"^{product}.*{suffix}$")
        links = soup.find_all("a", href=expr)
        paths = [dir_url + link.text for link in links]
        total_files = len(paths)
        if total_files < 1:
            raise exceptions.UnavailableError(f"Download failed. No files available.")
        headers = {"Athorization": f'Bearer {CREDENTIALS["LP_TOKEN"]}'}

        session = FuturesSession()
        reqs = []
        for path in paths:
            r = session.get(path, headers=headers)
            reqs.append((3, path, r))

        # for future in tqdm(as_completed(futures), total=total_files, desc='Downloading hdf files from LPDAAC.'):
        pbar = tqdm(total=total_files, desc=f"Downloading {product} .hdf files.")
        while reqs:
            tries, url, req = reqs.pop(0)

            try:
                resp = req.result()
                file_name = resp.url.split("/")[-1]
                resp_headers = resp.headers
                if resp.ok:
                    output = os.path.join(out_dir, file_name)
                    with open(output, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            f.write(chunk)
                    # checksum
                    # size of downloaded file (bytes)
                    observed_size = int(os.stat(output).st_size)
                    # size anticipated from header (bytes)
                    expected_size = int(resp_headers["Content-Length"])

                    # if checksum is failed, log and return empty
                    if int(observed_size) != int(expected_size):
                        w = f"\nExpected file size:\t{expected_size} bytes\nObserved file size:\t{observed_size} bytes"

                    out_list.append(output)
                    pbar.update(1)
                else:
                    print(resp.status_code)
            except:
                log.info(
                    f"HDF download failed for {url}, will retry. {tries} tries remaining."
                )
                if tries > 0:
                    reqs.append((tries - 1, url, req))
                else:
                    log.info(f"{tries}, {url}")
                    log.info(f"Download failed for URL: {url}")
                    break

        pbar.close()
        if len(out_list) != total_files:
            for file in out_list:
                os.remove(file)
            raise exceptions.UnavailableError(f"Download failed.")
    return out_list


def wget_from_laads(product, date_obj, out_dir, **kwargs):
    # download tiles and return list of file paths

    collection = get_collection(product)
    nrt = is_nrt(product)

    lp_date = date_obj.strftime("%Y.%m.%d")
    out_list = []

    if nrt:
        reqs = []
        doy = date_obj.strftime("%j")
        dir_url = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/archives/allData/{collection[1:]}/{product}/{date_obj.year}/{doy}"
        csv_url = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/{collection[1:]}/{product}/{date_obj.year}/{doy}?fields=all&format=csv"
        r = requests.get(csv_url)
        file_csv = StringIO(r.text)
        reader = csv.DictReader(file_csv)
        total_files = 0
        for row in reader:
            url = row["downloadsLink"]
            ext = url.split(".")[-1]
            if ext == "hdf":
                total_files += 1

        wget_command = [
            "wget",
            "-e",
            "robots=off",
            "-m",
            "-np",
            "-R",
            ".html,.tmp,.met",
            "-nH",
            "-nd",
            dir_url,
            "--header",
            f"Authorization: Bearer {CREDENTIALS['NRT_TOKEN']}",
            "-P",
            out_dir,
        ]

        if total_files < 1:
            raise exceptions.UnavailableError(f"Download failed. No files available.")

        files = []
        tries = 5
        while len(files) != total_files:
            subprocess.call(wget_command)
            files = glob.glob(
                f"{out_dir}/{product}*{str(date_obj.year)}{str(date_obj.timetuple().tm_yday).zfill(3)}*.hdf"
            )
            print(len(files))
            tries -= 1
            if tries <= 0:
                print("breaking")
                files = []
                break
        out_list = files

        for request in tqdm(reqs, desc="Downloading NRT .hdf files."):
            r = subprocess.run(request["command"])
            if r.returncode == 0:
                out_list.append(request["path"])

    else:
        if product == "VNP09H1":
            collection = "5000"
            ext = "h5"
        else:
            collection = "61"
            ext = "hdf"
        # WGET LAADS DAAC Data Pool
        # https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5000/VNP09H1/2023/097
        dir_url = f"{LAADS_DAAC_URL}{collection}/{product}/{date_obj.year}/{str(date_obj.timetuple().tm_yday).zfill(3)}/"
        json_url = dir_url + ".json"
        r = requests.get(json_url).json()
        total_files = r.get("file_count")
        print(total_files)
        files = []
        wget_command = [
            "wget",
            "-e",
            "robots=off",
            "-m",
            "-np",
            "-R",
            ".html,.tmp",
            "-nH",
            "-nd",
            f"--directory-prefix={out_dir}",
            f"{dir_url}",
            "--header",
            f"Authorization: Bearer {CREDENTIALS['LAADS_TOKEN']}",
        ]
        tries = 5
        while len(files) != total_files:
            subprocess.call(wget_command)
            files = glob.glob(
                f"{out_dir}/{product}*{str(date_obj.year)}{str(date_obj.timetuple().tm_yday).zfill(3)}*.{ext}"
            )
            print(len(files))
            tries -= 1
            if tries <= 0:
                print("breaking")
                files = []
                break
        out_list = files

    return out_list


def pull_from_cmr(product, date_obj, out_dir, **kwargs):
    # download tiles and return list of file paths

    collection = get_collection(product)
    nrt = is_nrt(product)

    out_list = []

    api = GranuleQuery()

    if nrt:
        reqs = []
        doy = date_obj.strftime("%j")
        csv_url = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/{collection[1:]}/{product}/{date_obj.year}/{doy}?fields=all&format=csv"
        r = requests.get(csv_url)
        file_csv = StringIO(r.text)
        reader = csv.DictReader(file_csv)

        for row in reader:
            url = row["downloadsLink"]
            ext = url.split(".")[-1]
            if ext == "hdf":
                request = {
                    "path": os.path.join(out_dir, os.path.basename(url)),
                    "command": [
                        "wget",
                        "-q",
                        "-e",
                        "robots=off",
                        "-m",
                        "-np",
                        "-R",
                        ".html,.tmp",
                        "-nH",
                        "-nd",
                        url,
                        "--header",
                        f"Authorization: Bearer {CREDENTIALS['NRT_TOKEN']}",
                        "-P",
                        out_dir,
                    ],
                }
                reqs.append(request)

        total_files = len(reqs)
        if total_files < 1:
            raise exceptions.UnavailableError(f"Download failed. No files available.")

        for request in tqdm(reqs, desc="Downloading NRT .hdf files."):
            r = subprocess.run(request["command"])
            if r.returncode == 0:
                out_list.append(request["path"])

    else:
        granules = (
            api.short_name(product)
            .version("061")
            .downloadable()
            .temporal(date_obj, date_obj)
            .get()
        )

        total_files = len(granules)

        headers = {"Athorization": f'Bearer {CREDENTIALS["LP_TOKEN"]}'}

        session = FuturesSession()
        reqs = []
        for granule in granules:
            path = granule.get("links")[0].get("href")
            r = session.get(path, headers=headers)
            reqs.append((3, path, r))

        # for future in tqdm(as_completed(futures), total=total_files, desc='Downloading hdf files from LPDAAC.'):
        pbar = tqdm(total=total_files, desc=f"Downloading {product} .hdf files.")
        while reqs:
            tries, url, req = reqs.pop(0)

            try:
                resp = req.result()
                file_name = resp.url.split("/")[-1]
                resp_headers = resp.headers
                if resp.ok:
                    output = os.path.join(out_dir, file_name)
                    with open(output, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            f.write(chunk)
                    # checksum
                    # size of downloaded file (bytes)
                    observed_size = int(os.stat(output).st_size)
                    # size anticipated from header (bytes)
                    expected_size = int(resp_headers["Content-Length"])

                    # if checksum is failed, log and return empty
                    if int(observed_size) != int(expected_size):
                        w = f"\nExpected file size:\t{expected_size} bytes\nObserved file size:\t{observed_size} bytes"

                    out_list.append(output)
                    pbar.update(1)
                else:
                    print(resp.status_code)
            except:
                log.info(
                    f"HDF download failed for {url}, will retry. {tries} tries remaining."
                )
                if tries > 0:
                    reqs.append((tries - 1, url, req))
                else:
                    log.info(f"{tries}, {url}")
                    log.info(f"Download failed for URL: {url}")
                    break

        pbar.close()
        if len(out_list) != total_files:
            for file in out_list:
                os.remove(file)
            raise exceptions.UnavailableError(f"Download failed.")
    return out_list


def get_available_dates(product: str, date_obj: str) -> list:
    """
    This function returns all available imagery dates for the
    given product x date-range combination. If passed a single date,
    returns that date if it is available or an empty list if not.

    ...

    Parameters
    ---------

    product:str
            String name of desired imagery product
    date:str
            Range in which to search for valid imagery.
            Can be one of: "%Y", "%Y-%m", "%Y-%m-%d". In the former two
            cases, loops over all dates within year or month, and returns
            those dates for which there is imagery available. If a full
            Y-m-d is passed, returns a list containing that date if there
            is imagery available, or an empty list if not.
    """

    def get_days_of_year(product, year) -> list:
        """Given product and year, returns valid days of year"""

        collection = get_collection(product)
        nrt = is_nrt(product)

        try:
            if nrt:
                headers = {"Athorization": f"Bearer {CREDENTIALS['NRT_TOKEN']}"}
                out_list = []
                # get and parse CSV
                csv_url = f"https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/details/allData/{collection[1:]}/{product}/{year}/?fields=all&format=csv"
                r = requests.get(csv_url, headers=headers)
                nrt_csv = StringIO(r.text)
                dir_files = [f for f in csv.DictReader(nrt_csv)]
                # extract valid days of year from CSV
                for d in dir_files:
                    doy = d["name"]
                    out_list.append(doy)

            else:
                # Scrape LP DAAC Data Pool
                # https: // e4ftl01.cr.usgs.gov/MOLT/MOD13Q1.061/2022.08.29/
                directory = get_lp_directory(product)
                dir_url = f"{LP_DAAC_URL}{directory}/{product}.{collection}/"
                dir_request = requests.get(dir_url)
                soup = BeautifulSoup(dir_request.content, "html.parser")
                expr = re.compile(f"^{year}")
                days = soup.find_all("a", href=expr)
                out_list = [
                    datetime.strptime(d.text.strip("/"), "%Y.%m.%d").strftime("%j")
                    for d in days
                ]

        except exceptions.UnavailableError:
            return []

        # return list
        return out_list

    def check_day_of_year(product, year, doy) -> bool:
        """Returns whether there is any data for a given product on a given date"""

        doy_list = get_days_of_year(product, year)

        if doy in doy_list:
            return True
        else:
            return False

    # confirm that product is valid
    if product not in NASA_PRODUCTS:
        raise exceptions.UnsupportedError(
            f"Product '{product}' is not currently supported."
        )

    out_list = []
    doy_list = []
    try:  # is it "%Y-%m-%d"?
        year = date_obj.strftime("%Y")
        doy = date_obj.strftime("%j")
        if check_day_of_year(product, year, doy):
            doy_list = [doy]
        else:
            doy_list = []
    except ValueError:
        log.error(r"Date must be of %Y-%m-%d")
        return []
    for doy in doy_list:
        out_list.append(
            datetime.strptime(f"{year}-{doy}", "%Y-%j").strftime("%Y-%m-%d")
        )
    return out_list


def create_ndvi_geotiff(file, out_dir):
    dataset = rasterio.open(file)

    file_path = dataset.name
    file_name = os.path.basename(file_path)
    ext = file_name.split(".")[-1]

    # calculate ndvi and export to geotiff
    ndvi_array, ndvi_nodata = get_ndvi_array(dataset)

    # apply mask
    ndvi_array = apply_mask(ndvi_array, dataset, ndvi_nodata)

    out_name = file_name.replace(ext, "ndvi.tif")
    output = os.path.join(out_dir, out_name)

    # coerce dtype to int16
    dtype = "int16"

    ndvi_array = ndvi_array.astype(dtype)

    profile = rasterio.open(dataset.subdatasets[0]).profile.copy()
    profile.update({"driver": "GTiff", "dtype": dtype, "nodata": ndvi_nodata})

    if "VNP" in file_name:
        f = h5py.File(file_path, "r")
        geo_info = get_h5_geo_info(f)
        if profile["height"] == 1200:  # VIIRS VNP09A1, VNP09GA - 1km
            yRes = -926.6254330555555
            xRes = 926.6254330555555
        elif profile["height"] == 2400:  # VIIRS VNP09H1, VNP09GA - 500m
            yRes = -463.31271652777775
            xRes = 463.31271652777775
        new_transform = rasterio.Affine(
            xRes, geo_info[1], geo_info[0], geo_info[3], yRes, geo_info[2]
        )
        profile.update({"transform": new_transform})

    # assign CRS if None
    if profile["crs"] == None:
        profile.update({"crs": SINUS_WKT})

    # create cog
    with MemoryFile() as memfile:
        with memfile.open(**profile) as mem:
            mem.write(ndvi_array)
            dst_profile = cog_profiles.get("deflate")
            cog_translate(
                mem,
                output,
                dst_profile,
                in_memory=True,
                quiet=True,
            )

    return output


def create_ndwi_geotiff(file, out_dir):
    dataset = rasterio.open(file)

    file_path = dataset.name
    file_name = os.path.basename(file_path)
    ext = file_name.split(".")[-1]

    # calculate ndvi and export to geotiff
    ndwi_array, ndwi_nodata = get_ndwi_array(dataset)

    # apply mask
    ndwi_array = apply_mask(ndwi_array, dataset, ndwi_nodata)

    out_name = file_name.replace(ext, "ndwi.tif")
    output = os.path.join(out_dir, out_name)

    # coerce dtype to int16
    dtype = "int16"

    ndwi_array = ndwi_array.astype(dtype)

    profile = rasterio.open(dataset.subdatasets[0]).profile.copy()
    profile.update({"driver": "GTiff", "dtype": dtype, "nodata": ndwi_nodata})

    if "VNP" in file_name:
        f = h5py.File(file_path, "r")
        geo_info = get_h5_geo_info(f)
        if profile["height"] == 1200:  # VIIRS VNP09A1, VNP09GA - 1km
            yRes = -926.6254330555555
            xRes = 926.6254330555555
        elif profile["height"] == 2400:  # VIIRS VNP09H1, VNP09GA - 500m
            yRes = -463.31271652777775
            xRes = 463.31271652777775
        new_transform = rasterio.Affine(
            xRes, geo_info[1], geo_info[0], geo_info[3], yRes, geo_info[2]
        )
        profile.update({"transform": new_transform})

    # assign CRS if None
    if profile["crs"] == None:
        profile.update({"crs": SINUS_WKT})

    # create cog
    with MemoryFile() as memfile:
        with memfile.open(**profile) as mem:
            mem.write(ndwi_array)
            dst_profile = cog_profiles.get("deflate")
            cog_translate(
                mem,
                output,
                dst_profile,
                in_memory=True,
                quiet=True,
            )

    return output


def create_sds_geotiff(file, product, sds_name, out_dir, mask=True):
    dataset = rasterio.open(file)

    file_path = dataset.name
    file_name = os.path.basename(file_path)

    # calculate ndvi and export to geotiff
    sds_array, sds_nodata = get_sds(dataset, sds_name)

    # apply mask
    if mask:
        sds_array = apply_mask(sds_array, dataset, sds_nodata)

    # if band is surface reflectance then clip values (exclude nodata)
    if sds_name.lower().find("refl") > -1 and product != "VNP09A1":
        sds_array[sds_array != sds_nodata] = np.clip(
            sds_array[sds_array != sds_nodata], 0, 10000
        )

    out_name = file_name.replace(".hdf", f".{sds_name}.tif")
    output = os.path.join(out_dir, out_name)

    dtype = get_dtype_from_sds_name(sds_name)

    sds_array = sds_array.astype(dtype)

    profile = rasterio.open(dataset.subdatasets[0]).profile.copy()
    profile.update({"driver": "GTiff", "dtype": dtype, "nodata": sds_nodata})

    if "VNP" in product:
        f = h5py.File(file_path, "r")
        geo_info = get_h5_geo_info(f)
        out_name = file_name.replace(".h5", f".{sds_name}.tif")
        output = os.path.join(out_dir, out_name)
        if profile["height"] == 1200:  # VIIRS VNP09A1, VNP09GA - 1km
            yRes = -926.6254330555555
            xRes = 926.6254330555555
        elif profile["height"] == 2400:  # VIIRS VNP09H1, VNP09GA - 500m
            yRes = -463.31271652777775
            xRes = 463.31271652777775
        new_transform = rasterio.Affine(
            xRes, geo_info[1], geo_info[0], geo_info[3], yRes, geo_info[2]
        )
        profile.update({"transform": new_transform})
        tags = dataset.tags()
        for tag in tags:
            if sds_name + "__FillValue" in tag:
                sds_nodata = tags[tag]
        profile.update({"nodata": int(sds_nodata)})

    # assign CRS if None
    if profile["crs"] == None:
        profile.update({"crs": SINUS_WKT})

    #  create cog
    with MemoryFile() as memfile:
        with memfile.open(**profile) as mem:
            mem.write(sds_array)
            dst_profile = cog_profiles.get("deflate")
            cog_translate(
                mem,
                output,
                dst_profile,
                in_memory=True,
                quiet=True,
            )

    return output
