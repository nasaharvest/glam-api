"""
Management command to fix CHIRPS ProductRaster dates based on dekad encoding.

CHIRPS filenames use dekad encoding where the last digit represents:
  - 1 = day 1 of month
  - 2 = day 11 of month
  - 3 = day 21 of month

Example: chirps-v2.0.2026.01.2.tif should be 2026-01-11, not 2026-01-02
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from glam.models import ProductRaster
from config.utils import extract_datetime_from_filename


class Command(BaseCommand):
    help = "Fix CHIRPS ProductRaster dates by re-extracting from filenames"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )
        parser.add_argument(
            "--product",
            type=str,
            default="chirps-precip",
            help="Product ID to fix (default: chirps-precip)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        product_id = options["product"]

        # Get all ProductRaster records for the specified product
        queryset = ProductRaster.objects.filter(
            product__product_id=product_id
        ).select_related("product")

        if not queryset.exists():
            self.stdout.write(
                self.style.WARNING(f"No datasets found for product: {product_id}")
            )
            return

        total = queryset.count()
        updated = 0
        errors = 0

        self.stdout.write(
            self.style.SUCCESS(f"\nFound {total} {product_id} datasets to process\n")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made\n")
            )

        for dataset in queryset:
            # Extract the correct date from the filename
            filename = (
                dataset.file_object.name if dataset.file_object else dataset.local_path
            )
            correct_date_str = extract_datetime_from_filename(filename)

            if not correct_date_str:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ {dataset.slug}: Could not extract date from {filename}"
                    )
                )
                errors += 1
                continue

            # Convert to date object
            from datetime import datetime

            correct_date = datetime.strptime(correct_date_str, "%Y-%m-%d").date()

            # Check if date needs updating
            if dataset.date != correct_date:
                self.stdout.write(f"  {dataset.slug}:")
                self.stdout.write(f"    From: {dataset.date} → To: {correct_date}")
                self.stdout.write(f"    File: {filename}")

                if not dry_run:
                    dataset.date = correct_date
                    dataset.save(update_fields=["date"])
                    self.stdout.write(self.style.SUCCESS("    ✓ Updated"))

                updated += 1
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ {dataset.slug}: Date already correct ({correct_date})"
                    )
                )

        # Summary
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(f"Total processed: {total}")
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated}"))
        self.stdout.write(self.style.ERROR(f"Errors: {errors}"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nDRY RUN MODE - Run without --dry-run to apply changes"
                )
            )
