"""Order status transitions as data.

Every allowed change is one row in TRANSITIONS. Anything not listed is rejected, so
ASSIGNED and OUT_FOR_DELIVERY (driver features, not built yet) cannot be reached.
"""

from dataclasses import dataclass
from enum import StrEnum

from accounts.models import UserRole
from orders.models import OrderStatus


class Actor(StrEnum):
    CUSTOMER = "CUSTOMER"
    STORE_OWNER = "STORE_OWNER"
    ADMIN = "ADMIN"


class Action(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    PREPARE = "prepare"
    READY = "ready"
    COMPLETE = "complete"
    CANCEL = "cancel"


@dataclass(frozen=True)
class Transition:
    source: str
    action: Action
    actor: Actor
    target: str
    reason_required: bool = False


S = OrderStatus
TRANSITIONS = (
    Transition(S.PENDING, Action.ACCEPT, Actor.STORE_OWNER, S.ACCEPTED),
    Transition(S.PENDING, Action.REJECT, Actor.STORE_OWNER, S.REJECTED, reason_required=True),
    Transition(S.PENDING, Action.CANCEL, Actor.CUSTOMER, S.CANCELLED),
    Transition(S.PENDING, Action.CANCEL, Actor.ADMIN, S.CANCELLED, reason_required=True),
    Transition(S.ACCEPTED, Action.PREPARE, Actor.STORE_OWNER, S.PREPARING),
    Transition(S.ACCEPTED, Action.CANCEL, Actor.STORE_OWNER, S.CANCELLED, reason_required=True),
    Transition(S.ACCEPTED, Action.CANCEL, Actor.ADMIN, S.CANCELLED, reason_required=True),
    Transition(S.PREPARING, Action.READY, Actor.STORE_OWNER, S.READY),
    Transition(S.PREPARING, Action.CANCEL, Actor.STORE_OWNER, S.CANCELLED, reason_required=True),
    Transition(S.PREPARING, Action.CANCEL, Actor.ADMIN, S.CANCELLED, reason_required=True),
    Transition(S.READY, Action.COMPLETE, Actor.STORE_OWNER, S.COMPLETED),
    Transition(S.READY, Action.CANCEL, Actor.ADMIN, S.CANCELLED, reason_required=True),
)
del S

TERMINAL_STATUSES = frozenset({OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.COMPLETED})
STOCK_RESTORING_STATUSES = frozenset({OrderStatus.REJECTED, OrderStatus.CANCELLED})

_BY_KEY = {(t.source, t.action, t.actor): t for t in TRANSITIONS}

_ACTOR_BY_ROLE = {
    UserRole.CUSTOMER: Actor.CUSTOMER,
    UserRole.STORE_OWNER: Actor.STORE_OWNER,
    UserRole.ADMIN: Actor.ADMIN,
}


def actor_for(user):
    """The state-machine actor for a user, or None if the role cannot change orders."""
    return _ACTOR_BY_ROLE.get(getattr(user, "role", None))


def find_transition(source, action, actor):
    return _BY_KEY.get((source, action, actor))


def allowed_actions(source, actor):
    """Actions this actor may take from this status, in table order."""
    return [t.action.value for t in TRANSITIONS if t.source == source and t.actor == actor]
