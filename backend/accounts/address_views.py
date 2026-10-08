from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.response import Response

from accounts import services
from accounts.filters import AddressFilter
from accounts.models import Address
from accounts.permissions import IsCustomer
from accounts.serializers import AddressSerializer
from core.ownership import OwnerField, OwnerScopedQuerysetMixin, get_customer_profile
from core.schema import standard_errors

ADDRESS_EXAMPLE = {
    "id": 1,
    "address_name": "Home",
    "address_line": "Plot 12, Haile Selassie Road",
    "city": "Dar es Salaam",
    "area": "Msasani",
    "latitude": "-6.748900",
    "longitude": "39.276800",
    "phone": "+255712345678",
    "is_default": True,
    "created_at": "2026-10-08T12:00:00+03:00",
    "updated_at": "2026-10-08T12:00:00+03:00",
}

ADDRESS_REQUEST_EXAMPLE = OpenApiExample(
    "New address",
    value={
        "address_name": "Home",
        "address_line": "Plot 12, Haile Selassie Road",
        "city": "Dar es Salaam",
        "area": "Msasani",
        "latitude": "-6.748900",
        "longitude": "39.276800",
        "phone": "+255712345678",
    },
    request_only=True,
)


class CustomerAddressMixin(OwnerScopedQuerysetMixin):
    permission_classes = [IsCustomer]
    owner_field = OwnerField.CUSTOMER
    queryset = Address.objects.all()
    serializer_class = AddressSerializer


@extend_schema_view(
    get=extend_schema(
        tags=["addresses"],
        summary="List my addresses",
        description="The default address comes first.",
        responses={200: AddressSerializer(many=True), **standard_errors(400, 401, 403)},
        examples=[OpenApiExample("Address", value=ADDRESS_EXAMPLE, response_only=True)],
    ),
    post=extend_schema(
        tags=["addresses"],
        summary="Add an address",
        description="The first address a customer adds becomes the default automatically.",
        request=AddressSerializer,
        responses={201: AddressSerializer, **standard_errors(400, 401, 403)},
        examples=[
            ADDRESS_REQUEST_EXAMPLE,
            OpenApiExample(
                "Created", value=ADDRESS_EXAMPLE, response_only=True, status_codes=["201"]
            ),
        ],
    ),
)
class AddressListCreateView(CustomerAddressMixin, generics.ListCreateAPIView):
    filterset_class = AddressFilter
    search_fields = ("address_name", "address_line", "area")
    ordering_fields = ("address_name", "created_at")
    ordering = ("-is_default", "address_name", "id")

    def perform_create(self, serializer):
        customer = get_customer_profile(self.request.user)
        serializer.instance = services.create_address(customer, serializer.validated_data)


@extend_schema_view(
    get=extend_schema(
        tags=["addresses"],
        summary="My address detail",
        responses={200: AddressSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Address", value=ADDRESS_EXAMPLE, response_only=True)],
    ),
    patch=extend_schema(
        tags=["addresses"],
        summary="Edit my address",
        description="is_default cannot be changed here; use set-default.",
        request=AddressSerializer,
        responses={200: AddressSerializer, **standard_errors(400, 401, 403, 404)},
        examples=[
            OpenApiExample("Rename", value={"address_name": "Office"}, request_only=True),
            OpenApiExample("Updated", value=ADDRESS_EXAMPLE, response_only=True),
        ],
    ),
    delete=extend_schema(
        tags=["addresses"],
        summary="Delete my address",
        description=(
            "If the deleted address was the default, the most recently added remaining "
            "address becomes the default. Past orders keep their address snapshot."
        ),
        responses={204: None, **standard_errors(401, 403, 404)},
    ),
)
class AddressDetailView(CustomerAddressMixin, generics.RetrieveUpdateDestroyAPIView):
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_update(self, serializer):
        serializer.instance = services.update_address(
            serializer.instance, serializer.validated_data
        )

    def perform_destroy(self, instance):
        services.delete_address(instance)


@extend_schema_view(
    post=extend_schema(
        tags=["addresses"],
        summary="Make this my default address",
        description="Atomically clears the previous default.",
        request=None,
        responses={200: AddressSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Default", value=ADDRESS_EXAMPLE, response_only=True)],
    ),
)
class AddressSetDefaultView(CustomerAddressMixin, generics.GenericAPIView):
    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        address = services.set_default_address(self.get_object())
        return Response(self.get_serializer(address).data, status=status.HTTP_200_OK)
