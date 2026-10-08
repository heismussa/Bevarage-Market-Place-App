from django.urls import path

from orders.views import (
    AdminOrderCancelView,
    OrderCancelView,
    OrderDetailView,
    OrderListCreateView,
)

urlpatterns = [
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path(
        "admin/orders/<int:pk>/cancel/",
        AdminOrderCancelView.as_view(),
        name="admin-order-cancel",
    ),
]
