from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.validators import validate_phone
from orders.models import Order, OrderItem, OrderStatusHistory
from orders.state_machine import ACTION_CHOICES, actor_for, allowed_actions
from payments.choices import CHECKOUT_PAYMENT_METHOD_CHOICES, PaymentMethod
from payments.models import Payment
from stores.models import Store


class CreateOrderSerializer(serializers.Serializer):
    """Only these fields are read. Prices, totals and statuses in the body are ignored."""

    address_id = serializers.IntegerField(min_value=1)
    payment_method = serializers.ChoiceField(choices=CHECKOUT_PAYMENT_METHOD_CHOICES)
    payer_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Mobile-money number for the payment prompt. Defaults to the account phone.",
    )
    notes = serializers.CharField(max_length=500, required=False, allow_null=True, allow_blank=True)

    def validate_payer_phone(self, value):
        if value:
            validate_phone(value)
        return value or None


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )


class AdminCancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, help_text="Shown to the customer.")


class OrderStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ("id", "store_name", "logo", "phone")
        read_only_fields = fields


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "unit", "quantity", "unit_price", "subtotal")
        read_only_fields = fields


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_role = serializers.SerializerMethodField(
        help_text="Role of the user who made the change; null means the system."
    )

    class Meta:
        model = OrderStatusHistory
        fields = ("from_status", "status", "changed_at", "changed_by_role", "notes")
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_changed_by_role(self, entry):
        return entry.changed_by.role if entry.changed_by else None


class PaymentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "payment_method", "payment_status", "amount", "currency", "payer_phone")
        read_only_fields = fields


class OrderListSerializer(serializers.ModelSerializer):
    store = OrderStoreSerializer(read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "store",
            "order_status",
            "payment_status",
            "total_amount",
            "item_count",
            "ordered_at",
        )
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    store = OrderStoreSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)
    payment = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField(
        help_text="Actions the current user may take now, e.g. ['cancel']."
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "store",
            "order_status",
            "payment_status",
            "status_reason",
            "delivery_address",
            "delivery_phone",
            "delivery_latitude",
            "delivery_longitude",
            "subtotal_amount",
            "delivery_fee",
            "total_amount",
            "notes",
            "items",
            "status_history",
            "payment",
            "allowed_actions",
            "ordered_at",
            "updated_at",
        )
        read_only_fields = fields

    @extend_schema_field(PaymentSummarySerializer(allow_null=True))
    def get_payment(self, order):
        payments = list(order.payments.all())
        latest = max(payments, key=lambda p: (p.created_at, p.pk), default=None)
        return PaymentSummarySerializer(latest).data if latest else None

    @extend_schema_field(
        serializers.ListField(child=serializers.ChoiceField(choices=ACTION_CHOICES))
    )
    def get_allowed_actions(self, order):
        request = self.context.get("request")
        actor = actor_for(request.user) if request else None
        return allowed_actions(order.order_status, actor) if actor else []


# --- Store owner ----------------------------------------------------------------------


class OrderCustomerSerializer(serializers.Serializer):
    full_name = serializers.CharField(source="user.full_name")
    phone = serializers.CharField(source="user.phone")


class OwnerOrderListSerializer(serializers.ModelSerializer):
    customer = OrderCustomerSerializer(read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        read_only=True,
        allow_null=True,
        help_text="Method of the latest payment attempt.",
    )

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "customer",
            "order_status",
            "payment_status",
            "payment_method",
            "total_amount",
            "item_count",
            "ordered_at",
        )
        read_only_fields = fields


class OwnerOrderDetailSerializer(OrderDetailSerializer):
    customer = OrderCustomerSerializer(read_only=True)

    class Meta(OrderDetailSerializer.Meta):
        fields = ("id", "order_number", "customer", *OrderDetailSerializer.Meta.fields[2:])
        read_only_fields = fields


class TransitionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Required for reject and cancel. Shown to the customer.",
    )


class DailySalesSerializer(serializers.Serializer):
    date = serializers.DateField()
    orders = serializers.IntegerField(help_text="COMPLETED orders placed that day.")
    sales = serializers.DecimalField(max_digits=14, decimal_places=2)


class LowStockItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    stock_quantity = serializers.IntegerField()
    low_stock_threshold = serializers.IntegerField()
    availability_status = serializers.CharField()


class DashboardSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    total_sales = serializers.DecimalField(
        max_digits=14, decimal_places=2, help_text="Sum of total_amount of COMPLETED orders."
    )
    low_stock_count = serializers.IntegerField()
    low_stock_items = LowStockItemSerializer(many=True, help_text="Lowest stock first, max 10.")
    sales_last_7_days = DailySalesSerializer(many=True)
    recent_orders = OwnerOrderListSerializer(many=True, help_text="Newest 5 orders.")


class TopProductSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    product_name = serializers.CharField()
    quantity_sold = serializers.IntegerField()
    sales = serializers.DecimalField(max_digits=14, decimal_places=2)


class AnalyticsSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=14, decimal_places=2)
    daily_sales = DailySalesSerializer(many=True)
    top_products = TopProductSerializer(many=True, help_text="Top 10 by quantity sold.")


class AnalyticsQuerySerializer(serializers.Serializer):
    """?from=YYYY-MM-DD&to=YYYY-MM-DD. Defaults to the last 30 days; max 366 days."""

    MAX_DAYS = 366
    DEFAULT_DAYS = 30

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = serializers.DateField(required=False, help_text="First day, inclusive.")
        fields["to"] = serializers.DateField(required=False, help_text="Last day, inclusive.")
        return fields

    def validate(self, attrs):
        end = attrs.get("to") or timezone.localdate()
        start = attrs.get("from") or end - timedelta(days=self.DEFAULT_DAYS - 1)
        if start > end:
            raise serializers.ValidationError({"to": ["to must be on or after from."]})
        if (end - start).days + 1 > self.MAX_DAYS:
            raise serializers.ValidationError(
                {"from": [f"The range can be at most {self.MAX_DAYS} days."]}
            )
        return {"date_from": start, "date_to": end}
