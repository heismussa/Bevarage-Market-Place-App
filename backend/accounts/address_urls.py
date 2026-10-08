from django.urls import path

from accounts.address_views import AddressDetailView, AddressListCreateView, AddressSetDefaultView

urlpatterns = [
    path("addresses/", AddressListCreateView.as_view(), name="address-list"),
    path("addresses/<int:pk>/", AddressDetailView.as_view(), name="address-detail"),
    path(
        "addresses/<int:pk>/set-default/",
        AddressSetDefaultView.as_view(),
        name="address-set-default",
    ),
]
