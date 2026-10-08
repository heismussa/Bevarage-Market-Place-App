from decimal import Decimal
from itertools import product as cartesian

from django.test import TestCase
from rest_framework.exceptions import NotFound, ValidationError

from catalog.models import AvailabilityStatus
from core.errors import ApiError, ErrorCode
from core.testing.factories import (
    AdminUserFactory,
    CustomerFactory,
    OrderFactory,
    OrderItemFactory,
    ProductFactory,
    StoreFactory,
    StoreOwnerFactory,
)
from orders import services
from orders.models import OrderStatus
from orders.state_machine import TRANSITIONS, Action, Actor, allowed_actions, find_transition
from orders.tests.helpers import place_order
from payments.choices import PaymentStatus


class StateMachineTableTests(TestCase):
    def test_terminal_and_driver_statuses_have_no_way_out(self):
        for status in (
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
            OrderStatus.COMPLETED,
            OrderStatus.ASSIGNED,
            OrderStatus.OUT_FOR_DELIVERY,
        ):
            for actor in Actor:
                with self.subTest(status=status, actor=actor):
                    self.assertEqual(allowed_actions(status, actor), [])

    def test_nothing_leads_to_driver_statuses(self):
        targets = {transition.target for transition in TRANSITIONS}
        self.assertNotIn(OrderStatus.ASSIGNED, targets)
        self.assertNotIn(OrderStatus.OUT_FOR_DELIVERY, targets)

    def test_allowed_actions_per_actor(self):
        self.assertEqual(allowed_actions(OrderStatus.PENDING, Actor.CUSTOMER), ["cancel"])
        self.assertEqual(
            allowed_actions(OrderStatus.PENDING, Actor.STORE_OWNER), ["accept", "reject"]
        )
        self.assertEqual(allowed_actions(OrderStatus.READY, Actor.ADMIN), ["cancel"])
        self.assertEqual(allowed_actions(OrderStatus.ACCEPTED, Actor.CUSTOMER), [])


class TransitionServiceTests(TestCase):
    def setUp(self):
        self.store = StoreFactory()
        self.customer = CustomerFactory()
        self.admin = AdminUserFactory()
        self.users = {
            Actor.CUSTOMER: self.customer.user,
            Actor.STORE_OWNER: self.store.owner.user,
            Actor.ADMIN: self.admin,
        }

    def make_order(self, status):
        order = OrderFactory(customer=self.customer, store=self.store, order_status=status)
        OrderItemFactory(order=order, quantity=2)
        return order

    def test_every_legal_transition(self):
        for transition in TRANSITIONS:
            with self.subTest(
                source=transition.source, action=transition.action, actor=transition.actor
            ):
                order = self.make_order(transition.source)
                reason = "Out of crates" if transition.reason_required else None

                result = services.transition_order(
                    order, transition.action, self.users[transition.actor], reason
                )

                self.assertEqual(result.order_status, transition.target)
                entry = result.status_history.get()
                self.assertEqual(entry.from_status, transition.source)
                self.assertEqual(entry.status, transition.target)
                self.assertEqual(entry.changed_by, self.users[transition.actor])
                self.assertEqual(entry.notes, reason)

    def test_every_illegal_transition_is_rejected(self):
        for status in OrderStatus:
            order = self.make_order(status)
            for action, actor in cartesian(Action, Actor):
                if find_transition(status, action, actor) is not None:
                    continue
                with self.subTest(status=status, action=action, actor=actor):
                    with self.assertRaises(ApiError) as caught:
                        services.transition_order(order, action, self.users[actor], "reason")
                    self.assertEqual(caught.exception.code, ErrorCode.INVALID_TRANSITION)
                    self.assertEqual(caught.exception.status_code, 409)
                    self.assertEqual(
                        caught.exception.details["allowed_actions"],
                        allowed_actions(status, actor),
                    )
            order.refresh_from_db()
            self.assertEqual(order.order_status, status)
            self.assertFalse(order.status_history.exists())

    def test_reason_is_required_where_listed(self):
        for transition in (t for t in TRANSITIONS if t.reason_required):
            with self.subTest(source=transition.source, actor=transition.actor):
                order = self.make_order(transition.source)
                with self.assertRaises(ValidationError) as caught:
                    services.transition_order(
                        order, transition.action, self.users[transition.actor], "   "
                    )
                self.assertIn("reason", caught.exception.detail)
                order.refresh_from_db()
                self.assertEqual(order.order_status, transition.source)

    def test_status_reason_is_saved_for_reject_and_cancel(self):
        order = self.make_order(OrderStatus.PENDING)

        services.transition_order(order, Action.REJECT, self.users[Actor.STORE_OWNER], "Closed")

        order.refresh_from_db()
        self.assertEqual(order.status_reason, "Closed")

    def test_users_who_cannot_see_the_order_get_not_found(self):
        order = self.make_order(OrderStatus.PENDING)
        strangers = (CustomerFactory().user, StoreOwnerFactory().user)

        for user in strangers:
            with self.subTest(role=user.role), self.assertRaises(NotFound):
                services.transition_order(order, Action.CANCEL, user)

    def test_cancel_marks_pending_payment_cancelled(self):
        order = place_order(self.customer, (ProductFactory(store=self.store), 1))

        services.transition_order(order, Action.CANCEL, self.customer.user)

        order.refresh_from_db()
        self.assertEqual(order.payment_status, PaymentStatus.CANCELLED)
        self.assertEqual(order.payments.get().payment_status, PaymentStatus.CANCELLED)


class StockRestoreTests(TestCase):
    def setUp(self):
        self.store = StoreFactory()
        self.customer = CustomerFactory()
        self.cola = ProductFactory(store=self.store, stock_quantity=3, price=Decimal("1500.00"))

    def test_cancel_restores_stock_exactly_once(self):
        order = place_order(self.customer, (self.cola, 3))
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 0)
        self.assertEqual(self.cola.availability_status, AvailabilityStatus.OUT_OF_STOCK)

        services.transition_order(order, Action.CANCEL, self.customer.user)
        with self.assertRaises(ApiError):
            services.transition_order(order, Action.CANCEL, self.customer.user)

        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 3)
        self.assertEqual(self.cola.availability_status, AvailabilityStatus.AVAILABLE)

    def test_reject_restores_stock_exactly_once(self):
        order = place_order(self.customer, (self.cola, 2))
        owner = self.store.owner.user

        services.transition_order(order, Action.REJECT, owner, "No crates")
        with self.assertRaises(ApiError):
            services.transition_order(order, Action.REJECT, owner, "No crates")

        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 3)

    def test_restock_keeps_unavailable_products_hidden(self):
        order = place_order(self.customer, (self.cola, 1))
        self.cola.refresh_from_db()
        self.cola.availability_status = AvailabilityStatus.UNAVAILABLE
        self.cola.save()

        services.transition_order(order, Action.CANCEL, self.customer.user)

        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 3)
        self.assertEqual(self.cola.availability_status, AvailabilityStatus.UNAVAILABLE)

    def test_completed_orders_keep_stock_taken(self):
        order = place_order(self.customer, (self.cola, 2))
        owner = self.store.owner.user
        for action in (Action.ACCEPT, Action.PREPARE, Action.READY, Action.COMPLETE):
            services.transition_order(order, action, owner)

        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock_quantity, 1)
        self.assertEqual(
            list(order.status_history.values_list("status", flat=True)),
            ["PENDING", "ACCEPTED", "PREPARING", "READY", "COMPLETED"],
        )
