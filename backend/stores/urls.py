from django.urls import path

from stores import views

urlpatterns = [
    path("stores/", views.PublicStoreListView.as_view(), name="store-list"),
    path("stores/<int:pk>/", views.PublicStoreDetailView.as_view(), name="store-detail"),
    path("owner/stores/", views.OwnerStoreListCreateView.as_view(), name="owner-store-list"),
    path(
        "owner/stores/<int:pk>/",
        views.OwnerStoreDetailView.as_view(),
        name="owner-store-detail",
    ),
]
