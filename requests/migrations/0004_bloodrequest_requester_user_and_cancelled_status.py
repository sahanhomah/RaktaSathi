from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('requests', '0003_bloodrequest_requester_notification_and_fulfilled_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='bloodrequest',
            name='requester_user',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='blood_requests',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='bloodrequest',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('notified', 'Notified'),
                    ('fulfilled', 'Fulfilled'),
                    ('cancelled', 'Cancelled'),
                ],
                default='pending',
                max_length=12,
            ),
        ),
    ]
