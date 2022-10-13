"""
cmaps/get_cmap.py

Define an interface to retrieve stored color maps.
Modified from Terracotta (https://github.com/DHI-GRAS/terracotta)
"""

from typing import Dict
import os

import numpy as np

from django.conf import settings

from ...models import Colormap


SUFFIX = '_rgba.npy'
EXTRA_CMAP_FOLDER = os.environ.get('TC_EXTRA_CMAP_FOLDER', '')

# terracotta was not installed, fall back to file system
PACKAGE_DIR = os.path.join(os.path.dirname(__file__), 'cmap_data')


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
