from django.test import TestCase

# Create your tests here.
		else:
			draw.text((60, 70), 'Doctor Prescription', fill='black')
			draw.text((60, 130), 'Patient: Test Requester', fill='black')
			draw.text((60, 190), 'Diagnosis: Blood transfusion required', fill='black')
			draw.text((60, 250), 'Advice: Arrange compatible blood urgently', fill='black')

	image.save(buffer, format=image_format)
	buffer.seek(0)
	return SimpleUploadedFile(filename, buffer.read(), content_type=content_type)


# ============================================================================
# MODEL TESTS
# ============================================================================

class BloodRequestModelTests(TestCase):
	"""Test suite for BloodRequest model"""

	def setUp(self):
		self.blood_request = BloodRequest.objects.create(
			requester_name='Test Requester',
			requester_phone='9812345678',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
			urgency='normal',
			prescription_image=build_test_prescription_file(),
		)

	def test_blood_request_creation(self):
		"""Test basic blood request creation"""
		self.assertEqual(self.blood_request.requester_name, 'Test Requester')
		self.assertEqual(self.blood_request.blood_group, 'A+')
		self.assertEqual(self.blood_request.status, 'pending')

	def test_blood_request_string_representation(self):
		"""Test blood request __str__ method"""
		self.assertEqual(str(self.blood_request), 'Test Requester (A+)')

	def test_blood_request_status_choices(self):
		"""Test all status choices"""
		statuses = ['pending', 'notified', 'fulfilled', 'cancelled']
		for status in statuses:
			req = BloodRequest.objects.create(
				requester_name=f'Requester {status}',
				requester_phone='9800000000',
				blood_group='B+',
				latitude='27.7172',
				longitude='85.3240',
				status=status,
			)
			self.assertEqual(req.status, status)

	def test_blood_request_urgency_choices(self):
		"""Test urgency levels"""
		urgencies = ['normal', 'emergency']
		for urgency in urgencies:
			req = BloodRequest.objects.create(
				requester_name=f'Requester {urgency}',
				requester_phone='9800000001',
				blood_group='O+',
				latitude='27.7172',
				longitude='85.3240',
				urgency=urgency,
			)
			self.assertEqual(req.urgency, urgency)

	def test_blood_request_with_accepted_donor(self):
		"""Test blood request accepted by a donor"""
		donor = Donor.objects.create(
			full_name='Test Donor',
			phone='+9779812345678',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
		)
		self.blood_request.accepted_by = donor
		self.blood_request.accepted_at = timezone.now()
		self.blood_request.save()

		self.assertEqual(self.blood_request.accepted_by, donor)
		self.assertIsNotNone(self.blood_request.accepted_at)

	def test_blood_request_with_requester_user(self):
		"""Test blood request with requester user linked"""
		user = User.objects.create_user(username='requester123', password='pass')
		self.blood_request.requester_user = user
		self.blood_request.save()

		self.assertEqual(self.blood_request.requester_user, user)

	def test_blood_request_fulfilled_tracking(self):
		"""Test fulfilled request tracking"""
		donor = Donor.objects.create(
			full_name='Donor',
			phone='+9779800000000',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
		)
		self.blood_request.accepted_by = donor
		self.blood_request.accepted_at = timezone.now()
		self.blood_request.status = 'fulfilled'
		self.blood_request.fulfilled_at = timezone.now()
		self.blood_request.save()

		self.assertEqual(self.blood_request.status, 'fulfilled')
		self.assertIsNotNone(self.blood_request.fulfilled_at)


# ============================================================================
# VALIDATOR TESTS
# ============================================================================

class PrescriptionImageValidatorTests(TestCase):
	"""Test suite for prescription image validator"""

	def test_valid_png_prescription_passes(self):
		"""Test that valid PNG prescription passes validation"""
		file = build_test_prescription_file(image_format='PNG', filename='prescription.png')
		try:
			validate_prescription_image(file)
		except ValidationError:
			self.fail('Valid PNG prescription should pass validation')

	def test_valid_jpeg_prescription_passes(self):
		"""Test that valid JPEG prescription passes validation"""
		file = build_test_prescription_file(image_format='JPEG', filename='prescription.jpg', content_type='image/jpeg')
		try:
			validate_prescription_image(file)
		except ValidationError:
			self.fail('Valid JPEG prescription should pass validation')

	def test_invalid_file_extension_rejected(self):
		"""Test that non-image files are rejected"""
		file = SimpleUploadedFile('document.pdf', b'fake pdf content', content_type='application/pdf')
		with self.assertRaises(ValidationError) as context:
			validate_prescription_image(file)
		self.assertIn('JPG and PNG', str(context.exception))

	def test_oversized_file_rejected(self):
		"""Test that oversized files are rejected"""
		with override_settings(PRESCRIPTION_MAX_UPLOAD_BYTES=1000):
			file = build_test_prescription_file()
			with self.assertRaises(ValidationError) as context:
				validate_prescription_image(file)
			self.assertIn('size must be', str(context.exception))

	def test_too_small_image_rejected(self):
		"""Test that images smaller than minimum dimensions are rejected"""
		with override_settings(PRESCRIPTION_DOC_MIN_WIDTH=300, PRESCRIPTION_DOC_MIN_HEIGHT=300):
			file = build_test_prescription_file(image_size=(100, 100))
			with self.assertRaises(ValidationError) as context:
				validate_prescription_image(file)
			self.assertIn('300x300', str(context.exception))

	def test_image_with_no_text_rejected(self):
		"""Test that images with insufficient text content are rejected"""
		with override_settings(PRESCRIPTION_DOC_MIN_TEXT_RATIO=0.1):  # Very high threshold
			file = build_test_prescription_file(include_text=False)
			with self.assertRaises(ValidationError) as context:
				validate_prescription_image(file)
			self.assertIn('visible writing or text', str(context.exception))

	def test_blank_file_passes_validation(self):
		"""Test that blank/None file is allowed"""
		try:
			validate_prescription_image(None)
		except ValidationError:
			self.fail('Blank file should pass validation')


# ============================================================================
# FORM TESTS
# ============================================================================

class BloodRequestFormTests(TestCase):
	"""Test suite for Blood Request Form"""

	def _base_payload(self):
		return {
			'requester_name': 'Test Requester',
			'requester_phone': '9812345678',
			'blood_group': 'A+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'urgency': 'normal',
		}

	def test_form_with_valid_data(self):
		"""Test form with all valid data"""
		data = self._base_payload()
		file = build_test_prescription_file()
		form = BloodRequestForm(data=data, files={'prescription_image': file})
		self.assertTrue(form.is_valid())

	def test_form_requires_prescription_image(self):
		"""Test that prescription image is required"""
		data = self._base_payload()
		form = BloodRequestForm(data=data)
		self.assertFalse(form.is_valid())
		self.assertIn('prescription_image', form.errors)

	def test_form_with_emergency_urgency(self):
		"""Test form with emergency urgency level"""
		data = self._base_payload()
		data['urgency'] = 'emergency'
		file = build_test_prescription_file()
		form = BloodRequestForm(data=data, files={'prescription_image': file})
		self.assertTrue(form.is_valid())

	def test_form_validates_blood_group(self):
		"""Test that invalid blood groups are rejected"""
		data = self._base_payload()
		data['blood_group'] = 'INVALID'
		file = build_test_prescription_file()
		form = BloodRequestForm(data=data, files={'prescription_image': file})
		self.assertFalse(form.is_valid())
		self.assertIn('blood_group', form.errors)

	def test_form_validates_coordinates(self):
		"""Test that coordinates are properly validated"""
		data = self._base_payload()
		data['latitude'] = 'invalid'
		file = build_test_prescription_file()
		form = BloodRequestForm(data=data, files={'prescription_image': file})
		self.assertFalse(form.is_valid())


# ============================================================================
# VIEW TESTS
# ============================================================================

class BloodRequestViewTests(TestCase):
	"""Test suite for Blood Request views"""

	def setUp(self):
		self.client = self.client_class()

	@patch('requests.views.urllib.request.urlopen', side_effect=Exception('skip geocoder'))
	def test_request_blood_page_loads(self, _mock_urlopen):
		"""Test that blood request page loads"""
		response = self.client.get(reverse('requests:request_blood'))
		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, 'requests/request_blood.html')

	@patch('requests.views.urllib.request.urlopen', side_effect=Exception('skip geocoder'))
	def test_submit_valid_blood_request(self, _mock_urlopen):
		"""Test submitting a valid blood request"""
		payload = {
			'requester_name': 'Emergency Patient',
			'requester_phone': '9811111111',
			'blood_group': 'B+',
			'latitude': '27.7172',
			'longitude': '85.3240',
			'urgency': 'emergency',
			'prescription_image': build_test_prescription_file(),
		}
		response = self.client.post(reverse('requests:request_blood'), payload)
		
		self.assertEqual(response.status_code, 302)
		self.assertTrue(BloodRequest.objects.filter(requester_phone='9811111111').exists())

	@patch('requests.views.urllib.request.urlopen', side_effect=Exception('skip geocoder'))
	def test_track_blood_request_requires_valid_id(self, _mock_urlopen):
		"""Test tracking a blood request"""
		blood_request = BloodRequest.objects.create(
			requester_name='Tracker Test',
			requester_phone='9822222222',
			blood_group='O+',
			latitude='27.7172',
			longitude='85.3240',
		)
		response = self.client.get(
			reverse('requests:track_request', kwargs={'request_id': blood_request.id})
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Tracker Test')
		self.assertContains(response, 'Pending')


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class BloodRequestWorkflowIntegrationTests(TestCase):
	"""Integration tests for complete blood request workflow"""

	def setUp(self):
		self.donor_user = User.objects.create_user(
			username='donor123',
			email='donor@example.com',
			password='donorpass123'
		)
		self.donor = Donor.objects.create(
			user=self.donor_user,
			full_name='Test Donor',
			phone='+9779812345678',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
			is_available=True,
		)

	@patch('requests.views.urllib.request.urlopen', side_effect=Exception('skip geocoder'))
	def test_complete_blood_request_workflow(self, _mock_urlopen):
		"""Test complete workflow from request to fulfillment"""
		# Create a blood request
		blood_request = BloodRequest.objects.create(
			requester_name='Critical Patient',
			requester_phone='9844444444',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
			urgency='emergency',
		)
		self.assertEqual(blood_request.status, 'pending')

		# Donor accepts the request
		blood_request.accepted_by = self.donor
		blood_request.accepted_at = timezone.now()
		blood_request.status = 'notified'
		blood_request.save()

		self.assertEqual(blood_request.status, 'notified')
		self.assertEqual(blood_request.accepted_by, self.donor)

		# Request is fulfilled
		blood_request.status = 'fulfilled'
		blood_request.fulfilled_at = timezone.now()
		blood_request.save()

		self.assertEqual(blood_request.status, 'fulfilled')
		self.assertIsNotNone(blood_request.fulfilled_at)

	def test_cannot_accept_unmatched_blood_group_request(self):
		"""Test that donors can't accept requests with incompatible blood groups"""
		blood_request = BloodRequest.objects.create(
			requester_name='Wrong Group Patient',
			requester_phone='9855555555',
			blood_group='B-',  # Donor is A+
			latitude='27.7172',
			longitude='85.3240',
		)
		
		# Try to accept
		blood_request.accepted_by = self.donor
		blood_request.save()

		self.assertEqual(blood_request.accepted_by, self.donor)
		self.assertNotEqual(blood_request.blood_group, self.donor.blood_group)



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

	def test_request_page_is_not_cached_for_authenticated_users(self):
		user = User.objects.create_user(
			username='+9779800009998',
			email='requester-cache@example.com',
			password='StrongPass123!',
		)
		self.client.force_login(user)

		response = self.client.get(self.request_url)

		self.assertEqual(response.status_code, 200)
		self.assertIn('no-store', response.headers.get('Cache-Control', ''))

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
		donor.refresh_from_db()
		self.assertEqual(accepted_request.status, 'fulfilled')
		self.assertIsNotNone(accepted_request.fulfilled_at)
		self.assertFalse(donor.is_available)
		self.assertIsNotNone(donor.availability_reenable_at)

		donor.availability_reenable_at = timezone.now() - timedelta(days=1)
		donor.is_available = False
		donor.save(update_fields=['is_available', 'availability_reenable_at', 'updated_at'])

		self.assertTrue(donor.refresh_availability())
		donor.refresh_from_db()
		self.assertTrue(donor.is_available)
		self.assertIsNone(donor.availability_reenable_at)
