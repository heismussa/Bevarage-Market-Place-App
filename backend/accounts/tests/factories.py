from decimal import Decimal

from accounts.models import User, UserRole
from catalog.models import Category, Product, ProductUnit
from stores.models import Store

PASSWORD = "Beverage#2026x"


def create_user(phone, role, full_name="Test User", email=None):
    return User.objects.create_user(
        phone=phone,
        password=PASSWORD,
        full_name=full_name,
        email=email,
        role=role,
    )


def create_customer(phone="+255712000001"):
    user = create_user(phone, UserRole.CUSTOMER, full_name="Test Customer")
    return user.customer_profile


def create_store_owner(phone="+255712000002"):
    user = create_user(phone, UserRole.STORE_OWNER, full_name="Test Owner")
    return user.store_owner_profile


def create_category(name="Soda", slug="soda"):
    return Category.objects.create(name=name, slug=slug)


def create_store(owner, name="Test Store"):
    return Store.objects.create(
        owner=owner,
        store_name=name,
        location="Kariakoo, Dar es Salaam",
        city="Dar es Salaam",
        area="Kariakoo",
        phone="+255713000099",
        delivery_fee=Decimal("1000.00"),
    )


def create_product(store, category, name="Cola", price=Decimal("1500.00"), stock=10):
    return Product.objects.create(
        store=store,
        category=category,
        name=name,
        unit=ProductUnit.BOTTLE,
        price=price,
        stock_quantity=stock,
    )
