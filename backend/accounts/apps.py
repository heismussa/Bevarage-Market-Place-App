from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "accounts"

    def ready(self):
        import accounts.schema  # noqa: F401  registers the OpenAPI auth extension
        from accounts.signals import connect_profile_signal

        connect_profile_signal()
