from django.urls import path

from catalog import views

urlpatterns = [
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path(
        "stores/<int:store_id>/products/",
        views.StoreProductListView.as_view(),
        name="store-product-list",
    ),
    path("products/<int:pk>/", views.ProductDetailView.as_view(), name="product-detail"),
    path(
        "owner/stores/<int:store_id>/products/",
        views.OwnerStoreProductListCreateView.as_view(),
        name="owner-store-product-list",
    ),
    path(
        "owner/products/<int:pk>/",
        views.OwnerProductDetailView.as_view(),
        name="owner-product-detail",
    ),
    path(
        "owner/products/<int:pk>/stock/",
        views.OwnerProductStockView.as_view(),
        name="owner-product-stock",
    ),
]
