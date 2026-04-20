from django.contrib import admin

from .models import Donor


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
	list_display = ('full_name', 'blood_group', 'phone', 'is_available', 'updated_at')
	list_filter = ('blood_group', 'is_available')
	search_fields = ('full_name', 'phone')
