from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.serializers import MeSerializer, RegisterSerializer, UserPublicSerializer


@extend_schema_view(
    post=extend_schema(tags=["auth"], summary="Register a customer or store owner"),
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
    post=extend_schema(tags=["auth"], summary="Log in with phone and password"),
)
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema_view(
    post=extend_schema(tags=["auth"], summary="Refresh an access token"),
)
class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []


@extend_schema_view(
    get=extend_schema(tags=["auth"], summary="Current user"),
    patch=extend_schema(tags=["auth"], summary="Update the current user"),
)
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
