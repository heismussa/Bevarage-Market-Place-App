from django.urls import path

from orders.owner_views import (
    OwnerOrderDetailView,
    OwnerOrderTransitionView,
    OwnerStoreAnalyticsView,
    OwnerStoreDashboardView,
    OwnerStoreOrderListView,
)
from orders.views import (
    AdminOrderCancelView,
    OrderCancelView,
    OrderDetailView,
    OrderListCreateView,
)

urlpatterns = [
    path(
        "owner/stores/<int:pk>/orders/",
        OwnerStoreOrderListView.as_view(),
        name="owner-store-orders",
    ),
    path(
        "owner/stores/<int:pk>/dashboard/",
        OwnerStoreDashboardView.as_view(),
        name="owner-store-dashboard",
    ),
    path(
        "owner/stores/<int:pk>/analytics/",
        OwnerStoreAnalyticsView.as_view(),
        name="owner-store-analytics",
    ),
    path("owner/orders/<int:pk>/", OwnerOrderDetailView.as_view(), name="owner-order-detail"),
    path(
        "owner/orders/<int:pk>/transition/",
        OwnerOrderTransitionView.as_view(),
        name="owner-order-transition",
    ),
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:pk>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path(
        "admin/orders/<int:pk>/cancel/",
        AdminOrderCancelView.as_view(),
        name="admin-order-cancel",
    ),
]
