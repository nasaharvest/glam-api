from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from botocore.exceptions import ClientError

from glam.tasks import download_new, upload_files_from_directory
from glam.ingest import add_product_rasters_from_storage
import logging

logger = logging.getLogger(__name__)


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
        try:
            add_product_rasters_from_storage()
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.stdout.write(
                self.style.ERROR(
                    f"AWS Error ({error_code}): Failed to access S3 bucket. "
                    f"Check your AWS credentials and permissions. Details: {str(e)}"
                )
            )
            logger.error(f"S3 access error: {str(e)}")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Unexpected error while adding rasters: {str(e)}")
            )
            logger.error(f"Unexpected error: {str(e)}")
