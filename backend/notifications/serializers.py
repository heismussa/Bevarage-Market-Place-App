from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(
        source="order.order_number", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "order",
            "order_number",
            "created_at",
        )
        read_only_fields = fields


class UnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class ReadAllSerializer(serializers.Serializer):
    updated = serializers.IntegerField(help_text="How many notifications were marked read.")
