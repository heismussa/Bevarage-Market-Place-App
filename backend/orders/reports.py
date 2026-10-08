"""Store dashboard and analytics. Every number is aggregated by the database.

Days are local calendar days (settings.TIME_ZONE). Sales are the total_amount of
COMPLETED orders (delivery fee included), bucketed by the day the order was placed.
Unpaid non-cash orders are invisible to the store owner and are not counted.
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from catalog.models import Product
from orders.models import Order, OrderItem, OrderStatus
from payments.models import Payment
from payments.services import visible_to_store_owner

ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))
LOW_STOCK_LIMIT = 10
RECENT_ORDERS_LIMIT = 5
TOP_PRODUCTS_LIMIT = 10
COMPLETED = Q(order_status=OrderStatus.COMPLETED)


def owner_order_queryset():
    """Orders with what the owner list needs, in a single query."""
    latest_method = (
        Payment.objects.filter(order=OuterRef("pk"))
        .order_by("-created_at", "-id")
        .values("payment_method")[:1]
    )
    return (
        Order.objects.select_related("customer__user")
        .annotate(item_count=Count("items"), payment_method=Subquery(latest_method))
        .order_by("-ordered_at", "-id")
    )


def _in_days(queryset, start, end):
    return queryset.filter(ordered_at__date__gte=start, ordered_at__date__lte=end)


def _order_totals(queryset):
    return queryset.aggregate(
        total_orders=Count("id"),
        completed_orders=Count("id", filter=COMPLETED),
        pending_orders=Count("id", filter=Q(order_status=OrderStatus.PENDING)),
        total_sales=Coalesce(Sum("total_amount", filter=COMPLETED), ZERO),
    )


def daily_sales(store, start, end):
    """One row per day from start to end, including days without sales."""
    rows = (
        _in_days(Order.objects.filter(store=store, order_status=OrderStatus.COMPLETED), start, end)
        .annotate(day=TruncDate("ordered_at", tzinfo=timezone.get_current_timezone()))
        .values("day")
        .annotate(orders=Count("id"), sales=Sum("total_amount"))
    )
    by_day = {row["day"]: row for row in rows}
    series = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        row = by_day.get(day)
        series.append(
            {
                "date": day,
                "orders": row["orders"] if row else 0,
                "sales": row["sales"] if row else Decimal("0.00"),
            }
        )
    return series


def store_orders(store):
    """Orders the store owner may see (unpaid non-cash orders are hidden)."""
    return visible_to_store_owner(Order.objects.filter(store=store))


def dashboard(store):
    totals = _order_totals(store_orders(store))
    low_stock = Product.objects.filter(
        store=store, deleted_at__isnull=True, stock_quantity__lte=F("low_stock_threshold")
    )
    today = timezone.localdate()
    return {
        "total_orders": totals["total_orders"],
        "pending_orders": totals["pending_orders"],
        "total_sales": totals["total_sales"],
        "low_stock_count": low_stock.count(),
        "low_stock_items": list(low_stock.order_by("stock_quantity", "name")[:LOW_STOCK_LIMIT]),
        "sales_last_7_days": daily_sales(store, today - timedelta(days=6), today),
        "recent_orders": list(
            visible_to_store_owner(owner_order_queryset().filter(store=store))[:RECENT_ORDERS_LIMIT]
        ),
    }


def top_products(store, start, end):
    """Best sellers by quantity among COMPLETED orders placed in the range."""
    return list(
        OrderItem.objects.filter(order__store=store, order__order_status=OrderStatus.COMPLETED)
        .filter(order__ordered_at__date__gte=start, order__ordered_at__date__lte=end)
        .values("product_id")
        .annotate(
            product_name=F("product__name"),
            quantity_sold=Sum("quantity"),
            sales=Sum("subtotal"),
        )
        .order_by("-quantity_sold", "product_name")[:TOP_PRODUCTS_LIMIT]
    )


def analytics(store, start, end):
    totals = _order_totals(_in_days(store_orders(store), start, end))
    return {
        "date_from": start,
        "date_to": end,
        **totals,
        "daily_sales": daily_sales(store, start, end),
        "top_products": top_products(store, start, end),
    }
