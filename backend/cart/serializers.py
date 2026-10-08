from rest_framework import serializers

from catalog.models import ProductUnit


class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class AddCartItemQuerySerializer(serializers.Serializer):
    replace = serializers.BooleanField(
        required=False,
        default=False,
        help_text="true empties a cart that holds another store's products before adding.",
    )


class CartStoreSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    store_name = serializers.CharField()
    logo = serializers.ImageField(allow_null=True)
    status = serializers.CharField()
    delivery_fee = serializers.DecimalField(max_digits=12, decimal_places=2)


class CartLineSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="item.id")
    product_id = serializers.IntegerField(source="item.product_id")
    name = serializers.CharField(source="item.product.name")
    image = serializers.ImageField(source="item.product.image", allow_null=True)
    unit = serializers.ChoiceField(source="item.product.unit", choices=ProductUnit.choices)
    unit_price = serializers.DecimalField(
        source="item.product.price",
        max_digits=12,
        decimal_places=2,
        help_text="Current product price. Totals always use this.",
    )
    price_when_added = serializers.DecimalField(
        source="item.unit_price", max_digits=12, decimal_places=2
    )
    quantity = serializers.IntegerField(source="item.quantity")
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    price_changed = serializers.BooleanField()
    available = serializers.BooleanField()
    max_available = serializers.IntegerField()
    counted_in_total = serializers.BooleanField(
        help_text="False when the line cannot be bought now; it is left out of the subtotal."
    )


class CartWarningSerializer(serializers.Serializer):
    code = serializers.ChoiceField(
        choices=["STORE_CLOSED", "PRODUCT_UNAVAILABLE", "INSUFFICIENT_STOCK", "PRICE_CHANGED"]
    )
    message = serializers.CharField()
    item_id = serializers.IntegerField(allow_null=True)


class CartSerializer(serializers.Serializer):
    store = CartStoreSerializer(allow_null=True)
    items = CartLineSerializer(source="lines", many=True)
    item_count = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    warnings = CartWarningSerializer(many=True)

    def get_item_count(self, summary) -> int:
        return sum(line.item.quantity for line in summary.lines)
