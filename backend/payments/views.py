from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from core.errors import ErrorCode
from core.ownership import OwnerField, OwnerScopedQuerysetMixin
from core.schema import error_response, standard_errors
from orders.models import Order
from payments import services
from payments.serializers import (
    PaymentInitiationSerializer,
    PaymentSerializer,
    PayOrderSerializer,
    WebhookAckSerializer,
)
from payments.throttles import PaymentInitiationThrottle

PAYMENT_EXAMPLE = {
    "id": 31,
    "payment_method": "MPESA",
    "payment_status": "PROCESSING",
    "amount": "5000.00",
    "currency": "TZS",
    "payer_phone": "+255712345678",
    "transaction_reference": "MOCK-3F9A1C0B7D2E4A6B8C1D",
    "payment_time": None,
    "created_at": "2026-10-08T13:06:00+03:00",
}

PAY_CONFLICT = error_response(
    "Payment cannot start: PAYMENT_NOT_ALLOWED (cash, already paid, order not PENDING) or "
    "PAYMENT_IN_PROGRESS (a prompt is waiting for approval)",
    ErrorCode.PAYMENT_IN_PROGRESS,
    "A payment prompt is already waiting for approval.",
    {"payment_id": 31},
)


class CustomerOrderMixin(OwnerScopedQuerysetMixin):
    permission_classes = [IsCustomer]
    owner_field = OwnerField.CUSTOMER
    queryset = Order.objects.all()


@extend_schema_view(
    post=extend_schema(
        tags=["payments"],
        summary="Pay for my order (mobile money)",
        description=(
            "Sends a payment prompt for a PENDING order, or retries after a FAILED attempt. "
            "This never marks the payment SUCCESS: poll GET /orders/{id}/payment/ until the "
            "provider's webhook confirms it. Rate-limited per customer."
        ),
        request=PayOrderSerializer,
        responses={
            200: PaymentInitiationSerializer,
            **standard_errors(400, 401, 403, 404, 429),
            409: PAY_CONFLICT,
        },
        examples=[
            OpenApiExample("Pay", value={"payer_phone": "+255712345678"}, request_only=True),
            OpenApiExample(
                "Prompt sent",
                value={
                    "payment": PAYMENT_EXAMPLE,
                    "instructions": (
                        "A payment prompt for 5000.00 TZS was sent to +255712345678. "
                        "Enter your PIN to approve."
                    ),
                },
                response_only=True,
            ),
        ],
    ),
)
class PayOrderView(CustomerOrderMixin, generics.GenericAPIView):
    serializer_class = PayOrderSerializer
    throttle_classes = [PaymentInitiationThrottle]
    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment, result = services.initiate_payment(
            order, serializer.validated_data.get("payer_phone")
        )
        return Response(
            {"payment": PaymentSerializer(payment).data, "instructions": result.instructions},
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        tags=["payments"],
        summary="Payment status of my order",
        description="The latest payment attempt. Poll this after POST /pay/.",
        responses={200: PaymentSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Payment", value=PAYMENT_EXAMPLE, response_only=True)],
    ),
)
class OrderPaymentView(CustomerOrderMixin, generics.GenericAPIView):
    serializer_class = PaymentSerializer
    http_method_names = ["get", "options"]

    def get(self, request, *args, **kwargs):
        payment = services.latest_payment(self.get_object())
        if payment is None:
            raise NotFound("This order has no payment.")
        return Response(self.get_serializer(payment).data)


class PaymentWebhookView(APIView):
    """Called by payment providers, not by the app. Authenticity comes from the signature."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["payments"],
        summary="Payment provider webhook",
        description=(
            "Server-to-server only. The raw body must carry a valid provider signature "
            "(mock provider: HMAC-SHA256 hex in X-Mock-Signature). Repeated deliveries of "
            "the same transaction_reference are acknowledged without changing anything. "
            "A paid amount different from the order total marks the payment FAILED and "
            "records REFUND_REQUIRED on the order history."
        ),
        parameters=[
            OpenApiParameter(
                "provider", str, OpenApiParameter.PATH, description="Provider name, e.g. mock"
            )
        ],
        request=OpenApiTypes.OBJECT,
        responses={
            200: WebhookAckSerializer,
            **standard_errors(400, 404),
            401: error_response(
                "Signature missing or wrong",
                ErrorCode.INVALID_SIGNATURE,
                "Webhook signature is missing or invalid.",
            ),
        },
        examples=[
            OpenApiExample(
                "Mock success",
                value={
                    "reference": "MOCK-3F9A1C0B7D2E4A6B8C1D",
                    "status": "SUCCESS",
                    "amount": "5000.00",
                    "currency": "TZS",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Acknowledged",
                value={"received": True, "payment_status": "SUCCESS"},
                response_only=True,
            ),
        ],
    )
    def post(self, request, provider):
        payment = services.handle_webhook(provider, request.body, request.headers)
        return Response({"received": True, "payment_status": payment.payment_status})
