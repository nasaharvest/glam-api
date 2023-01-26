# Generated by Django 3.2.15 on 2023-01-26 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('glam', '0009_auto_20230125_1717'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='zonalstats',
            constraint=models.UniqueConstraint(fields=('product_raster', 'cropmask_raster', 'boundary_layer', 'feature_id', 'date'), name='unique_stats_record'),
        ),
    ]
