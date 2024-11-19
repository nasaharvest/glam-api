"""
URL Configuration for glam_api

"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [path("", include("glam.urls"))] + static(
    settings.STATIC_URL, document_root=settings.STATIC_ROOT
)

if settings.ADMIN_SITE:
    urlpatterns += [path(f"{settings.ADMIN_SITE_NAME}/", admin.site.urls)]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
