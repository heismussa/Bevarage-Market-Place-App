from django.contrib import admin

from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "amount",
        "currency",
        "payment_method",
        "payment_status",
        "transaction_reference",
        "payment_time",
    )
    list_filter = ("payment_status", "payment_method", "currency")
    search_fields = ("transaction_reference", "payer_phone", "order__order_number")
    autocomplete_fields = ("order",)
    list_select_related = ("order",)
    readonly_fields = ("created_at", "updated_at")
