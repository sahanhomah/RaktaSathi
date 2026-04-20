from django.contrib import admin

from .models import SmsNotification


@admin.register(SmsNotification)
class SmsNotificationAdmin(admin.ModelAdmin):
    list_display = ('phone', 'status', 'blood_request', 'donor', 'created_at')
    list_filter = ('status',)
    search_fields = ('phone',)
    readonly_fields = ('created_at',)
