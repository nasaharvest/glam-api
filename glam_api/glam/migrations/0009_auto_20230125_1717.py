# Generated by Django 3.2.15 on 2023-01-25 22:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('glam', '0008_auto_20230113_1517'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='zonalstats',
            name='zstats_idx',
        ),
        migrations.RemoveIndex(
            model_name='zonalstats',
            name='zstats_idx_no_date',
        ),
        migrations.RemoveField(
            model_name='zonalstats',
            name='arable_pixels',
        ),
        migrations.RemoveField(
            model_name='zonalstats',
            name='boundary_raster',
        ),
        migrations.RemoveField(
            model_name='zonalstats',
            name='mean_value',
        ),
        migrations.AddField(
            model_name='zonalstats',
            name='boundary_layer',
            field=models.ForeignKey(default=1, help_text='BoundaryLayer', on_delete=django.db.models.deletion.CASCADE, to='glam.boundarylayer'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='zonalstats',
            name='max',
            field=models.FloatField(default=0, verbose_name='Maximum value derived from zonal statistics calculatin.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='zonalstats',
            name='mean',
            field=models.FloatField(default=0, help_text='Mean value derived from zonal statistics calculation.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='zonalstats',
            name='min',
            field=models.FloatField(default=0, verbose_name='Minimum value derived from zonal statistics calculation.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='zonalstats',
            name='pixel_count',
            field=models.FloatField(default=0, help_text='Number of pixels representing the specified feature.'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='zonalstats',
            name='std',
            field=models.FloatField(default=0, verbose_name='Standard deviation derived from zonal statistics calculation.'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='anomalybaselineraster',
            name='local_path',
            field=models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', max_length=256, path='/data/glam2/api/glam_api/local_files/baselines', recursive=True),
        ),
        migrations.AlterField(
            model_name='boundaryraster',
            name='local_path',
            field=models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', max_length=256, path='/data/glam2/api/glam_api/local_files/boundary_rasters', recursive=True),
        ),
        migrations.AlterField(
            model_name='cropmaskraster',
            name='local_path',
            field=models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', max_length=256, path='/data/glam2/api/glam_api/local_files/cropmask_rasters', recursive=True),
        ),
        migrations.AlterField(
            model_name='productraster',
            name='local_path',
            field=models.FilePathField(help_text='Path to dataset on current machine. Used to upload dataset file_object.', match='.*\\.tif$', max_length=256, path='/data/glam2/api/glam_api/local_files/product_rasters', recursive=True),
        ),
        migrations.AlterField(
            model_name='zonalstats',
            name='cropmask_raster',
            field=models.ForeignKey(help_text='Raster Dataset of CropMask.', null=True, on_delete=django.db.models.deletion.CASCADE, to='glam.cropmaskraster'),
        ),
        migrations.AlterField(
            model_name='zonalstats',
            name='feature_id',
            field=models.IntegerField(db_index=True, help_text='ID of feature within BoundaryLayer.'),
        ),
        migrations.AlterField(
            model_name='zonalstats',
            name='percent_arable',
            field=models.FloatField(help_text='Percent of the feature pixels with valid data for the product and mask dataset combination.'),
        ),
        migrations.AlterField(
            model_name='zonalstats',
            name='product_raster',
            field=models.ForeignKey(help_text='Raster dataset of Product.', on_delete=django.db.models.deletion.CASCADE, to='glam.productraster'),
        ),
        migrations.AddIndex(
            model_name='zonalstats',
            index=models.Index(fields=['product_raster', 'cropmask_raster', 'boundary_layer', 'feature_id', 'date'], name='zstats_idx'),
        ),
        migrations.AddIndex(
            model_name='zonalstats',
            index=models.Index(fields=['product_raster', 'cropmask_raster', 'boundary_layer', 'feature_id'], name='zstats_idx_no_date'),
        ),
    ]