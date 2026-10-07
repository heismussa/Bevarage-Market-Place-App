from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from accounts.models import Address, Customer, StoreOwner, User


class BeverageUserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("phone", "full_name", "role")


class BeverageUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = (
            "phone",
            "full_name",
            "email",
            "role",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = BeverageUserChangeForm
    add_form = BeverageUserCreationForm
    ordering = ("-created_at",)
    list_display = ("phone", "full_name", "role", "is_active", "is_staff", "created_at")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("phone", "full_name", "email")
    readonly_fields = ("last_login", "created_at", "updated_at")
    filter_horizontal = ("groups", "user_permissions")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profile", {"fields": ("full_name", "email", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "phone",
                    "full_name",
                    "role",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("phone", "full_name", "created_at")
    search_fields = ("user__phone", "user__full_name", "user__email")
    list_select_related = ("user",)
    readonly_fields = ("created_at",)

    @admin.display(description="Phone", ordering="user__phone")
    def phone(self, obj):
        return obj.user.phone

    @admin.display(description="Name", ordering="user__full_name")
    def full_name(self, obj):
        return obj.user.full_name


@admin.register(StoreOwner)
class StoreOwnerAdmin(admin.ModelAdmin):
    list_display = ("phone", "full_name", "created_at")
    search_fields = ("user__phone", "user__full_name", "user__email")
    list_select_related = ("user",)
    readonly_fields = ("created_at",)

    @admin.display(description="Phone", ordering="user__phone")
    def phone(self, obj):
        return obj.user.phone

    @admin.display(description="Name", ordering="user__full_name")
    def full_name(self, obj):
        return obj.user.full_name


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("address_name", "customer_phone", "city", "area", "is_default")
    list_filter = ("is_default", "city")
    search_fields = (
        "address_name",
        "address_line",
        "city",
        "area",
        "customer__user__phone",
    )
    autocomplete_fields = ("customer",)
    list_select_related = ("customer__user",)

    @admin.display(description="Customer", ordering="customer__user__phone")
    def customer_phone(self, obj):
        return obj.customer.user.phone
