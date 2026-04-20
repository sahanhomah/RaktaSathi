from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Donor(models.Model):
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

	full_name = models.CharField(max_length=120)
	phone = models.CharField(max_length=20)
	blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES)
	latitude = models.DecimalField(max_digits=9, decimal_places=6)
	longitude = models.DecimalField(max_digits=9, decimal_places=6)
	is_available = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

	def __str__(self) -> str:
		return f"{self.full_name} ({self.blood_group})"
