# Generated by Django 3.2.15 on 2023-01-26 20:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('glam', '0010_zonalstats_unique_stats_record'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='zonalstats',
            constraint=models.UniqueConstraint(condition=models.Q(('cropmask_raster__isnull', True)), fields=('product_raster', 'boundary_layer', 'feature_id', 'date'), name='unique_stats_record_null_cropmask'),
        ),
    ]