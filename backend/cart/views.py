from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from cart import services
from cart.serializers import (
    AddCartItemQuerySerializer,
    AddCartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)
from core.errors import ErrorCode
from core.ownership import get_customer_profile
from core.schema import error_response, standard_errors

CART_EXAMPLE = {
    "store": {
        "id": 1,
        "store_name": "ABC Drinks",
        "logo": None,
        "status": "OPEN",
        "delivery_fee": "2000.00",
    },
    "items": [
        {
            "id": 7,
            "product_id": 1,
            "name": "Coca-Cola 500ml",
            "image": None,
            "unit": "BOTTLE",
            "unit_price": "1600.00",
            "price_when_added": "1500.00",
            "quantity": 2,
            "line_total": "3200.00",
            "price_changed": True,
            "available": True,
            "max_available": 118,
        }
    ],
    "item_count": 2,
    "subtotal": "3200.00",
    "delivery_fee": "2000.00",
    "total": "5200.00",
    "warnings": [
        {
            "code": "PRICE_CHANGED",
            "message": "The price of Coca-Cola 500ml changed from 1500.00 to 1600.00.",
            "item_id": 7,
        }
    ],
}

EMPTY_CART_EXAMPLE = {
    "store": None,
    "items": [],
    "item_count": 0,
    "subtotal": "0.00",
    "delivery_fee": "0.00",
    "total": "0.00",
    "warnings": [],
}

CART_EXAMPLES = [
    OpenApiExample("Cart", value=CART_EXAMPLE, response_only=True),
    OpenApiExample("Empty cart", value=EMPTY_CART_EXAMPLE, response_only=True),
]

ITEM_ERRORS = {
    409: error_response(
        "The product cannot be added: CART_STORE_CONFLICT, PRODUCT_UNAVAILABLE, "
        "STORE_CLOSED or INSUFFICIENT_STOCK",
        ErrorCode.INSUFFICIENT_STOCK,
        "Only 3 of Coca-Cola 500ml left in stock.",
        {"product_id": 1, "requested": 5, "max_available": 3},
    ),
}

CONFLICT_EXAMPLE = OpenApiExample(
    "Cart has another store",
    value={
        "error": {
            "code": "CART_STORE_CONFLICT",
            "message": "Your cart has items from another store. Clear it to add this product.",
            "details": {
                "cart_store_id": 1,
                "cart_store_name": "ABC Drinks",
                "product_store_id": 2,
                "product_store_name": "Masaki Beverages",
            },
        }
    },
    response_only=True,
    status_codes=["409"],
)


class CustomerCartView(APIView):
    permission_classes = [IsCustomer]

    def customer(self):
        return get_customer_profile(self.request.user)

    def cart_response(self, response_status=status.HTTP_200_OK):
        summary = services.price_cart(services.load_cart(self.customer()))
        return Response(
            CartSerializer(summary, context={"request": self.request}).data,
            status=response_status,
        )


class CartView(CustomerCartView):
    @extend_schema(
        tags=["cart"],
        summary="My cart",
        description=(
            "Totals use CURRENT product prices. price_changed flags lines whose price differs "
            "from when they were added. Stock is not reserved. warnings lists every problem "
            "that would block checkout."
        ),
        responses={200: CartSerializer, **standard_errors(401, 403)},
        examples=CART_EXAMPLES,
    )
    def get(self, request):
        return self.cart_response()

    @extend_schema(
        tags=["cart"],
        summary="Empty my cart",
        request=None,
        responses={200: CartSerializer, **standard_errors(401, 403)},
        examples=[OpenApiExample("Empty cart", value=EMPTY_CART_EXAMPLE, response_only=True)],
    )
    def delete(self, request):
        services.clear_cart(self.customer())
        return self.cart_response()


class CartItemListView(CustomerCartView):
    @extend_schema(
        tags=["cart"],
        summary="Add a product to my cart",
        description=(
            "Adding a product already in the cart increases its quantity. A cart holds one "
            "store's products: adding from another store returns 409 CART_STORE_CONFLICT "
            "unless ?replace=true, which empties the cart first."
        ),
        parameters=[AddCartItemQuerySerializer],
        request=AddCartItemSerializer,
        responses={
            201: CartSerializer,
            **standard_errors(400, 401, 403, 404),
            **ITEM_ERRORS,
        },
        examples=[
            OpenApiExample("Add two", value={"product_id": 1, "quantity": 2}, request_only=True),
            OpenApiExample("Cart", value=CART_EXAMPLE, response_only=True, status_codes=["201"]),
            CONFLICT_EXAMPLE,
        ],
    )
    def post(self, request):
        query = AddCartItemQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        body = AddCartItemSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        services.add_item(
            self.customer(),
            body.validated_data["product_id"],
            body.validated_data["quantity"],
            replace=query.validated_data["replace"],
        )
        return self.cart_response(status.HTTP_201_CREATED)


ITEM_ID_PARAMETER = OpenApiParameter("pk", int, OpenApiParameter.PATH, description="Cart item id")


class CartItemDetailView(CustomerCartView):
    @extend_schema(
        tags=["cart"],
        summary="Change a cart line's quantity",
        parameters=[ITEM_ID_PARAMETER],
        request=UpdateCartItemSerializer,
        responses={
            200: CartSerializer,
            **standard_errors(400, 401, 403, 404),
            **ITEM_ERRORS,
        },
        examples=[
            OpenApiExample("Set to three", value={"quantity": 3}, request_only=True),
            *CART_EXAMPLES,
        ],
    )
    def patch(self, request, pk):
        body = UpdateCartItemSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        services.update_item_quantity(self.customer(), pk, body.validated_data["quantity"])
        return self.cart_response()

    @extend_schema(
        tags=["cart"],
        summary="Remove a line from my cart",
        description="When the last line is removed the cart no longer belongs to any store.",
        parameters=[ITEM_ID_PARAMETER],
        request=None,
        responses={200: CartSerializer, **standard_errors(401, 403, 404)},
        examples=CART_EXAMPLES,
    )
    def delete(self, request, pk):
        services.remove_item(self.customer(), pk)
        return self.cart_response()
