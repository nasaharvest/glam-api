"""
Sample Production Settings
"""

from ..settings import *

DATABASES = {
    ### postgresql/postgis configuration
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": get_env_variable("GLAM_DB_NAME"),
        "USER": get_env_variable("GLAM_DB_USER"),
        "PASSWORD": get_env_variable("GLAM_DB_PASSWORD"),
        "HOST": get_env_variable("GLAM_DB_HOST"),
        "PORT": 5432,
    },
}
