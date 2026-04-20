from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from donors.models import Donor
from donors.utils import can_donate_to, haversine_km
from notifications.services import send_email_notification_to_donor

from .forms import BloodRequestForm
from .models import BloodRequest


EMAIL_NOTIFICATION_RADIUS_KM = 5.0


def home(request):
	context = {
		'available_donors': Donor.objects.filter(is_available=True).count(),
		'total_requests': BloodRequest.objects.count(),
		'registered_donors': Donor.objects.count(),
		'lives_saved': BloodRequest.objects.filter(status='fulfilled').count(),
		'emergency_fulfilled': BloodRequest.objects.filter(status='fulfilled', urgency='emergency').count(),
	}
	return render(request, 'home.html', context)


@login_required
def request_blood(request):
	recommended = []
	request_record = None
	show_recommendations = True
	active_statuses = ['pending', 'notified']
	active_requests = BloodRequest.objects.filter(
		requester_user=request.user,
		status__in=active_statuses,
	).order_by('-created_at')

	if request.method == 'POST' and request.POST.get('action') == 'cancel_request':
		request_id = request.POST.get('request_id')
		request_to_cancel = BloodRequest.objects.filter(
			id=request_id,
			requester_user=request.user,
		).first()

		if request_to_cancel is None:
			messages.error(request, 'No matching request found for your account.')
		elif request_to_cancel.status in ['fulfilled', 'cancelled']:
			messages.info(request, 'This request is already completed or cancelled.')
		else:
			if request_to_cancel.prescription_image:
				request_to_cancel.prescription_image.delete(save=False)
				request_to_cancel.prescription_image = None
			request_to_cancel.status = 'cancelled'
			request_to_cancel.save(update_fields=['status', 'prescription_image'])
			messages.success(request, f'Request #{request_to_cancel.id} has been cancelled.')
		return redirect('requests:request')

	if request.method == 'POST' and request.POST.get('action') == 'complete_request':
		request_id = request.POST.get('request_id')
		request_to_complete = BloodRequest.objects.filter(
			id=request_id,
			requester_user=request.user,
		).first()

		if request_to_complete is None:
			messages.error(request, 'No matching request found for your account.')
		elif request_to_complete.status in ['fulfilled', 'cancelled']:
			messages.info(request, 'This request is already completed or cancelled.')
		elif request_to_complete.status != 'notified' or request_to_complete.accepted_by_id is None:
			messages.warning(request, 'Transaction can be completed only after a donor accepts your request.')
		else:
			request_to_complete.status = 'fulfilled'
			request_to_complete.fulfilled_at = timezone.now()
			request_to_complete.save(update_fields=['status', 'fulfilled_at'])
			messages.success(request, f'Request #{request_to_complete.id} marked as completed.')
		return redirect('requests:request')

	if request.method == 'POST' and request.POST.get('action') == 'create_request':
		if active_requests.exists():
			messages.info(request, 'You already have an active request. Track or complete it before creating a new one.')
			return redirect('requests:request')

		form = BloodRequestForm(request.POST, request.FILES)
		if form.is_valid():
			request_record = form.save(commit=False)
			request_record.requester_user = request.user
			request_record.save()
			eligible_matches = []
			eligible = Donor.objects.filter(is_available=True).exclude(user=request.user)
			for donor in eligible:
				if not can_donate_to(donor.blood_group, request_record.blood_group):
					continue
				distance_km = haversine_km(
					float(request_record.latitude),
					float(request_record.longitude),
					float(donor.latitude),
					float(donor.longitude),
				)
				eligible_matches.append({'donor': donor, 'distance_km': distance_km})

			eligible_matches.sort(key=lambda item: item['distance_km'])
			recommended = eligible_matches[:5]

			notified_count = 0
			for item in eligible_matches:
				if item['distance_km'] > EMAIL_NOTIFICATION_RADIUS_KM:
					break
				if send_email_notification_to_donor(request_record, item['donor'], item['distance_km']):
					notified_count += 1

			messages.success(
				request,
				f'Blood request submitted successfully. Email notifications sent to {notified_count} eligible donor(s) within {EMAIL_NOTIFICATION_RADIUS_KM:g} km.',
			)
			active_requests = BloodRequest.objects.filter(
				requester_user=request.user,
				status__in=active_statuses,
			).order_by('-created_at')
	else:
		form = BloodRequestForm()

	current_active_request = active_requests.first()

	return render(
		request,
		'requests/request_blood.html',
		{
			'form': form,
			'recommended': recommended,
			'request_record': request_record,
			'show_recommendations': show_recommendations,
			'active_requests': active_requests,
			'current_active_request': current_active_request,
		},
	)


def track_request(request):
	request_id = (request.GET.get('request_id') or request.POST.get('request_id') or '').strip()
	requester_phone = (request.GET.get('requester_phone') or request.POST.get('requester_phone') or '').strip()
	blood_request = None

	if request.method == 'POST' and request.POST.get('action') == 'complete_request':
		blood_request = BloodRequest.objects.filter(
			id=request_id,
			requester_phone=requester_phone,
		).first()
		if blood_request is None:
			messages.error(request, 'No matching request found. Check request ID and phone number.')
		elif blood_request.status != 'notified' or blood_request.accepted_by_id is None:
			messages.warning(request, 'This request is not in an accepted state yet.')
		else:
			blood_request.status = 'fulfilled'
			blood_request.fulfilled_at = timezone.now()
			blood_request.save(update_fields=['status', 'fulfilled_at'])
			messages.success(request, 'Transaction marked as completed. Thank you for confirming.')

	if blood_request is None and request_id and requester_phone:
		blood_request = BloodRequest.objects.filter(
			id=request_id,
			requester_phone=requester_phone,
		).first()
		if blood_request is None:
			messages.error(request, 'No matching request found. Check request ID and phone number.')

	return render(
		request,
		'requests/track_request.html',
		{
			'blood_request': blood_request,
			'request_id': request_id,
			'requester_phone': requester_phone,
		},
	)
