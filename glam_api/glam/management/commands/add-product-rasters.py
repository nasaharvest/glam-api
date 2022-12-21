from django.core.management.base import BaseCommand, CommandError
from ...utils.ingest import add_product_rasters


class Command(BaseCommand):
    help = 'bulk add product raster datasets'

    def add_arguments(self, parser):
        parser.add_argument(
            'product', nargs='+', type=str,
            help='product_id of product rasters to ingest')

    def handle(self, *args, **options):
        product = options['product'][0]
        add_product_rasters(product)
