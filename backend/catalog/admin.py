from django.contrib import admin

from catalog.models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "store",
        "category",
        "unit",
        "price",
        "stock_quantity",
        "availability_status",
        "deleted_at",
    )
    list_filter = ("availability_status", "unit", "category", "store")
    search_fields = ("name", "description", "store__store_name")
    autocomplete_fields = ("store", "category")
    list_select_related = ("store", "category")
