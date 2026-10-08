from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.validators import validate_phone
from orders.models import Order, OrderItem, OrderStatusHistory
from orders.state_machine import Action, actor_for, allowed_actions
from payments.choices import CHECKOUT_PAYMENT_METHOD_CHOICES
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
        serializers.ListField(child=serializers.ChoiceField(choices=[a.value for a in Action]))
    )
    def get_allowed_actions(self, order):
        request = self.context.get("request")
        actor = actor_for(request.user) if request else None
        return allowed_actions(order.order_status, actor) if actor else []
