from decimal import Decimal

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import Address, User, UserRole
from accounts.validators import validate_phone

REGISTRATION_ROLE_CHOICES = (
    (UserRole.CUSTOMER, UserRole.CUSTOMER.label),
    (UserRole.STORE_OWNER, UserRole.STORE_OWNER.label),
)


class RegisterSerializer(serializers.Serializer):
    """Public registration. ADMIN and DRIVER are not valid choices."""

    full_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    role = serializers.ChoiceField(choices=REGISTRATION_ROLE_CHOICES)

    def validate_phone(self, value):
        validate_phone(value)
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_email(self, value):
        if not value:
            return None
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate(self, attrs):
        candidate = User(
            phone=attrs["phone"],
            full_name=attrs["full_name"],
            email=attrs.get("email"),
            role=attrs["role"],
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            phone=validated_data["phone"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            email=validated_data.get("email"),
            role=validated_data["role"],
        )


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "full_name", "phone", "email", "role")
        read_only_fields = fields


class MeSerializer(serializers.ModelSerializer):
    """Profile of the authenticated user. role, is_staff, and is_active are fixed."""

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "phone",
            "email",
            "role",
            "is_staff",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "role",
            "is_staff",
            "is_active",
            "created_at",
            "updated_at",
        )
        extra_kwargs = {
            "email": {"allow_blank": True, "allow_null": True, "required": False},
        }

    def validate_email(self, value):
        if not value:
            return None
        return value.strip().lower()


class AddressSerializer(serializers.ModelSerializer):
    """is_default is read-only: the first address becomes default automatically and
    POST /addresses/{id}/set-default/ changes it."""

    class Meta:
        model = Address
        fields = (
            "id",
            "address_name",
            "address_line",
            "city",
            "area",
            "latitude",
            "longitude",
            "phone",
            "is_default",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "is_default", "created_at", "updated_at")
        extra_kwargs = {
            "latitude": {"min_value": Decimal("-90"), "max_value": Decimal("90")},
            "longitude": {"min_value": Decimal("-180"), "max_value": Decimal("180")},
        }

    def validate_phone(self, value):
        validate_phone(value)
        return value

    def validate(self, attrs):
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {"latitude": ["latitude and longitude must be sent together."]}
            )
        return attrs
