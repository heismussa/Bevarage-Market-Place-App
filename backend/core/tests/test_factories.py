from django.test import TestCase

from accounts.models import Customer, StoreOwner, UserRole
from core.testing import factories


class FactoryTests(TestCase):
    def test_every_factory_builds_a_valid_row(self):
        for factory_class in (
            factories.UserFactory,
            factories.AdminUserFactory,
            factories.CustomerFactory,
            factories.StoreOwnerFactory,
            factories.AddressFactory,
            factories.StoreFactory,
            factories.CategoryFactory,
            factories.ProductFactory,
            factories.CartFactory,
            factories.CartItemFactory,
            factories.OrderFactory,
            factories.OrderItemFactory,
            factories.OrderStatusHistoryFactory,
            factories.PaymentFactory,
            factories.NotificationFactory,
        ):
            with self.subTest(factory=factory_class.__name__):
                instance = factory_class()
                instance.full_clean()

    def test_profile_factories_reuse_the_signal_profile(self):
        customer = factories.CustomerFactory()
        owner = factories.StoreOwnerFactory()

        self.assertEqual(customer.user.role, UserRole.CUSTOMER)
        self.assertEqual(owner.user.role, UserRole.STORE_OWNER)
        self.assertEqual(Customer.objects.filter(user=customer.user).count(), 1)
        self.assertEqual(StoreOwner.objects.filter(user=owner.user).count(), 1)

    def test_users_get_a_usable_test_password(self):
        user = factories.UserFactory()

        self.assertTrue(user.check_password(factories.TEST_PASSWORD))

    def test_order_item_product_belongs_to_the_order_store(self):
        item = factories.OrderItemFactory()

        self.assertEqual(item.product.store, item.order.store)
