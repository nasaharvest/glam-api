import os
import re
import time
import gzip
import shutil
import logging
import functools
from datetime import datetime, timedelta
import requests
import subprocess
from multiprocessing import Pool

from tqdm import tqdm

import numpy as np

import rasterio
from rasterio.io import MemoryFile
from rasterio.crs import CRS
from rasterio.merge import merge
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.cogeo import cog_validate
from rio_cogeo.profiles import cog_profiles

from django_q.tasks import async_task

from django.conf import settings
from config.local_settings.credentials import CREDENTIALS
from ..utils import exceptions
from ..utils.daac import (get_available_dates, NASA_PRODUCTS, pull_from_lp,
                          create_ndvi_geotiff, create_ndwi_geotiff, get_sds_path, create_sds_geotiff)
from ..utils.spectral import SUPPORTED_INDICIES

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=settings.LOG_LEVELS[settings.LOG_LEVEL])
log = logging.getLogger(__name__)


class GlamDownloader(object):

    def __init__(self, product):
        if product in ["merra-2-min", "merra-2-max", "merra-2-mean"]:
            self.product = "merra-2"
        elif product.upper() in NASA_PRODUCTS:
            self.product = product.upper()
        else:
            self.product = product

    def _create_mosaic_cog_from_vrt(self, vrt_path):

        out_path = vrt_path.replace('vrt', 'tif')

        translate_command = ["gdal_translate", "-of", "COG", "-co",
                             "COMPRESS=DEFLATE", "-co", "BIGTIFF=IF_SAFER", vrt_path, out_path]
        subprocess.call(translate_command)
        # profile = cog_profiles.get("deflate")
        # log.info("Creating global mosaic & cloud optimizing.")
        # cog_translate(
        #     vrt_path,
        #     out_path,
        #     profile,
        #     allow_intermediate_compression=True,
        #     quiet=False
        # )

        os.remove(vrt_path)

        return out_path

    def _create_mosaic_cog_from_tifs(self, date, files, out_dir):

        year = date.strftime("%Y")
        doy = date.strftime("%j")

        # get index or sds name
        sample_file = files[0]
        variable = sample_file.split('.')[-2]

        file_name = f'{self.product}.{variable}.{year}.{doy}.tif'
        out_path = os.path.join(out_dir, file_name)
        vrt_path = out_path.replace('tif', 'vrt')

        log.info("Creating mosaic VRT.")
        # use gdal to build vrt of tile tiffs
        vrt_command = ["gdalbuildvrt", vrt_path]
        vrt_command += files
        subprocess.call(vrt_command)

        profile = cog_profiles.get("deflate")
        log.info("Creating global mosaic & cloud optimizing.")
        cog_translate(
            vrt_path,
            out_path,
            profile,
            allow_intermediate_compression=True,
            quiet=False
        )

        os.remove(vrt_path)

        return out_path

    def _cloud_optimize(self, dataset, out_file, nodata=False):

        meta = dataset.meta.copy()

        if nodata:
            meta.update({"nodata": nodata})

        out_meta = meta
        cog_options = cog_profiles.get("deflate")
        out_meta.update(cog_options)
        cog_translate(
            dataset,
            out_file,
            out_meta,
            allow_intermediate_compression=True,
            quiet=False
        )

        return True

    def _download_chirps_precip(self, date, out_dir, **kwargs):
        """
        Given date of chirps product, downloads file to directory
        Returns file path or None if download failed
        Downloaded files are COGs
        """
        try:
            # define file locations
            # output location for final file
            file_unzipped = os.path.join(out_dir, f"chirps-precip.{date}.tif")
            file_zipped = file_unzipped+".gz"  # initial location for zipped version of file

            # get url to be downloaded
            c_date = datetime.strptime(date, "%Y-%m-%d")
            c_year = c_date.strftime("%Y")
            c_month = c_date.strftime("%m").zfill(2)
            # convert day-of-month into 1, 2, or 3 depending on which third of the month it
            # falls in (1-10, 11-20, 21-end). Chirps urls use these integers instead of day
            c_day = str(int(np.ceil(int(c_date.strftime("%d"))/10)))
            url = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_dekad/tifs/chirps-v2.0.{c_year}.{c_month}.{c_day}.tif.gz"

            # download the gnuzip file
            with requests.Session() as session:
                # not sure if both these steps are strictly necessary. Try removing
                # one and see if everything breaks!
                r1 = session.request('get', url)
                r = session.get(r1.url)
            # nonexistent imagery gives a 404 response
            if r.status_code != 200:
                log.warning(f"Url {url} not found")
                return ()
            # write zipped .gz file to disk
            with open(file_zipped, "wb") as fd:  # write data in chunks
                for chunk in r.iter_content(chunk_size=1024*1024):
                    fd.write(chunk)

            # CHECKSUM
            # size of downloaded file in bytes
            observed_size = int(os.stat(file_zipped).st_size)
            # size of promised file in bytes, extracted from server-delivered headers
            expected_size = int(r.headers['Content-Length'])

            # checksum failure; return empty tuple
            if observed_size != expected_size:  # checksum failure
                w = f"WARNING:\nExpected file size:\t{expected_size} bytes\nObserved file size:\t{observed_size} bytes"
                log.warning(w)
                return ()  # no files for you today, but we'll try again tomorrow!

            # use gzip to unzip file to final location
            # tf = file_unzipped.replace(".tif", ".UNMASKED.tif")
            with gzip.open(file_zipped) as fz:
                with open(file_unzipped, "w+b") as fu:
                    shutil.copyfileobj(fz, fu)
            os.remove(file_zipped)  # delete zipped version

            raster = rasterio.open(file_unzipped)
            optimized = self._cloud_optimize(raster, file_unzipped, -9999)

            # return file path string in tuple
            if optimized:
                return file_unzipped

        except Exception as e:  # catch unhandled error; log warning message; return failure in form of empty tuple
            log.exception(f"Unhandled error downloading chirps for {date}")
            return None

    def _download_chirps_prelim(self, date, out_dir, **kwargs):
        """
        Given date of chirps preliminary data product, downloads file to directory
        Returns tuple containing file path or empty list if download failed
        Downloaded files are COGs in sinusoidal projection
        """
        try:
            # create formatted output filename
            file_out = os.path.join(
                out_dir, f"chirps-precip.{date}.prelim.tif")

            # get url to be downloaded
            c_date = datetime.strptime(date, "%Y-%m-%d")
            c_year = c_date.strftime("%Y")
            c_month = c_date.strftime("%m").zfill(2)
            # chirps uses "1", "2", and "3" in their filenames, so we convert day of month to one of those
            # based on which third of the month it falls in (1-10, 11-20, 20-end)
            c_day = str(int(np.ceil(int(c_date.strftime("%d"))/10)))
            url = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/prelim/global_dekad/tifs/chirps-v2.0.{c_year}.{c_month}.{c_day}.tif"

            # download file at url
            with requests.Session() as session:
                # not sure why both these steps are necessary, but too afraid to try
                # removing one and seeing if it breaks things
                r1 = session.request('get', url)
                r = session.get(r1.url)
            # nonexistent files don't throw an error, they just return a
            # 404 response
            if r.status_code != 200:
                log.warning(f"Url {url} not found")
                return ()
            # write output tif file
            with open(file_out, "wb") as fd:  # write data in chunks
                for chunk in r.iter_content(chunk_size=1024*1024):
                    fd.write(chunk)

            # CHECKSUM
            # size of downloaded file in bytes
            observed_size = int(os.stat(file_out).st_size)
            # size of promised file in bytes, extracted from server-delivered headers
            expected_size = int(r.headers['Content-Length'])

            # checksum failure; return empty tuple
            if observed_size != expected_size:  # checksum failure
                w = f"WARNING:\nExpected file size:\t{expected_size} bytes\nObserved file size:\t{observed_size} bytes"
                log.warning(w)
                return ()  # no files for you today, but we'll try again tomorrow!

            raster = rasterio.open(file_out)
            optimized = self._cloud_optimize(raster, file_out, -9999)

            # return file path string
            if optimized:
                return file_out

        except Exception as e:  # catch unhandled error; log warning message; return failure in form of empty tuple
            log.exception(
                f"Unhandled error downloading chirps-prelim for {date}")
            return ()

    def _download_copernicus_swi(self, date, out_dir, **kwargs):
        """
        Given date of swi product, downloads file to directory if possible
        Returns tuple containing file path or empty list if download failed
        Downloaded files are COGs in sinusoidal projection
        """

        # where final output will be written to disk
        out = os.path.join(out_dir, f"copernicus-swi.{date}.tif")
        # convert string date to datetime object
        dateObj = datetime.strptime(date, "%Y-%m-%d")
        year = dateObj.strftime("%Y")  # extract year
        month = dateObj.strftime("%m".zfill(2))  # extract month
        day = dateObj.strftime("%d".zfill(2))  # extract day

        # generate urls
        url = f"https://land.copernicus.vgt.vito.be/PDF/datapool/Vegetation/Soil_Water_Index/Daily_SWI_12.5km_Global_V3/{year}/{month}/{day}/SWI_{year}{month}{day}1200_GLOBE_ASCAT_V3.2.1/c_gls_SWI_{year}{month}{day}1200_GLOBE_ASCAT_V3.2.1.nc"

        # Temporary NetCDF file; later to be converted to tiff
        file_nc = out.replace("tif", "nc")

        # use requests module to download MERRA-2 file (.nc4)
        with requests.Session() as session:
            session.auth = (
                CREDENTIALS['COPERNICUS']['username'], CREDENTIALS['COPERNICUS']['password'])
            r = session.get(url)  # copernicus demands credentials twice!
            headers = r.headers

        # write output .nc file
        with open(file_nc, "wb") as fd:  # write data in chunks
            for chunk in r.iter_content(chunk_size=1024*1024):
                fd.write(chunk)

        # checksum
        # size of downloaded file (bytes)
        observed_size = int(os.stat(file_nc).st_size)
        # size anticipated from header (bytes)
        expected_size = int(headers['Content-Length'])

        # if checksum is failed, log and return empty
        if int(observed_size) != int(expected_size):
            w = f"\nExpected file size:\t{expected_size} bytes\nObserved file size:\t{observed_size} bytes"
            log.warning(w)
            os.remove(file_nc)
            return ()

        rio_path = f'netcdf:{os.path.abspath(file_nc)}:SWI_010'
        raster = rasterio.open(rio_path)

        optimized = self._cloud_optimize(raster, out, nodata=False)

        if optimized:
            os.remove(file_nc)
            return out

    def _download_merra_2(self, date, out_dir, **kwargs):
        merra2_urls = []
        for i in range(5):  # we are collecting the requested date along with 4 previous days
            m_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=i)
            m_year = m_date.strftime("%Y")
            m_month = m_date.strftime("%m").zfill(2)
            m_day = m_date.strftime("%d").zfill(2)
            page_url = f"https://goldsmr4.gesdisc.eosdis.nasa.gov/data/MERRA2/M2SDNXSLV.5.12.4/{m_year}/{m_month}/"
            try:
                page_object = requests.get(page_url)
                page_text = page_object.text
                # regular expression that matches file name of desired date file
                ex = re.compile(f'MERRA2\S*{m_year}{m_month}{m_day}.nc4')

                # matches desired file name from web page
                m_filename = re.search(ex, page_text).group()

                m_url = page_url + m_filename
                merra2_urls.append(m_url)

            except AttributeError:
                log.warning(
                    f"Failed to find Merra-2 URL for {m_date.strftime('%Y-%m-%d')}. We seem to have caught the merra-2 team in the middle of uploading their data... check {page_url} to be sure.")
                return False

        # dictionary of empty lists of metric-specific file paths, waiting to be filled
        merra_datasets = {}
        merra_datasets['min'] = []
        merra_datasets['max'] = []
        merra_datasets['mean'] = []

        for url in merra2_urls:
            url_date = url.split(".")[-2]
            # use requests module to download MERRA-2 file (.nc4)
            # Athenticated using netrc method
            r = requests.get(url)
            out_netcdf = os.path.join(
                out_dir, f"merra-2.{url_date}.NETCDF.TEMP.nc")  # NetCDF file path

            # write output .nc4 file
            with open(out_netcdf, "wb") as fd:  # write data in chunks
                for chunk in r.iter_content(chunk_size=1024*1024):
                    fd.write(chunk)

            # CHECKSUM
            # size of downloaded file in bytes
            observed_size = int(os.stat(out_netcdf).st_size)
            # size of promised file in bytes, extracted from server-delivered headers
            expected_size = int(r.headers['Content-Length'])

            # checksum failure; return empty tuple
            if observed_size != expected_size:  # checksum failure
                w = f"WARNING:\nExpected file size:\t{expected_size} bytes\nObserved file size:\t{observed_size} bytes"
                log.warning(w)
                return ()  # no files for you today, but we'll try again tomorrow!

            # merra-2-max
            max_path = f'netcdf:{os.path.abspath(out_netcdf)}:T2MMAX'
            max_dataset = rasterio.open(max_path)
            merra_datasets['max'].append(max_dataset)

            # memerra-2-mean
            mean_path = f'netcdf:{os.path.abspath(out_netcdf)}:T2MMEAN'
            mean_dataset = rasterio.open(mean_path)
            merra_datasets['mean'].append(mean_dataset)

            # memerra-2-min
            min_path = f'netcdf:{os.path.abspath(out_netcdf)}:T2MMIN'
            min_dataset = rasterio.open(min_path)
            merra_datasets['min'].append(min_dataset)

            merra_out = []

            for metric in merra_datasets.keys():
                out = os.path.join(
                    out_dir, f"merra-2.{date}.{metric}-temp.tif")

                dataset_list = merra_datasets[metric]
                mosaic, out_transform = merge(dataset_list)
                out_meta = dataset_list[0].meta.copy()

                crs = CRS.from_epsg(4326)
                out_meta.update({'driver': 'GTiff'})
                out_meta.update({'crs': crs})

                with rasterio.open(out, "w", **out_meta) as dest:
                    dest.write(mosaic)

                raster = rasterio.open(out)

                optimized = self._cloud_optimize(raster, out, nodata=False)
                if optimized:
                    merra_out.append(out)

            os.remove(out_netcdf)

            return merra_out

    def _download_nasa_product(self, date, out_dir, **kwargs):
        start = time.time()
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.strftime("%Y")
        doy = date_obj.strftime("%j")

        vi_functions = {
            "NDVI": create_ndvi_geotiff,
            # "GCVI":octvi.extract.gcviToRaster,
            "NDWI": create_ndwi_geotiff
        }

        # get provided Vegetation Index, default to NDVI
        vi = kwargs.get("vi", "NDVI")
        if vi not in SUPPORTED_INDICIES:
            raise exceptions.UnsupportedError(
                f"Vegetation index '{vi}' not recognized or not supported.")

        # get provided Science Dataset arguments
        sds = kwargs.get("sds", None)

        # download hdf files
        hdf_files = pull_from_lp(self.product, date_obj, out_dir, **kwargs)

        output = []

        if sds:
            if type(sds) == list:
                for ds in sds:
                    if "VNP" in self.product:
                        ds_files = []
                        for file in tqdm(hdf_files, desc=f'Creating intermediate {ds} cogs.'):
                            ds_files.append(create_sds_geotiff(
                                file, self.product, ds, out_dir, mask=False))

                        ds_mosaic = self._create_mosaic_cog_from_tifs(
                            date_obj, ds_files, out_dir)
                        output.append(ds_mosaic)
                        for file in ds_files:
                            os.remove(file)
                    else:
                        sds_paths = []
                        for file in tqdm(hdf_files, desc=f'Reading {ds} hdf files.'):
                            dataset = rasterio.open(file)
                            sds_path = get_sds_path(dataset, ds)
                            sds_paths.append(sds_path)

                        vrt_name = f'{self.product}.{ds}.{year}.{doy}.vrt'
                        vrt_path = os.path.join(out_dir, vrt_name)
                        log.info("Creating {ds} VRT.")
                        # use gdal to build vrt rather than creating intermediate tifs
                        vrt_command = ["gdalbuildvrt", vrt_path]
                        vrt_command += sds_paths
                        subprocess.call(vrt_command)

                        ds_mosaic = self._create_mosaic_cog_from_vrt(vrt_path)
                        output.append(ds_mosaic)

        if vi == False:
            for file in hdf_files:
                os.remove(file)
        else:
            vi_files = []
            for file in tqdm(hdf_files, desc=f'Creating {vi} files.'):
                vi_files.append(vi_functions[vi](file, out_dir))

            # Remove hdf files after tiffs are created.
            for file in hdf_files:
                os.remove(file)

            vi_mosaic = self._create_mosaic_cog_from_tifs(
                date_obj, vi_files, out_dir)
            output.append(vi_mosaic)

            # Remove tiffs after mosaic creation.
            for file in vi_files:
                os.remove(file)
        end = time.time()
        duration = end-start
        log.info(f'Download time: {str(timedelta(seconds=duration))}')

        return output

    def available_for_download(self, date: str) -> bool:
        """Returns whether imagery for given product and date is available for download from source"""

        # parse arguments
        try:
            datetime.strptime(date, "%Y-%m-%d").date()
        except:
            try:
                date = datetime.strptime(
                    date, "%Y.%j").strftime("%Y-%m-%d").date()
            except:
                raise exceptions.BadInputError(
                    f"Failed to parse input '{date}' as a date. Please use format YYYY-MM-DD or YYYY.DOY")

        # merra-2 always requires special behavior
        if "merra-2" in self.product:
            for i in range(5):  # we are collecting the requested date along with 4 previous days
                m_date = datetime.strptime(
                    date, "%Y-%m-%d") - timedelta(days=i)
                m_year = m_date.strftime("%Y")
                m_month = m_date.strftime("%m").zfill(2)
                m_day = m_date.strftime("%d").zfill(2)
                page_url = f"https://goldsmr4.gesdisc.eosdis.nasa.gov/data/MERRA2/M2SDNXSLV.5.12.4/{m_year}/{m_month}/"
                try:
                    page_object = requests.get(page_url)
                    page_text = page_object.text
                    # regular expression that matches file name of desired date file
                    ex = re.compile(f'MERRA2\S*{m_year}{m_month}{m_day}.nc4')
                    # matches desired file name from web page
                    m_filename = re.search(ex, page_text).group()
                except AttributeError:
                    log.warning(
                        f"Failed to find Merra-2 URL for {m_date.strftime('%Y-%m-%d')}. We seem to have caught the merra-2 team in the middle of uploading their data... check {page_url} to be sure.")
                    return False
            return True

        elif self.product == "chirps-precip":
            # get url to be downloaded
            c_date = datetime.strptime(date, "%Y-%m-%d")
            c_year = c_date.strftime("%Y")
            c_month = c_date.strftime("%m").zfill(2)
            c_day = str(int(np.ceil(int(c_date.strftime("%d"))/10)))
            # CHIRPS data has been moved off of FTP server onto HTTPS
            # url = f"ftp://ftp.chg.ucsb.edu/pub/org/chg/products/CHIRPS-2.0/global_dekad/tifs/chirps-v2.0.{c_year}.{c_month}.{c_day}.tif.gz"
            url = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_dekad/tifs/chirps-v2.0.{c_year}.{c_month}.{c_day}.tif.gz"
            req = requests.get(url)
            return req.ok

        elif self.product == "chirps-prelim":
            # get url to be downloaded
            c_date = datetime.strptime(date, "%Y-%m-%d")
            c_year = c_date.strftime("%Y")
            c_month = c_date.strftime("%m").zfill(2)
            c_day = str(int(np.ceil(int(c_date.strftime("%d"))/10)))
            url = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/prelim/global_dekad/tifs/chirps-v2.0.{c_year}.{c_month}.{c_day}.tif"
            req = requests.get(url)
            return req.ok

        elif self.product == "copernicus-swi":
            # convert string date to datetime object
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m".zfill(2))
            day = date_obj.strftime("%d".zfill(2))
            url = f"https://land.copernicus.vgt.vito.be/PDF/datapool/Vegetation/Soil_Water_Index/Daily_SWI_12.5km_Global_V3/{year}/{month}/{day}/SWI_{year}{month}{day}1200_GLOBE_ASCAT_V3.2.1/c_gls_SWI_{year}{month}{day}1200_GLOBE_ASCAT_V3.2.1.nc"
            with requests.Session() as session:
                session.auth = (
                    CREDENTIALS["COPERNICUS"]["username"], CREDENTIALS["COPERNICUS"]["password"])
                request = session.get(url)

                if request.ok:
                    if request.headers['Content-Type'] == 'application/octet-stream':
                        return True
                else:
                    return False

        elif self.product in NASA_PRODUCTS:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            if len(get_available_dates(self.product, date_obj)) > 0:
                return True
            else:
                return False

        # input product not supported
        else:
            raise exceptions.BadInputError(
                f"Product '{self.product}' not recognized")

    def list_available_for_download(self, start_date: str, format_doy=False) -> list:
        """A function that lists availabe-to-download imagery dates

        Parameters
        ----------
        product:str
            String name of product; e.g. MOD09Q1, merra-2-min, etc.
        start_date:str
            Date from which to begin search. Should be the latest
            product date already ingested. Can be formatted as
            YYYY-MM-DD or YYYY.DOY
        format_doy:bool
            Default false. If true, returns dates as YYYY.DOY rather
            than default YYYY-MM-DD

        Returns
        -------
        List of string dates in format YYYY-MM-DD or YYYY.DOY, depending
        on format_doy argument. Each date has available imagery to download.
        """
        # Parse Arguments
        try:
            latest = datetime.strptime(start_date, "%Y-%m-%d")
        except:
            try:
                latest = datetime.strptime(start_date, "%Y.%j")
            except:
                raise exceptions.BadInputError(
                    f"Failed to parse input '{start_date}' as a date. Please use format YYYY-MM-DD or YYYY.DOY")
        today = datetime.today()
        raw_dates = []
        filtered_dates = []

        if self.product == "merra-2":
            # get all possible dates
            while latest < today:
                latest = latest + timedelta(days=1)
                log.debug(
                    f"Found missing file in valid date range: merra-2 for {latest.strftime('%Y-%m-%d')}")
                raw_dates.append(latest.strftime("%Y-%m-%d"))
        elif self.product == "chirps-precip":
            # get all possible dates
            while latest < today:
                if int(latest.strftime("%d")) > 12:
                    # push the date into the next month, but not past the 11th day of the next month
                    latest = latest+timedelta(days=15)
                    # once we're in next month, slam the day back down to 01
                    latest = datetime.strptime(
                        latest.strftime("%Y-%m")+"-01", "%Y-%m-%d")
                else:
                    # 01 becomes 11, 11 becomes 21
                    latest = latest+timedelta(days=10)
                log.debug(
                    f"Found missing file in valid date range: chirps for {latest.strftime('%Y-%m-%d')}")
                raw_dates.append(latest.strftime("%Y-%m-%d"))
        elif self.product == "chirps-prelim":
            # get all possible dates
            while latest < today:
                if int(latest.strftime("%d")) > 12:
                    # push the date into the next month, but not past the 11th day of the next month
                    latest = latest+timedelta(days=15)
                    # once we're in next month, slam the day back down to 01
                    latest = datetime.strptime(
                        latest.strftime("%Y-%m")+"-01", "%Y-%m-%d").date()
                else:
                    # 01 becomes 11, 11 becomes 21
                    latest = latest+timedelta(days=10)
                log.debug(
                    f"Found missing file in valid date range: chirps-prelim for {latest.strftime('%Y-%m-%d')}")
                raw_dates.append(latest.strftime("%Y-%m-%d"))
        elif self.product == "copernicus-swi":
            # get all possible dates
            while latest < today:
                latest = latest + timedelta(days=5)
                log.debug(
                    f"Found missing file in valid date range: swi for {latest.strftime('%Y-%m-%d')}")
                raw_dates.append(latest.strftime("%Y-%m-%d"))

        elif self.product in NASA_PRODUCTS:
            if self.product == "MOD09Q1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2000.049", "%Y.%j")
                delta = 8

            elif self.product == "MYD09Q1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2002.185", "%Y.%j")
                delta = 8

            elif self.product == "MOD13Q1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2000.049", "%Y.%j")
                delta = 16

            elif self.product == "MYD13Q1":
                start_doy = 9
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2002.185", "%Y.%j")
                delta = 16

            elif self.product == "MOD09A1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2000.049", "%Y.%j")
                delta = 8

            elif self.product == "MYD09A1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2002.185", "%Y.%j")
                delta = 8

            elif self.product == "MOD13Q4N":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2002.185", "%Y.%j")
                delta = 1

            elif self.product == "MCD12Q1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2001.001", "%Y.%j")
                delta = 366

            elif self.product == "VNP09H1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2012.017", "%Y.%j")
                delta = 8

            elif self.product == "VNP09A1":
                start_doy = 1
                # get all possible dates
                if latest is None:
                    latest = datetime.strptime("2012.017", "%Y.%j")
                delta = 8

            else:
                raise exceptions.BadInputError(
                    f"Product '{self.product}' not recognized")

            d = datetime(latest.year, 1, start_doy)
            raw_dates.append(d.strftime("%Y-%m-%d"))
            while d < today:
                old_year = d.year
                d = d + timedelta(days=delta)
                if d.year != old_year:
                    d = d.replace(day=start_doy)
                if d >= latest:
                    log.debug(
                        f"Found missing file in valid date range: {self.product} for {latest.strftime('%Y-%m-%d')}")
                    raw_dates.append(d.strftime("%Y-%m-%d"))

        # filter products
        for rd in tqdm(raw_dates):
            if self.available_for_download(rd):
                filtered_dates.append(rd)

        # convert to DOY format if requested
        if format_doy:
            temp_dates = filtered_dates
            filtered_dates = []
            for td in temp_dates:
                filtered_dates.append(datetime.strptime(
                    td, "%Y-%m-%d").strftime("%Y.%j"))

        return filtered_dates

    def download_single_date(self, date: str, out_dir: str, **kwargs) -> str:

        # format date to YYYY-MM-DD
        try:
            date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            try:
                date = datetime.strptime(date, "%Y.%j").strftime("%Y-%m-%d")
            except:
                raise exceptions.BadInputError(
                    "Date must be of format YYYY-MM-DD or YYYY.DOY")

        # this dictionary maps each product name to its corresponding download
        # function. To download product "{prod}" with arguments "args", one
        # can call actions[{prod}](*args). This is what we do in the return
        # statement below
        actions = {
            "chirps-precip": self._download_chirps_precip,
            "chirps-prelim": self._download_chirps_prelim,
            "copernicus-swi": self._download_copernicus_swi,
            "merra-2": self._download_merra_2,
        }
        for prod in NASA_PRODUCTS:
            actions.update({prod: self._download_nasa_product})

        return actions[self.product](date, out_dir, **kwargs)

    def download_available_from_date(self, date: str, out_dir: str, **kwargs):
        log.info('Retreiving list of datasets available for download.')
        available = self.list_available_for_download(date)

        for d in tqdm(available, desc="Downloading available datasets."):
            self.download_single_date(d, out_dir, **kwargs)

        log.info("Download complete.")
        return True

# def download_new_by_product(product_name):
#     try:
#         product = Product.objects.get(name=product_name)
#         datasets = ProductDataset.objects.filter(product=product)
#         latest = datasets.order_by('-date')[0].date.isoformat()

#         available = list_available_for_download(product.name, latest)

#         product_directory = os.path.join(
#             settings.PRODUCT_DATASET_LOCAL_PATH, product.name)

#         for date in available:
#             try:
#                 image = pullFromSource(product.name, date, product_directory)
#                 logging.info(f'successfully downloaded {image} ')
#             except octvi.exceptions.UnavailableError as e:
#                 logging.info(e)
#                 logging.info(f'skipping {date}')
#                 pass

#     except Product.DoesNotExist:
#         logging.info(
#             f'{product_name} is not a valid product within the system.')


# def download_missing_by_product(product_name):
#     try:
#         product = Product.objects.get(name=product_name)
#         datasets = ProductDataset.objects.filter(product=product)
#         first = datasets.order_by('date')[0].date.isoformat()

#         available = list_available_for_download(product.name, first)

#         product_directory = os.path.join(
#             settings.PRODUCT_DATASET_LOCAL_PATH, product.name)

#         for date in tqdm(available):
#             try:
#                 product_ds = ProductDataset.objects.get(
#                     product=product, date=date)
#                 logging.info(f'{product.name}-{date} Exists')
#             except ProductDataset.DoesNotExist:
#                 logging.info(
#                     f'{product.name}-{date} Does Not Exist, Downloading...')
#                 image = pullFromSource(product.name, date, product_directory)
#                 logging.info(f'successfully downloaded {image} ')

#     except Product.DoesNotExist:
#         logging.info(
#             f'{product_name} is not a valid product within the system.')
