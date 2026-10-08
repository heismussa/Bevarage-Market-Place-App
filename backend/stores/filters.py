import django_filters
from django.db.models import Exists, OuterRef

from catalog.models import CategoryStatus, Product
from stores.models import Store, StoreStatus


class StoreFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=StoreStatus.choices)
    city = django_filters.CharFilter(lookup_expr="iexact")
    area = django_filters.CharFilter(lookup_expr="iexact")
    category = django_filters.NumberFilter(
        method="filter_category",
        label="Category id. Stores with at least one listed product in that category.",
    )

    class Meta:
        model = Store
        fields = ("status", "city", "area", "category")

    def filter_category(self, queryset, name, value):
        listed = Product.objects.filter(
            store=OuterRef("pk"),
            category_id=value,
            category__status=CategoryStatus.ACTIVE,
            deleted_at__isnull=True,
        )
        return queryset.filter(Exists(listed))
