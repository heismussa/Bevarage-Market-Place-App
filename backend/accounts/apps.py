from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "accounts"

    def ready(self):
        from accounts.signals import connect_profile_signal

        connect_profile_signal()
