from functools import cached_property

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.permissions import IsStoreOwner
from catalog import services
from catalog.filters import OwnerProductFilter, PublicProductFilter
from catalog.models import Category, CategoryStatus, Product
from catalog.serializers import (
    CategorySerializer,
    OwnerProductSerializer,
    PublicProductSerializer,
    StockUpdateSerializer,
)
from core.ownership import OwnerField, OwnerScopedQuerysetMixin, get_owned_or_404
from core.schema import standard_errors
from stores.models import Store

CATEGORY_EXAMPLE = {"id": 1, "name": "Soda", "slug": "soda", "description": "Soda"}

PUBLIC_PRODUCT_EXAMPLE = {
    "id": 1,
    "store": 1,
    "store_name": "ABC Drinks",
    "category": {"id": 1, "name": "Soda", "slug": "soda"},
    "name": "Coca-Cola 500ml",
    "description": "Coca-Cola 500ml",
    "image": "http://localhost:8000/media/products/coca-cola.png",
    "unit": "BOTTLE",
    "price": "1500.00",
    "stock_quantity": 120,
    "availability_status": "AVAILABLE",
    "in_stock": True,
}

OWNER_PRODUCT_EXAMPLE = {
    "id": 1,
    "store": 1,
    "category": 1,
    "category_detail": {"id": 1, "name": "Soda", "slug": "soda"},
    "name": "Coca-Cola 500ml",
    "description": "Coca-Cola 500ml",
    "image": None,
    "unit": "BOTTLE",
    "price": "1500.00",
    "stock_quantity": 4,
    "low_stock_threshold": 5,
    "availability_status": "AVAILABLE",
    "is_low_stock": True,
    "created_at": "2026-10-08T12:00:00+03:00",
    "updated_at": "2026-10-08T12:00:00+03:00",
}

OWNER_PRODUCT_REQUEST_EXAMPLE = OpenApiExample(
    "New product",
    value={
        "category": 1,
        "name": "Coca-Cola 500ml",
        "unit": "BOTTLE",
        "price": "1500.00",
        "stock_quantity": 120,
        "low_stock_threshold": 5,
    },
    request_only=True,
)


def public_products():
    return Product.objects.filter(
        deleted_at__isnull=True,
        store__is_active=True,
        category__status=CategoryStatus.ACTIVE,
    ).select_related("store", "category")


@extend_schema_view(
    get=extend_schema(
        tags=["catalog"],
        summary="List active categories",
        responses={200: CategorySerializer(many=True)},
        examples=[OpenApiExample("Category", value=CATEGORY_EXAMPLE, response_only=True)],
    ),
)
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(status=CategoryStatus.ACTIVE)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    search_fields = ("name",)
    ordering_fields = ("name",)
    ordering = ("name",)


@extend_schema_view(
    get=extend_schema(
        tags=["catalog"],
        summary="List a store's products",
        description=(
            "Products of an active store. Soft-deleted products and products in inactive "
            "categories are never listed."
        ),
        responses={200: PublicProductSerializer(many=True), **standard_errors(400, 404)},
        examples=[OpenApiExample("Product", value=PUBLIC_PRODUCT_EXAMPLE, response_only=True)],
    ),
)
class StoreProductListView(generics.ListAPIView):
    serializer_class = PublicProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    filterset_class = PublicProductFilter
    search_fields = ("name", "description")
    ordering_fields = ("name", "price")
    ordering = ("name", "id")

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        store = get_object_or_404(Store, pk=self.kwargs["store_id"], is_active=True)
        return public_products().filter(store=store)


@extend_schema_view(
    get=extend_schema(
        tags=["catalog"],
        summary="Product detail",
        responses={200: PublicProductSerializer, **standard_errors(404)},
        examples=[OpenApiExample("Product", value=PUBLIC_PRODUCT_EXAMPLE, response_only=True)],
    ),
)
class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = PublicProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        return public_products()


@extend_schema_view(
    get=extend_schema(
        tags=["owner-products"],
        summary="List my store's products",
        responses={
            200: OwnerProductSerializer(many=True),
            **standard_errors(400, 401, 403, 404),
        },
        examples=[OpenApiExample("Product", value=OWNER_PRODUCT_EXAMPLE, response_only=True)],
    ),
    post=extend_schema(
        tags=["owner-products"],
        summary="Add a product to my store",
        description=(
            "Send multipart/form-data to upload an image (JPEG, PNG or WebP, max 2 MB). "
            "The category must be ACTIVE. Stock 0 makes the product OUT_OF_STOCK."
        ),
        request=OwnerProductSerializer,
        responses={201: OwnerProductSerializer, **standard_errors(400, 401, 403, 404)},
        examples=[
            OWNER_PRODUCT_REQUEST_EXAMPLE,
            OpenApiExample(
                "Created", value=OWNER_PRODUCT_EXAMPLE, response_only=True, status_codes=["201"]
            ),
        ],
    ),
)
class OwnerStoreProductListCreateView(generics.ListCreateAPIView):
    serializer_class = OwnerProductSerializer
    permission_classes = [IsStoreOwner]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filterset_class = OwnerProductFilter
    search_fields = ("name", "description")
    ordering_fields = ("name", "price", "stock_quantity", "created_at")
    ordering = ("name", "id")

    @cached_property
    def store(self):
        return get_owned_or_404(
            Store.objects.all(),
            OwnerField.STORE_OWNER,
            self.request.user,
            pk=self.kwargs["store_id"],
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Product.objects.none()
        return Product.objects.filter(store=self.store, deleted_at__isnull=True).select_related(
            "category"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False) and self.request.method == "POST":
            context["store"] = self.store
        return context

    def perform_create(self, serializer):
        serializer.instance = services.create_product(self.store, serializer.validated_data)


class OwnerProductQuerysetMixin(OwnerScopedQuerysetMixin):
    permission_classes = [IsStoreOwner]
    owner_field = OwnerField.STORE_OF_OBJECT
    queryset = Product.objects.filter(deleted_at__isnull=True).select_related("category")


@extend_schema_view(
    get=extend_schema(
        tags=["owner-products"],
        summary="My product detail",
        responses={200: OwnerProductSerializer, **standard_errors(401, 403, 404)},
        examples=[OpenApiExample("Product", value=OWNER_PRODUCT_EXAMPLE, response_only=True)],
    ),
    patch=extend_schema(
        tags=["owner-products"],
        summary="Edit my product",
        request=OwnerProductSerializer,
        responses={200: OwnerProductSerializer, **standard_errors(400, 401, 403, 404)},
        examples=[
            OpenApiExample("Change price", value={"price": "1700.00"}, request_only=True),
            OpenApiExample(
                "Hide from customers",
                value={"availability_status": "UNAVAILABLE"},
                request_only=True,
            ),
        ],
    ),
    delete=extend_schema(
        tags=["owner-products"],
        summary="Delete my product (soft delete)",
        description=(
            "Sets deleted_at. The product disappears from every list; order history keeps it."
        ),
        responses={204: None, **standard_errors(401, 403, 404)},
    ),
)
class OwnerProductDetailView(OwnerProductQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OwnerProductSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def perform_update(self, serializer):
        serializer.instance = services.update_product(
            serializer.instance, serializer.validated_data
        )

    def perform_destroy(self, instance):
        services.soft_delete_product(instance)


@extend_schema_view(
    patch=extend_schema(
        tags=["owner-products"],
        summary="Set stock quantity",
        description=(
            "Stock 0 makes the product OUT_OF_STOCK. Stock above 0 on an OUT_OF_STOCK product "
            "makes it AVAILABLE. UNAVAILABLE products stay UNAVAILABLE unless stock is set to 0."
        ),
        request=StockUpdateSerializer,
        responses={200: OwnerProductSerializer, **standard_errors(400, 401, 403, 404)},
        examples=[
            OpenApiExample("Restock", value={"stock_quantity": 48}, request_only=True),
            OpenApiExample("Updated", value=OWNER_PRODUCT_EXAMPLE, response_only=True),
        ],
    ),
)
class OwnerProductStockView(OwnerProductQuerysetMixin, generics.GenericAPIView):
    serializer_class = StockUpdateSerializer
    http_method_names = ["patch", "options"]

    def patch(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = services.set_stock(product, serializer.validated_data["stock_quantity"])
        product = Product.objects.select_related("category").get(pk=product.pk)
        return Response(
            OwnerProductSerializer(product, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )
