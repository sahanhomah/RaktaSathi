from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from unittest.mock import patch

from requests.models import BloodRequest

from .forms import DonorRegistrationForm
from .models import Donor


User = get_user_model()


def build_test_prescription_file(filename='prescription.png'):
	return SimpleUploadedFile(
		filename,
		(
			b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
			b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x86\x8d\x00\x00\x00\x00IEND\xaeB`\x82'
		),
		content_type='image/png',
	)


class DonorRegistrationFormTests(TestCase):
	def _base_payload(self, phone):
		return {
			'full_name': 'Test Donor',
			'phone': phone,
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'is_available': True,
			'email': 'test@example.com',
			'password1': 'ComplexPass123!',
			'password2': 'ComplexPass123!',
		}

	def test_normalizes_10_digit_nepali_phone(self):
		form = DonorRegistrationForm(data=self._base_payload('9812345678'))
		self.assertTrue(form.is_valid())
		self.assertEqual(form.cleaned_data['phone'], '+9779812345678')

	def test_normalizes_number_with_leading_zero(self):
		form = DonorRegistrationForm(data=self._base_payload('09812345678'))
		self.assertTrue(form.is_valid())
		self.assertEqual(form.cleaned_data['phone'], '+9779812345678')

	def test_normalizes_number_without_plus_sign_country_code(self):
		form = DonorRegistrationForm(data=self._base_payload('9779812345678'))
		self.assertTrue(form.is_valid())
		self.assertEqual(form.cleaned_data['phone'], '+9779812345678')

	def test_rejects_invalid_phone(self):
		form = DonorRegistrationForm(data=self._base_payload('12345'))
		self.assertFalse(form.is_valid())
		self.assertIn('phone', form.errors)


class DonorProfileNearbyRequestTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='9800000001', password='safe-pass-123')
		self.donor = Donor.objects.create(
			user=self.user,
			full_name='Nearby Donor',
			phone='+9779800000001',
			blood_group='A+',
			latitude='27.717200',
			longitude='85.324000',
			is_available=True,
		)
		self.client.login(username='9800000001', password='safe-pass-123')

	@patch('donors.views.urllib.request.urlopen', side_effect=Exception('skip geocoder in tests'))
	def test_incoming_requests_page_shows_only_matching_nearby_pending_requests(self, _mock_urlopen):
		nearby_match = BloodRequest.objects.create(
			requester_name='Near Match',
			requester_phone='9811111111',
			blood_group='A+',
			latitude='27.710000',
			longitude='85.320000',
			urgency='normal',
			prescription_image=build_test_prescription_file(),
		)
		BloodRequest.objects.create(
			requester_name='Far Match',
			requester_phone='9822222222',
			blood_group='A+',
			latitude='28.500000',
			longitude='84.500000',
			urgency='normal',
		)
		BloodRequest.objects.create(
			requester_name='Near Wrong Group',
			requester_phone='9833333333',
			blood_group='B+',
			latitude='27.711000',
			longitude='85.321000',
			urgency='emergency',
		)

		response = self.client.get(reverse('donors:incoming_requests') + '?max_distance_km=50')

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, nearby_match.requester_name)
		self.assertContains(response, 'View prescribed document')
		self.assertNotContains(response, 'Far Match')
		self.assertNotContains(response, 'Near Wrong Group')

	@patch('donors.views.urllib.request.urlopen', side_effect=Exception('skip geocoder in tests'))
	def test_donor_can_accept_nearby_matching_request(self, _mock_urlopen):
		blood_request = BloodRequest.objects.create(
			requester_name='Emergency Case',
			requester_phone='9844444444',
			blood_group='A+',
			latitude='27.710000',
			longitude='85.320000',
			urgency='emergency',
		)

		response = self.client.post(
			reverse('donors:incoming_requests'),
			{
				'action': 'accept_request',
				'request_id': blood_request.id,
			},
		)

		self.assertEqual(response.status_code, 302)
		blood_request.refresh_from_db()
		self.assertEqual(blood_request.status, 'notified')
		self.assertEqual(blood_request.accepted_by_id, self.donor.id)
		self.assertIsNotNone(blood_request.accepted_at)

	@patch('donors.views.urllib.request.urlopen', side_effect=Exception('skip geocoder in tests'))
	def test_accepted_requester_details_remain_visible_until_transaction_completed(self, _mock_urlopen):
		accepted_request = BloodRequest.objects.create(
			requester_name='Visible Requester',
			requester_phone='9855555555',
			blood_group='A+',
			latitude='27.710000',
			longitude='85.320000',
			urgency='normal',
			status='notified',
			accepted_by=self.donor,
		)

		response = self.client.get(reverse('donors:incoming_requests'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Accepted Requests In Progress')
		self.assertContains(response, accepted_request.requester_name)
		self.assertContains(response, accepted_request.requester_phone)

		accepted_request.status = 'fulfilled'
		accepted_request.save(update_fields=['status'])

		followup = self.client.get(reverse('donors:incoming_requests'))
		self.assertEqual(followup.status_code, 200)
		self.assertNotContains(followup, accepted_request.requester_name)

	@patch('donors.views.urllib.request.urlopen', side_effect=Exception('skip geocoder in tests'))
	def test_donor_can_cancel_accepted_request(self, _mock_urlopen):
		accepted_request = BloodRequest.objects.create(
			requester_name='Cancel Candidate',
			requester_phone='9866666666',
			blood_group='A+',
			latitude='27.710000',
			longitude='85.320000',
			urgency='normal',
			status='notified',
			accepted_by=self.donor,
		)

		response = self.client.post(
			reverse('donors:incoming_requests'),
			{
				'action': 'cancel_accept',
				'request_id': accepted_request.id,
			},
		)

		self.assertEqual(response.status_code, 302)
		accepted_request.refresh_from_db()
		self.assertEqual(accepted_request.status, 'pending')
		self.assertIsNone(accepted_request.accepted_by_id)
		self.assertIsNone(accepted_request.accepted_at)
		self.assertIn('open for other donors', accepted_request.requester_notification)


class DonorLoginIdentifierTests(TestCase):
	def setUp(self):
		self.password = 'StrongPass123!'
		self.phone = '+9779801234567'
		self.email = 'login-test@example.com'
		self.user = User.objects.create_user(
			username=self.phone,
			email=self.email,
			password=self.password,
		)

	def test_login_with_email_and_password(self):
		response = self.client.post(
			reverse('donors:login'),
			{
				'username': self.email,
				'password': self.password,
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('donors:profile'))
		self.assertEqual(self.client.session.get('_auth_user_id'), str(self.user.id))

	def test_login_with_phone_and_password(self):
		response = self.client.post(
			reverse('donors:login'),
			{
				'username': '9801234567',
				'password': self.password,
			},
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, reverse('donors:profile'))
		self.assertEqual(self.client.session.get('_auth_user_id'), str(self.user.id))


class DonorRegistrationFlowTests(TestCase):
	def test_successful_signup_shows_congratulatory_message(self):
		payload = {
			'action': 'send_otp',
			'full_name': 'New Donor',
			'phone': '9812345678',
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'is_available': 'on',
			'email': 'new-donor@example.com',
			'password1': 'StrongPass123!',
			'password2': 'StrongPass123!',
		}

		with patch('donors.views._send_email_otp'):
			first_response = self.client.post(reverse('donors:register'), payload)

		self.assertEqual(first_response.status_code, 200)
		pending = self.client.session.get('donor_registration_otp')
		self.assertIsNotNone(pending)

		verify_response = self.client.post(
			reverse('donors:register'),
			{
				'action': 'verify_otp',
				'otp': pending['otp'],
			},
			follow=True,
		)

		self.assertEqual(verify_response.status_code, 200)
		flash_messages = [str(message) for message in get_messages(verify_response.wsgi_request)]
		self.assertTrue(
			any('Congratulations on signing up!' in message for message in flash_messages)
		)
