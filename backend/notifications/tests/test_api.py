from rest_framework import status
from rest_framework.test import APIClient

from core.errors import ErrorCode
from core.testing.api import ApiTestCase
from core.testing.factories import CustomerFactory
from notifications.models import Notification, NotificationType

LIST_URL = "/api/v1/notifications/"
COUNT_URL = "/api/v1/notifications/unread-count/"
READ_ALL_URL = "/api/v1/notifications/read-all/"


def read_url(notification):
    return f"/api/v1/notifications/{notification.pk}/read/"


def notify(user, *, is_read=False, title="Order accepted"):
    return Notification.objects.create(
        user=user,
        notification_type=NotificationType.ORDER_ACCEPTED,
        title=title,
        message="Your order was accepted.",
        is_read=is_read,
    )


class NotificationApiTests(ApiTestCase):
    def setUp(self):
        self.client, self.customer = self.customer_client()
        self.user = self.customer.user
        self.other = CustomerFactory().user
        self.unread = [notify(self.user, title=f"Unread {i}") for i in range(3)]
        self.read = notify(self.user, is_read=True)
        self.others = notify(self.other)

    def test_list_shows_only_my_notifications_newest_first(self):
        with self.assertNumQueries(3):
            response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data["results"]]
        self.assertCountEqual(ids, [n.pk for n in [*self.unread, self.read]])
        self.assertNotIn(self.others.pk, ids)
        self.assertEqual(
            set(response.data["results"][0]),
            {
                "id",
                "notification_type",
                "title",
                "message",
                "is_read",
                "order",
                "order_number",
                "created_at",
            },
        )

    def test_filter_by_is_read(self):
        unread = self.client.get(LIST_URL, {"is_read": "false"})
        read = self.client.get(LIST_URL, {"is_read": "true"})

        self.assertEqual(unread.data["count"], 3)
        self.assertEqual([row["id"] for row in read.data["results"]], [self.read.pk])

    def test_unread_count(self):
        with self.assertNumQueries(2):
            response = self.client.get(COUNT_URL)

        self.assertEqual(response.data, {"unread_count": 3})

    def test_mark_read_is_idempotent(self):
        target = self.unread[0]

        first = self.client.post(read_url(target))
        second = self.client.post(read_url(target))

        for response in (first, second):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data["is_read"])
        self.assertEqual(self.client.get(COUNT_URL).data["unread_count"], 2)

    def test_cannot_read_someone_elses_notification(self):
        self.assertError(
            self.client.post(read_url(self.others)), status.HTTP_404_NOT_FOUND, ErrorCode.NOT_FOUND
        )
        self.others.refresh_from_db()
        self.assertFalse(self.others.is_read)

    def test_read_all_touches_only_mine(self):
        response = self.client.post(READ_ALL_URL)

        self.assertEqual(response.data, {"updated": 3})
        self.assertFalse(Notification.objects.filter(user=self.user, is_read=False).exists())
        self.others.refresh_from_db()
        self.assertFalse(self.others.is_read)

    def test_store_owners_have_notifications_too(self):
        owner_client, owner = self.store_owner_client()
        notify(owner.user)

        self.assertEqual(owner_client.get(COUNT_URL).data, {"unread_count": 1})

    def test_anonymous_is_rejected(self):
        anonymous = APIClient()
        for request in (
            lambda: anonymous.get(LIST_URL),
            lambda: anonymous.get(COUNT_URL),
            lambda: anonymous.post(READ_ALL_URL),
            lambda: anonymous.post(read_url(self.unread[0])),
        ):
            self.assertError(request(), status.HTTP_401_UNAUTHORIZED, ErrorCode.NOT_AUTHENTICATED)
