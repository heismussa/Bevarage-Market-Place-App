from django.db import models


class PaymentMethod(models.TextChoices):
    MPESA = "MPESA", "M-Pesa"
    TIGO_PESA = "TIGO_PESA", "Tigo Pesa"
    AIRTEL_MONEY = "AIRTEL_MONEY", "Airtel Money"
    CARD = "CARD", "Card"
    BANK = "BANK", "Bank"
    CASH = "CASH", "Cash"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    REFUNDED = "REFUNDED", "Refunded"
