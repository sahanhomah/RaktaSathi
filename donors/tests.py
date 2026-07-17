from django.test import TestCase

# Create your tests here.

	def test_donor_creation(self):
		"""Test basic donor creation"""
		self.assertEqual(self.donor.full_name, 'John Doe')
		self.assertEqual(self.donor.blood_group, 'A+')
		self.assertTrue(self.donor.is_available)

	def test_donor_string_representation(self):
		"""Test donor __str__ method"""
		self.assertEqual(str(self.donor), 'John Doe (A+)')

	def test_mark_unavailable_until_default(self):
		"""Test marking donor unavailable with default 3-month duration"""
		self.donor.mark_unavailable_until()
		self.assertFalse(self.donor.is_available)
		self.assertIsNotNone(self.donor.availability_reenable_at)

	def test_mark_unavailable_until_custom_date(self):
		"""Test marking donor unavailable with custom date"""
		custom_date = timezone.now() + timedelta(days=30)
		self.donor.mark_unavailable_until(reenable_at=custom_date)
		self.assertFalse(self.donor.is_available)
		self.assertEqual(self.donor.availability_reenable_at, custom_date)

	def test_refresh_availability_when_expired(self):
		"""Test refreshing availability when expiration date has passed"""
		past_date = timezone.now() - timedelta(days=1)
		self.donor.is_available = False
		self.donor.availability_reenable_at = past_date
		self.donor.save()

		result = self.donor.refresh_availability()
		self.assertTrue(result)
		self.assertTrue(self.donor.is_available)
		self.assertIsNone(self.donor.availability_reenable_at)

	def test_refresh_availability_not_expired(self):
		"""Test refresh availability when still unavailable"""
		future_date = timezone.now() + timedelta(days=10)
		self.donor.is_available = False
		self.donor.availability_reenable_at = future_date
		self.donor.save()

		result = self.donor.refresh_availability()
		self.assertFalse(result)
		self.assertFalse(self.donor.is_available)

	def test_refresh_availability_already_available(self):
		"""Test refresh when donor is already available"""
		result = self.donor.refresh_availability()
		self.assertFalse(result)
		self.assertTrue(self.donor.is_available)

	def test_refresh_expired_availability_classmethod(self):
		"""Test bulk refresh of expired unavailability"""
		# Mark the initial donor as unavailable in the past
		self.donor.is_available = False
		self.donor.availability_reenable_at = timezone.now() - timedelta(days=1)
		self.donor.save()
		
		donor2 = Donor.objects.create(
			full_name='Jane Doe',
			phone='+9779887654321',
			blood_group='B+',
			latitude='27.7172',
			longitude='85.3240',
			is_available=False,
			availability_reenable_at=timezone.now() - timedelta(days=1),
		)
		donor3 = Donor.objects.create(
			full_name='Bob Smith',
			phone='+9779876543210',
			blood_group='O+',
			latitude='27.7172',
			longitude='85.3240',
			is_available=False,
			availability_reenable_at=timezone.now() + timedelta(days=5),
		)

		refreshed_count = Donor.refresh_expired_availability()
		self.assertEqual(refreshed_count, 2)

		self.donor.refresh_from_db()
		donor2.refresh_from_db()
		donor3.refresh_from_db()
		self.assertTrue(self.donor.is_available)
		self.assertTrue(donor2.is_available)
		self.assertFalse(donor3.is_available)

	def test_blood_group_choices(self):
		"""Test all blood group choices"""
		blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
		for i, bg in enumerate(blood_groups):
			donor = Donor.objects.create(
				full_name=f'Donor {bg}',
				phone=f'+977981234567{i}',
				blood_group=bg,
				latitude='27.7172',
				longitude='85.3240',
			)
			self.assertEqual(donor.blood_group, bg)


# ============================================================================
# FORM TESTS
# ============================================================================

class DonorRegistrationFormTests(TestCase):
	"""Test suite for Donor Registration Form"""
	
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
		"""Test phone normalization with 10-digit format"""
		form = DonorRegistrationForm(data=self._base_payload('9812345678'))
		self.assertTrue(form.is_valid())
		self.assertEqual(form.cleaned_data['phone'], '+9779812345678')

	def test_normalizes_number_with_leading_zero(self):
		"""Test phone normalization with leading zero"""
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
	def test_profile_shows_donation_history_summary_and_entries(self, _mock_urlopen):
		completed_request = BloodRequest.objects.create(
			requester_name='Completed Donation',
			requester_phone='9870000000',
			blood_group='A+',
			latitude='27.710000',
			longitude='85.320000',
			urgency='normal',
			status='fulfilled',
			accepted_by=self.donor,
			accepted_at=timezone.now() - timedelta(days=101),
			fulfilled_at=timezone.now() - timedelta(days=100),
		)
		BloodRequest.objects.create(
			requester_name='Deferred Donation',
			requester_phone='9870000001',
			blood_group='A+',
			latitude='27.711000',
			longitude='85.321000',
			urgency='emergency',
			status='notified',
			accepted_by=self.donor,
			accepted_at=timezone.now() - timedelta(days=5),
		)
		BloodRequest.objects.create(
			requester_name='Cancelled Donation',
			requester_phone='9870000002',
			blood_group='A+',
			latitude='27.712000',
			longitude='85.322000',
			urgency='normal',
			status='cancelled',
			accepted_by=self.donor,
			accepted_at=timezone.now() - timedelta(days=20),
		)

		response = self.client.get(reverse('donors:profile'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Past Donation History')
		self.assertContains(response, 'Total donations')
		self.assertContains(response, 'Completed donations only')
		self.assertContains(response, 'Eligible now')
		self.assertContains(response, completed_request.fulfilled_at.strftime('%b'))
		self.assertContains(response, 'Voluntary')
		self.assertContains(response, 'Emergency')
		self.assertContains(response, 'Completed')
		self.assertContains(response, 'Deferred')
		self.assertContains(response, 'Cancelled')

	@patch('donors.views.urllib.request.urlopen', side_effect=Exception('skip geocoder in tests'))
	def test_profile_shows_empty_state_when_no_donation_history_exists(self, _mock_urlopen):
		response = self.client.get(reverse('donors:profile'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'No donation history yet')
		self.assertIn('no-store', response.headers.get('Cache-Control', ''))

	@patch('donors.views.urllib.request.urlopen', side_effect=Exception('skip geocoder in tests'))
	def test_incoming_requests_page_is_not_cached(self, _mock_urlopen):
		response = self.client.get(reverse('donors:incoming_requests'))

		self.assertEqual(response.status_code, 200)
		self.assertIn('no-store', response.headers.get('Cache-Control', ''))

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
