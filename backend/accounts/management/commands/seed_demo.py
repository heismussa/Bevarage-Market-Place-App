import os
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from accounts.models import Address, Customer, StoreOwner, User, UserRole
from accounts.validators import validate_phone
from catalog.models import AvailabilityStatus, Category, CategoryStatus, Product, ProductUnit
from stores.models import Store, StoreStatus

ADMIN_PHONE = "+255712345001"
CUSTOMER_PHONE = "+255712345002"
ABC_OWNER_PHONE = "+255712345003"
FRESH_OWNER_PHONE = "+255712345004"

CATEGORIES = (
    "Soda",
    "Water",
    "Juice",
    "Energy Drinks",
    "Beer",
    "Wine",
    "Spirits",
    "Other",
)


def require_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise CommandError(
            f"Set {name} in the environment before running seed_demo. "
            "See .env.example."
        )
    return value


class Command(BaseCommand):
    help = (
        "Load idempotent demo data: categories, two stores, products, "
        "one customer, and one admin. Safe to run more than once."
    )

    def handle(self, *args, **options):
        admin_password = require_env("DEMO_ADMIN_PASSWORD")
        customer_password = require_env("DEMO_CUSTOMER_PASSWORD")
        owner_password = require_env("DEMO_STORE_OWNER_PASSWORD")

        with transaction.atomic():
            categories = self._categories()
            admin = self._user(
                phone=ADMIN_PHONE,
                password=admin_password,
                full_name="System Admin",
                email="admin@example.com",
                role=UserRole.ADMIN,
                is_staff=True,
                is_superuser=True,
            )
            customer = self._user(
                phone=CUSTOMER_PHONE,
                password=customer_password,
                full_name="John Mushi",
                email="customer@example.com",
                role=UserRole.CUSTOMER,
            )
            abc_owner = self._user(
                phone=ABC_OWNER_PHONE,
                password=owner_password,
                full_name="Amina Hassan",
                email="amina@example.com",
                role=UserRole.STORE_OWNER,
            )
            fresh_owner = self._user(
                phone=FRESH_OWNER_PHONE,
                password=owner_password,
                full_name="Neema Lyimo",
                email="neema@example.com",
                role=UserRole.STORE_OWNER,
            )
            abc = self._store(
                owner=abc_owner.store_owner_profile,
                store_name="ABC Drinks",
                description="Soft drinks, water, and beer from Kariakoo.",
                location="Kariakoo Market, Uhuru Street, Dar es Salaam",
                city="Dar es Salaam",
                area="Kariakoo",
                latitude=Decimal("-6.823490"),
                longitude=Decimal("39.274530"),
                phone="+255713000001",
                email="abc@example.com",
                delivery_fee=Decimal("2000.00"),
            )
            fresh = self._store(
                owner=fresh_owner.store_owner_profile,
                store_name="Fresh Beverages",
                description="Juices, water, and wine from Masaki.",
                location="Masaki Peninsula, Toure Drive, Dar es Salaam",
                city="Dar es Salaam",
                area="Masaki",
                latitude=Decimal("-6.747800"),
                longitude=Decimal("39.279200"),
                phone="+255713000002",
                email="fresh@example.com",
                delivery_fee=Decimal("2500.00"),
            )
            self._products(abc, categories, ABC_PRODUCTS)
            self._products(fresh, categories, FRESH_PRODUCTS)
            self._address(customer.customer_profile)

        self.stdout.write(self.style.SUCCESS("Demo data is ready."))
        self.stdout.write(f"Admin:        {admin.phone}")
        self.stdout.write(f"Customer:     {customer.phone}")
        self.stdout.write(f"ABC Drinks:   {abc_owner.phone}")
        self.stdout.write(f"Fresh owner:  {fresh_owner.phone}")
        self.stdout.write(
            "Passwords come from DEMO_ADMIN_PASSWORD, DEMO_CUSTOMER_PASSWORD, "
            "and DEMO_STORE_OWNER_PASSWORD. Running this again does not reset them."
        )

    def _categories(self):
        categories = {}
        for name in CATEGORIES:
            category, _created = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "description": name,
                    "status": CategoryStatus.ACTIVE,
                },
            )
            categories[name] = category
        return categories

    def _user(self, *, phone, password, full_name, email, role, is_staff=False, is_superuser=False):
        validate_phone(phone)
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                "full_name": full_name,
                "email": email.lower(),
                "role": role,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
                "is_active": True,
                "password": make_password(password),
            },
        )
        if role == UserRole.CUSTOMER:
            Customer.objects.get_or_create(user=user)
        elif role == UserRole.STORE_OWNER:
            StoreOwner.objects.get_or_create(user=user)
        if created:
            self.stdout.write(f"Created user {phone} ({role})")
        return user

    def _store(self, *, owner, store_name, **fields):
        store, created = Store.objects.get_or_create(
            owner=owner,
            store_name=store_name,
            defaults={
                **fields,
                "status": StoreStatus.OPEN,
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(f"Created store {store_name}")
        return store

    def _products(self, store, categories, rows):
        for row in rows:
            _product, created = Product.objects.get_or_create(
                store=store,
                name=row["name"],
                defaults={
                    "category": categories[row["category"]],
                    "description": row["name"],
                    "unit": row["unit"],
                    "price": row["price"],
                    "stock_quantity": row["stock"],
                    "low_stock_threshold": 5,
                    "availability_status": AvailabilityStatus.AVAILABLE,
                },
            )
            if created:
                self.stdout.write(f"Created product {row['name']} at {store.store_name}")

    def _address(self, customer):
        _address, created = Address.objects.get_or_create(
            customer=customer,
            address_name="Home",
            defaults={
                "address_line": "Plot 12, Haile Selassie Road",
                "city": "Dar es Salaam",
                "area": "Msasani",
                "latitude": Decimal("-6.748900"),
                "longitude": Decimal("39.276800"),
                "phone": CUSTOMER_PHONE,
                "is_default": True,
            },
        )
        if created:
            self.stdout.write("Created customer address Home")


ABC_PRODUCTS = (
    {"name": "Coca-Cola 500ml", "category": "Soda", "unit": ProductUnit.BOTTLE, "price": Decimal("1500.00"), "stock": 120},
    {"name": "Fanta 500ml", "category": "Soda", "unit": ProductUnit.BOTTLE, "price": Decimal("1500.00"), "stock": 80},
    {"name": "Sprite 500ml", "category": "Soda", "unit": ProductUnit.CAN, "price": Decimal("1500.00"), "stock": 60},
    {"name": "Water 1.5L", "category": "Water", "unit": ProductUnit.BOTTLE, "price": Decimal("1000.00"), "stock": 200},
    {"name": "Red Bull 250ml", "category": "Energy Drinks", "unit": ProductUnit.CAN, "price": Decimal("3500.00"), "stock": 45},
    {"name": "Kilimanjaro Premium Lager", "category": "Beer", "unit": ProductUnit.BOTTLE, "price": Decimal("3000.00"), "stock": 70},
)

FRESH_PRODUCTS = (
    {"name": "Coca-Cola 500ml", "category": "Soda", "unit": ProductUnit.BOTTLE, "price": Decimal("1600.00"), "stock": 90},
    {"name": "Water 1.5L", "category": "Water", "unit": ProductUnit.BOTTLE, "price": Decimal("1200.00"), "stock": 150},
    {"name": "Orange Juice 1L", "category": "Juice", "unit": ProductUnit.BOTTLE, "price": Decimal("4500.00"), "stock": 40},
    {"name": "Mango Juice 500ml", "category": "Juice", "unit": ProductUnit.BOTTLE, "price": Decimal("3000.00"), "stock": 55},
    {"name": "Mo Energy 500ml", "category": "Energy Drinks", "unit": ProductUnit.CAN, "price": Decimal("2500.00"), "stock": 35},
    {"name": "Chenin Blanc 750ml", "category": "Wine", "unit": ProductUnit.BOTTLE, "price": Decimal("28000.00"), "stock": 18},
)
