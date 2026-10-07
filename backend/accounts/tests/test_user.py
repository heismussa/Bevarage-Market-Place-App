from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import Customer, StoreOwner, User, UserRole
from accounts.tests.factories import PASSWORD


class UserCreationTests(TestCase):
    def test_customer_gets_a_profile_and_optional_email(self):
        user = User.objects.create_user(
            phone="+255712345678",
            password=PASSWORD,
            full_name="Amina Hassan",
            role=UserRole.CUSTOMER,
        )

        self.assertIsNone(user.email)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertTrue(Customer.objects.filter(user=user).exists())
        self.assertFalse(StoreOwner.objects.filter(user=user).exists())

    def test_two_users_may_omit_email(self):
        User.objects.create_user(
            phone="+255712345011",
            password=PASSWORD,
            full_name="One",
            role=UserRole.CUSTOMER,
        )
        User.objects.create_user(
            phone="+255712345012",
            password=PASSWORD,
            full_name="Two",
            role=UserRole.CUSTOMER,
        )

        self.assertEqual(User.objects.filter(email__isnull=True).count(), 2)

    def test_store_owner_gets_a_store_owner_profile(self):
        user = User.objects.create_user(
            phone="+255712345679",
            password=PASSWORD,
            full_name="Neema Lyimo",
            role=UserRole.STORE_OWNER,
        )

        self.assertTrue(StoreOwner.objects.filter(user=user).exists())
        self.assertFalse(Customer.objects.filter(user=user).exists())

    def test_superuser_is_admin_without_a_profile(self):
        admin = User.objects.create_superuser(
            phone="+255712345680",
            password=PASSWORD,
            full_name="System Admin",
        )

        self.assertEqual(admin.role, UserRole.ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertFalse(Customer.objects.filter(user=admin).exists())
        self.assertFalse(StoreOwner.objects.filter(user=admin).exists())

    def test_superuser_cannot_use_another_role(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                phone="+255712345681",
                password=PASSWORD,
                full_name="Not Admin",
                role=UserRole.CUSTOMER,
            )

    def test_phone_must_be_plus_255(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                phone="0712345678",
                password=PASSWORD,
                full_name="Bad Phone",
                role=UserRole.CUSTOMER,
            )

    def test_phone_is_unique(self):
        User.objects.create_user(
            phone="+255712345682",
            password=PASSWORD,
            full_name="First",
            role=UserRole.CUSTOMER,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    phone="+255712345682",
                    password=PASSWORD,
                    full_name="Second",
                    role=UserRole.CUSTOMER,
                )
