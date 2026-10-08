import django_filters

from orders.models import Order, OrderStatus


class CustomerOrderFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(field_name="order_status", choices=OrderStatus.choices)

    class Meta:
        model = Order
        fields = ("status",)
