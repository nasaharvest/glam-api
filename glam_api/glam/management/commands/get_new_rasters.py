from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from glam.utils import download_new, upload_files_from_directory
from glam.ingest import add_product_rasters_from_storage


class Command(BaseCommand):
    help = "Download new Rasters"

    def handle(self, *args, **options):
        self.stdout.write(f"Downloading new Rasters")
        download_new()

        self.stdout.write(f"Uploading new Rasters to S3")
        upload_files_from_directory(
            settings.PRODUCT_DATASET_LOCAL_PATH,
            settings.AWS_STORAGE_BUCKET_NAME,
            prefix="product-rasters",
        )

        self.stdout.write(f"Adding new Rasters to DB")
        add_product_rasters_from_storage()
