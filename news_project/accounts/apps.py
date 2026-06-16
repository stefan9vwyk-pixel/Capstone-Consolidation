from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    # Setup groups and registers tokens on startup.
    def ready(self):
        import accounts.signals
