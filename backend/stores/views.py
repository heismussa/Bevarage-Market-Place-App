from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny

from accounts.permissions import IsStoreOwner
from core.ownership import OwnerField, OwnerScopedQuerysetMixin, get_store_owner_profile
from core.schema import standard_errors
from stores import services
from stores.filters import StoreFilter
from stores.models import Store
from stores.serializers import (
    CoordinatesQuerySerializer,
    OwnerStoreSerializer,
    PublicStoreSerializer,
)

COORDINATE_PARAMETERS = [
    OpenApiParameter(
        "lat",
        OpenApiTypes.DOUBLE,
        description="Customer latitude. Send with lng to get distance_km.",
    ),
    OpenApiParameter(
        "lng",
        OpenApiTypes.DOUBLE,
        description="Customer longitude. Send with lat to get distance_km.",
    ),
]

PUBLIC_STORE_EXAMPLE = {
    "id": 1,
    "store_name": "ABC Drinks",
    "description": "Soft drinks, water, and beer from Kariakoo.",
    "logo": "http://localhost:8000/media/stores/logos/abc.png",
    "location": "Kariakoo Market, Uhuru Street, Dar es Salaam",
    "city": "Dar es Salaam",
    "area": "Kariakoo",
    "latitude": "-6.823490",
    "longitude": "39.274530",
    "phone": "+255713000001",
    "email": "abc@example.com",
    "status": "OPEN",
    "delivery_fee": "2000.00",
    "distance_km": 8.47,
}

OWNER_STORE_EXAMPLE = {
    **{key: value for key, value in PUBLIC_STORE_EXAMPLE.items() if key != "distance_km"},
    "is_active": True,
    "created_at": "2026-10-08T12:00:00+03:00",
    "updated_at": "2026-10-08T12:00:00+03:00",
}

OWNER_STORE_REQUEST_EXAMPLE = OpenApiExample(
    "Store profile",
    value={
        "store_name": "ABC Drinks",
        "location": "Kariakoo Market, Uhuru Street, Dar es Salaam",
        "city": "Dar es Salaam",
        "area": "Kariakoo",
        "latitude": "-6.823490",
        "longitude": "39.274530",
        "phone": "+255713000001",
        "status": "OPEN",
        "delivery_fee": "2000.00",
    },
    request_only=True,
)


def requested_ordering_terms(request):
    raw = request.query_params.get("ordering", "")
    return {term.strip().lstrip("-") for term in raw.split(",") if term.strip()}


class PublicStoreQuerysetMixin:
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PublicStoreSerializer

    def get_queryset(self):
        queryset = Store.objects.filter(is_active=True)
        if getattr(self, "swagger_fake_view", False):
            return queryset

        coordinates = CoordinatesQuerySerializer(data=self.request.query_params)
        coordinates.is_valid(raise_exception=True)
        if "lat" in coordinates.validated_data:
            return services.annotate_distance(
                queryset,
                coordinates.validated_data["lat"],
                coordinates.validated_data["lng"],
            )

        if "distance" in requested_ordering_terms(self.request):
            raise serializers.ValidationError(
                {"ordering": ["lat and lng are required to order by distance."]}
            )
        return queryset


@extend_schema_view(
    get=extend_schema(
        tags=["stores"],
        summary="List active stores",
        description=(
            "Only active stores. Send lat and lng to get distance_km and to allow "
            "ordering=distance (nearest first). Stores without coordinates sort last."
        ),
        parameters=COORDINATE_PARAMETERS,
        responses={200: PublicStoreSerializer(many=True), **standard_errors(400)},
        examples=[OpenApiExample("Store", value=PUBLIC_STORE_EXAMPLE, response_only=True)],
    ),
)
class PublicStoreListView(PublicStoreQuerysetMixin, generics.ListAPIView):
    filterset_class = StoreFilter
    search_fields = ("store_name", "description", "location", "city", "area")
    ordering_fields = ("store_name", "delivery_fee", "created_at", "distance")
    ordering = ("store_name", "id")


@extend_schema_view(
    get=extend_schema(
        tags=["stores"],
        summary="Store detail",
        parameters=COORDINATE_PARAMETERS,
        responses={200: PublicStoreSerializer, **standard_errors(400, 404)},
        examples=[OpenApiExample("Store", value=PUBLIC_STORE_EXAMPLE, response_only=True)],
    ),
)
class PublicStoreDetailView(PublicStoreQuerysetMixin, generics.RetrieveAPIView):
    pass


@extend_schema_view(
    get=extend_schema(
        tags=["owner-stores"],
        summary="List my stores",
        responses={200: OwnerStoreSerializer(many=True), **standard_errors(401, 403)},
        examples=[OpenApiExample("Store", value=OWNER_STORE_EXAMPLE, response_only=True)],
    ),
    post=extend_schema(
        tags=["owner-stores"],
        summary="Create a store",
        description="Send multipart/form-data to upload a logo (JPEG, PNG or WebP, max 2 MB).",
        request=OwnerStoreSerializer,
        responses={201: OwnerStoreSerializer, **standard_errors(400, 401, 403)},
        examples=[
            OWNER_STORE_REQUEST_EXAMPLE,
            OpenApiExample(
                "Created", value=OWNER_STORE_EXAMPLE, response_only=True, status_codes=["201"]
            ),
        ],
    ),
)
class OwnerStoreListCreateView(OwnerScopedQuerysetMixin, generics.ListCreateAPIView):
    queryset = Store.objects.all()
    serializer_class = OwnerStoreSerializer
    permission_classes = [IsStoreOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    owner_field = OwnerField.STORE_OWNER
    search_fields = ("store_name", "city", "area")
    ordering_fields = ("store_name", "created_at")
    ordering = ("store_name", "id")

    def perform_create(self, serializer):
        owner = get_store_owner_profile(self.request.user)
        serializer.instance = services.create_store(owner, serializer.validated_data)


@extend_schema_view(
    get=extend_schema(
        tags=["owner-stores"],
        summary="My store detail",
        responses={200: OwnerStoreSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Store", value=OWNER_STORE_EXAMPLE, response_only=True)],
    ),
    patch=extend_schema(
        tags=["owner-stores"],
        summary="Update my store",
        description=(
            "Profile, OPEN/CLOSED status, delivery_fee and logo. is_active is controlled by "
            "admins and is ignored here."
        ),
        request=OwnerStoreSerializer,
        responses={200: OwnerStoreSerializer, **standard_errors(400, 401, 403, 404)},
        examples=[
            OpenApiExample("Open the store", value={"status": "OPEN"}, request_only=True),
            OpenApiExample("Updated", value=OWNER_STORE_EXAMPLE, response_only=True),
        ],
    ),
)
class OwnerStoreDetailView(OwnerScopedQuerysetMixin, generics.RetrieveUpdateAPIView):
    queryset = Store.objects.all()
    serializer_class = OwnerStoreSerializer
    permission_classes = [IsStoreOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    owner_field = OwnerField.STORE_OWNER
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        serializer.instance = services.update_store(serializer.instance, serializer.validated_data)
