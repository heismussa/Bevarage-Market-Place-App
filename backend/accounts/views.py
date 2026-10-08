from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts import password_services
from accounts.serializers import (
    DetailSerializer,
    LoginSerializer,
    MeSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserPublicSerializer,
)
from accounts.throttles import PasswordResetConfirmThrottle, PasswordResetRequestThrottle
from accounts.tokens import SessionRefreshToken
from core.errors import ErrorCode
from core.schema import error_response, standard_errors

RESET_REQUESTED = "If this phone number is registered, a reset code has been sent by SMS."

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
        request=LoginSerializer,
        responses={
            200: TokenPairSerializer,
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
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Refresh an access token",
        description=(
            "Returns a new access token; keep using the same refresh token. Fails with "
            "TOKEN_INVALID once the password has been changed or reset."
        ),
        request=RefreshSerializer,
        responses={200: RefreshSerializer, **standard_errors(400), 401: TOKEN_INVALID},
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
    serializer_class = RefreshSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Forgot password: send a reset code",
        description=(
            "Sends a 6-digit code by SMS if the phone belongs to an active account. The "
            "response is the same either way, so it never reveals which numbers are "
            "registered. Limited per phone number."
        ),
        request=PasswordResetRequestSerializer,
        responses={200: DetailSerializer, **standard_errors(400, 429)},
        examples=[
            OpenApiExample("Request", value={"phone": "+255712345678"}, request_only=True),
            OpenApiExample("Sent", value={"detail": RESET_REQUESTED}, response_only=True),
        ],
    ),
)
class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password_services.request_password_reset(serializer.validated_data["phone"])
        return Response({"detail": RESET_REQUESTED})


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Forgot password: set a new password with the code",
        description=(
            "Every existing login on every device stops working; the user logs in again "
            "with the new password. A wrong or expired code is a VALIDATION_ERROR on "
            "`code`. Limited per phone number."
        ),
        request=PasswordResetConfirmSerializer,
        responses={200: DetailSerializer, **standard_errors(400, 429)},
        examples=[
            OpenApiExample(
                "Confirm",
                value={
                    "phone": "+255712345678",
                    "code": "482913",
                    "new_password": "a-new-strong-password",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Done",
                value={"detail": "Your password has been reset. Log in with the new password."},
                response_only=True,
            ),
        ],
    ),
)
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password_services.confirm_password_reset(**serializer.validated_data)
        return Response({"detail": "Your password has been reset. Log in with the new password."})


@extend_schema_view(
    post=extend_schema(
        tags=["auth"],
        summary="Change my password",
        description=(
            "Logs out every other device. Returns fresh tokens so this device stays "
            "logged in: replace the stored tokens with them."
        ),
        request=PasswordChangeSerializer,
        responses={200: TokenPairSerializer, **standard_errors(400, 401)},
        examples=[
            OpenApiExample(
                "Change",
                value={
                    "current_password": "the-old-password",
                    "new_password": "a-new-strong-password",
                },
                request_only=True,
            ),
            OpenApiExample(
                "New tokens",
                value={"refresh": "<jwt refresh>", "access": "<jwt access>"},
                response_only=True,
            ),
        ],
    ),
)
class PasswordChangeView(generics.GenericAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = password_services.change_password(request.user, **serializer.validated_data)
        refresh = SessionRefreshToken.for_user(user)
        return Response({"refresh": str(refresh), "access": str(refresh.access_token)})


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
