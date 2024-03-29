# Generated by Django 3.2.15 on 2023-01-04 17:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('glam', '0002_auto_20230104_0955'),
    ]

    operations = [
        migrations.AddField(
            model_name='cropmask',
            name='mask_type',
            field=models.CharField(choices=[('binary', 'Binary (Crop or No Crop'), ('percent', 'Percent Crop')], default='binary', help_text='Type of values present in mask raster (binary or percent crop).', max_length=32),
        ),
    ]
