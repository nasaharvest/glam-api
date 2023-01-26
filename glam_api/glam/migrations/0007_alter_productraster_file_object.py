# Generated by Django 3.2.15 on 2023-01-13 17:33

import config.storage_backends
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('glam', '0006_auto_20230110_1031'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productraster',
            name='file_object',
            field=models.FileField(blank=True, help_text='Stored dataset file. When dataset object is saved, the file_object is created using the local_path.', storage=config.storage_backends.RasterStorage(), upload_to='rasters'),
        ),
    ]