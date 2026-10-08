import django_filters

from accounts.models import Address


class AddressFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = Address
        fields = ("is_default", "city")
