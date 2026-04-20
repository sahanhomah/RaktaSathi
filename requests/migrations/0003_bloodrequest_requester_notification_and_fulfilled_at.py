from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requests', '0002_bloodrequest_accepted_by_accepted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='bloodrequest',
            name='fulfilled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='requester_notification',
            field=models.TextField(blank=True, default=''),
        ),
    ]
