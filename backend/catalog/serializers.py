from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from catalog.models import AvailabilityStatus, Category, CategoryStatus, Product
from core.validators import validate_image_upload


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description")
        read_only_fields = fields


class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")
        read_only_fields = fields


class PublicProductSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.store_name", read_only=True)
    category = CategorySummarySerializer(read_only=True)
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "store",
            "store_name",
            "category",
            "name",
            "description",
            "image",
            "unit",
            "price",
            "stock_quantity",
            "availability_status",
            "in_stock",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_in_stock(self, product):
        return product.stock_quantity > 0


class OwnerProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    category_detail = CategorySummarySerializer(source="category", read_only=True)
    is_low_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "store",
            "category",
            "category_detail",
            "name",
            "description",
            "image",
            "unit",
            "price",
            "stock_quantity",
            "low_stock_threshold",
            "availability_status",
            "is_low_stock",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "store", "created_at", "updated_at")
        extra_kwargs = {
            "stock_quantity": {"min_value": 0},
            "low_stock_threshold": {"min_value": 0},
            "availability_status": {
                "help_text": (
                    "Owners may set AVAILABLE or UNAVAILABLE. OUT_OF_STOCK is derived from "
                    "stock_quantity."
                )
            },
        }

    @extend_schema_field(serializers.BooleanField())
    def get_is_low_stock(self, product):
        return product.stock_quantity <= product.low_stock_threshold

    def validate_category(self, category):
        if category.status != CategoryStatus.ACTIVE:
            raise serializers.ValidationError("This category is not active.")
        return category

    def validate_price(self, price):
        if price <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        return price

    def validate_availability_status(self, value):
        if value == AvailabilityStatus.OUT_OF_STOCK:
            raise serializers.ValidationError(
                "OUT_OF_STOCK is set automatically when stock_quantity is 0."
            )
        return value

    def validate_image(self, value):
        validate_image_upload(value)
        return value

    def validate(self, attrs):
        store = self.instance.store if self.instance else self.context["store"]
        name = attrs.get("name")
        if name is not None:
            duplicates = Product.objects.filter(store=store, name=name, deleted_at__isnull=True)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"name": ["This store already has a product with this name."]}
                )
        return attrs


class StockUpdateSerializer(serializers.Serializer):
    stock_quantity = serializers.IntegerField(min_value=0)
