from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["health"],
        summary="Liveness check",
        responses=HealthResponseSerializer,
        examples=[OpenApiExample("OK", value={"status": "ok"}, response_only=True)],
    )
    def get(self, request):
        return Response({"status": "ok"})
