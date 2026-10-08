from rest_framework import serializers

from accounts.validators import validate_phone
from payments.models import Payment


class PayOrderSerializer(serializers.Serializer):
    payer_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Number that receives the payment prompt. Defaults to the previous one.",
    )

    def validate_payer_phone(self, value):
        if value:
            validate_phone(value)
        return value or None


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "payment_method",
            "payment_status",
            "amount",
            "currency",
            "payer_phone",
            "transaction_reference",
            "payment_time",
            "created_at",
        )
        read_only_fields = fields


class PaymentInitiationSerializer(serializers.Serializer):
    payment = PaymentSerializer()
    instructions = serializers.CharField(help_text="Text to show the customer.")


class WebhookAckSerializer(serializers.Serializer):
    received = serializers.BooleanField()
    payment_status = serializers.CharField()
