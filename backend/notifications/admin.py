from django.contrib import admin

from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "notification_type", "is_read", "order", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "message", "user__phone", "user__full_name")
    autocomplete_fields = ("user", "order")
    list_select_related = ("user", "order")
    readonly_fields = ("created_at",)
