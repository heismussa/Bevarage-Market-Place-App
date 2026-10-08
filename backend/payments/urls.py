from django.urls import path

from payments.views import OrderPaymentView, PaymentWebhookView, PayOrderView

urlpatterns = [
    path("orders/<int:pk>/pay/", PayOrderView.as_view(), name="order-pay"),
    path("orders/<int:pk>/payment/", OrderPaymentView.as_view(), name="order-payment"),
    path(
        "payments/webhook/<str:provider>/",
        PaymentWebhookView.as_view(),
        name="payment-webhook",
    ),
]
