"""Order event hook. Stage 6 turns these events into in-app notifications.

Callers schedule notify_order_event with transaction.on_commit, so it only runs after
the order change is saved.
"""

ORDER_CREATED = "ORDER_CREATED"


def status_event(status):
    """Event name for an order entering status, e.g. ORDER_ACCEPTED."""
    return f"ORDER_{status}"


def notify_order_event(order, event):
    """Placeholder until Stage 6. Must not raise."""
    return None
