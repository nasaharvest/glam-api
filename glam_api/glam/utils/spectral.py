import os
import logging

import numpy as np

from django.conf import settings

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=settings.LOG_LEVELS[settings.LOG_LEVEL])
log = logging.getLogger(__name__)


SUPPORTED_INDICIES = ["NDVI", "GCVI", "NDWI", False]


def calc_ndvi(red_array, nir_array) -> np.array:
    """
    A function to robustly build an NDVI array from two
    arrays (red and NIR) of the same shape.

    Resulting array is scaled by 10000, with values stored
    as integers. Nodata value is -3000.

    ...

    Parameters
    ----------

    red_array: numpy.array
            Array of red reflectances
    nir_array: numpy.array
            Array of near-infrared reflectances

    """

    # perform NDVI generation
    ndvi = np.divide((nir_array - red_array), (nir_array + red_array))

    # rescale and replace infinities
    ndvi = ndvi * 10000
    ndvi[ndvi == np.inf] = -3000
    ndvi[ndvi == -np.inf] = -3000
    ndvi = ndvi.astype(int)

    # return array
    return ndvi


def calcGcvi(green_array, nir_array) -> np.array:
    """
    A function to robustly build a GCVI array from two
    arrays (green and NIR) of the same shape.

    Resulting array is scaled by 10000, with values stored
    as integers. Nodata value is -3000.

    ...

    Parameters
    ----------

    green_array: numpy.array
            Array of green reflectances
    nir_array: numpy.array
            Array of near-infrared reflectances

    """

    # perform NDVI generation
    gcvi = np.divide(nir_array, green_array) - 1

    # rescale and replace infinities
    gcvi = gcvi * 10000
    gcvi[gcvi == np.inf] = -3000
    gcvi[gcvi == -np.inf] = -3000
    gcvi = gcvi.astype(int)

    # return array
    return gcvi


def calc_ndwi(nir_array, swir_array) -> np.array:
    """
    A function to robustly build an NDWI array from two
    arrays (SWIR and NIR) of the same shape.

    Resulting array is scaled by 10000, with values stored
    as integers. Nodata value is -3000.

    ...

    Parameters
    ----------

    nir_array: numpy.array
            Array of near-infrared reflectances
    swir_array: numpy.array
            Array of shortwave infrared reflectances

    """

    # perform NDVI generation
    ndwi = np.divide((nir_array - swir_array), (nir_array + swir_array))

    # rescale and replace infinities
    ndwi = ndwi * 10000
    ndwi[ndwi == np.inf] = -3000
    ndwi[ndwi == -np.inf] = -3000
    ndwi = ndwi.astype(int)

    # return array
    return ndwi
