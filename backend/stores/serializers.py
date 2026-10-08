from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from accounts.validators import validate_phone
from core.validators import validate_image_upload
from stores.models import Store

COORDINATE_KWARGS = {
    "latitude": {"min_value": Decimal("-90"), "max_value": Decimal("90")},
    "longitude": {"min_value": Decimal("-180"), "max_value": Decimal("180")},
}


class CoordinatesQuerySerializer(serializers.Serializer):
    """Optional ?lat=&lng= query parameters. Both or neither."""

    lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    lng = serializers.FloatField(required=False, min_value=-180, max_value=180)

    def validate(self, attrs):
        if ("lat" in attrs) != ("lng" in attrs):
            raise serializers.ValidationError({"lat": ["lat and lng must be sent together."]})
        return attrs


class PublicStoreSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Store
        fields = (
            "id",
            "store_name",
            "description",
            "logo",
            "location",
            "city",
            "area",
            "latitude",
            "longitude",
            "phone",
            "email",
            "status",
            "delivery_fee",
            "distance_km",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_km(self, store):
        distance = getattr(store, "distance", None)
        return None if distance is None else round(distance, 2)


class OwnerStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = (
            "id",
            "store_name",
            "description",
            "logo",
            "location",
            "city",
            "area",
            "latitude",
            "longitude",
            "phone",
            "email",
            "status",
            "is_active",
            "delivery_fee",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_active", "created_at", "updated_at")
        extra_kwargs = {
            **COORDINATE_KWARGS,
            "delivery_fee": {"min_value": Decimal("0")},
        }

    def validate_phone(self, value):
        validate_phone(value)
        return value

    def validate_logo(self, value):
        validate_image_upload(value)
        return value
