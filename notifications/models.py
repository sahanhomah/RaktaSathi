from django.db import models


class SmsNotification(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('demo', 'Demo'),
    ]

    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    gateway_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    blood_request = models.ForeignKey(
        'requests.BloodRequest',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    donor = models.ForeignKey(
        'donors.Donor',
        on_delete=models.CASCADE,
        related_name='notifications',
    )

    def __str__(self) -> str:
        return f"SMS to {self.phone} [{self.status}]"
