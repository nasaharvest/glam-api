from django.core.management.base import BaseCommand, CommandError
from ...utils.ingest import add_cropmask_rasters


class Command(BaseCommand):
    help = 'bulk add cropmask raster datasets'

    def handle(self, *args, **options):
        add_cropmask_rasters()
