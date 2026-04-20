import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('donors', '0001_initial'),
        ('requests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SmsNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=20)),
                ('status', models.CharField(max_length=10, choices=[('sent', 'Sent'), ('failed', 'Failed'), ('demo', 'Demo')])),
                ('gateway_response', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('blood_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='requests.bloodrequest')),
                ('donor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='donors.donor')),
            ],
        ),
    ]
