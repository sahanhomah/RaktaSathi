from django.test import TestCase

# Create your tests here.
			requester_name='Test Requester',
			requester_phone='9811111111',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
		)

	def test_sms_notification_creation(self):
		"""Test basic SMS notification creation"""
		notification = SmsNotification.objects.create(
			phone='+9779812345678',
			status='sent',
			gateway_response='Message sent successfully',
			blood_request=self.blood_request,
			donor=self.donor,
		)
		self.assertEqual(notification.phone, '+9779812345678')
		self.assertEqual(notification.status, 'sent')

	def test_sms_notification_string_representation(self):
		"""Test SMS notification __str__ method"""
		notification = SmsNotification.objects.create(
			phone='+9779812345678',
			status='sent',
			gateway_response='Success',
			blood_request=self.blood_request,
			donor=self.donor,
		)
		self.assertEqual(str(notification), 'SMS to +9779812345678 [sent]')

	def test_sms_notification_status_choices(self):
		"""Test all SMS status choices"""
		statuses = ['sent', 'failed', 'demo']
		for i, status in enumerate(statuses):
			notification = SmsNotification.objects.create(
				phone=f'+977981234567{i}',
				status=status,
				gateway_response=f'Gateway response for {status}',
				blood_request=self.blood_request,
				donor=self.donor,
			)
			self.assertEqual(notification.status, status)

	def test_sms_notification_cascade_delete_with_blood_request(self):
		"""Test that SMS notifications are deleted when blood request is deleted"""
		notification = SmsNotification.objects.create(
			phone='+9779812345678',
			status='sent',
			gateway_response='Success',
			blood_request=self.blood_request,
			donor=self.donor,
		)
		self.assertEqual(SmsNotification.objects.count(), 1)
		
		self.blood_request.delete()
		self.assertEqual(SmsNotification.objects.count(), 0)

	def test_sms_notification_cascade_delete_with_donor(self):
		"""Test that SMS notifications are deleted when donor is deleted"""
		notification = SmsNotification.objects.create(
			phone='+9779812345678',
			status='sent',
			gateway_response='Success',
			blood_request=self.blood_request,
			donor=self.donor,
		)
		self.assertEqual(SmsNotification.objects.count(), 1)
		
		self.donor.delete()
		self.assertEqual(SmsNotification.objects.count(), 0)


# ============================================================================
# SERVICE TESTS
# ============================================================================

class SendSmsNotificationServiceTests(TestCase):
	"""Test suite for SMS notification service"""

	def setUp(self):
		self.donor = Donor.objects.create(
			full_name='SMS Test Donor',
			phone='+9779812345678',
			blood_group='B+',
			latitude='27.7172',
			longitude='85.3240',
		)
		self.blood_request = BloodRequest.objects.create(
			requester_name='SMS Test Requester',
			requester_phone='9822222222',
			blood_group='B+',
			latitude='27.7172',
			longitude='85.3240',
		)

	def test_send_sms_notification_creates_record(self):
		"""Test that SMS notification creates a database record"""
		message = 'Please consider donating blood urgently'
		
		notification = send_sms_notification(
			self.blood_request,
			self.donor,
			message
		)
		
		self.assertIsNotNone(notification.id)
		self.assertEqual(notification.phone, self.donor.phone)
		self.assertEqual(notification.donor, self.donor)
		self.assertEqual(notification.blood_request, self.blood_request)

	def test_send_sms_notification_status_is_demo(self):
		"""Test that SMS notification status is demo (stub service)"""
		message = 'Demo message'
		
		notification = send_sms_notification(
			self.blood_request,
			self.donor,
			message
		)
		
		self.assertEqual(notification.status, 'demo')
		self.assertIn('DEMO', notification.gateway_response)

	def test_send_sms_notification_records_message(self):
		"""Test that SMS message is recorded in gateway response"""
		message = 'Blood needed urgently at Hospital XYZ'
		
		notification = send_sms_notification(
			self.blood_request,
			self.donor,
			message
		)
		
		self.assertIn(message, notification.gateway_response)


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
		self.assertIn('Requester phone: 9801112233', email.body)
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

	def test_send_email_notification_skips_donor_without_user(self):
		"""Test that email is not sent if donor has no user account"""
		blood_request = BloodRequest.objects.create(
			requester_name='No User Test',
			requester_phone='9811111111',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
		)
		donor_no_user = Donor.objects.create(
			full_name='No User Donor',
			phone='+9779800000000',
			blood_group='A+',
			latitude='27.7172',
			longitude='85.3240',
		)
		
		result = send_email_notification_to_donor(
			blood_request,
			donor_no_user,
			5.0
		)
		
		self.assertFalse(result)
		self.assertEqual(len(mail.outbox), 0)

	def test_send_email_notification_includes_distance(self):
		"""Test that email includes distance information"""
		donor_user = User.objects.create_user(
			username='+9779809999999',
			email='distance@example.com',
			password='pass123'
		)
		donor = Donor.objects.create(
			user=donor_user,
			full_name='Distance Test Donor',
			phone='+9779809999999',
			blood_group='O+',
			latitude='27.7172',
			longitude='85.3240',
		)
		blood_request = BloodRequest.objects.create(
			requester_name='Distance Test',
			requester_phone='9899999999',
			blood_group='O+',
			latitude='27.7172',
			longitude='85.3240',
		)
		
		send_email_notification_to_donor(
			blood_request,
			donor,
			3.7
		)
		
		email = mail.outbox[0]
		self.assertIn('3.70 km', email.body)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class NotificationIntegrationTests(TestCase):
	"""Integration tests for notification system"""

	def setUp(self):
		self.donor_user = User.objects.create_user(
			username='integrationdonor',
			email='integration@example.com',
			password='pass123'
		)
		self.donor = Donor.objects.create(
			user=self.donor_user,
			full_name='Integration Donor',
			phone='+9779812345678',
			blood_group='AB+',
			latitude='27.7172',
			longitude='85.3240',
		)

	def test_notification_workflow_for_matching_request(self):
		"""Test complete notification workflow for a new blood request"""
		blood_request = BloodRequest.objects.create(
			requester_name='Integration Requester',
			requester_phone='9844444444',
			blood_group='AB+',
			latitude='27.7172',
			longitude='85.3240',
			urgency='emergency',
		)
		
		# Send SMS notification
		sms_notification = send_sms_notification(
			blood_request,
			self.donor,
			f'Urgent blood request for {blood_request.blood_group} blood type'
		)
		
		# Verify SMS notification was created
		self.assertIsNotNone(sms_notification.id)
		self.assertEqual(sms_notification.blood_request, blood_request)
		self.assertEqual(sms_notification.donor, self.donor)
