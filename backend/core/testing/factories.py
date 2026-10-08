"""factory_boy factories for every model. Defaults produce valid, consistent rows."""

from decimal import Decimal

import factory
from django.utils.text import slugify

from accounts.models import Address, Customer, StoreOwner, User, UserRole
from cart.models import Cart, CartItem
from catalog.models import AvailabilityStatus, Category, Product, ProductUnit
from notifications.models import Notification, NotificationType
from orders.models import Order, OrderItem, OrderStatus, OrderStatusHistory
from payments.choices import PaymentMethod, PaymentStatus
from payments.models import Payment
from stores.models import Store, StoreStatus

TEST_PASSWORD = "Beverage#2026x"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    full_name = factory.Faker("name")
    phone = factory.Sequence(lambda n: f"+2557{n:08d}")
    email = None
    role = UserRole.CUSTOMER
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", TEST_PASSWORD)
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, password=password, **kwargs)


class AdminUserFactory(UserFactory):
    role = UserRole.ADMIN
    is_staff = True
    is_superuser = True


class CustomerFactory(factory.django.DjangoModelFactory):
    """The profile is created by the post_save signal; this returns that row."""

    class Meta:
        model = Customer
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory, role=UserRole.CUSTOMER)


class StoreOwnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StoreOwner
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory, role=UserRole.STORE_OWNER)


class AddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Address

    customer = factory.SubFactory(CustomerFactory)
    address_name = factory.Sequence(lambda n: f"Address {n}")
    address_line = factory.Sequence(lambda n: f"Plot {n}, Haile Selassie Road")
    city = "Dar es Salaam"
    area = "Msasani"
    latitude = Decimal("-6.748900")
    longitude = Decimal("39.276800")
    phone = factory.LazyAttribute(lambda o: o.customer.user.phone)
    is_default = False


class StoreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Store

    owner = factory.SubFactory(StoreOwnerFactory)
    store_name = factory.Sequence(lambda n: f"Store {n}")
    location = "Kariakoo Market, Dar es Salaam"
    city = "Dar es Salaam"
    area = "Kariakoo"
    latitude = Decimal("-6.823490")
    longitude = Decimal("39.274530")
    phone = "+255713000000"
    status = StoreStatus.OPEN
    is_active = True
    delivery_fee = Decimal("2000.00")


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    store = factory.SubFactory(StoreFactory)
    category = factory.SubFactory(CategoryFactory)
    name = factory.Sequence(lambda n: f"Product {n}")
    unit = ProductUnit.BOTTLE
    price = Decimal("1500.00")
    stock_quantity = 50
    low_stock_threshold = 5
    availability_status = AvailabilityStatus.AVAILABLE


class CartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cart

    customer = factory.SubFactory(CustomerFactory)
    store = None


class CartItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1
    unit_price = factory.LazyAttribute(lambda o: o.product.price)


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    order_number = factory.Sequence(lambda n: f"BDM-20260101-{n:04d}")
    customer = factory.SubFactory(CustomerFactory)
    store = factory.SubFactory(StoreFactory)
    address = None
    delivery_address = "Plot 12, Haile Selassie Road, Dar es Salaam"
    delivery_phone = factory.LazyAttribute(lambda o: o.customer.user.phone)
    subtotal_amount = Decimal("1500.00")
    delivery_fee = factory.LazyAttribute(lambda o: o.store.delivery_fee)
    total_amount = factory.LazyAttribute(lambda o: o.subtotal_amount + o.delivery_fee)
    order_status = OrderStatus.PENDING
    payment_status = PaymentStatus.PENDING


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory, store=factory.SelfAttribute("..order.store"))
    product_name = factory.LazyAttribute(lambda o: o.product.name)
    unit = factory.LazyAttribute(lambda o: o.product.unit)
    quantity = 1
    unit_price = factory.LazyAttribute(lambda o: o.product.price)
    subtotal = factory.LazyAttribute(lambda o: o.unit_price * o.quantity)


class OrderStatusHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderStatusHistory

    order = factory.SubFactory(OrderFactory)
    from_status = None
    status = OrderStatus.PENDING
    changed_by = None


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)
    amount = factory.LazyAttribute(lambda o: o.order.total_amount)
    payment_method = PaymentMethod.CASH
    payment_status = PaymentStatus.PENDING
    currency = "TZS"


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    order = None
    notification_type = NotificationType.ORDER_RECEIVED
    title = "Order received"
    message = "Your order has been received."
    is_read = False
