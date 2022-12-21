# Generated by Django 3.2.15 on 2022-12-12 16:33

import config.storage_backends
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('glam', '0006_alter_boundaryraster_file_object'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anomalybaselineraster',
            name='file_object',
            field=models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='baseline-rasters'),
        ),
        migrations.AlterField(
            model_name='boundarylayer',
            name='vector_file',
            field=models.FileField(blank=True, help_text='Vector geometry file for visual representation in the GLAM application', null=True, storage=config.storage_backends.VectorStorage(), upload_to='boundary-layers'),
        ),
        migrations.AlterField(
            model_name='boundaryraster',
            name='file_object',
            field=models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='boundary-rasters'),
        ),
        migrations.AlterField(
            model_name='cropmask',
            name='raster_file',
            field=models.FileField(blank=True, help_text='Cloud Optimized Geotiff to be used for visualization in TMS.', null=True, storage=config.storage_backends.RasterStorage(), upload_to='cropmasks'),
        ),
        migrations.AlterField(
            model_name='cropmask',
            name='source_file',
            field=models.FileField(blank=True, help_text='Original source file(s). Raster or Vector. (If Available)', null=True, storage=config.storage_backends.RasterStorage(), upload_to='cropmasks'),
        ),
        migrations.AlterField(
            model_name='cropmaskraster',
            name='file_object',
            field=models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='cropmask-rasters'),
        ),
        migrations.AlterField(
            model_name='productraster',
            name='file_object',
            field=models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='product-rasters'),
        ),
    ]
