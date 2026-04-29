import calendar

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()


def _add_months(value, months: int):
	target_month_index = value.month - 1 + months
	year = value.year + target_month_index // 12
	month = target_month_index % 12 + 1
	day = min(value.day, calendar.monthrange(year, month)[1])
	return value.replace(year=year, month=month, day=day)


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
	availability_reenable_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

	def mark_unavailable_until(self, reenable_at=None):
		self.is_available = False
		self.availability_reenable_at = reenable_at or _add_months(timezone.now(), 3)

	def refresh_availability(self, current_time=None) -> bool:
		current_time = current_time or timezone.now()
		if self.is_available or self.availability_reenable_at is None:
			return False

		if self.availability_reenable_at > current_time:
			return False

		self.is_available = True
		self.availability_reenable_at = None
		self.save(update_fields=['is_available', 'availability_reenable_at', 'updated_at'])
		return True

	@classmethod
	def refresh_expired_availability(cls, current_time=None) -> int:
		current_time = current_time or timezone.now()
		return cls.objects.filter(
			is_available=False,
			availability_reenable_at__isnull=False,
			availability_reenable_at__lte=current_time,
		).update(is_available=True, availability_reenable_at=None)

	def __str__(self) -> str:
		return f"{self.full_name} ({self.blood_group})"
