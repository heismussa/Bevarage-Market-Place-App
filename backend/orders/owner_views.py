from functools import cached_property

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStoreOwner
from core.ownership import OwnerField, OwnerScopedQuerysetMixin, get_owned_or_404
from core.schema import standard_errors
from orders import reports, services
from orders.filters import OwnerOrderFilter
from orders.models import Order
from orders.serializers import (
    AnalyticsQuerySerializer,
    AnalyticsSerializer,
    DashboardSerializer,
    OwnerOrderDetailSerializer,
    OwnerOrderListSerializer,
    TransitionSerializer,
)
from orders.views import (
    INVALID_TRANSITION_RESPONSE,
    ORDER_DETAIL_EXAMPLE,
    detail_response,
    order_detail_queryset,
)
from payments.services import visible_to_store_owner
from stores.models import Store

OWNER_ORDER_LIST_EXAMPLE = {
    "id": 42,
    "order_number": "BDM-20261008-0007",
    "customer": {"full_name": "Asha Juma", "phone": "+255712345678"},
    "order_status": "PENDING",
    "payment_status": "PENDING",
    "payment_method": "CASH",
    "total_amount": "5000.00",
    "item_count": 1,
    "ordered_at": "2026-10-08T13:05:00+03:00",
}

OWNER_ORDER_DETAIL_EXAMPLE = {
    "id": 42,
    "order_number": "BDM-20261008-0007",
    "customer": {"full_name": "Asha Juma", "phone": "+255712345678"},
    **{k: v for k, v in ORDER_DETAIL_EXAMPLE.items() if k not in ("id", "order_number")},
    "allowed_actions": ["accept", "reject"],
}

DAILY_EXAMPLE = [
    {"date": "2026-10-07", "orders": 3, "sales": "15500.00"},
    {"date": "2026-10-08", "orders": 0, "sales": "0.00"},
]

DASHBOARD_EXAMPLE = {
    "total_orders": 128,
    "pending_orders": 4,
    "total_sales": "842000.00",
    "low_stock_count": 2,
    "low_stock_items": [
        {
            "id": 7,
            "name": "Safari Lager 500ml",
            "stock_quantity": 2,
            "low_stock_threshold": 5,
            "availability_status": "AVAILABLE",
        }
    ],
    "sales_last_7_days": DAILY_EXAMPLE,
    "recent_orders": [OWNER_ORDER_LIST_EXAMPLE],
}

ANALYTICS_EXAMPLE = {
    "date_from": "2026-10-07",
    "date_to": "2026-10-08",
    "total_orders": 5,
    "completed_orders": 3,
    "pending_orders": 1,
    "total_sales": "15500.00",
    "daily_sales": DAILY_EXAMPLE,
    "top_products": [
        {
            "product_id": 1,
            "product_name": "Coca-Cola 500ml",
            "quantity_sold": 9,
            "sales": "13500.00",
        }
    ],
}


class OwnedStoreMixin:
    permission_classes = [IsStoreOwner]

    @cached_property
    def store(self):
        return get_owned_or_404(
            Store.objects.all(), OwnerField.STORE_OWNER, self.request.user, pk=self.kwargs["pk"]
        )


@extend_schema_view(
    get=extend_schema(
        tags=["owner-orders"],
        summary="List my store's orders",
        description=(
            "Newest first. date_from and date_to are local calendar days, both inclusive. "
            "search matches the order number or the customer's name. Cash orders appear at "
            "once; mobile-money orders appear only after payment_status is SUCCESS."
        ),
        responses={
            200: OwnerOrderListSerializer(many=True),
            **standard_errors(400, 401, 403, 404),
        },
        examples=[OpenApiExample("Order", value=OWNER_ORDER_LIST_EXAMPLE, response_only=True)],
    ),
)
class OwnerStoreOrderListView(OwnedStoreMixin, generics.ListAPIView):
    serializer_class = OwnerOrderListSerializer
    filterset_class = OwnerOrderFilter
    search_fields = ("order_number", "customer__user__full_name")
    ordering_fields = ("ordered_at", "total_amount")
    ordering = ("-ordered_at", "-id")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return visible_to_store_owner(reports.owner_order_queryset().filter(store=self.store))


class OwnerOrderMixin(OwnerScopedQuerysetMixin):
    """Unpaid non-cash orders do not exist for the store owner yet (404)."""

    permission_classes = [IsStoreOwner]
    owner_field = OwnerField.STORE_OF_OBJECT

    def get_queryset(self):
        return visible_to_store_owner(super().get_queryset())


@extend_schema_view(
    get=extend_schema(
        tags=["owner-orders"],
        summary="Order detail for my store",
        description=(
            "Customer name and phone, items, delivery location, order time, payment status, "
            "status history and allowed_actions for the store owner."
        ),
        responses={200: OwnerOrderDetailSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Order", value=OWNER_ORDER_DETAIL_EXAMPLE, response_only=True)],
    ),
)
class OwnerOrderDetailView(OwnerOrderMixin, generics.RetrieveAPIView):
    queryset = order_detail_queryset()
    serializer_class = OwnerOrderDetailSerializer


@extend_schema_view(
    post=extend_schema(
        tags=["owner-orders"],
        summary="Move an order to its next status",
        description=(
            "PENDING: accept or reject. ACCEPTED: prepare or cancel. PREPARING: ready or "
            "cancel. READY: complete. reason is required for reject and cancel and is shown "
            "to the customer. Rejecting or cancelling returns the stock."
        ),
        request=TransitionSerializer,
        responses={
            200: OwnerOrderDetailSerializer,
            **standard_errors(400, 401, 403, 404),
            409: INVALID_TRANSITION_RESPONSE,
        },
        examples=[
            OpenApiExample("Accept", value={"action": "accept"}, request_only=True),
            OpenApiExample(
                "Reject",
                value={"action": "reject", "reason": "Out of Safari crates"},
                request_only=True,
            ),
            OpenApiExample("Order", value=OWNER_ORDER_DETAIL_EXAMPLE, response_only=True),
        ],
    ),
)
class OwnerOrderTransitionView(OwnerOrderMixin, generics.GenericAPIView):
    queryset = Order.objects.all()
    serializer_class = TransitionSerializer
    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.transition_order(
            order,
            serializer.validated_data["action"],
            request.user,
            serializer.validated_data.get("reason"),
        )
        return detail_response(order, request, serializer_class=OwnerOrderDetailSerializer)


STORE_ID_PARAMETER = OpenApiParameter("pk", int, OpenApiParameter.PATH, description="Store id")


class OwnerStoreDashboardView(OwnedStoreMixin, APIView):
    @extend_schema(
        tags=["owner-dashboard"],
        summary="Store dashboard",
        description=(
            "total_sales sums total_amount of COMPLETED orders. sales_last_7_days has one row "
            "per local day ending today, including days without sales."
        ),
        parameters=[STORE_ID_PARAMETER],
        responses={200: DashboardSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Dashboard", value=DASHBOARD_EXAMPLE, response_only=True)],
    )
    def get(self, request, pk):
        data = reports.dashboard(self.store)
        return Response(DashboardSerializer(data, context={"request": request}).data)


class OwnerStoreAnalyticsView(OwnedStoreMixin, APIView):
    @extend_schema(
        tags=["owner-dashboard"],
        summary="Store analytics for a date range",
        description=(
            "?from=YYYY-MM-DD&to=YYYY-MM-DD, local days, both inclusive. Defaults to the last "
            "30 days ending today; at most 366 days. Sales and top products count COMPLETED "
            "orders placed in the range."
        ),
        parameters=[STORE_ID_PARAMETER, AnalyticsQuerySerializer],
        responses={200: AnalyticsSerializer, **standard_errors(400, 401, 403, 404)},
        examples=[OpenApiExample("Analytics", value=ANALYTICS_EXAMPLE, response_only=True)],
    )
    def get(self, request, pk):
        store = self.store
        query = AnalyticsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = reports.analytics(
            store, query.validated_data["date_from"], query.validated_data["date_to"]
        )
        return Response(AnalyticsSerializer(data).data)
