from django.conf import settings
from django.db import models

from .validators import validate_prescription_image


class BloodRequest(models.Model):
	BLOOD_GROUP_CHOICES = [
		('A+', 'A+'),
		('A-', 'A-'),
		('B+', 'B+'),
		('B-', 'B-'),
		('AB+', 'AB+'),
		('AB-', 'AB-'),
		('O+', 'O+'),
		('O-', 'O-'),
	]

	STATUS_CHOICES = [
		('pending', 'Pending'),
		('notified', 'Notified'),
		('fulfilled', 'Fulfilled'),
	]

	URGENCY_CHOICES = [
		('normal', 'Normal'),
		('emergency', 'Emergency'),
	]

	requester_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='blood_requests',
	)
	requester_name = models.CharField(max_length=120)
	requester_phone = models.CharField(max_length=20)
	prescription_image = models.ImageField(
		upload_to='prescriptions/',
		null=True,
		blank=False,
		validators=[validate_prescription_image],
	)
	blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES)
	latitude = models.DecimalField(max_digits=9, decimal_places=6)
	longitude = models.DecimalField(max_digits=9, decimal_places=6)
	urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='normal')
	status = models.CharField(
		max_length=12,
		choices=STATUS_CHOICES + [('cancelled', 'Cancelled')],
		default='pending',
	)
	accepted_by = models.ForeignKey(
		'donors.Donor',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='accepted_requests',
	)
	accepted_at = models.DateTimeField(null=True, blank=True)
	requester_notification = models.TextField(blank=True, default='')
	fulfilled_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self) -> str:
		return f"{self.requester_name} ({self.blood_group})"
