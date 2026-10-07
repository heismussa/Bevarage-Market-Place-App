from django.contrib import admin

from cart.models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ("product",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "store", "updated_at")
    list_filter = ("store",)
    search_fields = ("customer__user__phone", "customer__user__full_name", "store__store_name")
    autocomplete_fields = ("customer", "store")
    list_select_related = ("customer__user", "store")
    inlines = (CartItemInline,)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity", "unit_price")
    search_fields = ("product__name", "cart__customer__user__phone")
    autocomplete_fields = ("cart", "product")
    list_select_related = ("cart__customer__user", "product")
