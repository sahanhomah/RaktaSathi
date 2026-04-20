import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image, ImageDraw

from donors.models import Donor
from notifications.services import send_email_notification_to_donor
from requests.models import BloodRequest


User = get_user_model()
TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix='bloodbank-notifications-test-media-'))


def build_test_prescription_file(filename='prescription.png'):
	buffer = BytesIO()
	image = Image.new('RGB', (900, 1200), color='white')
	draw = ImageDraw.Draw(image)
	draw.rectangle((35, 35, 865, 1165), outline='black', width=3)
	draw.text((60, 70), 'Doctor Prescription', fill='black')
	draw.text((60, 130), 'Patient: Test Requester', fill='black')
	draw.text((60, 190), 'Advice: Arrange blood urgently', fill='black')
	image.save(buffer, format='PNG')
	buffer.seek(0)
	return SimpleUploadedFile(filename, buffer.read(), content_type='image/png')


@override_settings(
	MEDIA_ROOT=TEST_MEDIA_ROOT,
	EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
	DEFAULT_FROM_EMAIL='no-reply@bloodbank.local',
)
class EmailNotificationServiceTests(TestCase):
	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

	def test_notification_email_attaches_prescription_document(self):
		requester = User.objects.create_user(
			username='+9779803011111',
			email='requester@example.com',
			password='StrongPass123!',
		)
		donor_user = User.objects.create_user(
			username='+9779803022222',
			email='donor@example.com',
			password='StrongPass123!',
		)
		donor = Donor.objects.create(
			user=donor_user,
			full_name='Nearby Donor',
			phone='+9779803022222',
			blood_group='A+',
			latitude='27.710000',
			longitude='85.320000',
			is_available=True,
		)
		blood_request = BloodRequest.objects.create(
			requester_user=requester,
			requester_name='Requester',
			requester_phone='9801112233',
			blood_group='A+',
			latitude='27.717200',
			longitude='85.324000',
			urgency='emergency',
			prescription_image=build_test_prescription_file(),
		)

		sent = send_email_notification_to_donor(blood_request, donor, 2.4)

		self.assertTrue(sent)
		self.assertEqual(len(mail.outbox), 1)
		email = mail.outbox[0]
		self.assertEqual(email.to, ['donor@example.com'])
		self.assertIn('Urgent Blood Request Nearby', email.subject)
		self.assertEqual(len(email.attachments), 1)
		self.assertEqual(email.attachments[0][0], 'prescription.png')

	def test_notification_email_skips_when_donor_has_no_email(self):
		requester = User.objects.create_user(
			username='+9779803033333',
			email='requester2@example.com',
			password='StrongPass123!',
		)
		donor_user = User.objects.create_user(
			username='+9779803044444',
			email='',
			password='StrongPass123!',
		)
		donor = Donor.objects.create(
			user=donor_user,
			full_name='No Mail Donor',
			phone='+9779803044444',
			blood_group='A+',
			latitude='27.710000',
			longitude='85.320000',
			is_available=True,
		)
		blood_request = BloodRequest.objects.create(
			requester_user=requester,
			requester_name='Requester 2',
			requester_phone='9802112233',
			blood_group='A+',
			latitude='27.717200',
			longitude='85.324000',
			urgency='normal',
			prescription_image=build_test_prescription_file('prescription2.png'),
		)

		sent = send_email_notification_to_donor(blood_request, donor, 1.2)

		self.assertFalse(sent)
		self.assertEqual(len(mail.outbox), 0)
