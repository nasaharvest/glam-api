# Generated by Django 3.2.15 on 2022-12-22 19:40

import config.storage_backends
import datetime
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BoundaryLayer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Boundary layer name.', max_length=256)),
                ('layer_id', models.SlugField(blank=True, help_text='A unique character ID to identify Boundary Layer records.', max_length=256, unique=True)),
                ('display_name', models.CharField(help_text='Boundary Layer display name.', max_length=256)),
                ('display_name_en', models.CharField(help_text='Boundary Layer display name.', max_length=256, null=True)),
                ('display_name_es', models.CharField(help_text='Boundary Layer display name.', max_length=256, null=True)),
                ('display_name_pt', models.CharField(help_text='Boundary Layer display name.', max_length=256, null=True)),
                ('desc', models.TextField(help_text='Brief description of Boundary Layer.')),
                ('desc_en', models.TextField(help_text='Brief description of Boundary Layer.', null=True)),
                ('desc_es', models.TextField(help_text='Brief description of Boundary Layer.', null=True)),
                ('desc_pt', models.TextField(help_text='Brief description of Boundary Layer.', null=True)),
                ('meta', models.JSONField(blank=True, help_text='Optional metadata field to provide extra details.', null=True)),
                ('features', models.JSONField(blank=True, help_text='List of boundary features present in the boundary layer.', null=True)),
                ('date_created', models.DateField(help_text='Date the Boundary Layer version was created.')),
                ('date_added', models.DateField(help_text='Date the Boundary Layer was added to the system.')),
                ('source_data', models.FileField(blank=True, help_text='Original Boundary Layer raster or vector', null=True, storage=config.storage_backends.RasterStorage(), upload_to='boundary-layers')),
                ('vector_file', models.FileField(blank=True, help_text='Vector geometry file for visual representation in the GLAM application', null=True, storage=config.storage_backends.VectorStorage(), upload_to='boundary-layers')),
            ],
            options={
                'verbose_name': 'boundary layer',
            },
        ),
        migrations.CreateModel(
            name='BoundaryRaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, help_text='Dataset name. Generated automatically from file name.', max_length=256)),
                ('slug', models.SlugField(blank=True, help_text='Slug for dataset. (automatically generated)', max_length=256, unique=True)),
                ('features', models.JSONField(blank=True, help_text='List of boundary layer features present in the boundary raster dataset.', null=True)),
                ('meta', models.JSONField(blank=True, help_text='Optional metadata field to provide extra dataset details.', null=True)),
                ('date_created', models.DateField(help_text='Date the crop mask dataset version was created.')),
                ('date_added', models.DateField(auto_now_add=True, help_text='Date dataset added to system.')),
                ('local_path', models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', path='/data/glam2/api/glam_api/local_files/boundary_rasters', recursive=True)),
                ('file_object', models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='boundary-rasters')),
                ('boundary_layer', models.ForeignKey(help_text='Boundary Layer that the dataset belongs to.', on_delete=django.db.models.deletion.CASCADE, to='glam.boundarylayer')),
            ],
            options={
                'verbose_name': 'boundary layer raster dataset',
            },
        ),
        migrations.CreateModel(
            name='Crop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name of crop.', max_length=256)),
                ('crop_id', models.SlugField(blank=True, help_text='A unique character ID to identify Crop records.', max_length=256, unique=True)),
                ('display_name', models.CharField(help_text='Crop display name.', max_length=256)),
                ('desc', models.TextField(help_text='Description of crop.')),
            ],
        ),
        migrations.CreateModel(
            name='CropMask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Cropmask name.', max_length=256)),
                ('cropmask_id', models.SlugField(blank=True, help_text='A unique character ID to identify Crop Mask records.', max_length=256, unique=True)),
                ('coverage', models.CharField(default='Global', help_text='Text representation of spatial coverage/extent of crop mask.', max_length=256)),
                ('display_name', models.CharField(help_text='Cropmask display name.', max_length=256)),
                ('display_name_en', models.CharField(help_text='Cropmask display name.', max_length=256, null=True)),
                ('display_name_es', models.CharField(help_text='Cropmask display name.', max_length=256, null=True)),
                ('display_name_pt', models.CharField(help_text='Cropmask display name.', max_length=256, null=True)),
                ('desc', models.TextField(help_text='Brief cropmask decription.')),
                ('desc_en', models.TextField(help_text='Brief cropmask decription.', null=True)),
                ('desc_es', models.TextField(help_text='Brief cropmask decription.', null=True)),
                ('desc_pt', models.TextField(help_text='Brief cropmask decription.', null=True)),
                ('meta', models.JSONField(blank=True, help_text='Optional metadata field to provide extra details.', null=True)),
                ('date_created', models.DateField(help_text='Date that the cropmask version was created.')),
                ('date_added', models.DateField(help_text='Date cropmask added to the system.')),
                ('source_file', models.FileField(blank=True, help_text='Original source file(s). Raster or Vector. (If Available)', null=True, storage=config.storage_backends.RasterStorage(), upload_to='cropmasks')),
                ('raster_file', models.FileField(blank=True, help_text='Cloud Optimized Geotiff to be used for visualization in TMS.', null=True, storage=config.storage_backends.RasterStorage(), upload_to='cropmasks')),
                ('crop_type', models.ForeignKey(help_text='Crop that the mask represents.', on_delete=django.db.models.deletion.PROTECT, to='glam.crop')),
            ],
            options={
                'verbose_name': 'crop mask',
            },
        ),
        migrations.CreateModel(
            name='CropmaskRaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mask_type', models.CharField(choices=[('binary', 'Binary (Crop or No Crop'), ('percent', 'Percent Crop')], default='binary', help_text='Type of values present in mask raster (binary or percent crop). Used for zonal statistics calculations.', max_length=32)),
                ('name', models.CharField(blank=True, help_text='Dataset name. Generated automatically from file name.', max_length=256)),
                ('slug', models.SlugField(blank=True, help_text='Slug for dataset. (automatically generated)', max_length=256, unique=True)),
                ('meta', models.JSONField(blank=True, help_text='Optional metadata field to provide extra dataset details.', null=True)),
                ('date_created', models.DateField(help_text='Date the crop mask dataset version was created.')),
                ('date_added', models.DateField(auto_now_add=True, help_text='Date dataset added to system.')),
                ('local_path', models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', path='/data/glam2/api/glam_api/local_files/cropmask_rasters', recursive=True)),
                ('file_object', models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='cropmask-rasters')),
                ('crop_mask', models.ForeignKey(help_text='CropMask that the crop mask dataset belongs to.', on_delete=django.db.models.deletion.CASCADE, to='glam.cropmask')),
            ],
            options={
                'verbose_name': 'crop mask dataset',
            },
        ),
        migrations.CreateModel(
            name='DataSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Source name.', max_length=256)),
                ('source_id', models.SlugField(blank=True, help_text='A unique character ID to identify Data Source records.', max_length=256, unique=True)),
                ('display_name', models.CharField(help_text='Source display name.', max_length=256)),
                ('desc', models.TextField(help_text='Brief source description.')),
                ('desc_en', models.TextField(help_text='Brief source description.', null=True)),
                ('desc_es', models.TextField(help_text='Brief source description.', null=True)),
                ('desc_pt', models.TextField(help_text='Brief source description.', null=True)),
                ('link', models.URLField(help_text='URL link to Source.')),
                ('logo', models.ImageField(blank=True, help_text='Source logo.', null=True, storage=config.storage_backends.PublicStorage(), upload_to='logos')),
            ],
        ),
        migrations.CreateModel(
            name='ImageExport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique id for export', primary_key=True, serialize=False)),
                ('started', models.DateTimeField(auto_now_add=True, help_text='Date/Time export started.')),
                ('completed', models.DateTimeField(blank=True, help_text='Date/Time export completed.', null=True)),
                ('file_object', models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='exports')),
            ],
            options={
                'verbose_name': 'image export',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Product name.', max_length=256)),
                ('product_id', models.SlugField(blank=True, help_text='A unique character ID to identify Product records.', max_length=256, unique=True)),
                ('display_name', models.CharField(help_text='Product display name.', max_length=256)),
                ('display_name_en', models.CharField(help_text='Product display name.', max_length=256, null=True)),
                ('display_name_es', models.CharField(help_text='Product display name.', max_length=256, null=True)),
                ('display_name_pt', models.CharField(help_text='Product display name.', max_length=256, null=True)),
                ('desc', models.TextField(help_text='Description of product.')),
                ('desc_en', models.TextField(help_text='Description of product.', null=True)),
                ('desc_es', models.TextField(help_text='Description of product.', null=True)),
                ('desc_pt', models.TextField(help_text='Description of product.', null=True)),
                ('meta', models.JSONField(blank=True, help_text='Optional metadata field to provide extra details.', null=True)),
                ('link', models.URLField(blank=True, help_text='URL to product source or additional details.', null=True)),
                ('date_start', models.DateField(help_text='Date the product was first made available.')),
                ('date_added', models.DateField(help_text='Date the product was added to the system.')),
                ('composite', models.BooleanField(help_text='Is the product a composite?')),
                ('composite_period', models.IntegerField(blank=True, help_text='If the product is a composite - the compositing period. (in days)', null=True)),
                ('source', models.ForeignKey(help_text='Product data source/organization.', on_delete=django.db.models.deletion.PROTECT, to='glam.datasource')),
            ],
            options={
                'verbose_name': 'product',
            },
        ),
        migrations.CreateModel(
            name='ProductRaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prelim', models.BooleanField(default=False, help_text='Is this dataset preliminary/near real time?')),
                ('name', models.CharField(blank=True, help_text='Dataset name. Generated automatically from file name.', max_length=256)),
                ('slug', models.SlugField(blank=True, help_text='Slug for dataset. (automatically generated)', max_length=256, unique=True)),
                ('meta', models.JSONField(blank=True, help_text='Optional metadata field to provide extra dataset details.', null=True)),
                ('date', models.DateField(blank=True, db_index=True, help_text='Dataset date. If product is a composite see product details for when the date falls in the compositing period. Derived automatically from file name.')),
                ('date_added', models.DateField(auto_now_add=True, help_text='Date dataset added to system.')),
                ('local_path', models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', max_length=256, path='/data/glam2/api/glam_api/local_files/product_rasters', recursive=True)),
                ('file_object', models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='products')),
                ('product', models.ForeignKey(help_text='Product the dataset belongs to.', on_delete=django.db.models.deletion.CASCADE, related_name='datasets', to='glam.product')),
            ],
            options={
                'verbose_name': 'product dataset',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Tag', max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='ZonalStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_id', models.IntegerField(db_index=True, help_text='Feature of ZonalStats.')),
                ('arable_pixels', models.FloatField(help_text='Number of pixels representing arable land within the specified feature.')),
                ('percent_arable', models.FloatField(help_text='Percent of arable pixels for the product and mask dataset comination.')),
                ('mean_value', models.FloatField(help_text='Mean calculated for specified feature using the product and mask dataset combination.')),
                ('date', models.DateField(db_index=True, help_text='Date the ZonalStats represent, derived from the product dataset')),
                ('boundary_raster', models.ForeignKey(help_text='Boundary Layer dataset of ZonalStats.', on_delete=django.db.models.deletion.CASCADE, to='glam.boundaryraster')),
                ('cropmask_raster', models.ForeignKey(help_text='Cropmask dataset of ZonalStats.', null=True, on_delete=django.db.models.deletion.CASCADE, to='glam.cropmaskraster')),
                ('product_raster', models.ForeignKey(help_text='Product dataset of ZonalStats.', on_delete=django.db.models.deletion.CASCADE, to='glam.productraster')),
            ],
            options={
                'verbose_name': 'zonal stats',
                'verbose_name_plural': 'zonal stats',
            },
        ),
        migrations.CreateModel(
            name='Variable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Variable name.', max_length=256)),
                ('variable_id', models.SlugField(blank=True, help_text='A unique character ID to identify Variable records.', max_length=256, unique=True)),
                ('display_name', models.CharField(help_text='Variable display name.', max_length=256)),
                ('display_name_en', models.CharField(help_text='Variable display name.', max_length=256, null=True)),
                ('display_name_es', models.CharField(help_text='Variable display name.', max_length=256, null=True)),
                ('display_name_pt', models.CharField(help_text='Variable display name.', max_length=256, null=True)),
                ('desc', models.TextField(help_text='Description of variable measured by product.')),
                ('desc_en', models.TextField(help_text='Description of variable measured by product.', null=True)),
                ('desc_es', models.TextField(help_text='Description of variable measured by product.', null=True)),
                ('desc_pt', models.TextField(help_text='Description of variable measured by product.', null=True)),
                ('scale', models.FloatField(help_text='Scale to apply to measurements of variable derrived from product.')),
                ('units', models.CharField(help_text='Units of measurement for variable.', max_length=64)),
                ('unit_abbr', models.CharField(blank=True, help_text='Abbreviation of units of measurement.', max_length=32, null=True)),
                ('tags', models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag')),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag'),
        ),
        migrations.AddField(
            model_name='product',
            name='variable',
            field=models.ForeignKey(help_text='Variable measured by product.', on_delete=django.db.models.deletion.PROTECT, to='glam.variable'),
        ),
        migrations.AddField(
            model_name='datasource',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag'),
        ),
        migrations.AddField(
            model_name='cropmaskraster',
            name='product',
            field=models.ForeignKey(help_text='Product that the crop mask dataset belongs to.Necessary for matching product resolution in ZonalStats calculation.', on_delete=django.db.models.deletion.CASCADE, related_name='mask_datasets', to='glam.product'),
        ),
        migrations.AddField(
            model_name='cropmask',
            name='source',
            field=models.ForeignKey(help_text='Cropmask source.', on_delete=django.db.models.deletion.PROTECT, to='glam.datasource'),
        ),
        migrations.AddField(
            model_name='cropmask',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag'),
        ),
        migrations.AddField(
            model_name='crop',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag'),
        ),
        migrations.CreateModel(
            name='Colormap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Colormap name.', max_length=256)),
                ('colormap_id', models.SlugField(blank=True, help_text='A unique character ID to identify Colormap records.', max_length=256, unique=True)),
                ('desc', models.TextField(blank=True, help_text='Description of product.', null=True)),
                ('colormap_type', models.CharField(choices=[('perceptually-uniform-sequential', 'Perceptually Uniform Sequential'), ('sequential', 'Sequential'), ('sequential-2', 'Sequential (2)'), ('diverging', 'Diverging'), ('cyclic', 'Cyclic'), ('qualitative', 'Qualitative'), ('miscellaneous', 'Miscellaneous')], default='miscellaneous', help_text='Category/Type of colormap. (sequential, diverging, qualitative, etc.)', max_length=64)),
                ('date_added', models.DateField(auto_now_add=True)),
                ('file_object', models.FileField(blank=True, help_text='Colormap file. (.npy)', storage=config.storage_backends.ColormapStorage(), upload_to='colormaps')),
                ('tags', models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag')),
            ],
        ),
        migrations.AddField(
            model_name='boundaryraster',
            name='product',
            field=models.ForeignKey(help_text='Product that the Boundary Layer dataset belongs to.Necessary for matching product resolution in ZonalStats calculation.', on_delete=django.db.models.deletion.CASCADE, related_name='boundary_rasters', to='glam.product'),
        ),
        migrations.AddField(
            model_name='boundarylayer',
            name='masks',
            field=models.ManyToManyField(help_text='Cropmasks that are available for the Boundary Layer. (for ZonalStats generation)', to='glam.CropMask'),
        ),
        migrations.AddField(
            model_name='boundarylayer',
            name='source',
            field=models.ForeignKey(help_text='Boundary Layer source.', on_delete=django.db.models.deletion.PROTECT, to='glam.datasource'),
        ),
        migrations.AddField(
            model_name='boundarylayer',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag'),
        ),
        migrations.CreateModel(
            name='BoundaryFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_name', models.CharField(help_text='Boundary layer name.', max_length=256)),
                ('feature_id', models.BigIntegerField(db_index=True, help_text='A unique character ID to identify Boundary Layer records.', null=True)),
                ('properties', models.JSONField(blank=True, null=True)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(null=True, srid=4326)),
                ('boundary_layer', models.ForeignKey(help_text='Boundary layer that feature belongs to', on_delete=django.db.models.deletion.CASCADE, to='glam.boundarylayer')),
            ],
            options={
                'verbose_name': 'boundary feature',
            },
        ),
        migrations.CreateModel(
            name='AnomalyBaselineRaster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, help_text='Dataset name. Generated automatically from file name.', max_length=256)),
                ('slug', models.SlugField(blank=True, help_text='Slug for dataset. (automatically generated)', max_length=256, unique=True)),
                ('meta', models.JSONField(blank=True, help_text='Optional metadata field to provide extra dataset details.', null=True)),
                ('day_of_year', models.IntegerField(blank=True, help_text='Day of year that the baseline represents.Automatically derived from file name.')),
                ('baseline_length', models.CharField(blank=True, choices=[('5year', 'Five Year'), ('10year', 'Ten Year'), ('full', 'Full')], help_text='Length of Baseline', max_length=16)),
                ('baseline_type', models.CharField(blank=True, choices=[('mean', 'Mean'), ('median', 'Median')], help_text='Type of Baseline calculation.', max_length=16)),
                ('date_added', models.DateField(auto_now_add=True, help_text='Date dataset added to system.')),
                ('date_updated', models.DateField(blank=True, help_text='Date Baseline dataset updated/added to.')),
                ('local_path', models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', max_length=200, path='/data/glam2/api/glam_api/local_files/baselines', recursive=True)),
                ('file_object', models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='baseline-rasters')),
                ('product', models.ForeignKey(help_text='Product that the dataset is a Baseline of.', on_delete=django.db.models.deletion.CASCADE, to='glam.product')),
            ],
            options={
                'verbose_name': 'anomaly baseline dataset',
            },
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=datetime.date.today)),
                ('sticky', models.BooleanField(default=False, help_text='If multiple messages, keep this message at front/first')),
                ('header', models.TextField(help_text='Announcement Header')),
                ('header_en', models.TextField(help_text='Announcement Header', null=True)),
                ('header_es', models.TextField(help_text='Announcement Header', null=True)),
                ('header_pt', models.TextField(help_text='Announcement Header', null=True)),
                ('message', models.TextField(help_text='Announcement')),
                ('message_en', models.TextField(help_text='Announcement', null=True)),
                ('message_es', models.TextField(help_text='Announcement', null=True)),
                ('message_pt', models.TextField(help_text='Announcement', null=True)),
                ('image', models.ImageField(blank=True, help_text='Announcement Image.', null=True, storage=config.storage_backends.PublicStorage(), upload_to='announcements')),
                ('tags', models.ManyToManyField(blank=True, help_text='Optional tags to help searching and filtering.', to='glam.Tag')),
            ],
        ),
        migrations.AddIndex(
            model_name='zonalstats',
            index=models.Index(fields=['product_raster', 'cropmask_raster', 'boundary_raster', 'feature_id', 'date'], name='zstats_idx'),
        ),
        migrations.AddIndex(
            model_name='zonalstats',
            index=models.Index(fields=['product_raster', 'cropmask_raster', 'boundary_raster', 'feature_id'], name='zstats_idx_no_date'),
        ),
        migrations.AddIndex(
            model_name='boundaryfeature',
            index=models.Index(fields=['feature_name', 'feature_id', 'boundary_layer'], name='feature_name_id_layer_idx'),
        ),
    ]
