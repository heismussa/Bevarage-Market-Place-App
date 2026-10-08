from django.http import Http404
from rest_framework import generics, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from accounts.models import Address
from accounts.permissions import IsCustomer
from core.errors import ErrorCode
from core.ownership import (
    OwnerField,
    OwnerScopedQuerysetMixin,
    get_customer_profile,
    get_owned_or_404,
    get_store_owner_profile,
)
from core.testing.api import ApiTestCase
from core.testing.factories import AddressFactory, CustomerFactory, StoreOwnerFactory


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("id", "address_name")


class AddressDetailView(OwnerScopedQuerysetMixin, generics.RetrieveAPIView):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsCustomer]
    owner_field = OwnerField.CUSTOMER


class AddressListView(OwnerScopedQuerysetMixin, generics.ListAPIView):
    queryset = Address.objects.order_by("id")
    serializer_class = AddressSerializer
    permission_classes = [IsCustomer]
    owner_field = OwnerField.CUSTOMER


class NoPermissionDeclaredView(APIView):
    def get(self, request):
        return None


def call(view, user, **kwargs):
    request = APIRequestFactory().get("/")
    force_authenticate(request, user=user)
    response = view.as_view()(request, **kwargs)
    response.render()
    return response


class OwnershipTests(ApiTestCase):
    def setUp(self):
        self.alice = CustomerFactory()
        self.bob = CustomerFactory()
        self.alice_address = AddressFactory(customer=self.alice)
        self.bob_address = AddressFactory(customer=self.bob)

    def test_owner_can_read_own_object(self):
        response = call(AddressDetailView, self.alice.user, pk=self.alice_address.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_users_object_is_404_not_403(self):
        response = call(AddressDetailView, self.alice.user, pk=self.bob_address.pk)

        self.assertError(response, status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND)

    def test_list_only_contains_own_rows(self):
        response = call(AddressListView, self.alice.user)

        ids = [row["id"] for row in response.data["results"]]
        self.assertEqual(ids, [self.alice_address.pk])

    def test_wrong_role_is_403(self):
        owner = StoreOwnerFactory()

        response = call(AddressDetailView, owner.user, pk=self.alice_address.pk)

        self.assertError(response, status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED)

    def test_views_deny_by_default(self):
        response = call(NoPermissionDeclaredView, self.alice.user)

        self.assertError(response, status.HTTP_403_FORBIDDEN, ErrorCode.PERMISSION_DENIED)

    def test_get_owned_or_404(self):
        found = get_owned_or_404(
            Address.objects.all(), OwnerField.CUSTOMER, self.alice.user, pk=self.alice_address.pk
        )
        self.assertEqual(found, self.alice_address)

        with self.assertRaises(Http404):
            get_owned_or_404(
                Address.objects.all(), OwnerField.CUSTOMER, self.alice.user, pk=self.bob_address.pk
            )

    def test_profile_helpers(self):
        self.assertEqual(get_customer_profile(self.alice.user), self.alice)
        with self.assertRaises(PermissionDenied):
            get_store_owner_profile(self.alice.user)
