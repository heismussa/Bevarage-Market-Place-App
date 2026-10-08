import django_filters
from django import forms

from orders.models import Order, OrderStatus
from payments.choices import PaymentStatus


class CustomerOrderFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(field_name="order_status", choices=OrderStatus.choices)

    class Meta:
        model = Order
        fields = ("status",)


class DateRangeForm(forms.Form):
    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("date_from"), cleaned.get("date_to")
        if start and end and start > end:
            self.add_error("date_to", "date_to must be on or after date_from.")
        return cleaned


class OwnerOrderFilter(django_filters.FilterSet):
    """Dates are local (Africa/Dar_es_Salaam) calendar days and both ends are inclusive."""

    status = django_filters.ChoiceFilter(field_name="order_status", choices=OrderStatus.choices)
    payment_status = django_filters.ChoiceFilter(choices=PaymentStatus.choices)
    date_from = django_filters.DateFilter(field_name="ordered_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="ordered_at", lookup_expr="date__lte")

    class Meta:
        model = Order
        fields = ("status", "payment_status", "date_from", "date_to")
        form = DateRangeForm
