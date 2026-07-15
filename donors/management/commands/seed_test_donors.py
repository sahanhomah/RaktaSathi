from __future__ import annotations

from django.core.management.base import BaseCommand

from donors.models import Donor


NEPAL_LOCATIONS = [
	{"district": "Kathmandu", "province": "Bagmati", "latitude": 27.7172, "longitude": 85.3240},
	{"district": "Lalitpur", "province": "Bagmati", "latitude": 27.6588, "longitude": 85.3247},
	{"district": "Bhaktapur", "province": "Bagmati", "latitude": 27.6710, "longitude": 85.4298},
	{"district": "Pokhara", "province": "Gandaki", "latitude": 28.2096, "longitude": 83.9856},
	{"district": "Butwal", "province": "Lumbini", "latitude": 27.7006, "longitude": 83.4486},
	{"district": "Bharatpur", "province": "Bagmati", "latitude": 27.6839, "longitude": 84.4350},
	{"district": "Biratnagar", "province": "Koshi", "latitude": 26.4525, "longitude": 87.2718},
	{"district": "Dharan", "province": "Koshi", "latitude": 26.8129, "longitude": 87.2834},
	{"district": "Birgunj", "province": "Madhesh", "latitude": 27.0087, "longitude": 84.8770},
	{"district": "Janakpur", "province": "Madhesh", "latitude": 26.7288, "longitude": 85.9298},
	{"district": "Hetauda", "province": "Bagmati", "latitude": 27.4280, "longitude": 85.0322},
	{"district": "Nepalgunj", "province": "Lumbini", "latitude": 28.0519, "longitude": 81.6150},
	{"district": "Dhangadhi", "province": "Sudurpashchim", "latitude": 28.6966, "longitude": 80.5898},
	{"district": "Tulsipur", "province": "Lumbini", "latitude": 28.1300, "longitude": 82.2973},
	{"district": "Bhimdatta", "province": "Sudurpashchim", "latitude": 28.9632, "longitude": 80.1865},
	{"district": "Ghorahi", "province": "Lumbini", "latitude": 28.0465, "longitude": 82.4955},
	{"district": "Ilam", "province": "Koshi", "latitude": 26.9094, "longitude": 87.9283},
	{"district": "Siddharthanagar", "province": "Lumbini", "latitude": 27.5142, "longitude": 83.4456},
	{"district": "Jumla", "province": "Karnali", "latitude": 29.2747, "longitude": 82.1838},
	{"district": "Surkhet", "province": "Karnali", "latitude": 28.6014, "longitude": 81.6203},
]

BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']


class Command(BaseCommand):
	help = 'Create clearly labeled test donor records spread across Nepal.'

	def add_arguments(self, parser):
		parser.add_argument('--count', type=int, default=100, help='Number of test donors to create.')
		parser.add_argument('--start-phone', type=int, default=9800000000, help='Base phone number for generated records.')
		parser.add_argument('--dry-run', action='store_true', help='Show what would be created without writing to the database.')

	def handle(self, *args, **options):
		count = max(1, options['count'])
		start_phone = options['start_phone']
		dry_run = options['dry_run']

		created = 0
		updated = 0

		for index in range(count):
			location = NEPAL_LOCATIONS[index % len(NEPAL_LOCATIONS)]
			blood_group = BLOOD_GROUPS[index % len(BLOOD_GROUPS)]
			phone = str(start_phone + index)
			full_name = f"Test Donor {index + 1:03d} - {location['district']}"

			if dry_run:
				self.stdout.write(
					f"[dry-run] {full_name} | {phone} | {blood_group} | "
					f"{location['district']}, {location['province']}"
				)
				continue

			donor, was_created = Donor.objects.get_or_create(
				phone=phone,
				defaults={
					'full_name': full_name,
					'blood_group': blood_group,
					'latitude': location['latitude'],
					'longitude': location['longitude'],
					'is_available': True,
				},
			)

			if was_created:
				created += 1
			else:
				donor.full_name = full_name
				donor.blood_group = blood_group
				donor.latitude = location['latitude']
				donor.longitude = location['longitude']
				donor.is_available = True
				donor.availability_reenable_at = None
				donor.save(update_fields=['full_name', 'blood_group', 'latitude', 'longitude', 'is_available', 'availability_reenable_at', 'updated_at'])
				updated += 1

		if dry_run:
			self.stdout.write(self.style.SUCCESS(f'Dry run complete for {count} test donors.'))
			return

		self.stdout.write(self.style.SUCCESS(
			f'Created {created} test donors and updated {updated} existing records.'
		))
