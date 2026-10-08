import django_filters
from django.db.models import F

from catalog.models import AvailabilityStatus, Product


class PublicProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    availability = django_filters.ChoiceFilter(
        field_name="availability_status", choices=AvailabilityStatus.choices
    )
    in_stock = django_filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Product
        fields = ("category", "availability", "in_stock")

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock_quantity__gt=0)
        return queryset.filter(stock_quantity=0)


class OwnerProductFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    availability = django_filters.ChoiceFilter(
        field_name="availability_status", choices=AvailabilityStatus.choices
    )
    low_stock = django_filters.BooleanFilter(
        method="filter_low_stock",
        label="true: stock_quantity <= low_stock_threshold",
    )

    class Meta:
        model = Product
        fields = ("category", "availability", "low_stock")

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock_quantity__lte=F("low_stock_threshold"))
        return queryset.filter(stock_quantity__gt=F("low_stock_threshold"))
