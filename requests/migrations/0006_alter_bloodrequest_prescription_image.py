from django.db import migrations, models

import requests.validators


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0005_bloodrequest_prescription_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bloodrequest',
            name='prescription_image',
            field=models.ImageField(null=True, upload_to='prescriptions/', validators=[requests.validators.validate_prescription_image]),
        ),
    ]
