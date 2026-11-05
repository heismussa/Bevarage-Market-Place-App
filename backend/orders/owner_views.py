from functools import cached_property

from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
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
from core.errors import ApiError, ErrorCode
from core.ownership import OwnerField, OwnerScopedQuerysetMixin, get_owned_or_404
from core.schema import standard_errors
from orders import reports, services
from orders.filters import OwnerOrderFilter
from orders.models import Order, OrderStatus
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
from payments.choices import PaymentStatus
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

COMPARISON_EXAMPLE = {
    "current": {
        "date_from": "2026-10-02",
        "date_to": "2026-10-08",
        "total_orders": 27,
        "total_sales": "121500.00",
    },
    "previous": {
        "date_from": "2026-09-25",
        "date_to": "2026-10-01",
        "total_orders": 24,
        "total_sales": "112500.00",
    },
    "orders_change_percent": "12.5",
    "sales_change_percent": "8.0",
}

PAYMENT_METHODS_EXAMPLE = [
    {"payment_method": "MPESA", "orders": 12, "sales": "58500.00", "orders_percent": "48.0"},
    {"payment_method": "TIGO_PESA", "orders": 3, "sales": "18000.00", "orders_percent": "12.0"},
    {"payment_method": "AIRTEL_MONEY", "orders": 0, "sales": "0.00", "orders_percent": "0.0"},
    {"payment_method": "CASH", "orders": 10, "sales": "45000.00", "orders_percent": "40.0"},
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
    "last_7_days_vs_previous": COMPARISON_EXAMPLE,
    "payment_methods_last_7_days": PAYMENT_METHODS_EXAMPLE,
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
    "payment_methods": PAYMENT_METHODS_EXAMPLE,
    "compared_to_previous": {
        "current": {
            "date_from": "2026-10-07",
            "date_to": "2026-10-08",
            "total_orders": 5,
            "total_sales": "15500.00",
        },
        "previous": {
            "date_from": "2026-10-05",
            "date_to": "2026-10-06",
            "total_orders": 4,
            "total_sales": "12400.00",
        },
        "orders_change_percent": "25.0",
        "sales_change_percent": "25.0",
    },
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


CSV_EXAMPLE = (
    "order_number,ordered_at,order_status,payment_status,payment_method,customer_name,"
    "customer_phone,item_count,subtotal_amount,delivery_fee,total_amount,delivery_address\r\n"
    "BDM-20261008-0007,2026-10-08 13:05,COMPLETED,SUCCESS,MPESA,Asha Juma,+255712345678,"
    '2,4500.00,1500.00,6000.00,"Plot 12, Haile Selassie Road"\r\n'
)


@extend_schema_view(
    get=extend_schema(
        tags=["owner-orders"],
        summary="Export my store's orders as CSV",
        description=(
            "Same filters, search and ordering as the orders list, without pagination. Returns "
            "a UTF-8 CSV file (opens in Excel) with Content-Disposition: attachment. Times are "
            f"local. At most {reports.EXPORT_MAX_ROWS} orders; narrow the dates if you get "
            "VALIDATION_ERROR. Do not send Accept: text/csv; send no Accept header or */*."
        ),
        parameters=[
            OpenApiParameter("status", str, enum=OrderStatus.values),
            OpenApiParameter("payment_status", str, enum=PaymentStatus.values),
            OpenApiParameter("date_from", OpenApiTypes.DATE, description="Local day, inclusive."),
            OpenApiParameter("date_to", OpenApiTypes.DATE, description="Local day, inclusive."),
            OpenApiParameter("search", str, description="Order number or customer name."),
            OpenApiParameter(
                "ordering",
                str,
                description="ordered_at, -ordered_at, total_amount or -total_amount.",
            ),
        ],
        responses={
            (200, "text/csv"): OpenApiTypes.STR,
            **standard_errors(400, 401, 403, 404),
        },
        examples=[
            OpenApiExample("CSV", value=CSV_EXAMPLE, response_only=True, media_type="text/csv")
        ],
    ),
)
class OwnerStoreOrderExportView(OwnerStoreOrderListView):
    pagination_class = None

    def list(self, request, *args, **kwargs):
        orders = list(self.filter_queryset(self.get_queryset())[: reports.EXPORT_MAX_ROWS + 1])
        if len(orders) > reports.EXPORT_MAX_ROWS:
            raise ApiError(
                ErrorCode.VALIDATION_ERROR,
                f"Too many orders to export (more than {reports.EXPORT_MAX_ROWS}). "
                "Choose a shorter date range.",
                details={"date_from": ["Choose a shorter date range."]},
            )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        filename = f"orders-{self.store.pk}-{timezone.localdate():%Y%m%d}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        reports.write_orders_csv(response, orders)
        return response


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
            "total_orders and total_sales are all time; total_sales sums total_amount of "
            "COMPLETED orders. sales_last_7_days has one row per local day ending today, "
            "including days without sales. last_7_days_vs_previous compares those 7 days with "
            "the 7 days before (for '+12% vs last week'). payment_methods_last_7_days splits "
            "the COMPLETED orders of those 7 days by payment method."
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
            "30 days ending today; at most 366 days. Sales, top products and payment_methods "
            "count COMPLETED orders placed in the range. compared_to_previous compares the "
            "range with the equally long period just before it."
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
