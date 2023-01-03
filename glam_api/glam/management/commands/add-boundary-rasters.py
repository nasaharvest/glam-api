from django.core.management.base import BaseCommand, CommandError
from ...utils.ingest import add_boundary_rasters


class Command(BaseCommand):
    help = 'bulk add boundary layer raster datasets'

    def handle(self, *args, **options):
        add_boundary_rasters()
