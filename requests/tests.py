import shutil
import tempfile
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw

from donors.models import Donor
from .models import BloodRequest


User = get_user_model()
TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix='bloodbank-test-media-'))


def build_test_prescription_file(
	filename='prescription.png',
	image_format='PNG',
	content_type='image/png',
	image_size=(900, 1200),
	include_text=True,
	handwritten=False,
):
	buffer = BytesIO()
	image = Image.new('RGB', image_size, color='white')
	if include_text:
		draw = ImageDraw.Draw(image)
		draw.rectangle((35, 35, image_size[0] - 35, image_size[1] - 35), outline='black', width=3)
		if handwritten:
			handwritten_lines = [
				((60, 85), (300, 70)),
				((60, 155), (420, 145)),
				((60, 225), (500, 215)),
				((60, 295), (460, 285)),
				((60, 365), (380, 355)),
			]
			for start, end in handwritten_lines:
				draw.line([start, end], fill='black', width=5)
			draw.line((540, 390, 700, 405), fill='black', width=4)
		else:
			draw.text((60, 70), 'Doctor Prescription', fill='black')
			draw.text((60, 130), 'Patient: Test Requester', fill='black')
			draw.text((60, 190), 'Diagnosis: Blood transfusion required', fill='black')
			draw.text((60, 250), 'Advice: Arrange compatible blood urgently', fill='black')
			draw.text((60, 310), 'Doctor Reg No: NMC-12345', fill='black')
			draw.text((60, 370), 'Signature: _______________', fill='black')
	image.save(buffer, format=image_format)
	buffer.seek(0)
	return SimpleUploadedFile(filename, buffer.read(), content_type=content_type)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class BloodRequestAccessTests(TestCase):
	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
		shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

	def setUp(self):
		self.home_url = reverse('requests:home')
		self.request_url = reverse('requests:request')

	def test_homepage_is_public_for_anonymous_user(self):
		response = self.client.get(self.home_url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Donate Blood, Save Lives')

	def test_anonymous_user_is_redirected_to_login(self):
		response = self.client.get(self.request_url)
		self.assertEqual(response.status_code, 302)
		self.assertIn(reverse('donors:login'), response.url)

	def test_logged_in_user_can_submit_blood_request(self):
		user = User.objects.create_user(
			username='+9779800009999',
			email='requester@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		payload = {
			'action': 'create_request',
			'requester_name': 'Requester One',
			'requester_phone': '9801112233',
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'urgency': 'emergency',
			'prescription_image': build_test_prescription_file(),
		}

		response = self.client.post(self.request_url, payload)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(BloodRequest.objects.count(), 1)
		self.assertEqual(BloodRequest.objects.first().requester_user, user)

	def test_request_creation_rejects_unsupported_image_type(self):
		user = User.objects.create_user(
			username='+9779800000002',
			email='requester-gif@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		payload = {
			'action': 'create_request',
			'requester_name': 'Requester GIF',
			'requester_phone': '9801110002',
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'urgency': 'normal',
			'prescription_image': build_test_prescription_file(
				filename='prescription.gif',
				image_format='GIF',
				content_type='image/gif',
			),
		}

		response = self.client.post(self.request_url, payload)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(BloodRequest.objects.count(), 0)
		self.assertContains(response, 'Only JPG and PNG files are allowed.')

	def test_request_creation_rejects_oversized_prescription(self):
		user = User.objects.create_user(
			username='+9779800000003',
			email='requester-large@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		with self.settings(PRESCRIPTION_MAX_UPLOAD_BYTES=50):
			payload = {
				'action': 'create_request',
				'requester_name': 'Requester Large',
				'requester_phone': '9801110003',
				'blood_group': 'A+',
				'latitude': '27.7172',
				'longitude': '85.3240',
				'urgency': 'normal',
				'prescription_image': build_test_prescription_file(),
			}

			response = self.client.post(self.request_url, payload)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(BloodRequest.objects.count(), 0)
		self.assertContains(response, 'Prescription image size must be')

	def test_request_creation_rejects_non_document_image(self):
		user = User.objects.create_user(
			username='+9779800000004',
			email='requester-no-text@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		payload = {
			'action': 'create_request',
			'requester_name': 'Requester No Text',
			'requester_phone': '9801110004',
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'urgency': 'normal',
			'prescription_image': build_test_prescription_file(include_text=False),
		}

		response = self.client.post(self.request_url, payload)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(BloodRequest.objects.count(), 0)
		self.assertContains(response, 'Prescription image must contain visible writing or text on the document.')

	def test_request_creation_accepts_handwritten_prescription(self):
		user = User.objects.create_user(
			username='+9779800000005',
			email='requester-handwritten@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		payload = {
			'action': 'create_request',
			'requester_name': 'Requester Handwritten',
			'requester_phone': '9801110005',
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'urgency': 'normal',
			'prescription_image': build_test_prescription_file(handwritten=True),
		}

		response = self.client.post(self.request_url, payload)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(BloodRequest.objects.count(), 1)
		self.assertEqual(BloodRequest.objects.first().requester_user, user)

	def test_request_creation_requires_prescription_image(self):
		user = User.objects.create_user(
			username='+9779800000001',
			email='requester-no-image@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		payload = {
			'action': 'create_request',
			'requester_name': 'Requester No Image',
			'requester_phone': '9801110000',
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'urgency': 'normal',
		}

		response = self.client.post(self.request_url, payload)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(BloodRequest.objects.count(), 0)
		self.assertContains(response, 'This field is required.')

	def test_active_request_is_visible_on_request_page_and_can_be_cancelled(self):
		user = User.objects.create_user(
			username='+9779800011111',
			email='active-request@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)
		active_request = BloodRequest.objects.create(
			requester_user=user,
			requester_name='Requester Two',
			requester_phone='9800001111',
			blood_group='B+',
			latitude='27.700000',
			longitude='85.300000',
			urgency='normal',
			status='pending',
		)

		response = self.client.get(self.request_url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, f'Request #{active_request.id} •')

		cancel_response = self.client.post(
			self.request_url,
			{
				'action': 'cancel_request',
				'request_id': active_request.id,
			},
		)
		self.assertEqual(cancel_response.status_code, 302)
		active_request.refresh_from_db()
		self.assertEqual(active_request.status, 'cancelled')

		followup = self.client.get(self.request_url)
		self.assertEqual(followup.status_code, 200)
		self.assertNotContains(followup, f'Request #{active_request.id} •')

	def test_cancelling_request_deletes_prescription_file(self):
		user = User.objects.create_user(
			username='+9779800011112',
			email='cancel-file@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)
		active_request = BloodRequest.objects.create(
			requester_user=user,
			requester_name='Requester With File',
			requester_phone='9800002222',
			blood_group='B+',
			latitude='27.700000',
			longitude='85.300000',
			urgency='normal',
			status='pending',
			prescription_image=build_test_prescription_file(),
		)

		stored_path = Path(active_request.prescription_image.path)
		self.assertTrue(stored_path.exists())

		cancel_response = self.client.post(
			self.request_url,
			{
				'action': 'cancel_request',
				'request_id': active_request.id,
			},
		)

		self.assertEqual(cancel_response.status_code, 302)
		active_request.refresh_from_db()
		self.assertEqual(active_request.status, 'cancelled')
		self.assertFalse(active_request.prescription_image)
		self.assertFalse(stored_path.exists())

	def test_transaction_complete_button_only_shows_after_donor_accepts(self):
		user = User.objects.create_user(
			username='+9779800099999',
			email='button-visibility@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		pending_request = BloodRequest.objects.create(
			requester_user=user,
			requester_name='Requester Pending',
			requester_phone='9801112222',
			blood_group='A+',
			latitude='27.700000',
			longitude='85.300000',
			urgency='normal',
			status='pending',
		)

		response = self.client.get(self.request_url)
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, 'Transaction Complete')

		donor_user = User.objects.create_user(
			username='+9779800088888',
			email='donor-for-button@example.com',
			password='StrongPass123!',
		)
		donor = Donor.objects.create(
			user=donor_user,
			full_name='Accepted Donor',
			phone='+9779800088888',
			blood_group='O+',
			latitude='27.710000',
			longitude='85.310000',
			is_available=True,
		)

		pending_request.status = 'notified'
		pending_request.accepted_by = donor
		pending_request.accepted_at = timezone.now()
		pending_request.save(update_fields=['status', 'accepted_by', 'accepted_at'])

		accepted_response = self.client.get(self.request_url)
		self.assertEqual(accepted_response.status_code, 200)
		self.assertContains(accepted_response, 'Transaction Complete')

	def test_requester_can_mark_notified_request_as_completed(self):
		user = User.objects.create_user(
			username='+9779800077777',
			email='requester-complete@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		donor_user = User.objects.create_user(
			username='+9779800066666',
			email='donor-complete@example.com',
			password='StrongPass123!',
		)
		donor = Donor.objects.create(
			user=donor_user,
			full_name='Completing Donor',
			phone='+9779800066666',
			blood_group='O+',
			latitude='27.710000',
			longitude='85.310000',
			is_available=True,
		)

		accepted_request = BloodRequest.objects.create(
			requester_user=user,
			requester_name='Requester Complete',
			requester_phone='9803334444',
			blood_group='A+',
			latitude='27.700000',
			longitude='85.300000',
			urgency='normal',
			status='notified',
			accepted_by=donor,
			accepted_at=timezone.now(),
		)

		response = self.client.post(
			self.request_url,
			{
				'action': 'complete_request',
				'request_id': accepted_request.id,
			},
		)

		self.assertEqual(response.status_code, 302)
		accepted_request.refresh_from_db()
		self.assertEqual(accepted_request.status, 'fulfilled')
		self.assertIsNotNone(accepted_request.fulfilled_at)
