from django.db.models import Count, Prefetch
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, IsCustomer
from core.errors import ErrorCode
from core.ownership import OwnerField, OwnerScopedQuerysetMixin, get_customer_profile
from core.schema import error_response, standard_errors
from orders import services
from orders.filters import CustomerOrderFilter
from orders.models import Order, OrderStatusHistory
from orders.serializers import (
    AdminCancelOrderSerializer,
    CancelOrderSerializer,
    CreateOrderSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)
from orders.state_machine import Action

ORDER_DETAIL_EXAMPLE = {
    "id": 42,
    "order_number": "BDM-20261008-0007",
    "store": {"id": 1, "store_name": "ABC Drinks", "logo": None, "phone": "+255713000000"},
    "order_status": "PENDING",
    "payment_status": "PENDING",
    "status_reason": None,
    "delivery_address": "Plot 12, Haile Selassie Road, Msasani, Dar es Salaam",
    "delivery_phone": "+255712345678",
    "delivery_latitude": "-6.748900",
    "delivery_longitude": "39.276800",
    "subtotal_amount": "3000.00",
    "delivery_fee": "2000.00",
    "total_amount": "5000.00",
    "notes": "Call when you arrive",
    "items": [
        {
            "id": 90,
            "product": 1,
            "product_name": "Coca-Cola 500ml",
            "unit": "BOTTLE",
            "quantity": 2,
            "unit_price": "1500.00",
            "subtotal": "3000.00",
        }
    ],
    "status_history": [
        {
            "from_status": None,
            "status": "PENDING",
            "changed_at": "2026-10-08T13:05:00+03:00",
            "changed_by_role": "CUSTOMER",
            "notes": None,
        }
    ],
    "payment": {
        "id": 31,
        "payment_method": "MPESA",
        "payment_status": "PENDING",
        "amount": "5000.00",
        "currency": "TZS",
        "payer_phone": "+255712345678",
    },
    "allowed_actions": ["cancel"],
    "ordered_at": "2026-10-08T13:05:00+03:00",
    "updated_at": "2026-10-08T13:05:00+03:00",
}

ORDER_LIST_EXAMPLE = {
    "id": 42,
    "order_number": "BDM-20261008-0007",
    "store": {"id": 1, "store_name": "ABC Drinks", "logo": None, "phone": "+255713000000"},
    "order_status": "PENDING",
    "payment_status": "PENDING",
    "total_amount": "5000.00",
    "item_count": 1,
    "ordered_at": "2026-10-08T13:05:00+03:00",
}

INVALID_TRANSITION_RESPONSE = error_response(
    "The order's current status does not allow this action",
    ErrorCode.INVALID_TRANSITION,
    "You cannot cancel an order that is ACCEPTED.",
    {"order_status": "ACCEPTED", "action": "cancel", "allowed_actions": []},
)


def order_detail_queryset():
    history = OrderStatusHistory.objects.select_related("changed_by").order_by("changed_at", "id")
    return Order.objects.select_related("store", "customer__user").prefetch_related(
        "items", "payments", Prefetch("status_history", queryset=history)
    )


def detail_response(
    order, request, response_status=status.HTTP_200_OK, serializer_class=OrderDetailSerializer
):
    order = order_detail_queryset().get(pk=order.pk)
    return Response(
        serializer_class(order, context={"request": request}).data, status=response_status
    )


class CustomerOrderMixin(OwnerScopedQuerysetMixin):
    permission_classes = [IsCustomer]
    owner_field = OwnerField.CUSTOMER


@extend_schema_view(
    get=extend_schema(
        tags=["orders"],
        summary="List my orders",
        description="Newest first. Filter with ?status=PENDING (any order status).",
        responses={200: OrderListSerializer(many=True), **standard_errors(400, 401, 403)},
        examples=[OpenApiExample("Order", value=ORDER_LIST_EXAMPLE, response_only=True)],
    ),
    post=extend_schema(
        tags=["orders"],
        summary="Place an order from my cart",
        description=(
            "Checks out the whole cart in one transaction: prices, subtotal, delivery fee and "
            "total are recomputed from the database (anything else in the body is ignored), "
            "stock is taken, a PENDING payment is created and the cart is emptied. Sending "
            "the same request twice fails the second time with EMPTY_CART."
        ),
        request=CreateOrderSerializer,
        responses={
            201: OrderDetailSerializer,
            **standard_errors(400, 401, 403),
            409: error_response(
                "Checkout blocked: EMPTY_CART, STORE_CLOSED, PRODUCT_UNAVAILABLE or "
                "INSUFFICIENT_STOCK. details.problems lists every affected line.",
                ErrorCode.INSUFFICIENT_STOCK,
                "Only 1 of Coca-Cola 500ml left in stock.",
                {
                    "problems": [
                        {
                            "code": "INSUFFICIENT_STOCK",
                            "product_id": 1,
                            "name": "Coca-Cola 500ml",
                            "requested": 2,
                            "max_available": 1,
                        }
                    ]
                },
            ),
        },
        examples=[
            OpenApiExample(
                "Pay with M-Pesa",
                value={
                    "address_id": 3,
                    "payment_method": "MPESA",
                    "payer_phone": "+255712345678",
                    "notes": "Call when you arrive",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Pay cash", value={"address_id": 3, "payment_method": "CASH"}, request_only=True
            ),
            OpenApiExample(
                "Created", value=ORDER_DETAIL_EXAMPLE, response_only=True, status_codes=["201"]
            ),
        ],
    ),
)
class OrderListCreateView(CustomerOrderMixin, generics.ListCreateAPIView):
    queryset = Order.objects.all()
    filterset_class = CustomerOrderFilter
    search_fields = ("order_number", "store__store_name")
    ordering_fields = ("ordered_at", "total_amount")
    ordering = ("-ordered_at", "-id")

    def get_queryset(self):
        return super().get_queryset().select_related("store").annotate(item_count=Count("items"))

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateOrderSerializer
        return OrderListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.create_order(
            get_customer_profile(request.user), **serializer.validated_data
        )
        return detail_response(order, request, status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=["orders"],
        summary="My order detail",
        description=(
            "Items, the status timeline, the latest payment and allowed_actions (the "
            "actions the current user may take now)."
        ),
        responses={200: OrderDetailSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Order", value=ORDER_DETAIL_EXAMPLE, response_only=True)],
    ),
)
class OrderDetailView(CustomerOrderMixin, generics.RetrieveAPIView):
    queryset = order_detail_queryset()
    serializer_class = OrderDetailSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["orders"],
        summary="Cancel my order",
        description="Only while the order is PENDING. Stock is returned to the store.",
        request=CancelOrderSerializer,
        responses={
            200: OrderDetailSerializer,
            **standard_errors(400, 401, 403, 404),
            409: INVALID_TRANSITION_RESPONSE,
        },
        examples=[
            OpenApiExample("Cancel", value={"reason": "Ordered by mistake"}, request_only=True),
        ],
    ),
)
class OrderCancelView(CustomerOrderMixin, generics.GenericAPIView):
    queryset = Order.objects.all()
    serializer_class = CancelOrderSerializer
    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.transition_order(
            order, Action.CANCEL, request.user, serializer.validated_data.get("reason")
        )
        return detail_response(order, request)


@extend_schema_view(
    post=extend_schema(
        tags=["admin-orders"],
        summary="Cancel any order (admin)",
        description=(
            "Cancels any order that is not yet COMPLETED, REJECTED or CANCELLED. The reason "
            "is required and shown to the customer. Stock is returned to the store."
        ),
        request=AdminCancelOrderSerializer,
        responses={
            200: OrderDetailSerializer,
            **standard_errors(400, 401, 403, 404),
            409: INVALID_TRANSITION_RESPONSE,
        },
        examples=[
            OpenApiExample(
                "Cancel", value={"reason": "Customer called support"}, request_only=True
            ),
        ],
    ),
)
class AdminOrderCancelView(generics.GenericAPIView):
    permission_classes = [IsAdminRole]
    queryset = Order.objects.all()
    serializer_class = AdminCancelOrderSerializer
    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.transition_order(
            order, Action.CANCEL, request.user, serializer.validated_data["reason"]
        )
        return detail_response(order, request)
