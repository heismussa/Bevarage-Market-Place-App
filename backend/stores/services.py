import math

from django.db import transaction
from django.db.models import ExpressionWrapper, F, FloatField, Value
from django.db.models.functions import ASin, Cast, Cos, Least, Power, Radians, Sin, Sqrt

from stores.models import Store

EARTH_RADIUS_KM = 6371.0


def _float(value):
    return Value(float(value), output_field=FloatField())


def annotate_distance(queryset, latitude, longitude):
    """Annotate `distance` (km, Haversine) from the given point. NULL when the store has no
    coordinates. Computed in the database so it can be filtered and ordered."""
    origin_lat = math.radians(float(latitude))
    origin_lng = math.radians(float(longitude))
    store_lat = Radians(Cast(F("latitude"), FloatField()))
    store_lng = Radians(Cast(F("longitude"), FloatField()))

    half_chord = Power(Sin((store_lat - _float(origin_lat)) / _float(2)), 2) + Cos(
        _float(origin_lat)
    ) * Cos(store_lat) * Power(Sin((store_lng - _float(origin_lng)) / _float(2)), 2)
    # Floating-point error can push sqrt(a) a hair above 1, which ASIN rejects.
    central_angle = ASin(Least(Sqrt(half_chord), _float(1)))

    return queryset.annotate(
        distance=ExpressionWrapper(
            _float(2 * EARTH_RADIUS_KM) * central_angle, output_field=FloatField()
        )
    )


@transaction.atomic
def create_store(owner, data):
    return Store.objects.create(owner=owner, **data)


@transaction.atomic
def update_store(store, data):
    store = Store.objects.select_for_update().get(pk=store.pk)
    for field, value in data.items():
        setattr(store, field, value)
    store.save()
    return store
