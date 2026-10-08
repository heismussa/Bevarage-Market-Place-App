from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.serializers import MeSerializer, RegisterSerializer, UserPublicSerializer
from core.errors import ErrorCode
from core.schema import error_response, standard_errors

USER_EXAMPLE = {
    "id": 7,
    "full_name": "Amina Hassan",
    "phone": "+255712345678",
    "email": "amina@example.com",
    "role": "CUSTOMER",
}

TOKEN_INVALID = error_response(
    "Token is invalid or expired",
    ErrorCode.TOKEN_INVALID,
    "Given token not valid for any token type",
)


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Register a customer or store owner",
        request=RegisterSerializer,
        responses={201: UserPublicSerializer, **standard_errors(400)},
        examples=[
            OpenApiExample(
                "Customer",
                value={
                    "full_name": "Amina Hassan",
                    "phone": "+255712345678",
                    "password": "a-strong-password",
                    "email": "amina@example.com",
                    "role": "CUSTOMER",
                },
                request_only=True,
            ),
            OpenApiExample("Created", value=USER_EXAMPLE, response_only=True, status_codes=["201"]),
        ],
    ),
)
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserPublicSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Log in with phone and password",
        request=TokenObtainPairSerializer,
        responses={
            200: TokenObtainPairSerializer,
            **standard_errors(400),
            401: error_response(
                "Wrong phone or password",
                ErrorCode.AUTHENTICATION_FAILED,
                "No active account found with the given credentials",
            ),
        },
        examples=[
            OpenApiExample(
                "Login",
                value={"phone": "+255712345678", "password": "a-strong-password"},
                request_only=True,
            ),
            OpenApiExample(
                "Tokens",
                value={"access": "<jwt access>", "refresh": "<jwt refresh>"},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    ),
)
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Refresh an access token",
        request=TokenRefreshSerializer,
        responses={200: TokenRefreshSerializer, **standard_errors(400), 401: TOKEN_INVALID},
        examples=[
            OpenApiExample("Refresh", value={"refresh": "<jwt refresh>"}, request_only=True),
            OpenApiExample(
                "New access token",
                value={"access": "<jwt access>"},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    ),
)
class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema_view(
    get=extend_schema(
        tags=["auth"],
        summary="Current user",
        responses={200: MeSerializer, **standard_errors(401)},
    ),
    patch=extend_schema(
        tags=["auth"],
        summary="Update the current user (role, is_staff and is_active are read-only)",
        request=MeSerializer,
        responses={200: MeSerializer, **standard_errors(400, 401)},
        examples=[
            OpenApiExample(
                "Rename",
                value={"full_name": "Amina H. Hassan"},
                request_only=True,
            ),
        ],
    ),
)
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
