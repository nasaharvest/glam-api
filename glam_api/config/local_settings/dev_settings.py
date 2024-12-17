"""
Sample Development Settings
"""

from ..settings import *

DATABASES = {
    ### sqlite configuration for local development
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.spatialite",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

### GEODJANGO CONFIGURATION OPTIONS ###

# GEOS_LIBRARY_PATH = '/home/bob/local/lib/libgeos_c.so'
# GDAL_LIBRARY_PATH = '/home/sue/local/lib/libgdal.so'
