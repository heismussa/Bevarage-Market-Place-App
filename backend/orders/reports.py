"""Store dashboard and analytics. Every number is aggregated by the database.

Days are local calendar days (settings.TIME_ZONE). Sales are the total_amount of
COMPLETED orders (delivery fee included), bucketed by the day the order was placed.
Unpaid non-cash orders are invisible to the store owner and are not counted.
"""

import csv
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from catalog.models import Product
from orders.models import Order, OrderItem, OrderStatus
from payments.choices import CHECKOUT_PAYMENT_METHOD_CHOICES
from payments.models import Payment
from payments.services import visible_to_store_owner

ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=14, decimal_places=2))
LOW_STOCK_LIMIT = 10
RECENT_ORDERS_LIMIT = 5
TOP_PRODUCTS_LIMIT = 10
DASHBOARD_DAYS = 7
COMPLETED = Q(order_status=OrderStatus.COMPLETED)
ONE_DECIMAL = Decimal("0.1")


def latest_payment_method():
    return (
        Payment.objects.filter(order=OuterRef("pk"))
        .order_by("-created_at", "-id")
        .values("payment_method")[:1]
    )


def owner_order_queryset():
    """Orders with what the owner list needs, in a single query."""
    return (
        Order.objects.select_related("customer__user")
        .annotate(item_count=Count("items"), payment_method=Subquery(latest_payment_method()))
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


def percent(part, whole):
    """part / whole as a percentage with one decimal; None when whole is 0."""
    if not whole:
        return None
    return (Decimal(part) * 100 / Decimal(whole)).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def change_percent(current, previous):
    """Growth from previous to current; None when previous is 0 (no baseline)."""
    if not previous:
        return None
    return percent(Decimal(current) - Decimal(previous), previous)


def compare_periods(store, start, end):
    """start..end against the equally long period just before it, in one query."""
    length = (end - start).days + 1
    previous_start = start - timedelta(days=length)
    previous_end = start - timedelta(days=1)
    current = Q(ordered_at__date__gte=start)
    previous = Q(ordered_at__date__lt=start)
    row = _in_days(store_orders(store), previous_start, end).aggregate(
        orders=Count("id", filter=current),
        previous_orders=Count("id", filter=previous),
        sales=Coalesce(Sum("total_amount", filter=COMPLETED & current), ZERO),
        previous_sales=Coalesce(Sum("total_amount", filter=COMPLETED & previous), ZERO),
    )
    return {
        "current": {
            "date_from": start,
            "date_to": end,
            "total_orders": row["orders"],
            "total_sales": row["sales"],
        },
        "previous": {
            "date_from": previous_start,
            "date_to": previous_end,
            "total_orders": row["previous_orders"],
            "total_sales": row["previous_sales"],
        },
        "orders_change_percent": change_percent(row["orders"], row["previous_orders"]),
        "sales_change_percent": change_percent(row["sales"], row["previous_sales"]),
    }


def payment_methods(store, start, end):
    """COMPLETED orders placed in the range, grouped by the latest payment's method.

    The four checkout methods are always listed (with zeros) so charts keep their legend.
    """
    rows = (
        _in_days(store_orders(store).filter(COMPLETED), start, end)
        .annotate(method=Subquery(latest_payment_method()))
        .order_by()
        .values("method")
        .annotate(orders=Count("id"), sales=Sum("total_amount"))
    )
    by_method = {row["method"]: row for row in rows if row["method"]}
    methods = [value for value, _ in CHECKOUT_PAYMENT_METHOD_CHOICES]
    methods += sorted(set(by_method) - set(methods))
    total = sum(row["orders"] for row in by_method.values())
    result = []
    for method in methods:
        row = by_method.get(method)
        orders = row["orders"] if row else 0
        result.append(
            {
                "payment_method": method,
                "orders": orders,
                "sales": row["sales"] if row else Decimal("0.00"),
                "orders_percent": percent(orders, total) if total else Decimal("0.0"),
            }
        )
    return result


def dashboard(store):
    totals = _order_totals(store_orders(store))
    low_stock = Product.objects.filter(
        store=store, deleted_at__isnull=True, stock_quantity__lte=F("low_stock_threshold")
    )
    today = timezone.localdate()
    week_start = today - timedelta(days=DASHBOARD_DAYS - 1)
    return {
        "total_orders": totals["total_orders"],
        "pending_orders": totals["pending_orders"],
        "total_sales": totals["total_sales"],
        "low_stock_count": low_stock.count(),
        "low_stock_items": list(low_stock.order_by("stock_quantity", "name")[:LOW_STOCK_LIMIT]),
        "sales_last_7_days": daily_sales(store, week_start, today),
        "last_7_days_vs_previous": compare_periods(store, week_start, today),
        "payment_methods_last_7_days": payment_methods(store, week_start, today),
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


EXPORT_MAX_ROWS = 5000
EXPORT_COLUMNS = (
    "order_number",
    "ordered_at",
    "order_status",
    "payment_status",
    "payment_method",
    "customer_name",
    "customer_phone",
    "item_count",
    "subtotal_amount",
    "delivery_fee",
    "total_amount",
    "delivery_address",
)
# Spreadsheet apps run cells starting with these as formulas.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _plain_text(value):
    value = value or ""
    return "'" + value if value.startswith(FORMULA_PREFIXES) else value


def write_orders_csv(stream, orders):
    """Orders from owner_order_queryset(); the BOM makes Excel read the file as UTF-8."""
    stream.write("\ufeff")
    writer = csv.writer(stream)
    writer.writerow(EXPORT_COLUMNS)
    for order in orders:
        writer.writerow(
            (
                order.order_number,
                timezone.localtime(order.ordered_at).strftime("%Y-%m-%d %H:%M"),
                order.order_status,
                order.payment_status,
                order.payment_method or "",
                _plain_text(order.customer.user.full_name),
                order.customer.user.phone,
                order.item_count,
                order.subtotal_amount,
                order.delivery_fee,
                order.total_amount,
                _plain_text(order.delivery_address),
            )
        )


def analytics(store, start, end):
    totals = _order_totals(_in_days(store_orders(store), start, end))
    return {
        "date_from": start,
        "date_to": end,
        **totals,
        "daily_sales": daily_sales(store, start, end),
        "top_products": top_products(store, start, end),
        "payment_methods": payment_methods(store, start, end),
        "compared_to_previous": compare_periods(store, start, end),
    }
