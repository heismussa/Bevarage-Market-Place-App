from django.db import models


class PaymentMethod(models.TextChoices):
    MPESA = "MPESA", "M-Pesa"
    TIGO_PESA = "TIGO_PESA", "Tigo Pesa"
    AIRTEL_MONEY = "AIRTEL_MONEY", "Airtel Money"
    CARD = "CARD", "Card"
    BANK = "BANK", "Bank"
    CASH = "CASH", "Cash"


MOBILE_MONEY_METHODS = frozenset(
    {PaymentMethod.MPESA, PaymentMethod.TIGO_PESA, PaymentMethod.AIRTEL_MONEY}
)

# Methods a customer may choose at checkout. CARD and BANK have no provider yet.
CHECKOUT_PAYMENT_METHOD_CHOICES = [
    (method.value, method.label)
    for method in PaymentMethod
    if method == PaymentMethod.CASH or method in MOBILE_MONEY_METHODS
]


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    REFUNDED = "REFUNDED", "Refunded"
