from django.contrib import admin

from stores.models import Store


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        "store_name",
        "owner",
        "city",
        "area",
        "status",
        "is_active",
        "delivery_fee",
    )
    list_filter = ("status", "is_active", "city")
    search_fields = ("store_name", "phone", "email", "city", "area", "location")
    autocomplete_fields = ("owner",)
    list_select_related = ("owner__user",)
