from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0004_bloodrequest_requester_user_and_cancelled_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='bloodrequest',
            name='prescription_image',
            field=models.ImageField(null=True, upload_to='prescriptions/'),
        ),
    ]
