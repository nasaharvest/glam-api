"""
cmaps/get_cmap.py

Define an interface to retrieve stored color maps.
Modified from Terracotta (https://github.com/DHI-GRAS/terracotta)
"""

from typing import Dict
import os
import logging

import numpy as np

from django.core.files import File

from django.conf import settings

from ...models import Colormap

logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S',
    level=settings.LOG_LEVELS[settings.LOG_LEVEL])
log = logging.getLogger(__name__)


SUFFIX = '_rgba.npy'
EXTRA_CMAP_FOLDER = os.environ.get('TC_EXTRA_CMAP_FOLDER', '')

# terracotta was not installed, fall back to file system
PACKAGE_DIR = os.path.join(os.path.dirname(__file__), 'cmap_data')

cmap_categories = {'perceptually-uniform-sequential': ['viridis',
                                                       'plasma',
                                                       'inferno',
                                                       'magma',
                                                       'cividis'],
                   'sequential': ['Greys',
                                  'Purples',
                                  'Blues',
                                  'Greens',
                                  'Oranges',
                                  'Reds',
                                  'YlOrBr',
                                  'YlOrRd',
                                  'OrRd',
                                  'PuRd',
                                  'RdPu',
                                  'BuPu',
                                  'GnBu',
                                  'PuBu',
                                  'YlGnBu',
                                  'PuBuGn',
                                  'BuGn',
                                  'YlGn'],
                   'sequential-2': ['binary',
                                    'gist_yarg',
                                    'gist_gray',
                                    'gray',
                                    'bone',
                                    'pink',
                                    'spring',
                                    'summer',
                                    'autumn',
                                    'winter',
                                    'cool',
                                    'Wistia',
                                    'hot',
                                    'afmhot',
                                    'gist_heat',
                                    'copper'],
                   'diverging': ['PiYG',
                                 'PRGn',
                                 'BrBG',
                                 'PuOr',
                                 'RdGy',
                                 'RdBu',
                                 'RdYlBu',
                                 'RdYlGn',
                                 'Spectral',
                                 'coolwarm',
                                 'bwr',
                                 'seismic'],
                   'cyclic': ['twilight', 'twilight_shifted', 'hsv'],
                   'qualitative': ['Pastel1',
                                   'Pastel2',
                                   'Paired',
                                   'Accent',
                                   'Dark2',
                                   'Set1',
                                   'Set2',
                                   'Set3',
                                   'tab10',
                                   'tab20',
                                   'tab20b',
                                   'tab20c'],
                   'miscellaneous': ['flag',
                                     'prism',
                                     'ocean',
                                     'gist_earth',
                                     'terrain',
                                     'gist_stern',
                                     'gnuplot',
                                     'gnuplot2',
                                     'CMRmap',
                                     'cubehelix',
                                     'brg',
                                     'gist_rainbow',
                                     'rainbow',
                                     'jet',
                                     'nipy_spectral',
                                     'gist_ncar']}


def _get_cmap_category(cmap):
    cmap_category = 'Miscellaneous'
    for category in cmap_categories:
        cmap_list = cmap_categories[category]
        if cmap in cmap_list:
            cmap_category = category
    return cmap_category


def _get_cmap_files() -> Dict[str, str]:
    cmap_files = {}
    for f in os.listdir(PACKAGE_DIR):
        if not f.endswith(SUFFIX):
            continue

        cmap_name = f[:-len(SUFFIX)]
        cmap_files[cmap_name] = os.path.join(PACKAGE_DIR, f)

    if not EXTRA_CMAP_FOLDER:
        return cmap_files

    if not os.path.isdir(EXTRA_CMAP_FOLDER):
        raise IOError(f'invalid TC_EXTRA_CMAP_FOLDER: {EXTRA_CMAP_FOLDER}')

    for f in os.listdir(EXTRA_CMAP_FOLDER):
        if not f.endswith(SUFFIX):
            continue

        f_path = os.path.join(EXTRA_CMAP_FOLDER, f)
        try:
            _read_cmap(f_path)
        except ValueError as exc:
            raise ValueError(f'invalid custom colormap \
                             {f}: {exc!s}') from None

        cmap_name = f[:-len(SUFFIX)]
        cmap_files[cmap_name] = f_path

    return cmap_files


def load_colormaps_from_file():
    files = _get_cmap_files()
    for cmap in files:
        colormap = Colormap(
            name=cmap,
            colormap_type=_get_cmap_category(cmap)
        )

        filepath = files[cmap]
        cmap_file = open(filepath, 'rb')
        colormap.file_object.save(os.path.basename(filepath), File(cmap_file))
        colormap.save()
        logging.info(f'Successfully saved: {cmap}')


if settings.USE_S3:
    try:
        AVAILABLE_CMAPS = list(
            Colormap.objects.all().values_list('colormap_id', flat=True))
    except:
        AVAILABLE_CMAPS = []
else:
    CMAP_FILES = _get_cmap_files()
    AVAILABLE_CMAPS = sorted(CMAP_FILES.keys())


def _read_cmap(path: str) -> np.ndarray:
    with open(path, 'rb') as f:
        cmap_data = np.load(f)

    if cmap_data.shape != (255, 4):
        raise ValueError(f'invalid shape (expected: (255, 4); \
                         got: {cmap_data.shape})')

    if cmap_data.dtype != np.uint8:
        raise ValueError(f'invalid dtype (expected: uint8; got: \
                         {cmap_data.dtype})')

    return cmap_data


def _read_cmap_s3(cmap) -> np.ndarray:
    """Retreive file from django object"""
    cmap_data = np.load(cmap.file_object)

    if cmap_data.shape != (255, 4):
        raise ValueError(f'invalid shape (expected: (255, 4); \
                         got: {cmap_data.shape})')

    if cmap_data.dtype != np.uint8:
        raise ValueError(f'invalid dtype (expected: uint8; got: \
                         {cmap_data.dtype})')

    return cmap_data


def get_cmap(name: str) -> np.ndarray:
    """Retrieve the given colormap and return RGBA values \
        as a uint8 NumPy array of shape (255, 4)
    """
    name = name.lower()

    if settings.USE_S3:
        try:
            cmap = Colormap.objects.get(colormap_id=name)
        except:
            raise ValueError(f'Unknown colormap {name}, \
                             must be one of {AVAILABLE_CMAPS}')

        cmap_data = _read_cmap_s3(cmap)
    else:
        if name not in AVAILABLE_CMAPS:
            raise ValueError(f'Unknown colormap {name}, \
                             must be one of {AVAILABLE_CMAPS}')

        cmap_data = _read_cmap(CMAP_FILES[name])

    return cmap_data
