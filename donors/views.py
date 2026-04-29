import random
import time
import urllib.parse
import urllib.request
import json
from django.core.paginator import Paginator

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.utils import timezone
from django.shortcuts import redirect, render
from django.urls import reverse
from django.db import transaction

from .forms import DonorRegistrationForm, EmailOtpVerificationForm
from .models import Donor
from .utils import BLOOD_GROUP_ORDER, can_donate_to, haversine_km
from requests.models import BloodRequest


User = get_user_model()
OTP_SESSION_KEY = 'donor_registration_otp'
OTP_TTL_SECONDS = 300
NEARBY_REQUEST_RADIUS_KM = 200.0
MAX_NEARBY_REQUESTS = 20


def _infer_city_from_coordinates(latitude: float, longitude: float) -> str:
	# Approximate city inference for Kathmandu Valley bounds.
	if 27.64 <= latitude <= 27.79 and 85.27 <= longitude <= 85.42:
		return 'Kathmandu'
	if 27.63 <= latitude <= 27.73 and 85.28 <= longitude <= 85.39:
		return 'Lalitpur'
	if 27.64 <= latitude <= 27.72 and 85.38 <= longitude <= 85.46:
		return 'Bhaktapur'
	return 'Other'


def _send_email_otp(email: str, otp: str) -> None:
	subject = 'Blood Bank donor registration OTP'
	message = f'Your OTP is {otp}. It expires in 5 minutes.'
	from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@bloodbank.local')
	send_mail(subject, message, from_email, [email], fail_silently=False)


def _get_nearby_requests_for_donor(donor: Donor, max_distance_km: float = NEARBY_REQUEST_RADIUS_KM):
	nearby_requests = []
	pending_requests = BloodRequest.objects.filter(
		status='pending',
		accepted_by__isnull=True,
	).exclude(requester_user=donor.user)

	for pending_request in pending_requests:
		if not can_donate_to(donor.blood_group, pending_request.blood_group):
			continue
		distance_km = haversine_km(
			float(pending_request.latitude),
			float(pending_request.longitude),
			float(donor.latitude),
			float(donor.longitude),
		)
		if distance_km <= max_distance_km:
			nearby_requests.append(
				{
					'request': pending_request,
					'distance_km': distance_km,
					'urgency_rank': 0 if pending_request.urgency == 'emergency' else 1,
				}
			)

	nearby_requests.sort(key=lambda item: (item['urgency_rank'], item['distance_km']))
	return nearby_requests[:MAX_NEARBY_REQUESTS]


def register_donor(request):
	otp_required = False
	otp_form = EmailOtpVerificationForm()

	if request.method == 'POST':
		action = request.POST.get('action', 'send_otp')

		if action == 'verify_otp':
			pending = request.session.get(OTP_SESSION_KEY)
			if not pending:
				messages.error(request, 'OTP session expired. Please submit the form again.')
				form = DonorRegistrationForm()
			else:
				form = DonorRegistrationForm(pending['form_data'])
				otp_required = True
				otp_form = EmailOtpVerificationForm(request.POST)

				if otp_form.is_valid():
					current_time = int(time.time())
					if current_time > pending['expires_at']:
						request.session.pop(OTP_SESSION_KEY, None)
						messages.error(request, 'OTP has expired. Please request a new OTP.')
					elif otp_form.cleaned_data['otp'] != pending['otp']:
						messages.error(request, 'Invalid OTP. Please try again.')
					elif form.is_valid():
						with transaction.atomic():
							donor = form.save(commit=False)
							user = User.objects.create_user(
								username=form.cleaned_data['phone'],
								first_name=form.cleaned_data['full_name'],
								email=form.cleaned_data['email'],
								password=form.cleaned_data['password1'],
							)
							donor.user = user
							donor.save()
							login(request, user, backend='donors.backends.EmailOrPhoneBackend')
						request.session.pop(OTP_SESSION_KEY, None)
						messages.success(
							request,
							'Congratulations on signing up! Thank you for thinking of giving back to society through blood donation.',
						)
						return redirect('requests:home')
					else:
						messages.error(request, 'Submitted registration data is no longer valid. Please try again.')
		else:
			form = DonorRegistrationForm(request.POST)
			if form.is_valid():
				otp = f'{random.randint(0, 999999):06d}'
				expires_at = int(time.time()) + OTP_TTL_SECONDS
				form_data = {
					'full_name': form.cleaned_data['full_name'],
					'phone': form.cleaned_data['phone'],
					'blood_group': form.cleaned_data['blood_group'],
					'latitude': str(form.cleaned_data['latitude']),
					'longitude': str(form.cleaned_data['longitude']),
					'is_available': 'on' if form.cleaned_data.get('is_available') else '',
					'email': form.cleaned_data['email'],
					'password1': form.cleaned_data['password1'],
					'password2': form.cleaned_data['password2'],
				}
				request.session[OTP_SESSION_KEY] = {
					'otp': otp,
					'expires_at': expires_at,
					'form_data': form_data,
				}

				try:
					_send_email_otp(form.cleaned_data['email'], otp)
					otp_required = True
					otp_form = EmailOtpVerificationForm()
					messages.success(request, '📧 Verification code sent! Check your email and enter the code below.')
				except Exception as e:
					request.session.pop(OTP_SESSION_KEY, None)
					messages.error(request, f'Could not send OTP email: {str(e)}. Please try again.')
			else:
				otp_required = False
	else:
		form = DonorRegistrationForm()
		request.session.pop(OTP_SESSION_KEY, None)

	return render(
		request,
		'donors/register.html',
		{
			'form': form,
			'otp_form': otp_form,
			'otp_required': otp_required,
		},
	)


@login_required
def profile(request):
	donor = Donor.objects.filter(user=request.user).first()
	nearby_requests_count = 0
	location_parts = {
		'city': '',
		'district': '',
		'country': '',
	}

	if donor is None:
		messages.info(request, 'No donor profile is linked to this account yet.')
	else:
		donor.refresh_availability()
		if request.method == 'POST' and request.POST.get('action') == 'toggle_availability':
			donor.is_available = not donor.is_available
			donor.availability_reenable_at = None
			donor.save(update_fields=['is_available', 'availability_reenable_at', 'updated_at'])
			state = 'ON' if donor.is_available else 'OFF'
			messages.success(request, f'Availability turned {state}.')
			return redirect('donors:profile')

		nearby_requests_count = len(_get_nearby_requests_for_donor(donor))

		try:
			query = urllib.parse.urlencode(
				{
					'lat': donor.latitude,
					'lon': donor.longitude,
					'format': 'jsonv2',
					'addressdetails': 1,
				}
			)
			url = f'https://nominatim.openstreetmap.org/reverse?{query}'
			request_obj = urllib.request.Request(
				url,
				headers={'User-Agent': 'bloodbank-app/1.0'},
			)
			with urllib.request.urlopen(request_obj, timeout=3) as response:
				payload = json.loads(response.read().decode('utf-8'))

			address = payload.get('address', {})
			location_parts = {
				'city': address.get('city') or address.get('town') or address.get('village') or '',
				'district': address.get('state_district') or address.get('county') or address.get('state') or '',
				'country': address.get('country') or '',
			}
		except Exception:
			location_parts = {
				'city': '',
				'district': '',
				'country': '',
			}

	return render(
		request,
		'donors/profile.html',
		{
			'donor': donor,
			'location_parts': location_parts,
			'nearby_requests_count': nearby_requests_count,
			'nearby_radius_km': int(NEARBY_REQUEST_RADIUS_KM),
		},
	)


@login_required
def incoming_requests(request):
	donor = Donor.objects.filter(user=request.user).first()
	if donor is None:
		messages.info(request, 'No donor profile is linked to this account yet.')
		return redirect('donors:profile')

	donor.refresh_availability()
	selected_distance_km = NEARBY_REQUEST_RADIUS_KM
	raw_selected_distance = request.GET.get('max_distance_km') or request.POST.get('max_distance_km')
	if raw_selected_distance is not None:
		try:
			selected_distance_km = float(raw_selected_distance)
		except (TypeError, ValueError):
			selected_distance_km = NEARBY_REQUEST_RADIUS_KM

	selected_distance_km = max(1.0, min(NEARBY_REQUEST_RADIUS_KM, selected_distance_km))
	selected_blood_group = (request.GET.get('blood_group') or '').strip()
	selected_city = (request.GET.get('city') or '').strip()
	compatible_blood_groups = [
		group for group in BLOOD_GROUP_ORDER
		if can_donate_to(donor.blood_group, group)
	]
	if selected_blood_group and selected_blood_group not in compatible_blood_groups:
		selected_blood_group = ''

	if request.method == 'POST' and request.POST.get('action') == 'accept_request':
		donor.refresh_availability()
		request_id = request.POST.get('request_id')
		incoming_request_record = BloodRequest.objects.filter(id=request_id).first()

		if incoming_request_record is None:
			messages.error(request, 'The selected blood request does not exist.')
		elif incoming_request_record.requester_user_id == request.user.id:
			messages.error(request, 'You cannot accept a blood request created from your own account.')
		elif not can_donate_to(donor.blood_group, incoming_request_record.blood_group):
			messages.error(request, 'Your blood group is not compatible with this request.')
		elif incoming_request_record.status != 'pending' or incoming_request_record.accepted_by_id is not None:
			messages.warning(request, 'This request has already been accepted by another donor.')
		elif not donor.is_available:
			messages.error(request, 'Turn your availability ON before accepting a request.')
		else:
			distance_km = haversine_km(
				float(incoming_request_record.latitude),
				float(incoming_request_record.longitude),
				float(donor.latitude),
				float(donor.longitude),
			)
			if distance_km > selected_distance_km:
				messages.error(request, 'Only nearby requests can be accepted from this page.')
			else:
				incoming_request_record.status = 'notified'
				incoming_request_record.accepted_by = donor
				incoming_request_record.accepted_at = timezone.now()
				incoming_request_record.requester_notification = (
					f"Donor {donor.full_name} ({donor.phone}) accepted your request at "
					f"{incoming_request_record.accepted_at.strftime('%Y-%m-%d %H:%M')}."
				)
				incoming_request_record.save(
					update_fields=['status', 'accepted_by', 'accepted_at', 'requester_notification']
				)
				messages.success(request, 'Request accepted. Please contact the requester immediately.')

		incoming_requests_url = reverse('donors:incoming_requests')
		return redirect(f'{incoming_requests_url}?max_distance_km={selected_distance_km:g}')

	if request.method == 'POST' and request.POST.get('action') == 'cancel_accept':
		donor.refresh_availability()
		request_id = request.POST.get('request_id')
		accepted_request_record = BloodRequest.objects.filter(
			id=request_id,
			accepted_by=donor,
		).first()

		if accepted_request_record is None:
			messages.error(request, 'No accepted request found for your account.')
		elif accepted_request_record.status != 'notified':
			messages.warning(request, 'Only in-progress accepted requests can be cancelled.')
		else:
			accepted_request_record.status = 'pending'
			accepted_request_record.accepted_by = None
			accepted_request_record.accepted_at = None
			accepted_request_record.requester_notification = (
				'Donor acceptance was cancelled. Your request is open for other donors again.'
			)
			accepted_request_record.save(
				update_fields=['status', 'accepted_by', 'accepted_at', 'requester_notification']
			)
			messages.success(request, 'Acceptance cancelled. The request is now open again.')

		incoming_requests_url = reverse('donors:incoming_requests')
		return redirect(f'{incoming_requests_url}?max_distance_km={selected_distance_km:g}')

	accepted_requests = []
	accepted_request_records = BloodRequest.objects.filter(
		accepted_by=donor,
		status='notified',
	).order_by('-accepted_at', '-created_at')

	for accepted_request in accepted_request_records:
		accepted_distance_km = haversine_km(
			float(accepted_request.latitude),
			float(accepted_request.longitude),
			float(donor.latitude),
			float(donor.longitude),
		)
		accepted_requests.append(
			{
				'request': accepted_request,
				'distance_km': accepted_distance_km,
				'city': _infer_city_from_coordinates(
					float(accepted_request.latitude),
					float(accepted_request.longitude),
				),
			}
		)

	nearby_requests = _get_nearby_requests_for_donor(donor, max_distance_km=selected_distance_km)

	for item in nearby_requests:
		item['city'] = _infer_city_from_coordinates(
			float(item['request'].latitude),
			float(item['request'].longitude),
		)

	if selected_blood_group:
		nearby_requests = [
			item for item in nearby_requests
			if item['request'].blood_group == selected_blood_group
		]

	if selected_city:
		nearby_requests = [
			item for item in nearby_requests
			if item.get('city', '').lower() == selected_city.lower()
		]

	city_options = sorted({item.get('city', 'Other') for item in nearby_requests})
	paginator = Paginator(nearby_requests, 6)
	page_obj = paginator.get_page(request.GET.get('page') or 1)

	return render(
		request,
		'donors/incoming_requests.html',
		{
			'donor': donor,
			'accepted_requests': accepted_requests,
			'nearby_requests': page_obj.object_list,
			'page_obj': page_obj,
			'nearby_radius_km': int(NEARBY_REQUEST_RADIUS_KM),
			'selected_distance_km': selected_distance_km,
			'selected_blood_group': selected_blood_group,
			'blood_group_options': compatible_blood_groups,
			'selected_city': selected_city,
			'city_options': city_options,
		},
	)
