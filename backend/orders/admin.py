from django.contrib import admin

from orders.models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product",)


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    ordering = ("changed_at",)
    readonly_fields = ("from_status", "status", "changed_by", "changed_at", "notes")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer",
        "store",
        "order_status",
        "payment_status",
        "total_amount",
        "ordered_at",
    )
    list_filter = ("order_status", "payment_status", "store")
    search_fields = (
        "order_number",
        "customer__user__phone",
        "customer__user__full_name",
        "delivery_phone",
    )
    autocomplete_fields = ("customer", "store", "address")
    list_select_related = ("customer__user", "store")
    inlines = (OrderItemInline, OrderStatusHistoryInline)
    readonly_fields = ("ordered_at", "created_at", "updated_at")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product_name", "unit", "quantity", "unit_price", "subtotal")
    list_filter = ("unit",)
    search_fields = ("product_name", "order__order_number")
    autocomplete_fields = ("order", "product")
    list_select_related = ("order", "product")


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "status", "changed_by", "changed_at")
    list_filter = ("status",)
    search_fields = ("order__order_number", "notes")
    readonly_fields = (
        "order",
        "from_status",
        "status",
        "changed_by",
        "changed_at",
        "notes",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
