from django.test import TestCase
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from catalog.models import Category
from core.pagination import StandardPagination
from core.testing.factories import CategoryFactory


class CategoryNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.order_by("id")
    serializer_class = CategoryNameSerializer
    permission_classes = [AllowAny]


class PaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        CategoryFactory.create_batch(25)

    def get(self, query=""):
        request = APIRequestFactory().get(f"/categories/{query}")
        return CategoryListView.as_view()(request)

    def test_default_page_size_is_20(self):
        response = self.get()

        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])

    def test_client_can_choose_page_size(self):
        response = self.get("?page_size=5&page=2")

        self.assertEqual(len(response.data["results"]), 5)

    def test_page_size_is_capped_at_100(self):
        request = Request(APIRequestFactory().get("/categories/?page_size=500"))

        self.assertEqual(StandardPagination().get_page_size(request), 100)

    def test_list_uses_one_count_and_one_select(self):
        with self.assertNumQueries(2):
            self.get()
