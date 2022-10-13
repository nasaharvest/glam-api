import os
import datetime
import uuid

from django.conf import settings
from django.db import models
from django.contrib.gis.db import models as geomodels
from django.core.files import File
from django.core.files.storage import FileSystemStorage

from django_q.tasks import async_task

from config.storage_backends import (RasterStorage, ColormapStorage,
                                     VectorStorage, PublicStorage)

from .utils.admin_units import get_unique_admin_units

# from .tasks.queue import queue_dataset_stats_queue
from .utils.helpers import generate_unique_slug
# from .utils.stats import queue_zonal_stats


if not settings.USE_S3_RASTERS:
    raster_storage = FileSystemStorage()
    vector_storage = FileSystemStorage()
    cmap_storage = FileSystemStorage()
    public_storage = FileSystemStorage()
elif settings.USE_S3_RASTERS:
    raster_storage = RasterStorage()
    vector_storage = VectorStorage()
    cmap_storage = ColormapStorage()
    public_storage = PublicStorage()


class Tag(models.Model):
    """
    Simple tags to help searching and filtering.
    """
    name = models.CharField(
        max_length=256,
        help_text="Tag")

    def __str__(self):
        return self.name


class Announcement(models.Model):
    date = models.DateField(default=datetime.date.today)
    sticky = models.BooleanField(
        default=False, help_text="If multiple messages, keep this message at front/first")
    header = models.TextField(help_text="Announcement Header")
    message = models.TextField(help_text="Announcement")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")
    image = models.ImageField(upload_to='announcements', storage=public_storage,
                              null=True, blank=True, help_text="Announcement Image.")

    def __str__(self):
        return self.header


class DataSource(models.Model):
    """
    Model to store details on the sources of products, 
    masks, administrative layers, or GLAM partners
    """
    name = models.CharField(max_length=256, help_text="Source name.")
    source_id = models.SlugField(blank=True, unique=True, max_length=256,
                                 help_text="A unique character ID to identify Data Source records.")
    display_name = models.CharField(
        max_length=256, help_text="Source display name.")
    desc = models.TextField(help_text="Brief source description.")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")
    link = models.URLField(help_text="URL link to Source.")
    logo = models.ImageField(upload_to='logos', storage=public_storage,
                             null=True, blank=True, help_text="Source logo.")

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.source_id:
            self.source_id = generate_unique_slug(self, 'source_id')
        super().save(*args, **kwargs)


class Variable(models.Model):
    """
    Scientific variable measured by raster product
    """
    name = models.CharField(max_length=256, help_text="Variable name.")
    variable_id = models.SlugField(blank=True, unique=True, max_length=256,
                                   help_text="A unique character ID to identify Variable records.")
    display_name = models.CharField(
        max_length=256, help_text="Variable display name.")
    desc = models.TextField(
        help_text="Description of variable measured by product.")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")
    scale = models.FloatField(
        help_text="Scale to apply to measurements of variable derrived from product.")
    units = models.CharField(
        max_length=64, help_text="Units of measurement for variable.")
    unit_abbr = models.CharField(
        max_length=32, null=True, blank=True, help_text="Abbreviation of units of measurement.")

    def __str__(self):
        return self.variable_id

    def save(self, *args, **kwargs):
        if not self.variable_id:
            self.variable_id = generate_unique_slug(self, 'variable_id')
        super().save(*args, **kwargs)


class Crop(models.Model):
    """
    Model to store and describe different crop types.
    """
    name = models.CharField(max_length=256, help_text="Name of crop.")
    crop_id = models.SlugField(blank=True, unique=True, max_length=256,
                               help_text="A unique character ID to identify Crop records.")
    display_name = models.CharField(
        max_length=256, help_text="Crop display name.")
    desc = models.TextField(help_text="Description of crop.")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")

    def __str__(self):
        return self.crop_id

    def save(self, *args, **kwargs):
        if not self.crop_id:
            self.crop_id = generate_unique_slug(self, 'crop_id')
        super().save(*args, **kwargs)


class Colormap(models.Model):
    """
    Colormaps
    Model to store available numpy colormap files (generated from matplotlib)
    # Reference:
    # https://matplotlib.org/3.1.1/gallery/color/colormap_reference.html
    """
    COLORMAP_TYPE_CHOICES = [
        ('perceptually-uniform-sequential', 'Perceptually Uniform Sequential'),
        ('sequential', 'Sequential'),
        ('sequential-2', 'Sequential (2)'),
        ('diverging', 'Diverging'),
        ('cyclic', 'Cyclic'),
        ('qualitative', 'Qualitative'),
        ('miscellaneous', 'Miscellaneous')
    ]

    name = models.CharField(max_length=256, help_text="Colormap name.")
    colormap_id = models.SlugField(blank=True, unique=True, max_length=256,
                                   help_text="A unique character ID to identify Colormap records.")
    desc = models.TextField(
        help_text="Description of product.", blank=True, null=True)
    colormap_type = models.CharField(max_length=64, choices=COLORMAP_TYPE_CHOICES, default='miscellaneous',
                                     help_text="Category/Type of colormap. (sequential, diverging, qualitative, etc.)")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")
    date_added = models.DateField(auto_now_add=True)
    file_object = models.FileField(
        upload_to='colormaps', storage=cmap_storage, blank=True, help_text="Colormap file. (.npy)")

    def __str__(self):
        return self.colormap_id

    def save(self, *args, **kwargs):
        if not self.colormap_id:
            self.colormap_id = generate_unique_slug(self, 'colormap_id')
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Raster Product Model
    """
    name = models.CharField(max_length=256, help_text="Product name.")
    product_id = models.SlugField(blank=True, unique=True, max_length=256,
                                  help_text="A unique character ID to identify Product records.")
    display_name = models.CharField(
        max_length=256, help_text="Product display name.")
    desc = models.TextField(help_text="Description of product.")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")
    meta = models.JSONField(
        blank=True, null=True, help_text="Optional metadata field to provide extra details.")
    source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, help_text="Product data source/organization.")
    variable = models.ForeignKey(
        Variable, on_delete=models.PROTECT, help_text="Variable measured by product.")
    link = models.URLField(
        blank=True, null=True, help_text="URL to product source or additional details.")
    date_start = models.DateField(
        help_text="Date the product was first made available.")
    date_added = models.DateField(
        help_text="Date the product was added to the system.")
    composite = models.BooleanField(help_text="Is the product a composite?")
    composite_period = models.IntegerField(
        null=True, blank=True, help_text="If the product is a composite - the compositing period. (in days)")

    def __str__(self):
        return self.product_id

    def save(self, *args, **kwargs):
        if not self.product_id:
            self.product_id = generate_unique_slug(self, 'product_id')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "product"


class CropMask(models.Model):
    """
    Crop Mask Model
    Details of available crop masks and the original raster files
    """
    name = models.CharField(max_length=256, help_text="Cropmask name.")
    cropmask_id = models.SlugField(blank=True, unique=True, max_length=256,
                                   help_text="A unique character ID to identify Crop Mask records.")
    crop_type = models.ForeignKey(
        Crop, on_delete=models.PROTECT, help_text="Crop that the mask represents.")
    display_name = models.CharField(
        max_length=256, help_text="Cropmask display name.")
    desc = models.TextField(help_text="Brief cropmask decription.")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")
    meta = models.JSONField(
        blank=True, null=True, help_text="Optional metadata field to provide extra details.")
    source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, help_text="Cropmask source.")
    date_created = models.DateField(
        help_text="Date that the cropmask version was created.")
    date_added = models.DateField(
        help_text="Date cropmask added to the system.")
    raster_file = models.FileField(upload_to='masks', storage=raster_storage, blank=True,
                                   null=True, help_text="Original cropmask raster file. (if available)")
    vector_file = models.FileField(upload_to='vectors', storage=vector_storage,
                                   blank=True, null=True, help_text="Original cropmask vector file. (if available)")

    def __str__(self):
        return self.cropmask_id

    def save(self, *args, **kwargs):
        if not self.cropmask_id:
            self.cropmask_id = generate_unique_slug(self, 'cropmask_id')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "crop mask"


class AdminLayer(models.Model):
    """
    Administrative Layer Model
    Store Layer details, original raster file or vector file if available.
    """
    name = models.CharField(
        max_length=256, help_text="Administrative layer name.")
    adminlayer_id = models.SlugField(blank=True, unique=True, max_length=256,
                                     help_text="A unique character ID to identify Administrative Layer records.")
    display_name = models.CharField(
        max_length=256, help_text="Administrative Layer display name.")
    desc = models.TextField(
        help_text="Brief description of Adminsitrative Layer.")
    tags = models.ManyToManyField(
        Tag, blank=True, help_text="Optional tags to help searching and filtering.")
    meta = models.JSONField(
        blank=True, null=True, help_text="Optional metadata field to provide extra details.")
    source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, help_text="Administrative Layer source.")
    admin_units = models.JSONField(
        blank=True, null=True, help_text="List of administrative units present in the administrative layer.")
    date_created = models.DateField(
        help_text="Date the Administrative Layer version was created.")
    date_added = models.DateField(
        help_text="Date the Administrative Layer was added to the system.")
    masks = models.ManyToManyField(
        CropMask, help_text="Cropmasks that are available for the Administrative Layer. (for ZonalStats generation)")
    primary_raster = models.FileField(upload_to='regions', storage=raster_storage, blank=True,
                                      null=True, help_text="Original Administrative Layer raster file. (if available)")
    vector_file = models.FileField(upload_to='vectors', storage=vector_storage, blank=True,
                                   null=True, help_text="Original Administrative Layer vector file. (if available)")

    def __str__(self):
        return self.adminlayer_id

    def save(self, *args, **kwargs):
        if not self.adminlayer_id:
            self.adminlayer_id = generate_unique_slug(self, 'adminlayer_id')
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "administrative layer"


class AdminUnit(geomodels.Model):
    """
    Administrative Layer Units
    Admin Units that belong to each Administrative Layer
    """

    admin_unit_name = models.CharField(
        max_length=256, help_text="Administrative layer name.")
    admin_unit_id = models.BigIntegerField(
        null=True, db_index=True, help_text="A unique character ID to identify Administrative Layer records.")
    admin_layer = models.ForeignKey(
        AdminLayer, on_delete=models.CASCADE, help_text="layer that administrative unit belongs to")
    properties = models.JSONField(blank=True, null=True)
    geom = geomodels.MultiPolygonField(null=True)

    def __str__(self):
        return self.admin_unit_name

    class Meta:
        verbose_name = "administrative unit"

        indexes = [
            models.Index(
                fields=[
                    'admin_unit_name', 'admin_unit_id',
                    'admin_layer'
                ], name='adminunit_name_id_layer_idx'
            )
        ]


class ProductDataset(models.Model):
    """
    Raster Datasets that belong to each product
    """
    product = models.ForeignKey(Product, related_name='datasets',
                                on_delete=models.CASCADE, help_text="Product the dataset belongs to.")
    prelim = models.BooleanField(
        default=False, help_text="Is this dataset preliminary/near real time?")
    name = models.CharField(max_length=256, blank=True,
                            help_text="Dataset name. Generated automatically from file name.")
    slug = models.SlugField(blank=True, unique=True, max_length=256,
                            help_text="Slug for dataset. (automatically generated)")
    meta = models.JSONField(
        blank=True, null=True, help_text="Optional metadata field to provide extra dataset details.")
    date = models.DateField(blank=True, db_index=True,
                            help_text="Dataset date. If product is a composite see product details for when the date falls in the compositing period. Derived automatically from file name.")
    date_added = models.DateField(
        auto_now_add=True, help_text="Date dataset added to system.")
    local_path = models.FilePathField(path=settings.PRODUCT_DATASET_LOCAL_PATH, match=".*\.tif$",
                                      recursive=True, help_text="Path to dataset on current machine. Used to upload dataset file_object.")
    file_object = models.FileField(upload_to='rasters', storage=raster_storage, blank=True,
                                   help_text="Stored dataset file. When dataset object is saved, the file_object is created using the local_path.")

    def __str__(self):
        return self.slug

    def upload_file(self, created=False):
        # triggered on object save
        # if dataset is new, create file_object using local_path
        # method necessasry for file upload to s3 using django-storages
        if created:
            with open(self.local_path, 'rb') as f:
                self.file_object = File(f, name=os.path.basename(f.name))
                self.save()

    def queue_zonal_stats(self, created=False):
        # queue zonal stats creation
        if created:
            async_task('glam.utils.stats.queue_zonal_stats',
                       self.product.product_id, self.date)

    def save(self, *args, **kwargs):
        created = self.pk is None

        if not self.name:
            # generate name
            base_file = os.path.basename(self.local_path)
            fileName, fileExt = os.path.splitext(base_file)
            self.name = fileName

        if not self.slug:
            # generate slug
            self.slug = generate_unique_slug(self, 'slug')

        if not self.date:
            # derive date from file name
            base_file = os.path.basename(self.local_path)
            parts = base_file.split(".")
            try:
                ds_date = datetime.datetime.strptime(
                    f"{parts[1]}.{parts[2]}", "%Y.%j").strftime("%Y-%m-%d")
            except:
                ds_date = datetime.datetime.strptime(
                    parts[1], "%Y-%m-%d").strftime("%Y-%m-%d")
            self.date = ds_date

            # to do
            # trigger baseline refresh/recalculation
            # queue_baseline_update(self.product, self.date)

        super().save(*args, **kwargs)

        self.upload_file(created)
        self.queue_zonal_stats(created)

    class Meta:
        verbose_name = "product dataset"


class MaskDataset(models.Model):
    """
    Raster Dataset of Crop Mask - 
    Resampled to match resolution of related product \
     for ZonalStats calculation
    """
    crop_mask = models.ForeignKey(
        CropMask, on_delete=models.CASCADE,
        help_text="CropMask that the crop mask dataset belongs to.")
    product = models.ForeignKey(
        Product, related_name='mask_datasets', on_delete=models.CASCADE,
        help_text="Product that the crop mask dataset belongs to."
                  "Necessary for matching product resolution in ZonalStats "
                  "calculation.")
    name = models.CharField(
        max_length=256, blank=True,
        help_text="Dataset name. Generated automatically from file name.")
    slug = models.SlugField(
        blank=True, unique=True, max_length=256,
        help_text="Slug for dataset. (automatically generated)")
    meta = models.JSONField(
        blank=True, null=True,
        help_text="Optional metadata field to provide extra dataset details.")
    date_created = models.DateField(
        help_text="Date the crop mask dataset version was created.")
    date_added = models.DateField(
        auto_now_add=True, help_text="Date dataset added to system.")
    local_path = models.FilePathField(
        path=settings.MASK_DATASET_LOCAL_PATH,
        match=".*\.tif$", recursive=True,
        help_text="Path to dataset on current machine. "
                  "Used to upload dataset file_object.")
    file_object = models.FileField(
        upload_to='masks', storage=raster_storage, blank=True,
        help_text="Stored dataset file. When dataset object is saved, "
                  "the file_object is created using the local_path.")

    def __str__(self):
        return self.slug

    def upload_file(self, created=False):
        # triggered on object save
        # if dataset is new, create file_object using local_path
        # method necessasry for file upload to s3 using django-storages
        if created:
            with open(self.local_path, 'rb') as f:
                self.file_object = File(f, name=os.path.basename(f.name))
                self.save()

    def save(self, *args, **kwargs):
        created = self.pk is None

        if not self.name:
            # generate name
            base_file = os.path.basename(self.local_path)
            fileName, fileExt = os.path.splitext(base_file)
            self.name = fileName

        if not self.slug:
            # generate slug
            self.slug = generate_unique_slug(self, 'slug')

        super().save(*args, **kwargs)

        self.upload_file(created)

    class Meta:
        verbose_name = "crop mask dataset"


class AdminDataset(models.Model):
    """
    Raster Dataset of Administrative Layer -
    Resampled to match resolution of related product \
     for ZonalStats calculation
    """
    admin_layer = models.ForeignKey(
        AdminLayer, on_delete=models.CASCADE,
        help_text="Administrative Layer that the dataset belongs to.")
    product = models.ForeignKey(
        Product, related_name='admin_datasets', on_delete=models.CASCADE,
        help_text="Product that the Administrative Layer dataset belongs to."
                  "Necessary for matching product resolution in ZonalStats "
                  "calculation.")
    name = models.CharField(
        max_length=256, blank=True,
        help_text="Dataset name. Generated automatically from file name.")
    slug = models.SlugField(
        blank=True, unique=True, max_length=256,
        help_text="Slug for dataset. (automatically generated)")
    admin_units = models.JSONField(
        blank=True, null=True,
        help_text="List of administrative units present "
                  "in the administrative layer dataset.")
    meta = models.JSONField(
        blank=True, null=True,
        help_text="Optional metadata field to provide extra dataset details.")
    date_created = models.DateField(
        help_text="Date the crop mask dataset version was created.")
    date_added = models.DateField(
        auto_now_add=True, help_text="Date dataset added to system.")
    local_path = models.FilePathField(
        path=settings.ADMIN_DATASET_LOCAL_PATH,
        match=".*\.tif$", recursive=True,
        help_text="Path to dataset on current machine. "
                  "Used to upload dataset file_object.")
    file_object = models.FileField(
        upload_to='regions', storage=raster_storage, blank=True,
        help_text="Stored dataset file. When dataset object is saved, "
                  "the file_object is created using the local_path.")

    def __str__(self):
        return self.slug

    def upload_file(self, created=False):
        # triggered on object save
        # if dataset is new, create file_object using local_path
        # method necessasry for file upload to s3 using django-storages
        if created:
            with open(self.local_path, 'rb') as f:
                self.file_object = File(f, name=os.path.basename(f.name))
                self.save()

    def save(self, *args, **kwargs):
        created = self.pk is None

        if not self.name:
            # generate name
            base_file = os.path.basename(self.local_path)
            fileName, fileExt = os.path.splitext(base_file)
            self.name = fileName

        if not self.slug:
            # generate slug
            self.slug = generate_unique_slug(self, 'slug')

        if created:
            # if dataset is new, generate admin units
            self.admin_units = get_unique_admin_units(self.local_path)

        super().save(*args, **kwargs)

        self.upload_file(created)

    class Meta:
        verbose_name = "administrative layer dataset"


class AnomalyBaselineDataset(models.Model):
    """
    Model to store Baseline Datasets for anomaly calculation
    """
    FIVE = '5year'
    TEN = '10year'
    FULL = 'full'
    BASELINE_LENGTH_CHOICES = [
        (FIVE, 'Five Year'),
        (TEN, 'Ten Year'),
        (FULL, 'Full')
    ]

    MEAN = 'mean'
    MEDIAN = 'median'
    BASELINE_TYPE_CHOICES = [
        (MEAN, 'Mean'),
        (MEDIAN, 'Median')
    ]

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        help_text="Product that the dataset is a Baseline of.")
    name = models.CharField(
        max_length=256, blank=True,
        help_text="Dataset name. Generated automatically from file name.")
    slug = models.SlugField(
        blank=True, unique=True, max_length=256,
        help_text="Slug for dataset. (automatically generated)")
    meta = models.JSONField(
        blank=True, null=True,
        help_text="Optional metadata field to provide extra dataset details.")
    day_of_year = models.IntegerField(
        blank=True,
        help_text="Day of year that the baseline represents."
                  "Automatically derived from file name.")
    baseline_length = models.CharField(
        max_length=16, choices=BASELINE_LENGTH_CHOICES, blank=True,
        help_text="Length of Baseline")
    baseline_type = models.CharField(
        max_length=16, choices=BASELINE_TYPE_CHOICES, blank=True,
        help_text="Type of Baseline calculation.")
    date_added = models.DateField(
        auto_now_add=True, help_text="Date dataset added to system.")
    date_updated = models.DateField(
        blank=True, help_text="Date Baseline dataset updated/added to.")
    local_path = models.FilePathField(
        path=settings.ANOMALY_BASELINE_LOCAL_PATH,
        match=".*\.tif$", recursive=True, max_length=200,
        help_text="Path to dataset on current machine. "
                  "Used to upload dataset file_object.")
    file_object = models.FileField(
        upload_to='rasters', storage=raster_storage, blank=True,
        help_text="Stored dataset file. When dataset object is saved, "
                  "the file_object is created using the local_path.")

    def __str__(self):
        return self.slug

    def upload_file(self, created=True):
        # triggered on object save
        # create file_object using local_path
        # * even if dataset instance is not new - to update baselines *
        # method necessasry for file upload to s3 using django-storages
        if created:
            with open(self.local_path, 'rb') as f:
                self.file_object = File(f, name=os.path.basename(f.name))
                self.save()

    def save(self, *args, **kwargs):
        created = self.pk is None

        if not self.name:
            # generate name
            base_file = os.path.basename(self.local_path)
            fileName, fileExt = os.path.splitext(base_file)
            self.name = fileName

        if not self.slug:
            # generate slug
            self.slug = generate_unique_slug(self, 'slug')

        if not self.day_of_year:
            # get day of year from file name
            base_file = os.path.basename(self.local_path)
            parts = base_file.split(".")
            baseline = parts[2].split("_")
            if self.product.product_id == 'chirps':
                month, day = parts[1].split('-')
                day_value = int(month+day)
                self.day_of_year = day_value
            else:
                self.day_of_year = int(parts[1])

        if not self.baseline_length:
            # get baseline length from file name
            base_file = os.path.basename(self.local_path)
            parts = base_file.split(".")
            baseline = parts[2].split("_")
            self.baseline_length = baseline[2]

        if not self.baseline_type:
            # get baseline type from file name
            base_file = os.path.basename(self.local_path)
            parts = base_file.split(".")
            baseline = parts[2].split("_")
            self.baseline_type = baseline[1]

        self.date_updated = datetime.date.fromtimestamp(
            os.stat(self.local_path).st_mtime)

        super().save(*args, **kwargs)

        # dont automatically upload file
        # self.upload_file()

    class Meta:
        verbose_name = "anomaly baseline dataset"


class ZonalStats(models.Model):
    """
    Zonal Statistics - 
    Calculated per combination of each product dataset and corresponding
    crop mask(s) and administrative layer(s)
    """
    product_dataset = models.ForeignKey(
        ProductDataset, on_delete=models.CASCADE,
        help_text="Product dataset of ZonalStats.")
    mask_dataset = models.ForeignKey(
        MaskDataset, null=True, on_delete=models.CASCADE,
        help_text="Cropmask dataset of ZonalStats.")
    admin_dataset = models.ForeignKey(
        AdminDataset, on_delete=models.CASCADE,
        help_text="Administrative Layer dataset of ZonalStats.")
    admin_unit_id = models.IntegerField(
        db_index=True,
        help_text="Administrative Unit of ZonalStats.")
    arable_pixels = models.FloatField(
        help_text="Number of pixels representing arable land "
                  "within the specified administrative unit.")
    percent_arable = models.FloatField(
        help_text="Percent of arable pixels for the "
                  "product and mask dataset comination.")
    mean_value = models.FloatField(
        help_text="Mean calculated for specified administrative unit "
                  "using the product and mask dataset combination.")
    date = models.DateField(
        db_index=True,
        help_text="Date the ZonalStats represent, derived from the product dataset")

    class Meta:
        verbose_name = "zonal stats"
        verbose_name_plural = "zonal stats"

        indexes = [
            models.Index(
                fields=[
                    'product_dataset', 'mask_dataset',
                    'admin_dataset', 'admin_unit_id',
                    'date'
                ], name='zstats_idx'
            ),
            models.Index(
                fields=[
                    'product_dataset', 'mask_dataset',
                    'admin_dataset', 'admin_unit_id'
                ], name='zstats_idx_no_date'
            )
        ]


class ImageExport(models.Model):
    """
    Model to store image exports
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique id for export")
    started = models.DateTimeField(
        auto_now_add=True,
        help_text="Date/Time export started.")
    completed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date/Time export completed.")
    file_object = models.FileField(
        upload_to='exports', storage=raster_storage, blank=True,
        help_text="Stored dataset file. When dataset object is saved, "
                  "the file_object is created using the local_path.")

    class Meta:
        verbose_name = "image export"
