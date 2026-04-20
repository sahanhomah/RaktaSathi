from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('donors', '0002_donor_user'),
        ('requests', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bloodrequest',
            name='accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='bloodrequest',
            name='accepted_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='accepted_requests', to='donors.donor'),
        ),
    ]
