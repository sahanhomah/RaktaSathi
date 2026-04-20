from django.contrib import admin

from .models import BloodRequest


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
	list_display = (
		'requester_name',
		'blood_group',
		'urgency',
		'status',
		'accepted_by',
		'accepted_at',
		'created_at',
	)
	list_filter = ('blood_group', 'urgency', 'status')
	search_fields = ('requester_name', 'requester_phone')
