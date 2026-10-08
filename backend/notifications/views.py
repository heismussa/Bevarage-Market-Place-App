from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.schema import standard_errors
from notifications import services
from notifications.filters import NotificationFilter
from notifications.models import Notification
from notifications.serializers import (
    NotificationSerializer,
    ReadAllSerializer,
    UnreadCountSerializer,
)

NOTIFICATION_EXAMPLE = {
    "id": 12,
    "notification_type": "ORDER_ACCEPTED",
    "title": "Order accepted",
    "message": "Kariakoo Drinks accepted order BDM-20261008-0007.",
    "is_read": False,
    "order": 7,
    "order_number": "BDM-20261008-0007",
    "created_at": "2026-10-08T13:10:00+03:00",
}


class OwnNotificationsMixin:
    """Every signed-in role has notifications; each user only ever sees their own."""

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).select_related("order")


@extend_schema_view(
    get=extend_schema(
        tags=["notifications"],
        summary="My notifications",
        description="Newest first. Filter with ?is_read=false for unread only.",
        responses={200: NotificationSerializer(many=True), **standard_errors(400, 401)},
        examples=[
            OpenApiExample(
                "Page",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [NOTIFICATION_EXAMPLE],
                },
                response_only=True,
            )
        ],
    ),
)
class NotificationListView(OwnNotificationsMixin, generics.ListAPIView):
    filterset_class = NotificationFilter


@extend_schema_view(
    get=extend_schema(
        tags=["notifications"],
        summary="Unread notification count",
        description="For the badge on the bell icon.",
        responses={200: UnreadCountSerializer, **standard_errors(401)},
        examples=[OpenApiExample("Count", value={"unread_count": 3}, response_only=True)],
    ),
)
class UnreadCountView(OwnNotificationsMixin, generics.GenericAPIView):
    serializer_class = UnreadCountSerializer

    def get(self, request, *args, **kwargs):
        return Response({"unread_count": services.unread_count(request.user)})


@extend_schema_view(
    post=extend_schema(
        tags=["notifications"],
        summary="Mark one notification read",
        description="Safe to repeat. Another user's notification returns 404.",
        request=None,
        responses={200: NotificationSerializer, **standard_errors(401, 404)},
        examples=[
            OpenApiExample(
                "Read", value={**NOTIFICATION_EXAMPLE, "is_read": True}, response_only=True
            )
        ],
    ),
)
class MarkReadView(OwnNotificationsMixin, generics.GenericAPIView):
    def post(self, request, *args, **kwargs):
        notification = services.mark_read(self.get_object())
        return Response(self.get_serializer(notification).data)


@extend_schema_view(
    post=extend_schema(
        tags=["notifications"],
        summary="Mark all my notifications read",
        request=None,
        responses={200: ReadAllSerializer, **standard_errors(401)},
        examples=[OpenApiExample("Done", value={"updated": 3}, response_only=True)],
    ),
)
class ReadAllView(OwnNotificationsMixin, generics.GenericAPIView):
    serializer_class = ReadAllSerializer

    def post(self, request, *args, **kwargs):
        return Response({"updated": services.mark_all_read(request.user)})
