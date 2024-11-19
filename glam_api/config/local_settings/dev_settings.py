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
