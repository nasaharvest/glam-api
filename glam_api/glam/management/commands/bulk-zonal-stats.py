from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Product, CropMask, BoundaryLayer
from ...utils.stats import queue_bulk_stats


class Command(BaseCommand):
    help = 'bulk create zonal stats - be careful'

    def add_arguments(self, parser):
        parser.add_argument(
            '-p', '--products', type=str, nargs='+',
            help='product_id(s) of product datasets to calculate stats for.')
        parser.add_argument(
            '-c', '--cropmasks', type=str, nargs='+',
            help='cropmask_id(s) of cropmask datasets to calculate stats for.')
        parser.add_argument(
            '-b', '--boundarylayers', type=str, nargs='+',
            help='layer_id(s) of boundary datasets to calculate stats for.')
        parser.add_argument(
            '-y', '--years', type=str, nargs='+',
            help='years to calculate stats for.')
        parser.add_argument(
            '--all', action='store_true',
            help='!!! BEWARE: queue zonal stats '
                 'for all possible dataset combinations !!!'
        )

    def handle(self, *args, **options):
        # print(options)
        all_combos = options['all']

        years = options['years']
        valid_years = None
        if years:
            valid_years = []
            for year in years:
                try:
                    valid_year = datetime.strptime(year, '%Y').year
                    valid_years.append(valid_year)
                except ValueError as e:
                    raise CommandError(e)

        products = options['products']
        cropmasks = options['cropmasks']
        boundarylayers = options['boundarylayers']
        if products == cropmasks == boundarylayers == None:
            if all_combos:
                pass
            else:
                raise CommandError(
                    'Please provide Product/CropMask/BoundaryLayer options '
                    'or specify the "-all" option.')

        if products:
            for product in products:
                try:
                    Product.objects.get(product_id=product)
                    # self.stdout.write(f'{options}')
                except Product.DoesNotExist:
                    raise CommandError(f'Invalid Product supplied: {product}')
        if cropmasks:
            for cropmask in cropmasks:
                try:
                    CropMask.objects.get(cropmask_id=cropmask)
                except CropMask.DoesNotExist:
                    raise CommandError(
                        f'Invalid Cropmask supplied: {cropmask}')
        if boundarylayers:
            for boundarylayer in boundarylayers:
                try:
                    BoundaryLayer.objects.get(layer_id=boundarylayer)
                except BoundaryLayer.DoesNotExist:
                    raise CommandError(
                        f'Invalid BoundaryLayer supplied: {boundarylayer}')

        queue_bulk_stats(
            products=products,
            cropmasks=cropmasks,
            boundarylayers=boundarylayers,
            years=valid_years
        )
